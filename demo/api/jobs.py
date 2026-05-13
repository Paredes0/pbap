"""
demo/api/jobs.py — FIFO job queue with a single worker thread.

N=1 worker is deliberate: every tool in the pipeline runs in its own
subprocess and several load PLM weights (ESM-2, ProtT5) that occupy
2–4 GB of VRAM each. Running two pipelines in parallel on a single
GPU is asking for OOM. If the operator has dedicated hardware with
headroom, bumping WORKER_COUNT is mechanical (see comment below).

Lifecycle:
    PENDING → RUNNING → DONE / FAILED / TIMEOUT
    PENDING → CANCELLED (only while still in the queue)

State is in-memory; restarting the backend forgets all jobs and
input FASTAs. This is intentional for a non-commercial demo — no
PII is persisted by design.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from runner import (
    RunResult,
    cleanup_job,
    new_job_id,
    prepare_job_dir,
    run_pipeline,
)


logger = logging.getLogger("pbap.demo.jobs")


JOB_STATUSES = ("PENDING", "RUNNING", "DONE", "FAILED", "TIMEOUT", "CANCELLED")


@dataclass
class Job:
    job_id: str
    submitted_ip: str
    submitted_at: float
    tools: list[str]
    n_peptides: int
    status: str = "PENDING"
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    queue_position: Optional[int] = None
    result: Optional[RunResult] = None
    error: Optional[str] = None
    fasta_path: Optional[str] = field(default=None, repr=False)


class JobManager:
    """In-memory FIFO queue with a single worker thread.

    Public API: submit, get, cancel, snapshot. All thread-safe.

    To raise concurrency, instantiate with worker_count > 1 — but
    only after confirming the host has enough VRAM for two PLM tools
    to coexist (see jobs.py module docstring).
    """

    def __init__(self, worker_count: int = 1):
        if worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        self._jobs: dict[str, Job] = {}
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._workers: list[threading.Thread] = []
        for i in range(worker_count):
            t = threading.Thread(target=self._worker_loop, name=f"pbap-worker-{i}",
                                 daemon=True)
            t.start()
            self._workers.append(t)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def submit(self, ip: str, fasta_text: str, tools: list[str], n_peptides: int) -> Job:
        job_id = new_job_id()
        _, fasta_path = prepare_job_dir(job_id, fasta_text)
        job = Job(
            job_id=job_id, submitted_ip=ip, submitted_at=time.time(),
            tools=list(tools), n_peptides=n_peptides,
            fasta_path=str(fasta_path),
        )
        with self._lock:
            self._jobs[job_id] = job
            self._recompute_positions_unlocked()
        self._queue.put(job_id)
        logger.info("job_submitted id=%s ip=%s n_pep=%d tools=%s",
                    job_id, ip, n_peptides, ",".join(tools))
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == "PENDING":
                self._recompute_positions_unlocked()
            return job

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status != "PENDING":
                return False
            job.status = "CANCELLED"
            job.finished_at = time.time()
            self._recompute_positions_unlocked()
            return True

    def snapshot(self) -> dict:
        with self._lock:
            pending = sum(1 for j in self._jobs.values() if j.status == "PENDING")
            running = sum(1 for j in self._jobs.values() if j.status == "RUNNING")
            done = sum(1 for j in self._jobs.values() if j.status == "DONE")
            failed = sum(1 for j in self._jobs.values() if j.status in ("FAILED", "TIMEOUT"))
        return {
            "pending": pending, "running": running,
            "done": done, "failed_or_timeout": failed,
            "total_known": len(self._jobs),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _recompute_positions_unlocked(self) -> None:
        position = 0
        for jid in list(self._queue.queue):
            job = self._jobs.get(jid)
            if job and job.status == "PENDING":
                position += 1
                job.queue_position = position

    def _worker_loop(self) -> None:
        while True:
            try:
                job_id = self._queue.get()
            except Exception:
                continue
            try:
                self._run_one(job_id)
            except Exception as exc:
                logger.exception("worker_error job=%s err=%s", job_id, exc)
            finally:
                self._queue.task_done()

    def _run_one(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status == "CANCELLED":
                return
            job.status = "RUNNING"
            job.started_at = time.time()
            job.queue_position = 0

        from pathlib import Path
        fasta_path = Path(job.fasta_path) if job.fasta_path else None
        if fasta_path is None or not fasta_path.exists():
            with self._lock:
                job.status = "FAILED"
                job.finished_at = time.time()
                job.error = "Job's input FASTA disappeared before execution."
            return

        result = run_pipeline(job_id, fasta_path, job.tools)

        with self._lock:
            job.result = result
            job.finished_at = time.time()
            if result.status == "OK":
                job.status = "DONE"
            elif result.status == "TIMEOUT":
                job.status = "TIMEOUT"
                job.error = result.error
            else:
                job.status = "FAILED"
                job.error = result.error
            self._recompute_positions_unlocked()
        logger.info("job_finished id=%s status=%s runtime=%.1fs",
                    job_id, job.status, result.runtime_seconds)

    def janitor_prune(self, max_age_seconds: int = 86400) -> int:
        """Drop finished jobs older than `max_age_seconds` and rm their dirs."""
        now = time.time()
        removed = 0
        with self._lock:
            stale = [
                jid for jid, j in self._jobs.items()
                if j.status in ("DONE", "FAILED", "TIMEOUT", "CANCELLED")
                and j.finished_at is not None
                and (now - j.finished_at) > max_age_seconds
            ]
            for jid in stale:
                self._jobs.pop(jid, None)
                cleanup_job(jid)
                removed += 1
        if removed:
            logger.info("janitor_pruned %d stale jobs", removed)
        return removed
