#!/usr/bin/env python3
"""
run_tool_prediction.py
=======================
Runs a bioactivity prediction tool on its specific test dataset.
Loads positives from ALL leakage grades (Gold/Silver/Bronze/Red) + negatives,
runs prediction ONCE on the combined set, then computes metrics stratified by grade.

Called by audit_pipeline.sh:
    python run_tool_prediction.py --tool TOOL_ID --config pipeline_config.yaml \
        --output-dir Tool_Audits/tool_id/predictions
"""

import argparse
import csv
import json
import logging
import math
import os
import subprocess
import sys
from datetime import datetime, timezone

from audit_lib.config import load_pipeline_config, get_tool_config
from audit_lib.provenance import generate_provenance

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_NAME = "run_tool_prediction.py"
SCRIPT_VERSION = "2.0.0"
GRADES = ("Gold", "Silver", "Bronze", "Red")


# =============================================================================
# FASTA helpers
# =============================================================================

def _read_fasta(fasta_path):
    """Return list of (id, sequence) from a FASTA file."""
    seqs = []
    current_id, current_seq = None, []
    with open(fasta_path, "r") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if current_id and current_seq:
                    seqs.append((current_id, "".join(current_seq)))
                current_id = line[1:].split()[0]
                current_seq = []
            elif current_id is not None:
                current_seq.append(line)
    if current_id and current_seq:
        seqs.append((current_id, "".join(current_seq)))
    return seqs


