#!/usr/bin/env python3
"""
cdhit_leakage_analysis.py
=========================
Runs CD-HIT-2D to quantify data leakage between the validation/test pool
and each tool's training dataset at three identity thresholds (40 %, 60 %, 80 %).

Graduated confidence system:
  - Gold:   Survives all thresholds (40 %, 60 %, 80 %) - no leakage
  - Silver: Survives 60 % and 80 % but not 40 % - minor similarity
  - Bronze: Survives 80 % only - moderate similarity
  - Red:    Fails 80 % - high similarity / likely leakage

Called by audit_pipeline.sh:
    python cdhit_leakage_analysis.py \\
        --tool TOOL_ID \\
        --config pipeline_config.yaml \\
        --test-fasta pool.fasta \\
        --training-fasta training.fasta \\
        --output-dir leakage_report/
"""

import argparse
import csv
import json
import logging
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone

# -- audit_lib imports --------------------------------------------------------
from audit_lib.config import load_pipeline_config, get_tool_config
from audit_lib.cdhit_utils import run_cdhit2d, classify_leakage_grades, parse_fasta_ids
from audit_lib.tool_length_range import compute_tool_length_range
from audit_lib.provenance import generate_provenance

# -- Constants ----------------------------------------------------------------

SCRIPT_NAME = "cdhit_leakage_analysis.py"
SCRIPT_VERSION = "2.0.0"
DEFAULT_THRESHOLDS = [0.40, 0.60, 0.80]

# -- Logging ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# =============================================================================
# Helpers
# =============================================================================


def _filter_fasta(input_fasta, output_fasta, keep_ids):
    """Write a FASTA containing only sequences whose ID is in *keep_ids*."""
    writing = False
    with open(input_fasta, "r") as fin, open(output_fasta, "w") as fout:
        for line in fin:
            if line.startswith(">"):
                seq_id = line.strip().lstrip(">").split()[0]
                writing = seq_id in keep_ids
            if writing:
                fout.write(line)


def _count_fasta_sequences(fasta_path):
    """Count sequences in a FASTA file."""
    count = 0
    with open(fasta_path, "r") as f:
        for line in f:
            if line.startswith(">"):
                count += 1
    return count


# =============================================================================
# Core pipeline
# =============================================================================




