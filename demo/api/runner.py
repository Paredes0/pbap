"""
demo/api/runner.py — subprocess wrapper around `scripts/run_audit.py`.

Runs ONE job and returns paths to the artifacts the API will serve.
This module is deliberately thin: it does not parse predictions, does
not enforce limits, does not retry. Validation lives in `limits.py`;
parsing is the orchestrator's job.

Configuration (via env, see `.env.example`):

    PBAP_REPO_ROOT       absolute path to the cloned pbap repo
                         (default: parent of demo/)
    PBAP_RUN_ENV         micromamba env that has the orchestrator's
                         5 deps (pandas, numpy, pyyaml, openpyxl,
                         requests). Default: "ml"
    PBAP_RUN_TIMEOUT     hard kill after this many seconds. Default 600.
    PBAP_JOBS_DIR        where to materialize per-job inputs/outputs.
                         Default: <repo>/demo/api/jobs_data
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


REPO_ROOT = Path(_env("PBAP_REPO_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
RUN_ENV = _env("PBAP_RUN_ENV", "ml")
RUN_TIMEOUT = int(_env("PBAP_RUN_TIMEOUT", "600"))
JOBS_DIR = Path(_env("PBAP_JOBS_DIR", str(REPO_ROOT / "demo" / "api" / "jobs_data"))).resolve()


@dataclass
class RunResult:
    job_id: str
    status: str
    runtime_seconds: float
    output_dir: Optional[Path]
    report_html: Optional[Path]
    consolidated_csv: Optional[Path]
    consolidated_json: Optional[Path]
    health_json: Optional[Path]
    error: Optional[str]


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def prepare_job_dir(job_id: str, fasta_text: str) -> tuple[Path, Path]:
    """Create the job's working directory and write its input FASTA."""
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    fasta_path = job_dir / "input.fasta"
    fasta_path.write_text(fasta_text, encoding="utf-8")
    return job_dir, fasta_path


def run_pipeline(job_id: str, fasta_path: Path, tools: list[str]) -> RunResult:
    """Invoke the orchestrator and classify the outcome.

    Returns a RunResult regardless of success — callers should check
    `.status` ('OK' | 'TIMEOUT' | 'ERROR').
    """
    job_dir = fasta_path.parent
    output_dir = job_dir / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "run.log"

    cmd = [
        "micromamba", "run", "-n", RUN_ENV,
        "python", str(REPO_ROOT / "scripts" / "run_audit.py"),
        "--input", str(fasta_path),
        "--output", str(output_dir),
        "--tools", ",".join(tools) if tools else "all",
    ]

    t0 = time.monotonic()
    try:
        completed = subprocess.run(
            cmd, cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(_format_log(exc.stdout, exc.stderr), encoding="utf-8")
        return RunResult(
            job_id=job_id, status="TIMEOUT",
            runtime_seconds=time.monotonic() - t0,
            output_dir=output_dir, report_html=None,
            consolidated_csv=None, consolidated_json=None, health_json=None,
            error=f"Job exceeded the {RUN_TIMEOUT}s time limit.",
        )
    except FileNotFoundError as exc:
        return RunResult(
            job_id=job_id, status="ERROR",
            runtime_seconds=time.monotonic() - t0,
            output_dir=None, report_html=None,
            consolidated_csv=None, consolidated_json=None, health_json=None,
            error=f"Launcher missing: {exc}. Is micromamba on PATH?",
        )

    runtime = time.monotonic() - t0
    log_path.write_text(_format_log(completed.stdout, completed.stderr), encoding="utf-8")

    if completed.returncode != 0:
        tail = _tail(completed.stderr)
        return RunResult(
            job_id=job_id, status="ERROR", runtime_seconds=runtime,
            output_dir=output_dir, report_html=None,
            consolidated_csv=None, consolidated_json=None, health_json=None,
            error=f"Orchestrator exited with code {completed.returncode}. "
                  f"Tail: {tail[-400:]}",
        )

    report_html = output_dir / "REPORT.html"
    consolidated_csv = output_dir / "consolidated.csv"
    consolidated_json = output_dir / "consolidated.json"
    health_json = output_dir / "tool_health_report.json"

    if not report_html.exists() or not consolidated_csv.exists():
        return RunResult(
            job_id=job_id, status="ERROR", runtime_seconds=runtime,
            output_dir=output_dir, report_html=None,
            consolidated_csv=None, consolidated_json=None, health_json=None,
            error="Orchestrator completed but expected output files are missing.",
        )

    return RunResult(
        job_id=job_id, status="OK", runtime_seconds=runtime,
        output_dir=output_dir, report_html=report_html,
        consolidated_csv=consolidated_csv,
        consolidated_json=consolidated_json if consolidated_json.exists() else None,
        health_json=health_json if health_json.exists() else None,
        error=None,
    )


def cleanup_job(job_id: str) -> None:
    """Remove the job's working directory. Idempotent."""
    job_dir = JOBS_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


def _format_log(stdout: str | None, stderr: str | None) -> str:
    parts = ["=== STDOUT ===\n", stdout or "", "\n=== STDERR ===\n", stderr or ""]
    return "".join(parts)


def _tail(text: str | None, lines: int = 40) -> str:
    if not text:
        return ""
    return "\n".join(text.rstrip("\n").split("\n")[-lines:])
