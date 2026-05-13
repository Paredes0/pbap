#!/usr/bin/env python3
"""
wrappers/bert_ampep60_cli.py
=============================
CLI wrapper for BERT-AmPEP60 prediction.

BERT-AmPEP60 (AMP_regression_EC_SA) has no CLI — the predict/predict.py script
uses hardcoded file paths. This wrapper:
  1. Accepts standard --input FASTA --output CSV interface
  2. Writes a temp FASTA to the location predict.py expects
  3. Runs predict.py (auto-downloads OneDrive weights on first run)
  4. Reads the hardcoded output CSV and reformats it

Usage (called by run_tool_prediction.py via arg_style: wrapper):
    python wrappers/bert_ampep60_cli.py --input input.fasta --output predictions.csv

Model outputs MIC (µM) for E. coli and S. aureus separately.
Output CSV includes both raw MIC values + computed binary label (AMP/non-AMP)
based on mean MIC <= regression_threshold µM (configured in pipeline_config.yaml,
default 1.0 µM).

Columns: ID, Sequence, ec_predicted_MIC_μM, sa_predicted_MIC_μM,
         mean_predicted_MIC_uM, Prediction
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile


POSITIVE_LABEL = "AMP"
NEGATIVE_LABEL = "non-AMP"


def parse_args():
    parser = argparse.ArgumentParser(
        description="BERT-AmPEP60 CLI wrapper for audit pipeline"
    )
    parser.add_argument("--input", required=True, help="Input FASTA file")
    parser.add_argument("--output", required=True, help="Output CSV file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="MIC threshold (µM) below which peptide is classified as AMP (default: 1.0)",
    )
    parser.add_argument(
        "--repo-dir",
        default=None,
        help="Path to AMP_regression_EC_SA repo (auto-detected if not set)",
    )
    return parser.parse_args()


def find_repo_dir(script_path: str) -> str:
    """Find AMP_regression_EC_SA repo directory."""
    candidates = [
        os.environ.get("BERT_AMPEP60_DIR", ""),
        os.path.join(os.path.dirname(script_path), "..", "Dataset_Bioactividad",
                     "Tool_Repos", "AMP_regression_EC_SA"),
        os.path.join(os.path.dirname(script_path), "..", "Dataset_Bioactividad",
                     "Tool_Repos", "bert_ampep60"),
    ]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "predict", "predict.py")):
            return os.path.abspath(c)
    raise FileNotFoundError(
        "Cannot find AMP_regression_EC_SA repo (predict/predict.py not found). "
        "Set BERT_AMPEP60_DIR or pass --repo-dir."
    )


def read_fasta(fasta_path: str) -> list[tuple[str, str]]:
    seqs = []
    current_header, current_seq = None, []
    with open(fasta_path, "r") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if current_header is not None:
                    seqs.append((current_header, "".join(current_seq)))
                current_header = line[1:].split()[0]
                current_seq = []
            elif current_header is not None:
                current_seq.append(line)
    if current_header is not None:
        seqs.append((current_header, "".join(current_seq)))
    return seqs


def patch_and_run_predict(repo_dir: str, input_fasta: str, output_dir: str) -> str | None:
    """
    Temporarily modify predict.py to use our input/output paths, run it,
    then restore. Returns path to output CSV or None.
    """
    predict_script = os.path.join(repo_dir, "predict", "predict.py")
    if not os.path.isfile(predict_script):
        print(f"ERROR: predict.py not found at {predict_script}")
        return None

    # Read the predict script
    with open(predict_script, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Determine what the script currently uses as input/output
    # The script has lines like:
    #   fasta_path = "train_po.fasta"
    #   csv_path = "train_po.csv"
    # We patch these to use absolute paths

    predict_dir = os.path.join(repo_dir, "predict")
    temp_output_csv = os.path.join(output_dir, "bert_ampep60_raw_predictions.csv")

    patched_content = original_content

    # Patch fasta_path line
    import re
    patched_content = re.sub(
        r'^(fasta_path\s*=\s*).*$',
        f'fasta_path = r"{os.path.abspath(input_fasta)}"',
        patched_content,
        flags=re.MULTILINE,
    )

    # Patch csv_path (output) line
    patched_content = re.sub(
        r'^(csv_path\s*=\s*).*$',
        f'csv_path = r"{os.path.abspath(temp_output_csv)}"',
        patched_content,
        flags=re.MULTILINE,
    )

    if patched_content == original_content:
        print("WARNING: Could not find fasta_path/csv_path variables in predict.py")
        print("  Falling back to copying FASTA to predict/train_po.fasta")
        # Fallback: copy to expected default location
        shutil.copy2(input_fasta, os.path.join(predict_dir, "train_po.fasta"))
        temp_output_csv = os.path.join(predict_dir, "train_po.csv")
        run_predict_script = original_content
    else:
        run_predict_script = patched_content

    # Write patched script to temp
    patched_script_path = os.path.join(predict_dir, "_predict_patched.py")
    with open(patched_script_path, "w", encoding="utf-8") as f:
        f.write(run_predict_script)

    # Run the patched script
    print(f"[bert_ampep60_cli] Running BERT-AmPEP60 predict...", flush=True)
    result = subprocess.run(
        [sys.executable, patched_script_path],
        cwd=predict_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )

    # Clean up patched script
    try:
        os.remove(patched_script_path)
    except OSError:
        pass

    if result.returncode != 0:
        print(f"ERROR: predict.py failed (rc={result.returncode})")
        print(f"STDERR: {result.stderr[:500]}")
        return None

    if os.path.exists(temp_output_csv):
        return temp_output_csv

    print(f"ERROR: Output CSV not found: {temp_output_csv}")
    return None


def reformat_output(raw_csv: str, sequences: list, threshold: float, output_csv: str):
    """
    Reformat BERT-AmPEP60 raw output to standard pipeline format.
    Adds: ID (from input FASTA order), mean_predicted_MIC_uM, Prediction.
    """
    import pandas as pd

    df_raw = pd.read_csv(raw_csv)

    # BERT-AmPEP60 output columns:
    # ec_predicted_MIC_μM, sa_predicted_MIC_μM (back-transformed pMIC)
    # May also have: ec_pMIC, sa_pMIC, sequence columns

    ec_col = next((c for c in df_raw.columns if "ec" in c.lower() and "mic" in c.lower()), None)
    sa_col = next((c for c in df_raw.columns if "sa" in c.lower() and "mic" in c.lower()), None)

    if ec_col is None or sa_col is None:
        print(f"WARNING: Could not find EC/SA MIC columns in {raw_csv}")
        print(f"  Available columns: {list(df_raw.columns)}")

    rows = []
    for i, (seq_id, seq) in enumerate(sequences):
        if i < len(df_raw):
            row = df_raw.iloc[i]
            ec_mic = float(row[ec_col]) if ec_col else None
            sa_mic = float(row[sa_col]) if sa_col else None
        else:
            ec_mic = sa_mic = None

        # Compute mean MIC
        mics = [m for m in [ec_mic, sa_mic] if m is not None]
        mean_mic = sum(mics) / len(mics) if mics else None

        # Binarize
        if mean_mic is not None:
            label = POSITIVE_LABEL if mean_mic <= threshold else NEGATIVE_LABEL
        else:
            label = "unknown"

        rows.append({
            "ID": seq_id,
            "Sequence": seq,
            "ec_predicted_MIC_uM": round(ec_mic, 4) if ec_mic is not None else "",
            "sa_predicted_MIC_uM": round(sa_mic, 4) if sa_mic is not None else "",
            "mean_predicted_MIC_uM": round(mean_mic, 4) if mean_mic is not None else "",
            "Prediction": label,
        })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["ID", "Sequence", "ec_predicted_MIC_uM", "sa_predicted_MIC_uM",
                      "mean_predicted_MIC_uM", "Prediction"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    n_amp = sum(1 for r in rows if r["Prediction"] == POSITIVE_LABEL)
    print(
        f"[bert_ampep60_cli] Done: {len(rows)} predictions "
        f"({n_amp} AMP, {len(rows)-n_amp} non-AMP, threshold={threshold} µM) → {output_csv}",
        flush=True,
    )


def main():
    args = parse_args()

    script_path = os.path.abspath(__file__)
    repo_dir = args.repo_dir or find_repo_dir(script_path)
    print(f"[bert_ampep60_cli] Using repo: {repo_dir}", flush=True)

    sequences = read_fasta(args.input)
    if not sequences:
        print(f"ERROR: No sequences in {args.input}")
        sys.exit(1)
    print(f"[bert_ampep60_cli] Loaded {len(sequences)} sequences", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    output_dir = os.path.dirname(os.path.abspath(args.output))

    raw_csv = patch_and_run_predict(repo_dir, args.input, output_dir)
    if raw_csv is None:
        sys.exit(1)

    reformat_output(raw_csv, sequences, args.threshold, args.output)


if __name__ == "__main__":
    main()
