"""
audit_lib.tool_length_range
===========================
Compute a tool's effective amino-acid length range from its extracted training data,
with graceful fallback to the `length_range` declared in pipeline_config.yaml or the
paper/repo documentation.

The positive dataset for a tool MUST be constrained to the length range the tool was
actually trained on, otherwise:
  - sequences shorter than min_train are padded / rejected by the tool (silent bias)
  - sequences longer than max_train are truncated / rejected (false negatives)

Rationale
---------
Each tool has its own training distribution. Running ToxinPred3 (trained on 5-35 aa)
on a dataset containing 40-50 aa peptides measures a generalization regime the tool
was never intended for. By clipping the pool to the tool's training range BEFORE
CD-HIT-2D grading, we measure leakage and performance in the domain the tool claims.

Strategy
--------
1. If training_data/ contains FASTA or CSV with sequence column → compute empirical
   range. Use p1 to p99 (robust to a few outliers) or full min..max (strict).
2. Else fall back to tool_cfg["length_range"] from pipeline_config.yaml.
3. Else default to [5, 50].
"""

from __future__ import annotations

import glob
import logging
import os

import pandas as pd

log = logging.getLogger(__name__)


def _iter_fasta_lengths(fasta_path: str):
    """Yield sequence lengths from a FASTA file."""
    seq = []
    with open(fasta_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if seq:
                    yield len("".join(seq))
                seq = []
            else:
                seq.append(line)
        if seq:
            yield len("".join(seq))


def _find_sequence_column(df: pd.DataFrame, hints=None):
    """Locate the sequence column in a DataFrame using hints."""
    if hints is None:
        hints = ("sequence", "seq", "peptide", "aa_sequence")
    low_map = {c.lower(): c for c in df.columns}
    for h in hints:
        if h in low_map:
            return low_map[h]
    # heuristic: find column with mostly uppercase alpha strings of length 4-200
    for col in df.columns:
        try:
            sample = df[col].dropna().astype(str).head(20)
            if sample.empty:
                continue
            hits = sum(1 for v in sample if v.isalpha() and 3 <= len(v) <= 200 and v.isupper())
            if hits >= max(5, int(0.6 * len(sample))):
                return col
        except Exception:
            continue
    return None


def collect_training_lengths(training_dir: str, sequence_column_hints=None) -> list[int]:
    """
    Walk a training data directory and return all sequence lengths found in
    FASTA (.fasta, .fa) or CSV (.csv, .tsv) files.
    """
    if not os.path.isdir(training_dir):
        return []

    lengths: list[int] = []

    # FASTA files
    for ext in ("*.fasta", "*.fa"):
        for path in glob.glob(os.path.join(training_dir, "**", ext), recursive=True):
            try:
                lengths.extend(list(_iter_fasta_lengths(path)))
            except Exception as e:
                log.warning("  [length_range] Failed reading FASTA %s: %s", path, e)

    # CSV / TSV files
    for ext in ("*.csv", "*.tsv"):
        for path in glob.glob(os.path.join(training_dir, "**", ext), recursive=True):
            try:
                sep = "\t" if path.endswith(".tsv") else ","
                df = pd.read_csv(path, sep=sep)
                col = _find_sequence_column(df, hints=sequence_column_hints)
                if col:
                    col_lens = df[col].dropna().astype(str).str.len().tolist()
                    lengths.extend([int(x) for x in col_lens if x > 0])
            except Exception as e:
                log.warning("  [length_range] Failed reading CSV %s: %s", path, e)

    return lengths


def compute_tool_length_range(
    tool_id: str,
    tool_cfg: dict,
    training_dir: str | None = None,
    mode: str = "robust",
    hard_min: int = 5,
    hard_max: int = 100,
) -> tuple[int, int]:
    """
    Return (min_len, max_len) for a tool.

    Parameters
    ----------
    tool_id : str
    tool_cfg : dict
        Tool config dict from pipeline_config.yaml (may contain "length_range").
    training_dir : str | None
        Path to Tool_Audits/{tool_id}/training_data/. If present and non-empty,
        empirical range is computed.
    mode : str
        "strict"   → use full min..max observed (no outlier trimming)
        "robust"   → use floor(p1) .. ceil(p99) (default, recommended)
        "config"   → skip empirical, use tool_cfg["length_range"] directly
    hard_min, hard_max : int
        Absolute clamps. Never return outside [hard_min, hard_max].

    Returns (min_len, max_len, source) where source is one of:
        "empirical_strict", "empirical_robust", "config_length_range", "default"
    """
    import math

    src_tag = ""
    lo = hi = None

    if mode != "config" and training_dir and os.path.isdir(training_dir):
        hints = (
            tool_cfg.get("training_data", {}).get("sequence_column_hints")
            if isinstance(tool_cfg, dict)
            else None
        )
        lengths = collect_training_lengths(training_dir, sequence_column_hints=hints)
        lengths = [L for L in lengths if L >= 2]  # ignore malformed
        if lengths:
            s = pd.Series(lengths)
            if mode == "strict":
                lo, hi = int(s.min()), int(s.max())
                src_tag = "empirical_strict"
            else:
                lo = int(math.floor(s.quantile(0.01)))
                hi = int(math.ceil(s.quantile(0.99)))
                src_tag = "empirical_robust"
            log.info(
                "  [length_range] %s: empirical n=%d min=%d max=%d p1=%d p99=%d -> using (%d, %d) [%s]",
                tool_id, len(lengths), int(s.min()), int(s.max()),
                int(s.quantile(0.01)), int(s.quantile(0.99)), lo, hi, src_tag,
            )

    if lo is None or hi is None:
        # Fall back to config
        rng = None
        if isinstance(tool_cfg, dict):
            rng = tool_cfg.get("length_range")
        if rng and isinstance(rng, (list, tuple)) and len(rng) == 2:
            lo, hi = int(rng[0]), int(rng[1])
            src_tag = "config_length_range"
            log.info(
                "  [length_range] %s: no training data found — using config length_range=(%d, %d)",
                tool_id, lo, hi,
            )
        else:
            lo, hi = hard_min, hard_max
            src_tag = "default"
            log.warning(
                "  [length_range] %s: no training data and no length_range in config — using default (%d, %d)",
                tool_id, lo, hi,
            )

    # Sanity clamps
    lo = max(lo, hard_min)
    hi = min(hi, hard_max)
    if lo >= hi:
        log.warning("  [length_range] %s: degenerate range lo=%d >= hi=%d, resetting to defaults",
                    tool_id, lo, hi)
        lo, hi = hard_min, hard_max

    return lo, hi, src_tag


def filter_pool_by_length(
    pool_df: pd.DataFrame,
    min_len: int,
    max_len: int,
    seq_col: str = "Sequence",
    len_col: str | None = "Length",
) -> pd.DataFrame:
    """
    Return a subset of pool_df whose peptides have length in [min_len, max_len].
    Uses len_col if present, otherwise recomputes from seq_col.
    """
    if pool_df.empty:
        return pool_df.copy()
    if len_col and len_col in pool_df.columns:
        lens = pool_df[len_col].astype(int)
    else:
        lens = pool_df[seq_col].astype(str).str.len()
    mask = (lens >= min_len) & (lens <= max_len)
    return pool_df[mask].reset_index(drop=True)
