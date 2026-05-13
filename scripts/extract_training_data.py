#!/usr/bin/env python3
"""
extract_training_data.py
========================
Clones tool GitHub repositories and extracts training datasets for
CD-HIT-2D leakage analysis.

Called by audit_pipeline.sh as:
    python extract_training_data.py --tool TOOL_ID --config pipeline_config.yaml --output-dir DIR

For each tool:
1. Read tool config from pipeline_config.yaml
2. Clone the repo (if not cloned) to {repos_dir}/{tool_id}
3. Search for data files using search_patterns and score by data_keywords
4. Extract sequences from FASTA/CSV/TSV/TXT files
5. Classify files into training/test/other splits by path keywords
6. Deduplicate sequences
7. Export training FASTA and CSV summary
8. Generate provenance JSON
9. If no sequences found, write STANDBY_REPORT.json and exit
"""

import argparse
import csv
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from audit_lib.config import load_pipeline_config, get_tool_config
from audit_lib.sequence_utils import validate_sequence, find_column

# ============================================================================
# CONSTANTS
# ============================================================================

SCRIPT_VERSION = "2.0.0"

# Minimum length override for training data extraction (short peptides OK)
MIN_SEQ_LENGTH = 3

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ============================================================================
# SEQUENCE EXTRACTION
# ============================================================================


def extract_sequences_from_fasta(filepath):
    """Parse FASTA file and return list of (header, sequence) tuples."""
    sequences = []
    current_header = None
    current_seq = []

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_header and current_seq:
                    seq = "".join(current_seq).upper()
                    if validate_sequence(seq, min_length=MIN_SEQ_LENGTH):
                        sequences.append((current_header, seq))
                current_header = line[1:].strip()
                current_seq = []
            else:
                current_seq.append(line)

        # Last sequence
        if current_header and current_seq:
            seq = "".join(current_seq).upper()
            if validate_sequence(seq, min_length=MIN_SEQ_LENGTH):
                sequences.append((current_header, seq))

    return sequences


def extract_sequences_from_tabular(filepath, seq_hints, label_hints, delimiter=None):
    """Parse CSV/TSV file and return sequences with metadata."""
    import pandas as pd

    try:
        if delimiter:
            df = pd.read_csv(filepath, sep=delimiter, engine="python",
                             on_bad_lines="skip")
        elif filepath.endswith(".tsv"):
            df = pd.read_csv(filepath, sep="\t", engine="python",
                             on_bad_lines="skip")
        else:
            df = pd.read_csv(filepath, engine="python", on_bad_lines="skip")
    except Exception as e:
        log.warning(f"  Could not parse {filepath}: {e}")
        return [], None, None

    if df.empty:
        return [], None, None

    # Find sequence column using audit_lib utility
    seq_col = find_column(df, *seq_hints)
    if not seq_col:
        # Fallback: detect column where most values look like peptides
        for col in df.columns:
            sample = df[col].dropna().head(20).astype(str)
            valid_count = sum(
                validate_sequence(s, min_length=MIN_SEQ_LENGTH) for s in sample
            )
            if valid_count >= len(sample) * 0.5 and len(sample) > 0:
                seq_col = col
                break

    if not seq_col:
        return [], None, None

    # Find label column using audit_lib utility
    label_col = find_column(df, *label_hints)

    # Extract sequences
    sequences = []
    for idx, row in df.iterrows():
        seq = str(row[seq_col]).strip().upper()
        if validate_sequence(seq, min_length=MIN_SEQ_LENGTH):
            label = (
                str(row[label_col])
                if label_col and label_col in row.index
                else "unknown"
            )
            header = f"row_{idx}|label={label}"
            sequences.append((header, seq))

    return sequences, seq_col, label_col