def _read_fasta_lengths(fasta_path: str) -> dict:
    """Return {header_id: length} from a FASTA file (header_id = first whitespace-delimited token)."""
    lens = {}
    cur_header = None
    cur_len = 0
    with open(fasta_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if cur_header is not None:
                    lens[cur_header] = cur_len
                cur_header = line[1:].split()[0]
                cur_len = 0
            elif cur_header is not None:
                cur_len += len(line.strip())
        if cur_header is not None:
            lens[cur_header] = cur_len
    return lens


def _classify_length_status(length: int, min_len: int, max_len: int) -> str:
    """Return one of: within_range | too_short | too_long."""
    if length < min_len:
        return "too_short"
    if length > max_len:
        return "too_long"
    return "within_range"


def run_leakage_analysis(tool_id, pipeline_config, test_fasta, training_fasta,
                         output_dir):
    """
    Run CD-HIT-2D at 3 thresholds, classify sequences, and export results.

    Returns a dict with status, summary, and output paths.
    """
    # -- 1. Load config and resolve parameters --------------------------------
    cfg = load_pipeline_config(pipeline_config)
    tool_cfg = get_tool_config(tool_id, cfg)

    thresholds = cfg["global"].get("cdhit_thresholds", DEFAULT_THRESHOLDS)
    ssh_cfg = cfg.get("ssh", {})
    ssh_host = ssh_cfg.get("linux_host", None)
    ssh_user = ssh_cfg.get("linux_user", None)
    cdhit_binary = ssh_cfg.get("cdhit_binary", None)
    sshfs_mount = ssh_cfg.get("sshfs_mount_windows", None)
    linux_base = ssh_cfg.get("linux_base_path", None)

    os.makedirs(output_dir, exist_ok=True)

    # -- 1b. Compute per-tool training length range and tag test peptides ----
    training_dir = os.path.dirname(os.path.abspath(training_fasta))
    len_mode = cfg.get("global", {}).get("length_range_mode", "robust")
    min_len_tool, max_len_tool, rng_src = compute_tool_length_range(
        tool_id=tool_id,
        tool_cfg=tool_cfg,
        training_dir=training_dir,
        mode=len_mode,
    )
    log.info("  Tool training length range: [%d, %d] (source=%s, mode=%s)",
             min_len_tool, max_len_tool, rng_src, len_mode)

    test_lengths = _read_fasta_lengths(test_fasta)
    length_status = {
        sid: _classify_length_status(L, min_len_tool, max_len_tool)
        for sid, L in test_lengths.items()
    }
    status_counts = Counter(length_status.values())
    log.info(
        "  Length status: within=%d  too_short=%d  too_long=%d (total=%d) "
        "-- out-of-range peptides are KEPT and flagged for downstream analysis",
        status_counts.get("within_range", 0),
        status_counts.get("too_short", 0),
        status_counts.get("too_long", 0),
        len(test_lengths),
    )

    # -- 2. Parse all test IDs ------------------------------------------------
    test_ids = parse_fasta_ids(test_fasta)
    n_test = len(test_ids)
    n_train = _count_fasta_sequences(training_fasta)

    log.info("=" * 60)
    log.info("LEAKAGE ANALYSIS: %s", tool_id)
    log.info("  Test sequences:     %d", n_test)
    log.info("  Training sequences: %d", n_train)
    log.info("  Thresholds:         %s", thresholds)
    log.info("  SSH host:           %s", ssh_host or "(local)")
    log.info("=" * 60)

    if n_test == 0:
        log.error("No test sequences found in %s", test_fasta)
        return {"status": "error", "message": "empty test FASTA"}

    # -- 3. Run CD-HIT-2D at each threshold -----------------------------------
    # Use a temp dir inside output_dir (accessible via SSHFS from Linux)
    tmpdir = os.path.join(output_dir, "_cdhit2d_tmp")
    os.makedirs(tmpdir, exist_ok=True)
    results_by_threshold = {}  # {float_threshold: set_of_survivor_ids}

    try:
        for threshold in sorted(thresholds, reverse=True):  # 0.80, 0.60, 0.40
            label = f"{threshold * 100:.0f}"
            output_path = os.path.join(tmpdir, f"cdhit2d_{tool_id}_{label}")

            log.info("--- Threshold: %s%% ---", label)
            result = run_cdhit2d(
                training_fasta=training_fasta,
                test_fasta=test_fasta,
                output_path=output_path,
                identity=threshold,
                ssh_host=ssh_host,
                ssh_user=ssh_user,
                cdhit_binary=cdhit_binary,
                sshfs_mount=sshfs_mount,
                linux_base=linux_base,
            )

            if result["returncode"] != 0:
                log.error("  CD-HIT-2D failed at %s%% (returncode=%d)",
                          label, result["returncode"])
                # Use empty set so classify_leakage_grades treats as all-failed
                results_by_threshold[threshold] = set()
            else:
                survivors = result["survivors"]
                results_by_threshold[threshold] = survivors
                n_survived = len(survivors)
                n_leaked = n_test - n_survived
                pct_leaked = n_leaked / n_test * 100
                log.info("  Survived: %d/%d (%.1f%%)", n_survived, n_test,
                         100.0 - pct_leaked)
                log.info("  Leaked:   %d/%d (%.1f%%)", n_leaked, n_test,
                         pct_leaked)

                # Copy .clstr file to output_dir for inspection
                clstr = result.get("clstr_path", "")
                if clstr and os.path.exists(clstr):
                    dest = os.path.join(output_dir,
                                        f"cdhit2d_{tool_id}_{label}.clstr")
                    shutil.copy2(clstr, dest)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # -- 4. Classify sequences ------------------------------------------------
    grades = classify_leakage_grades(test_ids, results_by_threshold)

    grade_counts = Counter(grades.values())
    log.info("")
    log.info("=" * 60)
    log.info("LEAKAGE SUMMARY: %s", tool_id)
    log.info("=" * 60)
    for grade in ("Gold", "Silver", "Bronze", "Red"):
        count = grade_counts.get(grade, 0)
        pct = count / n_test * 100 if n_test > 0 else 0.0
        log.info("  %-8s: %4d (%5.1f%%)", grade, count, pct)

    # -- 5. Export results ----------------------------------------------------

    # 5a. Classification CSV
    csv_path = os.path.join(output_dir,
                            f"leakage_{tool_id}_classifications.csv")
    s80 = results_by_threshold.get(0.80, set())
    s60 = results_by_threshold.get(0.60, set())
    s40 = results_by_threshold.get(0.40, set())

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Sequence_ID", "Grade", "Length", "Length_Status",
                         "Survives_80", "Survives_60", "Survives_40"])
        for seq_id in sorted(grades):
            writer.writerow([
                seq_id,
                grades[seq_id],
                test_lengths.get(seq_id, 0),
                length_status.get(seq_id, "unknown"),
                seq_id in s80,
                seq_id in s60,
                seq_id in s40,
            ])
    log.info("  Classifications saved: %s", csv_path)

    # 5b. Summary report JSON
    # Cross-tabulate length status x grade
    grade_x_status = {}
    for sid, g in grades.items():
        st = length_status.get(sid, "unknown")
        grade_x_status.setdefault(g, Counter())[st] += 1
    grade_x_status_serial = {
        g: dict(counts) for g, counts in grade_x_status.items()
    }

    summary = {
        "tool": tool_id,
        "n_test": n_test,
        "n_train": n_train,
        "thresholds": thresholds,
        "grades": {g: grade_counts.get(g, 0)
                   for g in ("Gold", "Silver", "Bronze", "Red")},
        "grade_percentages": {
            g: round(grade_counts.get(g, 0) / n_test * 100, 1) if n_test else 0
            for g in ("Gold", "Silver", "Bronze", "Red")
        },
        "survivors_80": len(s80),
        "survivors_60": len(s60),
        "survivors_40": len(s40),
        "tool_length_range": {
            "min": min_len_tool,
            "max": max_len_tool,
            "source": rng_src,
            "mode": len_mode,
        },
        "length_status_counts": dict(status_counts),
        "length_status_percentages": {
            st: round(status_counts.get(st, 0) / n_test * 100, 1) if n_test else 0
            for st in ("within_range", "too_short", "too_long")
        },
        "grade_x_length_status": grade_x_status_serial,
    }

    report = {
        "script": SCRIPT_NAME,
        "script_version": SCRIPT_VERSION,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "test_fasta": os.path.abspath(test_fasta),
        "training_fasta": os.path.abspath(training_fasta),
        "summary": summary,
    }

    json_path = os.path.join(output_dir, f"leakage_{tool_id}_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log.info("  Report saved: %s", json_path)

    # 5c. Per-grade FASTAs for downstream use (Gold, Silver, Bronze, Red)
    grade_fasta_paths = {}
    for grade in ("Gold", "Silver", "Bronze", "Red"):
        grade_ids = {sid for sid, g in grades.items() if g == grade}
        grade_fasta_path = os.path.join(
            output_dir, f"{grade.lower()}_survivors_{tool_id}.fasta"
        )
        _filter_fasta(test_fasta, grade_fasta_path, grade_ids)
        grade_fasta_paths[grade] = grade_fasta_path
        log.info("  %s FASTA (%d seqs): %s", grade, len(grade_ids), grade_fasta_path)

    # -- 6. Provenance --------------------------------------------------------
    generate_provenance(
        output_dir=output_dir,
        script_name=SCRIPT_NAME,
        tool_id=tool_id,
        parameters={
            "script_version": SCRIPT_VERSION,
            "test_fasta": os.path.abspath(test_fasta),
            "training_fasta": os.path.abspath(training_fasta),
            "thresholds": thresholds,
            "ssh_host": ssh_host,
        },
        output_stats=summary,
    )

    return {
        "status": "success",
        "summary": summary,
        "csv_path": csv_path,
        "json_path": json_path,
        "grade_fasta_paths": grade_fasta_paths,
        "gold_fasta_path": grade_fasta_paths.get("Gold", ""),  # backward compat
    }


# =============================================================================
# CLI
# =============================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="CD-HIT-2D leakage analysis between test and training datasets.",
    )
    parser.add_argument("--tool", required=True, dest="tool_id",
                        help="Tool identifier (must exist in pipeline_config).")
    parser.add_argument("--config", required=True, dest="pipeline_config",
                        help="Path to pipeline_config.yaml.")
    parser.add_argument("--test-fasta", required=True,
                        help="Path to test/validation pool FASTA.")
    parser.add_argument("--training-fasta", required=True,
                        help="Path to the tool's training FASTA.")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for leakage report outputs.")
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate inputs
    for label, path in [("test-fasta", args.test_fasta),
                        ("training-fasta", args.training_fasta)]:
        if not os.path.isfile(path):
            log.error("File not found for --%s: %s", label, path)
            sys.exit(1)

    result = run_leakage_analysis(
        tool_id=args.tool_id,
        pipeline_config=args.pipeline_config,
        test_fasta=args.test_fasta,
        training_fasta=args.training_fasta,
        output_dir=args.output_dir,
    )

    if result["status"] != "success":
        log.error("Leakage analysis failed: %s", result.get("message", "unknown"))
        sys.exit(1)

    log.info("Leakage analysis complete for %s", args.tool_id)
    sys.exit(0)


if __name__ == "__main__":
    main()