def _build_grade_fastas_from_csv(tool_id, pos_dir, pool_fasta_path):
    """
    Fallback: reconstruct per-grade sequences from classifications CSV + pool FASTA.
    Used when per-grade FASTAs don't exist yet (e.g., pre-v2 leakage output).
    Returns dict {grade: [(id, seq)]}.
    """
    class_csv = os.path.join(pos_dir, f"leakage_{tool_id}_classifications.csv")
    if not os.path.exists(class_csv):
        log.warning("  [FALLBACK] Classifications CSV not found: %s", class_csv)
        return {g: [] for g in GRADES}
    if not pool_fasta_path or not os.path.exists(pool_fasta_path):
        log.warning("  [FALLBACK] Pool FASTA not found: %s", pool_fasta_path)
        return {g: [] for g in GRADES}

    log.info("  [FALLBACK] Rebuilding grade sequences from classifications CSV + pool FASTA")
    id_to_grade = {}
    with open(class_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            id_to_grade[row["Sequence_ID"]] = row["Grade"]

    all_seqs = _read_fasta(pool_fasta_path)
    result = {g: [] for g in GRADES}
    for seq_id, seq in all_seqs:
        grade = id_to_grade.get(seq_id)
        if grade in result:
            result[grade].append((seq_id, seq))

    for grade in GRADES:
        log.info("  [FALLBACK] %s: %d sequences", grade, len(result[grade]))
    return result


# =============================================================================
# Input preparation
# =============================================================================

def prepare_input(tool_id, tool_cfg, output_dir, cfg):
    """
    Build the combined input file (all grades + negatives) and ground-truth CSV.

    Ground-truth columns: ID, Sequence, True_Label (1=positive/0=negative), Grade
    Returns (input_path, truth_path) or (None, None) on failure.
    """
    run_cmd = tool_cfg.get("run_command", {})
    input_format = run_cmd.get("input_format", "fasta")

    tool_dir = os.path.dirname(output_dir)
    pos_dir = os.path.join(tool_dir, "leakage_report")
    neg_dir = os.path.join(tool_dir, "test_negatives")

    # Derive pool FASTA path for fallback (Dataset_Bioactividad/Category_Pools/)
    base_dir = os.path.normpath(os.path.join(tool_dir, "../.."))
    category = tool_cfg.get("category", "")
    pool_fasta = os.path.join(base_dir, "Category_Pools", f"{category}_pool.fasta")

    sequences = []  # (seq_id, seq, label, grade)

    # --- Load positives per grade ---
    # Try per-grade FASTA files first; fall back to classifications CSV for
    # any grade whose FASTA is missing (e.g., produced by pre-v2 leakage step).
    missing_grades = []
    for grade in GRADES:
        grade_fasta = os.path.join(pos_dir, f"{grade.lower()}_survivors_{tool_id}.fasta")
        if os.path.exists(grade_fasta):
            seqs = _read_fasta(grade_fasta)
            for seq_id, seq in seqs:
                sequences.append((seq_id, seq, 1, grade))
            log.info("  Loaded %d %s positives", len(seqs), grade)
        else:
            missing_grades.append(grade)
            log.debug("  %s FASTA not found: %s", grade, grade_fasta)

    if missing_grades:
        log.info("  [FALLBACK] Grade FASTAs missing for %s — rebuilding from classifications CSV",
                 missing_grades)
        grade_seqs = _build_grade_fastas_from_csv(tool_id, pos_dir, pool_fasta)
        for grade in missing_grades:
            seqs = grade_seqs.get(grade, [])
            for seq_id, seq in seqs:
                sequences.append((seq_id, seq, 1, grade))
            if seqs:
                log.info("  [FALLBACK] Loaded %d %s positives", len(seqs), grade)

    n_positives = sum(1 for s in sequences if s[2] == 1)
    log.info("  Total positives (all grades): %d", n_positives)

    # --- Load negatives ---
    neg_csv = os.path.join(neg_dir, f"negatives_{tool_id}.csv")
    n_neg_loaded = 0
    if os.path.exists(neg_csv):
        df_neg = pd.read_csv(neg_csv)
        for idx, row in df_neg.iterrows():
            seq_id = str(row.get("ID", f"neg_{idx}"))
            seq = str(row.get("Sequence", "")).strip().upper()
            if seq:
                sequences.append((seq_id, seq, 0, "Negative"))
                n_neg_loaded += 1
        log.info("  Loaded %d negatives", n_neg_loaded)
    else:
        log.warning("  Negatives CSV not found: %s", neg_csv)

    if not sequences:
        log.error("  No sequences to predict!")
        return None, None

    os.makedirs(output_dir, exist_ok=True)

    # --- Write input file ---
    if input_format == "fasta":
        input_path = os.path.join(output_dir, f"input_{tool_id}.fasta")
        with open(input_path, "w", encoding="utf-8") as f:
            for seq_id, seq, label, grade in sequences:
                f.write(f">{seq_id}\n{seq}\n")
    elif input_format == "csv":
        input_path = os.path.join(output_dir, f"input_{tool_id}.csv")
        with open(input_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Sequence"])
            for seq_id, seq, label, grade in sequences:
                writer.writerow([seq_id, seq])
    elif input_format == "txt":
        # Plain text: one sequence per line (no headers) — used by APEX
        input_path = os.path.join(output_dir, f"input_{tool_id}.txt")
        with open(input_path, "w", encoding="utf-8") as f:
            for seq_id, seq, label, grade in sequences:
                f.write(f"{seq}\n")
    else:
        input_path = os.path.join(output_dir, f"input_{tool_id}.txt")
        with open(input_path, "w", encoding="utf-8") as f:
            for seq_id, seq, label, grade in sequences:
                f.write(f"{seq}\n")

    # --- Write ground truth (includes Grade column) ---
    truth_path = os.path.join(output_dir, f"ground_truth_{tool_id}.csv")
    with open(truth_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Sequence", "True_Label", "Grade"])
        for seq_id, seq, label, grade in sequences:
            writer.writerow([seq_id, seq, label, grade])

    n_pos = sum(1 for s in sequences if s[2] == 1)
    n_neg = sum(1 for s in sequences if s[2] == 0)
    log.info("  Input file: %s", input_path)
    log.info("  Ground truth: %s", truth_path)
    log.info("  Total: %d sequences (pos=%d, neg=%d)", len(sequences), n_pos, n_neg)

    return input_path, truth_path


# =============================================================================
# Prediction execution — extended (arg_style, output_capture, regression)
# =============================================================================

def _parse_stdout_python_list(stdout: str, sequences: list, tool_id: str,
                               output_dir: str, pos_label: str = "ACP") -> str | None:
    """
    Parse a Python list of labels printed to stdout (e.g. DeepBP: ['ACP', 'non-ACP', ...]).
    Aligns by position with the input sequences list.
    Returns path to saved CSV, or None.
    """
    import ast
    # Find the list in stdout
    stdout = stdout.strip()
    list_start = stdout.find("[")
    list_end = stdout.rfind("]")
    if list_start == -1 or list_end == -1:
        log.error("  Could not find Python list in stdout: %s", stdout[:200])
        return None
    try:
        labels = ast.literal_eval(stdout[list_start:list_end + 1])
    except Exception as e:
        log.error("  Failed to parse stdout list: %s", e)
        return None

    if len(labels) != len(sequences):
        log.warning(
            "  stdout list length (%d) != input sequences (%d) — aligning by index",
            len(labels), len(sequences)
        )

    rows = []
    for i, (seq_id, seq, true_label, grade) in enumerate(sequences):
        pred_str = labels[i] if i < len(labels) else "unknown"
        rows.append({
            "ID": seq_id,
            "Sequence": seq,
            "Prediction": pred_str,
        })

    out_path = os.path.join(output_dir, f"predictions_{tool_id}_stdout.csv")
    df_out = pd.DataFrame(rows)
    df_out.to_csv(out_path, index=False)
    log.info("  Parsed stdout list → CSV: %s", out_path)
    return out_path


def _binarize_regression_output(pred_path: str, run_cmd: dict,
                                 tool_id: str, output_dir: str) -> str | None:
    """
    Convert regression CSV output to binary classification CSV.
    Uses regression_column, regression_threshold, and regression_direction from run_cmd.
    Returns path to binarized CSV or None.
    """
    reg_col = run_cmd.get("regression_column")
    threshold = float(run_cmd.get("regression_threshold", 0.5))
    direction = run_cmd.get("regression_direction", "higher_is_positive")
    pred_col_name = run_cmd.get("output_parsing", {}).get("prediction_column", "Predicted_Class")
    pos_label = run_cmd.get("output_parsing", {}).get("positive_label", "positive")
    neg_label = "non-" + pos_label

    try:
        df = pd.read_csv(pred_path)
    except Exception as e:
        log.error("  Could not read regression output %s: %s", pred_path, e)
        return None

    if not reg_col or reg_col not in df.columns:
        # Try to find a numeric column
        numeric_cols = df.select_dtypes(include=["float64", "float32", "int64"]).columns.tolist()
        if not numeric_cols:
            log.error("  No numeric column for regression binarization in %s", pred_path)
            return None
        reg_col = numeric_cols[0]
        log.warning("  regression_column not found, using first numeric col: %s", reg_col)

    if direction == "lower_is_positive":
        df[pred_col_name] = df[reg_col].apply(
            lambda v: pos_label if v <= threshold else neg_label
        )
    else:
        df[pred_col_name] = df[reg_col].apply(
            lambda v: pos_label if v >= threshold else neg_label
        )

    out_path = os.path.join(output_dir, f"predictions_{tool_id}_binarized.csv")
    df.to_csv(out_path, index=False)
    log.info(
        "  Binarized regression output → %s (col=%s, threshold=%.3f, dir=%s)",
        out_path, reg_col, threshold, direction
    )
    return out_path


def run_prediction(tool_id, tool_cfg, input_path, output_dir, pipeline_cfg,
                   sequences=None):
    """
    Execute the prediction tool. Returns output CSV path or None.

    Supports:
      - arg_style: flagged (default) | positional | wrapper
      - output_capture: file (default) | hardcoded_file | stdout
      - regression_threshold: binarize continuous output
    """
    run_cmd = tool_cfg.get("run_command", {})
    if not run_cmd:
        log.warning("  No run_command configured for %s", tool_id)
        return None

    cmd_type = run_cmd.get("type", "python_script")
    arg_style = run_cmd.get("arg_style", "flagged")
    output_capture = run_cmd.get("output_capture", "file")
    output_format = run_cmd.get("output_format", "csv")
    extra_args = run_cmd.get("extra_args", []) or []
    hardcoded_output_name = run_cmd.get("hardcoded_output_name", None)

    # Script resolution
    wrapper_script = run_cmd.get("wrapper_script", None)
    if arg_style == "wrapper" and wrapper_script:
        # Wrapper lives in pipeline root, not in repo
        pipeline_root = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(pipeline_root, wrapper_script)
    else:
        script = run_cmd.get("script", "predict.py")

    input_flag = run_cmd.get("input_flag", "-i")
    output_flag = run_cmd.get("output_flag", "-o")
    positional_input_index = run_cmd.get("positional_input_index", 0)

    # Resolve conda env
    conda_env_key = tool_cfg.get("conda_env", "")
    envs = pipeline_cfg.get("environments", {})
    env_info = envs.get(conda_env_key, {})
    conda_name = env_info.get("conda_name", conda_env_key)

    # Resolve repo dir
    global_cfg = pipeline_cfg.get("global", {})
    repos_dir = global_cfg.get("repos_dir", "Dataset_Bioactividad/Tool_Repos")
    if not os.path.isabs(repos_dir):
        repos_dir = os.path.abspath(repos_dir)
    github_url = tool_cfg.get("github_url", "")
    repo_name = (
        github_url.rstrip("/").split("/")[-1].replace(".git", "")
        if github_url else tool_id
    )
    repo_dir = os.path.join(repos_dir, repo_name)

    input_path_abs = os.path.abspath(input_path)
    output_dir_abs = os.path.abspath(output_dir)
    output_path = os.path.join(output_dir_abs, f"predictions_{tool_id}.{output_format}")

    # --- Build command ---
    if cmd_type == "python_script":
        if arg_style == "wrapper":
            # Wrapper takes --input / --output flags like a standard tool
            cmd = ["python", script,
                   input_flag or "--input", input_path_abs,
                   output_flag or "--output", output_path]
        elif arg_style == "positional":
            # Input is positional; no -i flag; output is captured from hardcoded file / stdout
            cmd = ["python", os.path.join(repo_dir, script)]
            # Insert input at positional_input_index
            positional_args = [input_path_abs]
            cmd.extend(positional_args)
            # No output flag in positional mode
        elif arg_style == "flagged":
            script_path = os.path.join(repo_dir, script)
            cmd = ["python", script_path]
            if input_flag:
                cmd.extend([input_flag, input_path_abs])
            if output_flag:
                cmd.extend([output_flag, output_path])
        else:
            # Default: flagged
            script_path = os.path.join(repo_dir, script)
            cmd = ["python", script_path]
            if input_flag:
                cmd.extend([input_flag, input_path_abs])
            if output_flag:
                cmd.extend([output_flag, output_path])

        cmd.extend([str(a) for a in extra_args])
    else:
        log.warning("  Unknown command type: %s", cmd_type)
        return None

    # Quote paths with spaces
    cmd_str = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    conda_cmd = f"micromamba run -n {conda_name} {cmd_str}"

    log.info("  arg_style: %s | output_capture: %s", arg_style, output_capture)
    log.info("  Running: %s", conda_cmd)
    log.info("  Conda env: %s", conda_name)
    log.info("  Working dir: %s", repo_dir)

    cwd = repo_dir if (arg_style != "wrapper" and os.path.isdir(repo_dir)) else None

    try:
        result = subprocess.run(
            conda_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=cwd,
        )

        log_path = os.path.join(output_dir, f"prediction_{tool_id}_stdout.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}\n")

        if result.returncode != 0:
            log.error("  Prediction failed (rc=%d)", result.returncode)
            log.error("  STDERR: %s", result.stderr[:500])
            return None

        # --- Capture output according to output_capture mode ---
        actual_output = None

        if output_capture == "stdout":
            # Parse stdout directly (e.g., DeepBP Python list)
            stdout_type = run_cmd.get("stdout_parse_type", "python_list")
            if stdout_type == "python_list":
                pos_label = run_cmd.get("output_parsing", {}).get("positive_label", "ACP")
                actual_output = _parse_stdout_python_list(
                    result.stdout, sequences or [], tool_id, output_dir, pos_label
                )
            else:
                # Save raw stdout as CSV
                actual_output = os.path.join(output_dir, f"predictions_{tool_id}_stdout.txt")
                with open(actual_output, "w") as f:
                    f.write(result.stdout)

        elif output_capture == "hardcoded_file":
            # Tool writes to a hardcoded filename in cwd (repo_dir)
            if hardcoded_output_name:
                hardcoded_path = os.path.join(cwd or output_dir, hardcoded_output_name)
                if os.path.exists(hardcoded_path):
                    # Move/copy to output_dir
                    import shutil
                    actual_output = os.path.join(output_dir, f"predictions_{tool_id}.csv")
                    shutil.copy2(hardcoded_path, actual_output)
                    log.info("  Copied hardcoded output %s → %s",
                             hardcoded_path, actual_output)
                else:
                    # Try output_dir
                    alt_path = os.path.join(output_dir, hardcoded_output_name)
                    if os.path.exists(alt_path):
                        actual_output = alt_path
                    else:
                        log.warning("  Hardcoded output not found at %s or %s",
                                    hardcoded_path, alt_path)

        elif output_capture == "file":
            if os.path.exists(output_path):
                actual_output = output_path
            else:
                log.warning("  Expected output not found: %s", output_path)

        if actual_output is None:
            log.warning("  No output captured. Check %s", log_path)
            return None

        # --- Regression binarization ---
        regression_threshold = run_cmd.get("regression_threshold", None)
        if regression_threshold is not None:
            log.info("  Applying regression binarization (threshold=%.3f)...",
                     float(regression_threshold))
            binarized = _binarize_regression_output(
                actual_output, run_cmd, tool_id, output_dir
            )
            if binarized:
                actual_output = binarized

        log.info("  Prediction output: %s", actual_output)
        return actual_output

    except subprocess.TimeoutExpired:
        log.error("  Prediction timed out (600s)")
        return None
    except Exception as e:
        log.error("  Prediction error: %s", e)
        return None


# =============================================================================
# Per-grade metrics computation
# =============================================================================

def _safe_mcc(tp, tn, fp, fn):
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / denom if denom > 0 else 0.0


def _metrics_for_df(df_sub):
    """Compute classification metrics for a subset DataFrame."""
    tp = int(((df_sub["True_Label"] == 1) & (df_sub["Predicted"] == 1)).sum())
    fn = int(((df_sub["True_Label"] == 1) & (df_sub["Predicted"] == 0)).sum())
    tn = int(((df_sub["True_Label"] == 0) & (df_sub["Predicted"] == 0)).sum())
    fp = int(((df_sub["True_Label"] == 0) & (df_sub["Predicted"] == 1)).sum())
    n_pos = tp + fn
    n_neg = tn + fp
    acc = (tp + tn) / (n_pos + n_neg) if (n_pos + n_neg) > 0 else 0.0
    sens = tp / n_pos if n_pos > 0 else 0.0
    spec = tn / n_neg if n_neg > 0 else 0.0
    mcc = _safe_mcc(tp, tn, fp, fn)
    return {
        "n_positives": n_pos,
        "n_negatives": n_neg,
        "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "accuracy": round(acc, 4),
        "sensitivity": round(sens, 4),
        "specificity": round(spec, 4),
        "mcc": round(mcc, 4),
    }


def compute_grade_metrics(tool_id, tool_cfg, pred_path, truth_path, output_dir):
    """
    Parse prediction output, merge with ground truth, compute per-grade metrics.

    For each grade G: evaluate on (positives with grade=G) + (all negatives).
    This reveals leakage inflation:
      - Gold metrics = performance on non-leaked sequences (most trustworthy)
      - Red metrics  = performance on highly similar / leaked sequences (inflated)

    Saves grade_metrics_{tool_id}.json and returns the path.
    """
    pred_cfg = tool_cfg.get("run_command", {}).get("output_parsing", {})
    id_col = pred_cfg.get("id_column", "Subject")
    pred_col = pred_cfg.get("prediction_column", "Prediction")
    pos_label = pred_cfg.get("positive_label", "Toxin")
    score_col = pred_cfg.get("score_column", None)

    df_truth = pd.read_csv(truth_path)
    df_pred = pd.read_csv(pred_path)

    # Columns to pull from predictions
    pred_cols = [id_col, pred_col]
    if score_col and score_col in df_pred.columns:
        pred_cols.append(score_col)

    df_merged = df_truth.merge(
        df_pred[pred_cols].rename(columns={id_col: "ID"}),
        on="ID",
        how="left",
    )

    n_matched = int(df_merged[pred_col].notna().sum())
    n_missing = int(df_merged[pred_col].isna().sum())
    if n_missing > 0:
        log.warning("  %d sequences had no matching prediction (check ID alignment)", n_missing)

    df_merged["Predicted"] = (df_merged[pred_col] == pos_label).astype(int)

    # Grade column may be missing for old ground-truth files
    if "Grade" not in df_merged.columns:
        log.warning("  Ground truth has no Grade column — skipping per-grade breakdown")
        df_merged["Grade"] = "Unknown"

    metrics = {}

    # Overall (all sequences)
    metrics["overall"] = _metrics_for_df(df_merged)

    # Per grade: grade's positives vs ALL negatives
    neg_mask = df_merged["True_Label"] == 0
    for grade in GRADES:
        grade_mask = (df_merged["Grade"] == grade) & (df_merged["True_Label"] == 1)
        n_grade_pos = int(grade_mask.sum())
        if n_grade_pos == 0:
            metrics[grade] = {
                "n_positives": 0, "n_negatives": int(neg_mask.sum()),
                "TP": 0, "TN": 0, "FP": 0, "FN": 0,
                "accuracy": 0.0, "sensitivity": 0.0, "specificity": 0.0, "mcc": 0.0,
                "note": "no positives in this grade",
            }
        else:
            df_sub = df_merged[grade_mask | neg_mask].copy()
            metrics[grade] = _metrics_for_df(df_sub)

    # Log summary table
    log.info("")
    log.info("  %-10s  %5s  %7s %7s %7s %7s",
             "Grade", "n_pos", "Acc", "Sens", "Spec", "MCC")
    log.info("  " + "-" * 55)
    for key in ("Gold", "Silver", "Bronze", "Red", "overall"):
        m = metrics[key]
        log.info("  %-10s  %5d  %7.4f %7.4f %7.4f %7.4f",
                 key, m["n_positives"],
                 m["accuracy"], m["sensitivity"], m["specificity"], m["mcc"])

    # Leakage bias indicator
    gold_mcc = metrics["Gold"].get("mcc", 0.0)
    red_mcc = metrics["Red"].get("mcc", 0.0)
    if metrics["Red"]["n_positives"] > 0 and metrics["Gold"]["n_positives"] > 0:
        bias = red_mcc - gold_mcc
        log.info("")
        log.info("  Leakage bias (Red MCC - Gold MCC): %+.4f", bias)
        if abs(bias) > 0.1:
            log.warning("  [WARNING] Significant leakage inflation detected (bias=%.4f)", bias)

    # Save JSON
    metrics_payload = {
        "script": SCRIPT_NAME,
        "script_version": SCRIPT_VERSION,
        "tool": tool_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_total": len(df_merged),
        "n_matched_predictions": n_matched,
        "output_parsing_config": pred_cfg,
        "metrics": metrics,
    }

    metrics_path = os.path.join(output_dir, f"grade_metrics_{tool_id}.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2, ensure_ascii=False)
    log.info("  Grade metrics saved: %s", metrics_path)

    return metrics_path


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run prediction tool on all leakage grades, compute per-grade metrics."
    )
    parser.add_argument("--tool", required=True, dest="tool_id")
    parser.add_argument("--config", required=True, dest="pipeline_config")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    cfg = load_pipeline_config(args.pipeline_config)
    tool_cfg = get_tool_config(args.tool_id, cfg)

    log.info("=" * 60)
    log.info("PREDICTION: %s (%s)", tool_cfg["display_name"], args.tool_id)
    log.info("=" * 60)

    # 1. Prepare combined input (all grades + negatives)
    input_path, truth_path = prepare_input(
        args.tool_id, tool_cfg, args.output_dir, cfg
    )
    if not input_path:
        log.error("Failed to prepare input")
        sys.exit(1)

    # 2. Run the tool
    # Load sequences for stdout parsing alignment (positional tools like DeepBP)
    _seqs_for_stdout = []
    if os.path.exists(truth_path):
        try:
            import pandas as _pd
            _df_t = _pd.read_csv(truth_path)
            _seqs_for_stdout = list(zip(
                _df_t["ID"].tolist(), _df_t["Sequence"].tolist(),
                _df_t["True_Label"].tolist(), _df_t["Grade"].tolist()
            ))
        except Exception:
            pass

    pred_path = run_prediction(
        args.tool_id, tool_cfg, input_path, args.output_dir, cfg,
        sequences=_seqs_for_stdout,
    )

    # 3. Compute per-grade metrics (if prediction succeeded)
    metrics_path = None
    if pred_path:
        log.info("")
        log.info("=== Per-Grade Prediction Metrics ===")
        try:
            metrics_path = compute_grade_metrics(
                args.tool_id, tool_cfg, pred_path, truth_path, args.output_dir
            )
        except Exception as e:
            log.warning("  Metrics computation failed: %s", e)

    # 4. Provenance
    generate_provenance(
        output_dir=args.output_dir,
        script_name=SCRIPT_NAME,
        tool_id=args.tool_id,
        parameters={
            "script_version": SCRIPT_VERSION,
            "conda_env": tool_cfg.get("conda_env", ""),
            "run_command": tool_cfg.get("run_command", {}),
        },
        output_stats={
            "input_path": input_path,
            "truth_path": truth_path,
            "prediction_output": pred_path,
            "metrics_path": metrics_path,
            "success": pred_path is not None,
        },
    )

    if pred_path:
        log.info("\nPrediction complete: %s", pred_path)
        if metrics_path:
            log.info("Metrics: %s", metrics_path)
    else:
        log.warning("\nPrediction did not produce output (check logs)")
        sys.exit(1)


if __name__ == "__main__":
    main()
