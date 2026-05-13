"""
demo/api/limits.py — input validation and per-IP / global rate limiting.

The backend's only safety net. The frontend may also validate, but
this module is the source of truth and must reject anything that
violates the contract.

Configuration is loaded from environment variables (see `.env.example`)
so the operator can dial limits without touching code:

    MAX_PEPTIDES_PER_JOB     default 50
    MIN_PEPTIDE_LEN          default 5
    MAX_PEPTIDE_LEN          default 100
    JOBS_PER_IP_PER_HOUR     default 3
    DAILY_GLOBAL_JOB_CAP     default 200
    ALLOWED_TOOLS            comma-separated, default = all 10 active

All counters are in-memory. Restarting the backend resets them. For a
single-host demo that is acceptable; if abuse becomes an issue, swap
the dict for Redis without changing the public interface.
"""
from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")

DEFAULT_TOOLS = (
    "toxinpred3", "antibp3", "hemopi2", "hemodl", "deepb3p",
    "deepbp", "apex", "perseucpp", "acp_dpe", "bertaip",
)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_tools(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(name)
    if not raw:
        return default
    items = tuple(t.strip() for t in raw.split(",") if t.strip())
    return items or default


@dataclass
class Limits:
    max_peptides_per_job: int = field(default_factory=lambda: _env_int("MAX_PEPTIDES_PER_JOB", 50))
    min_peptide_len: int = field(default_factory=lambda: _env_int("MIN_PEPTIDE_LEN", 5))
    max_peptide_len: int = field(default_factory=lambda: _env_int("MAX_PEPTIDE_LEN", 100))
    jobs_per_ip_per_hour: int = field(default_factory=lambda: _env_int("JOBS_PER_IP_PER_HOUR", 3))
    daily_global_cap: int = field(default_factory=lambda: _env_int("DAILY_GLOBAL_JOB_CAP", 200))
    allowed_tools: tuple[str, ...] = field(default_factory=lambda: _env_tools("ALLOWED_TOOLS", DEFAULT_TOOLS))


LIMITS = Limits()


# ----------------------------------------------------------------------------
# Input validation
# ----------------------------------------------------------------------------

class ValidationError(ValueError):
    """Raised when user input violates the demo contract."""


_HEADER_SAFE = re.compile(r"[^A-Za-z0-9_.:|/\-]+")


def parse_input_to_fasta(text: str) -> str:
    """Turn raw user text into a clean FASTA string.

    Accepts either:
      - FASTA already (lines starting with '>'),
      - plain peptides one per line (we synthesize headers).

    Returns a FASTA string; raises ValidationError on any contract
    breach (count, length, alphabet).
    """
    if text is None or not text.strip():
        raise ValidationError("Empty input. Paste up to "
                              f"{LIMITS.max_peptides_per_job} peptides or a FASTA.")

    lines = [ln.rstrip() for ln in text.splitlines()]
    if any(ln.startswith(">") for ln in lines):
        pairs = _parse_fasta_lines(lines)
    else:
        pairs = _parse_plain_lines(lines)

    if not pairs:
        raise ValidationError("No peptides found in input.")
    if len(pairs) > LIMITS.max_peptides_per_job:
        raise ValidationError(
            f"Too many peptides ({len(pairs)}). The public demo accepts at "
            f"most {LIMITS.max_peptides_per_job} per submission."
        )

    cleaned: list[tuple[str, str]] = []
    seen_headers: set[str] = set()
    for idx, (hdr, seq) in enumerate(pairs, start=1):
        seq_u = seq.upper()
        if not seq_u:
            raise ValidationError(f"Sequence #{idx} ({hdr!r}) is empty.")
        if not (LIMITS.min_peptide_len <= len(seq_u) <= LIMITS.max_peptide_len):
            raise ValidationError(
                f"Sequence #{idx} ({hdr!r}) has length {len(seq_u)}. "
                f"Allowed range: {LIMITS.min_peptide_len}–{LIMITS.max_peptide_len}."
            )
        bad = sorted(set(seq_u) - STANDARD_AA)
        if bad:
            raise ValidationError(
                f"Sequence #{idx} ({hdr!r}) contains non-standard residues: "
                f"{''.join(bad)}. The demo accepts only ACDEFGHIKLMNPQRSTVWY."
            )
        safe_hdr = _HEADER_SAFE.sub("_", hdr).strip("_") or f"seq{idx}"
        if safe_hdr in seen_headers:
            safe_hdr = f"{safe_hdr}_{idx}"
        seen_headers.add(safe_hdr)
        cleaned.append((safe_hdr, seq_u))

    return "\n".join(f">{h}\n{s}" for h, s in cleaned) + "\n"


def _parse_fasta_lines(lines: Iterable[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    cur_hdr: str | None = None
    cur_seq: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if cur_hdr is not None:
                pairs.append((cur_hdr, "".join(cur_seq)))
            cur_hdr = line[1:].split()[0] or f"seq{len(pairs) + 1}"
            cur_seq = []
        else:
            cur_seq.append(line)
    if cur_hdr is not None:
        pairs.append((cur_hdr, "".join(cur_seq)))
    return pairs


def _parse_plain_lines(lines: Iterable[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        pairs.append((f"seq{len(pairs) + 1}", line))
    return pairs


def validate_tools(tools: Iterable[str]) -> list[str]:
    """Filter requested tools against the operator allow-list."""
    requested = [t.strip() for t in tools if t and t.strip()]
    if not requested:
        return list(LIMITS.allowed_tools)
    bad = [t for t in requested if t not in LIMITS.allowed_tools]
    if bad:
        raise ValidationError(
            f"Tools not enabled on this demo: {', '.join(bad)}. "
            f"Allowed: {', '.join(LIMITS.allowed_tools)}."
        )
    return requested


# ----------------------------------------------------------------------------
# Rate limiting (per-IP and global)
# ----------------------------------------------------------------------------

class RateLimitError(RuntimeError):
    """Raised when an IP exceeded its quota or the global daily cap."""


@dataclass
class _Counter:
    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """In-memory rate limiter.

    Two windows:
      - per-IP: sliding 1-hour window, max `jobs_per_ip_per_hour` events.
      - global: rolling 24-hour window, max `daily_global_cap` events.

    Thread-safe. Both windows are pruned on each `acquire()`; the
    daily window doubles as a global counter.
    """

    def __init__(self, limits: Limits = LIMITS):
        self._limits = limits
        self._per_ip: dict[str, _Counter] = {}
        self._global: _Counter = _Counter()
        self._lock = threading.Lock()

    def acquire(self, ip: str) -> None:
        """Record one job for `ip`. Raises RateLimitError if over quota."""
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400

        with self._lock:
            self._global.timestamps = [t for t in self._global.timestamps if t > day_ago]
            if len(self._global.timestamps) >= self._limits.daily_global_cap:
                raise RateLimitError(
                    "The demo has reached its daily job cap "
                    f"({self._limits.daily_global_cap}). Please try again tomorrow."
                )

            ctr = self._per_ip.setdefault(ip, _Counter())
            ctr.timestamps = [t for t in ctr.timestamps if t > hour_ago]
            if len(ctr.timestamps) >= self._limits.jobs_per_ip_per_hour:
                wait_minutes = int((ctr.timestamps[0] + 3600 - now) / 60) + 1
                raise RateLimitError(
                    "Too many submissions from your IP "
                    f"({self._limits.jobs_per_ip_per_hour}/hour). "
                    f"Retry in ~{wait_minutes} min."
                )

            ctr.timestamps.append(now)
            self._global.timestamps.append(now)

    def snapshot(self) -> dict:
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        with self._lock:
            day_count = sum(1 for t in self._global.timestamps if t > day_ago)
            active_ips = sum(
                1 for ctr in self._per_ip.values()
                if any(t > hour_ago for t in ctr.timestamps)
            )
        return {
            "jobs_last_24h": day_count,
            "daily_cap": self._limits.daily_global_cap,
            "active_ips_last_hour": active_ips,
        }
