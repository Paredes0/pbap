"""
demo/api/server.py — FastAPI backend for the public PBAP demo.

Endpoints:
    POST   /submit          submit a job (sequences + optional tool list)
    GET    /status/{id}     poll job state and queue position
    GET    /result/{id}     fetch artifacts of a finished job (csv/html/json)
    GET    /health          liveness + queue + rate snapshot
    GET    /                landing page (operator-friendly, not user-facing)

Design notes:
  - Stateless across restarts (jobs live in memory). This is desired:
    no PII persists, ever.
  - Trusts the X-Forwarded-For header for client IP, expected from the
    Cloudflare Tunnel ingress. If you're not behind a trusted proxy,
    flip TRUST_PROXY_HEADERS off in the env.
  - CORS is open by default because the frontend is a Hugging Face
    Space served from a different domain. Lock it down in production
    via ALLOWED_ORIGINS.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from jobs import JobManager
from limits import (
    LIMITS, RateLimitError, RateLimiter, ValidationError,
    parse_input_to_fasta, validate_tools,
)


# ----------------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------------

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("pbap.demo.server")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


TRUST_PROXY_HEADERS = _env_bool("TRUST_PROXY_HEADERS", True)

# CORS: by default the backend rejects cross-origin requests outright. The
# operator MUST set ALLOWED_ORIGINS to the public Space domain (or to "*"
# explicitly, accepting the trade-off) before the demo is reachable from a
# browser. Refusing to default to "*" forces a conscious decision and
# avoids the common footgun where a forgotten env var leaves the API
# wide open.
_RAW_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()] or []

WORKER_COUNT = int(os.environ.get("WORKER_COUNT", "1"))
JANITOR_INTERVAL_SECONDS = int(os.environ.get("JANITOR_INTERVAL_SECONDS", "3600"))
JANITOR_JOB_TTL_SECONDS = int(os.environ.get("JANITOR_JOB_TTL_SECONDS", "86400"))

# Comma-separated list of /CIDR or exact IPs that are allowed to populate
# the X-Forwarded-For chain. Cloudflare Tunnel terminates on 127.0.0.1
# from the uvicorn process's perspective, so the safe default is to
# trust only loopback. Operators behind a different proxy must extend
# this list explicitly.
_RAW_TRUSTED = os.environ.get("TRUSTED_PROXY_HOSTS", "127.0.0.1,::1")
TRUSTED_PROXY_HOSTS = {h.strip() for h in _RAW_TRUSTED.split(",") if h.strip()}

app = FastAPI(
    title="PBAP demo API",
    description=(
        "Backend for the free non-commercial PBAP demo. "
        "See https://github.com/Paredes0/pbap for the full pipeline."
    ),
    version="0.1.0",
)
if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    logger.warning(
        "ALLOWED_ORIGINS is empty; CORS middleware NOT installed. "
        "Set ALLOWED_ORIGINS to the public Space domain (or '*' to explicitly "
        "accept the risk) in demo/api/.env before exposing the demo."
    )

jobs = JobManager(worker_count=WORKER_COUNT)
rate_limiter = RateLimiter()


def _client_ip(request: Request) -> str:
    """Return the IP we'll use for rate-limiting.

    The X-Forwarded-For chain looks like `client, proxy1, proxy2, …` where
    each proxy appends its predecessor's source IP. The trustworthy IP is
    the **last** one set by a proxy we control — so we walk the chain
    from the right and keep the first entry whose immediate hop is in
    TRUSTED_PROXY_HOSTS. This is the standard mitigation against header
    spoofing (an attacker can put anything in the leftmost field but
    cannot forge the chain past a trusted proxy).
    """
    immediate_hop = request.client.host if request.client else "unknown"
    if not TRUST_PROXY_HEADERS or immediate_hop not in TRUSTED_PROXY_HOSTS:
        return immediate_hop

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        chain = [p.strip() for p in forwarded.split(",") if p.strip()]
        if chain:
            # Walk right-to-left: the rightmost untrusted IP is the real client.
            for ip in reversed(chain):
                if ip not in TRUSTED_PROXY_HOSTS:
                    return ip
    real = request.headers.get("X-Real-IP")
    if real:
        return real.strip()
    return immediate_hop


# ----------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------

class SubmitRequest(BaseModel):
    text: str = Field(..., description="FASTA or one peptide per line.")
    tools: list[str] = Field(default_factory=list,
                             description="Subset of allowed tool IDs. Empty = all.")


class SubmitResponse(BaseModel):
    job_id: str
    status: str
    queue_position: int | None
    n_peptides: int
    tools: list[str]


class StatusResponse(BaseModel):
    job_id: str
    status: str
    queue_position: int | None
    submitted_at: float
    started_at: float | None
    finished_at: float | None
    runtime_seconds: float | None
    error: str | None


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------

@app.get("/", response_class=PlainTextResponse)
def index() -> str:
    return (
        "PBAP demo backend — see /health for status and /docs for the OpenAPI UI.\n"
        "Source code and license: https://github.com/Paredes0/pbap\n"
        "Contact: noeparedesalf@gmail.com\n"
    )


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "limits": {
            "max_peptides_per_job": LIMITS.max_peptides_per_job,
            "min_peptide_len": LIMITS.min_peptide_len,
            "max_peptide_len": LIMITS.max_peptide_len,
            "jobs_per_ip_per_hour": LIMITS.jobs_per_ip_per_hour,
            "daily_global_cap": LIMITS.daily_global_cap,
            "allowed_tools": list(LIMITS.allowed_tools),
        },
        "queue": jobs.snapshot(),
        "rate": rate_limiter.snapshot(),
        "uptime_seconds": int(time.monotonic() - _START_TIME),
    }


@app.post("/submit", response_model=SubmitResponse)
def submit(payload: SubmitRequest, request: Request) -> SubmitResponse:
    ip = _client_ip(request)

    try:
        tools = validate_tools(payload.tools)
        fasta_text = parse_input_to_fasta(payload.text)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        rate_limiter.acquire(ip)
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    n_peptides = sum(1 for ln in fasta_text.splitlines() if ln.startswith(">"))
    job = jobs.submit(ip=ip, fasta_text=fasta_text, tools=tools, n_peptides=n_peptides)
    return SubmitResponse(
        job_id=job.job_id, status=job.status,
        queue_position=job.queue_position,
        n_peptides=job.n_peptides, tools=job.tools,
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
def status(job_id: str) -> StatusResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id.")
    runtime = None
    if job.started_at and job.finished_at:
        runtime = job.finished_at - job.started_at
    return StatusResponse(
        job_id=job.job_id, status=job.status,
        queue_position=job.queue_position,
        submitted_at=job.submitted_at,
        started_at=job.started_at, finished_at=job.finished_at,
        runtime_seconds=runtime, error=job.error,
    )


@app.get("/result/{job_id}/{kind}")
def result(job_id: str, kind: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id.")
    if job.status != "DONE" or job.result is None:
        raise HTTPException(
            status_code=409,
            detail=f"Job is {job.status.lower()}, no artifacts available.",
        )

    artifact_map = {
        "report": (job.result.report_html, "text/html"),
        "csv": (job.result.consolidated_csv, "text/csv"),
        "json": (job.result.consolidated_json, "application/json"),
        "health": (job.result.health_json, "application/json"),
    }
    if kind not in artifact_map:
        raise HTTPException(status_code=400, detail=f"Unknown artifact {kind!r}.")
    path, media_type = artifact_map[kind]
    if path is None or not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"Artifact {kind!r} not produced.")
    filename_map = {
        "report": "REPORT.html",
        "csv": "consolidated.csv",
        "json": "consolidated.json",
        "health": "tool_health_report.json",
    }
    return FileResponse(path, media_type=media_type, filename=filename_map[kind])


@app.post("/cancel/{job_id}")
def cancel(job_id: str) -> dict:
    ok = jobs.cancel(job_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail="Job is not pending and cannot be cancelled.",
        )
    return {"job_id": job_id, "status": "CANCELLED"}


@app.exception_handler(404)
def _not_found(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found.", "see": "/docs"},
    )


# ----------------------------------------------------------------------------
# Janitor (prune finished jobs)
# ----------------------------------------------------------------------------

_START_TIME = time.monotonic()


def _janitor_loop():
    while True:
        time.sleep(JANITOR_INTERVAL_SECONDS)
        try:
            jobs.janitor_prune(max_age_seconds=JANITOR_JOB_TTL_SECONDS)
        except Exception:
            logger.exception("janitor_error")


_janitor_thread = threading.Thread(target=_janitor_loop, name="pbap-janitor", daemon=True)
_janitor_thread.start()