def extract_sequences_from_txt(filepath):
    """Try to extract sequences from a plain text file (one per line or FASTA)."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline().strip()

    # If starts with >, treat as FASTA
    if first_line.startswith(">"):
        return extract_sequences_from_fasta(filepath)

    # Otherwise try one-sequence-per-line
    sequences = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            seq = line.strip().upper()
            if validate_sequence(seq, min_length=MIN_SEQ_LENGTH):
                sequences.append((f"line_{i}", seq))

    return sequences

def infer_label_from_filename(filepath: str, pos_pattern: str, neg_pattern: str) -> str | None:
    """Return 'positive', 'negative', or None based on filename patterns."""
    fname = os.path.basename(filepath).lower()
    if pos_pattern.lower() in fname:
        return "positive"
    if neg_pattern.lower() in fname:
        return "negative"
    return None


def infer_label_from_header_prefix(header: str, pos_prefix: str, neg_prefix: str) -> str | None:
    """Return 'positive', 'negative', or None based on FASTA header prefix."""
    if pos_prefix and header.startswith(pos_prefix):
        return "positive"
    if neg_prefix and header.startswith(neg_prefix):
        return "negative"
    return None


def extract_labeled_sequences(training_cfg: dict, data_files: list,
                                seq_hints: list, label_hints: list) -> list:
    """
    Extract sequences with label awareness based on training_cfg.label_source.

    Returns list of dicts: {header, sequence, source_file, label}
    where label is 'positive', 'negative', or 'unknown'.

    label_source options:
      filename        : infer from filename (_pos / _neg patterns)
      header_prefix   : infer from FASTA header prefix (>Positive_ / >Negative_)
      column          : read from DataFrame column (standard — existing behavior)
      inverted_column : read from column but invert (0=positive, 1=negative)
      regression_column: threshold continuous value to binary
      None / default  : all sequences labeled 'unknown'
    """
    import pandas as pd

    label_source = training_cfg.get("label_source") or "column"
    pos_fname_pat = training_cfg.get("positive_filename_pattern", "_pos")
    neg_fname_pat = training_cfg.get("negative_filename_pattern", "_neg")
    pos_hdr_pfx = training_cfg.get("header_prefix_positive", "Positive_")
    neg_hdr_pfx = training_cfg.get("header_prefix_negative", "Negative_")
    label_inverted = training_cfg.get("label_inverted", False)
    reg_col = training_cfg.get("regression_column", None)
    reg_threshold = float(training_cfg.get("regression_positive_threshold", 0.5))

    all_entries = []

    for df_info in data_files:
        filepath = df_info["path"]
        ext = os.path.splitext(filepath)[1].lower()

        # ---- Determine file-level label if label_source == filename ----
        file_label = None
        if label_source == "filename":
            file_label = infer_label_from_filename(filepath, pos_fname_pat, neg_fname_pat)

        try:
            if ext in [".fasta", ".fa"]:
                seqs_raw = extract_sequences_from_fasta(filepath)
                for header, seq in seqs_raw:
                    if label_source == "filename":
                        label = file_label or "unknown"
                    elif label_source == "header_prefix":
                        label = infer_label_from_header_prefix(
                            header, pos_hdr_pfx, neg_hdr_pfx) or "unknown"
                    else:
                        label = "unknown"
                    all_entries.append({
                        "header": header, "sequence": seq,
                        "source_file": df_info["rel_path"], "label": label,
                    })

            elif ext in [".csv", ".tsv"]:
                if ext == ".tsv":
                    df = pd.read_csv(filepath, sep="	", engine="python", on_bad_lines="skip")
                else:
                    df = pd.read_csv(filepath, engine="python", on_bad_lines="skip")

                if df.empty:
                    continue

                seq_col = find_column(df, *seq_hints)
                if not seq_col:
                    for col in df.columns:
                        sample = df[col].dropna().head(20).astype(str)
                        valid_count = sum(
                            validate_sequence(s, min_length=MIN_SEQ_LENGTH) for s in sample
                        )
                        if valid_count >= len(sample) * 0.5 and len(sample) > 0:
                            seq_col = col
                            break
                if not seq_col:
                    continue

                for idx, row in df.iterrows():
                    seq = str(row[seq_col]).strip().upper()
                    if not validate_sequence(seq, min_length=MIN_SEQ_LENGTH):
                        continue

                    label = "unknown"
                    if label_source in ("column", "inverted_column"):
                        lbl_col = find_column(df, *label_hints)
                        if lbl_col and lbl_col in row.index:
                            raw_lbl = str(row[lbl_col]).strip()
                            # Try numeric label
                            try:
                                numeric = float(raw_lbl)
                                if label_source == "inverted_column" or label_inverted:
                                    # 0 = positive, 1 = negative (e.g., DeepBP)
                                    label = "positive" if numeric == 0 else "negative"
                                else:
                                    # Standard: 1 = positive, 0 = negative
                                    label = "positive" if numeric == 1 else "negative"
                            except ValueError:
                                # String label
                                lbl_lower = raw_lbl.lower()
                                pos_kws = ["1", "positive", "pos", "acp", "amp", "aip", "abp",
                                           "hemolytic", "toxic", "antifungal", "antiviral",
                                           "antitumor", "anticancer", "allergen"]
                                label = "positive" if any(k in lbl_lower for k in pos_kws) else "negative"
                    elif label_source == "regression_column":
                        reg_lbl_col = find_column(df, *(reg_col,) if reg_col else label_hints)
                        if reg_lbl_col and reg_lbl_col in row.index:
                            try:
                                val = float(row[reg_lbl_col])
                                label = "positive" if val >= reg_threshold else "negative"
                            except (ValueError, TypeError):
                                label = "unknown"
                    elif label_source == "filename":
                        label = file_label or "unknown"

                    all_entries.append({
                        "header": f"row_{idx}|label={label}",
                        "sequence": seq,
                        "source_file": df_info["rel_path"],
                        "label": label,
                    })

        except Exception as e:
            log.warning(f"  Error in label-aware extraction of {df_info['rel_path']}: {e}")

    return all_entries



# ============================================================================
# CLONE & SEARCH
# ============================================================================


def clone_repo(repo_url, clone_dir):
    """Clone a git repository if not already present."""
    if os.path.isdir(clone_dir):
        log.info(f"  Repo already cloned: {clone_dir}")
        return True

    log.info(f"  Cloning {repo_url} -> {clone_dir}")
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, clone_dir],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log.error(f"  Git clone failed: {result.stderr}")
            return False
        log.info("  Clone successful")
        return True
    except subprocess.TimeoutExpired:
        log.error("  Git clone timed out")
        return False
    except FileNotFoundError:
        log.error("  Git not found. Please install git.")
        return False


def search_data_files(repo_dir, patterns, keywords):
    """Search repository for potential data files matching patterns and keywords."""
    import glob as glob_mod

    found_files = []

    for pattern in patterns:
        matches = glob_mod.glob(os.path.join(repo_dir, pattern), recursive=True)
        for match in matches:
            filename = os.path.basename(match).lower()
            rel_path = os.path.relpath(match, repo_dir)

            # Skip very large files (>100MB)
            try:
                size_mb = os.path.getsize(match) / (1024 * 1024)
            except OSError:
                continue
            if size_mb > 100:
                continue

            # Skip non-data directories
            skip_dirs = [".git", "__pycache__", "node_modules", ".egg", "dist"]
            if any(d in rel_path for d in skip_dirs):
                continue

            # Score by keyword relevance
            score = 0
            for kw in keywords:
                if kw.lower() in filename or kw.lower() in rel_path.lower():
                    score += 1

            found_files.append({
                "path": match,
                "rel_path": rel_path,
                "filename": filename,
                "size_mb": round(size_mb, 2),
                "keyword_score": score,
            })

    # Sort by keyword relevance (highest first), then by size
    found_files.sort(key=lambda x: (-x["keyword_score"], x["size_mb"]))
    return found_files


# ============================================================================
# STANDBY REPORT
# ============================================================================


def _write_standby_report(output_dir, tool_cfg, standby_msg, data_files):
    """Write STANDBY_REPORT.json so audit_pipeline.sh can detect standby status."""
    report = {
        "status": "STANDBY",
        "tool": tool_cfg.get("display_name", tool_cfg.get("tool_id", "unknown")),
        "repo_url": tool_cfg.get("github_url", ""),
        "message": standby_msg,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files_found": [
            {
                "path": f["rel_path"],
                "size_mb": f["size_mb"],
                "keyword_score": f["keyword_score"],
            }
            for f in data_files[:30]
        ],
    }
    # audit_pipeline.sh checks for exactly "STANDBY_REPORT.json"
    report_path = os.path.join(output_dir, "STANDBY_REPORT.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log.info(f"  Standby report saved: {report_path}")


# ============================================================================
# EXTRACT PIPELINE
# ============================================================================


def extract_training_data(tool_id, tool_cfg, global_cfg, output_dir):
    """
    Main extraction pipeline for a single tool.

    Args:
        tool_id: Tool identifier string
        tool_cfg: Tool config dict from pipeline_config.yaml (via get_tool_config)
        global_cfg: Global config dict from pipeline_config.yaml
        output_dir: Output directory for extracted data

    Returns:
        dict with status, sequences found, and any standby messages.
    """
    os.makedirs(output_dir, exist_ok=True)

    # --- Early exit if tool is explicitly marked STANDBY in pipeline_config.yaml ---
    if tool_cfg.get("standby", False):
        standby_msg = tool_cfg.get(
            "standby_reason",
            f"Tool '{tool_id}' is marked standby in pipeline_config.yaml.",
        )
        log.warning(f"[{tool_id}] STANDBY (from config): {standby_msg}")
        _write_standby_report(output_dir, tool_cfg, standby_msg, [])
        return {"status": "standby", "message": standby_msg}

    display_name = tool_cfg.get("display_name", tool_id)
    repo_url = tool_cfg.get("github_url", "")
    training_cfg = tool_cfg.get("training_data", {})

    # Resolve repos directory
    repos_dir = global_cfg.get("repos_dir")
    if not repos_dir:
        repos_dir = os.path.join(os.path.dirname(output_dir), "Tool_Repos")
    os.makedirs(repos_dir, exist_ok=True)

    repo_dir = os.path.join(repos_dir, tool_id)

    search_patterns = training_cfg.get(
        "search_patterns",
        ["**/*.csv", "**/*.tsv", "**/*.fasta", "**/*.fa", "**/*.txt"],
    )
    data_keywords = training_cfg.get(
        "data_keywords",
        ["train", "positive", "negative", "dataset"],
    )
    seq_hints = training_cfg.get(
        "sequence_column_hints",
        ["sequence", "seq", "peptide", "Sequence"],
    )
    label_hints = training_cfg.get(
        "label_column_hints",
        ["label", "class", "target", "Label", "Class"],
    )

    log.info("=" * 60)
    log.info(f"EXTRACTING TRAINING DATA: {display_name}")
    log.info("=" * 60)

    # Step 1: Clone
    log.info("\n--- Step 1: Cloning repository ---")
    if not repo_url:
        standby_msg = f"STANDBY: No github_url configured for tool '{tool_id}'."
        log.warning(standby_msg)
        _write_standby_report(output_dir, tool_cfg, standby_msg, [])
        return {"status": "standby", "message": standby_msg}

    if not clone_repo(repo_url, repo_dir):
        return {"status": "error", "message": "Failed to clone repository"}

    # Step 2: Search for data files
    log.info("\n--- Step 2: Searching for data files ---")
    data_files = search_data_files(repo_dir, search_patterns, data_keywords)

    log.info(f"  Found {len(data_files)} potential data files:")
    for df_info in data_files[:20]:
        log.info(
            f"    [{df_info['keyword_score']}] {df_info['rel_path']} "
            f"({df_info['size_mb']} MB)"
        )

    if not data_files:
        standby_msg = (
            f"STANDBY: No data files found in {display_name} repo.\n"
            f"Repo cloned at: {repo_dir}\n"
            f"Please check the repo manually and provide the path to training data."
        )
        log.warning(standby_msg)
        _write_standby_report(output_dir, tool_cfg, standby_msg, data_files)
        return {"status": "standby", "message": standby_msg}

    # Step 3: Extract sequences (label-aware)
    log.info("\n--- Step 3: Extracting sequences (label-aware) ---")
    label_source = training_cfg.get("label_source") or "column"
    log.info(f"  label_source: {label_source}")

    labeled_entries = extract_labeled_sequences(
        training_cfg, data_files, seq_hints, label_hints
    )

    # Build all_extractions for compatibility with provenance + split logic
    all_extractions = {}
    total_sequences = len(labeled_entries)
    for entry in labeled_entries:
        src_file = entry["source_file"]
        if src_file not in all_extractions:
            all_extractions[src_file] = {"sequences": [], "count": 0,
                                          "seq_col": None, "label_col": None,
                                          "keyword_score": 0}
        all_extractions[src_file]["sequences"].append((entry["header"], entry["sequence"]))
        all_extractions[src_file]["count"] += 1

    for rel_path, ext_info in all_extractions.items():
        log.info(f"  {rel_path}: {ext_info['count']} sequences extracted")

    if total_sequences == 0:
        standby_msg = (
            f"STANDBY: Data files found but no valid peptide sequences extracted.\n"
            f"Files found: {[f['rel_path'] for f in data_files[:10]]}\n"
            f"Repo at: {repo_dir}\n"
            f"Please check file formats and provide guidance."
        )
        log.warning(standby_msg)
        _write_standby_report(output_dir, tool_cfg, standby_msg, data_files)
        return {"status": "standby", "message": standby_msg}

    log.info(
        f"\n  Total sequences extracted: {total_sequences} "
        f"from {len(all_extractions)} files"
    )

    # Step 4: Classify data splits by path keywords
    log.info("\n--- Step 4: Classifying data splits ---")
    training_seqs = []
    test_seqs = []
    other_seqs = []

    for entry in labeled_entries:
        rel_path = entry["source_file"]
        path_lower = rel_path.lower()
        is_train = any(kw in path_lower for kw in ["train", "trn"])
        is_test = any(
            kw in path_lower
            for kw in ["test", "tst", "independent", "ind", "valid"]
        )
        if is_train:
            training_seqs.append(entry)
        elif is_test:
            test_seqs.append(entry)
        else:
            other_seqs.append(entry)

    log.info(f"  Training: {len(training_seqs)} sequences")
    log.info(f"  Test/Val: {len(test_seqs)} sequences")
    log.info(f"  Other:    {len(other_seqs)} sequences")

    # If no clear training split, combine all as potential training data
    if not training_seqs:
        log.warning("  No files clearly labeled as training data.")
        log.warning("  Treating ALL extracted sequences as potential training data.")
        training_seqs = test_seqs + other_seqs
        if total_sequences < 50:
            standby_msg = (
                f"STANDBY: Only {total_sequences} sequences found and none clearly "
                f"labeled as training data.\n"
                f"Extracted from: {list(all_extractions.keys())}\n"
                f"Please verify these are the correct training sequences."
            )
            log.warning(standby_msg)
            _write_standby_report(output_dir, tool_cfg, standby_msg, data_files)

    # Step 5: Deduplicate and export
    log.info("\n--- Step 5: Deduplicating and exporting ---")

    seen = set()
    unique_training = []
    for entry in training_seqs:
        seq = entry["sequence"]
        if seq not in seen:
            seen.add(seq)
            unique_training.append(entry)

    log.info(f"  Unique training sequences: {len(unique_training)}")

    # Label counts
    n_pos = sum(1 for e in unique_training if e.get("label") == "positive")
    n_neg = sum(1 for e in unique_training if e.get("label") == "negative")
    n_unk = len(unique_training) - n_pos - n_neg
    log.info(f"  Labels — positive: {n_pos}, negative: {n_neg}, unknown: {n_unk}")

    # Export ALL-sequences FASTA
    fasta_path = os.path.join(output_dir, f"training_{tool_id}.fasta")
    with open(fasta_path, "w") as f:
        for i, entry in enumerate(unique_training):
            lbl = entry.get("label", "unknown")
            f.write(
                f">{tool_id}_train_{i}|label={lbl}|{entry['header']}|src={entry['source_file']}\n"
            )
            f.write(f"{entry['sequence']}\n")
    log.info(f"  FASTA (all) saved: {fasta_path}")

    # Export POSITIVE-only FASTA (for CD-HIT-2D leakage analysis)
    pos_entries = [e for e in unique_training if e.get("label") == "positive"]
    if not pos_entries:
        # If no labeled positives, fall back to all sequences (conservative)
        log.warning(
            f"  No positives labeled — using ALL sequences for leakage FASTA "
            f"(label_source='{label_source}')"
        )
        pos_entries = unique_training

    fasta_pos_path = os.path.join(output_dir, f"training_{tool_id}_positive.fasta")
    with open(fasta_pos_path, "w") as f:
        for i, entry in enumerate(pos_entries):
            f.write(
                f">{tool_id}_trainpos_{i}|{entry['header']}|src={entry['source_file']}\n"
            )
            f.write(f"{entry['sequence']}\n")
    log.info(f"  FASTA (positives only, n={len(pos_entries)}) saved: {fasta_pos_path}")

    # Export CSV summary
    csv_path = os.path.join(output_dir, f"training_{tool_id}_summary.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Sequence", "Length", "Label", "Source_File", "Original_Header"])
        for i, entry in enumerate(unique_training):
            writer.writerow([
                f"{tool_id}_train_{i}",
                entry["sequence"],
                len(entry["sequence"]),
                entry.get("label", "unknown"),
                entry["source_file"],
                entry["header"],
            ])
    log.info(f"  CSV saved: {csv_path}")

    # Step 6: Provenance
    log.info("\n--- Step 6: Generating provenance ---")
    provenance = {
        "script": "extract_training_data.py",
        "script_version": SCRIPT_VERSION,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": display_name,
        "tool_id": tool_id,
        "repo_url": repo_url,
        "repo_dir": repo_dir,
        "files_found": len(data_files),
        "files_with_sequences": len(all_extractions),
        "file_details": {
            rel_path: {
                "count": ext_info["count"],
                "seq_col": ext_info["seq_col"],
                "label_col": ext_info["label_col"],
                "keyword_score": ext_info["keyword_score"],
            }
            for rel_path, ext_info in all_extractions.items()
        },
        "split_counts": {
            "training": len(training_seqs),
            "test_validation": len(test_seqs),
            "other": len(other_seqs),
        },
        "unique_training_sequences": len(unique_training),
        "label_source": label_source,
        "label_counts": {"positive": n_pos, "negative": n_neg, "unknown": n_unk},
        "output_files": {
            "fasta": fasta_path,
            "fasta_positives": fasta_pos_path,
            "csv": csv_path,
        },
    }

    prov_file = os.path.join(
        output_dir,
        f"PROVENANCE_extract_{tool_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(prov_file, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)
    log.info(f"  Provenance saved: {prov_file}")

    log.info(f"\n{'=' * 60}")
    log.info(f"EXTRACTION COMPLETE: {display_name}")
    log.info(f"  Training sequences: {len(unique_training)}")
    log.info(f"{'=' * 60}")

    return {
        "status": "success",
        "tool": display_name,
        "training_sequences": len(unique_training),
        "fasta_path": fasta_path,
        "fasta_positive_path": fasta_pos_path,
        "csv_path": csv_path,
        "provenance_path": prov_file,
    }


# ============================================================================
# CLI
# ============================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract training data from bioactivity prediction tool repositories."
    )
    parser.add_argument(
        "--tool",
        required=True,
        help="Tool ID to extract training data for (must exist in pipeline_config.yaml).",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to pipeline_config.yaml.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for extracted training data.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Load config
    pipeline_cfg = load_pipeline_config(args.config)
    global_cfg = pipeline_cfg.get("global", {})

    # Get tool-specific config
    try:
        tool_cfg = get_tool_config(args.tool, pipeline_cfg)
    except KeyError as e:
        log.error(str(e))
        sys.exit(1)

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    result = extract_training_data(args.tool, tool_cfg, global_cfg, output_dir)

    if result["status"] == "standby":
        log.warning(f"\n*** {args.tool}: STANDBY - User intervention needed ***")
        log.warning(result["message"])
    elif result["status"] == "error":
        log.error(f"\n*** {args.tool}: ERROR ***")
        log.error(result["message"])
        sys.exit(1)

    # Summary
    log.info("\n" + "=" * 60)
    log.info("EXTRACTION SUMMARY")
    log.info("=" * 60)
    status = result["status"].upper()
    if result["status"] == "success":
        log.info(f"  {args.tool}: {status} ({result['training_sequences']} sequences)")
    else:
        log.info(f"  {args.tool}: {status}")


if __name__ == "__main__":
    main()
