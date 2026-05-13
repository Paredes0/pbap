#!/usr/bin/env python3
"""
auditoria_validation.py
========================
Per-tool QC/audit script. Reads from audit_lib and pipeline configs.
Produces Shannon index, KS test, chi-squared AA, habitat diversity report.

Usage (called by audit_pipeline.sh):
    python auditoria_validation.py --tool toxinpred3 --config pipeline_config.yaml --output-dir Tool_Audits/toxinpred3
"""

import argparse
import json
import logging
import os
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from audit_lib.config import load_pipeline_config, get_tool_config
from audit_lib.sequence_utils import find_column, STANDARD_AA, DEFAULT_LENGTH_BINS
from audit_lib.provenance import generate_provenance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

STANDARD_AA_LIST = sorted(STANDARD_AA)


# ============================================================================
# HELPERS
# ============================================================================

def _shannon_index(series):
    counts = series.value_counts()
    total = counts.sum()
    if total == 0:
        return 0.0
    proportions = counts / total
    return -sum(p * np.log(p) for p in proportions if p > 0)


def _compute_aa_freq(sequences):
    total = Counter()
    n_total = 0
    for seq in sequences:
        seq = str(seq).strip().upper()
        for c in seq:
            if c in STANDARD_AA:
                total[c] += 1
                n_total += 1
    return {aa: total[aa] / n_total if n_total > 0 else 0 for aa in STANDARD_AA_LIST}


# ============================================================================
# AUDIT FUNCTIONS
# ============================================================================

def audit_basic_stats(df, label="Dataset"):
    stats = {"label": label, "total_entries": len(df)}
    seq_col = find_column(df, "Sequence", "seq")
    if seq_col:
        unique_seqs = df[seq_col].nunique()
        stats["unique_sequences"] = unique_seqs
        stats["duplicates"] = len(df) - unique_seqs
    len_col = find_column(df, "Length", "length")
    if len_col:
        stats["length_min"] = int(df[len_col].min())
        stats["length_max"] = int(df[len_col].max())
        stats["length_mean"] = round(float(df[len_col].mean()), 1)
        stats["length_std"] = round(float(df[len_col].std()), 1)
    org_col = find_column(df, "Organism", "organism")
    if org_col:
        stats["unique_organisms"] = int(df[org_col].nunique())
    log.info(f"\n{'='*60}")
    log.info(f"BASIC STATS: {label}")
    log.info(f"{'='*60}")
    for k, v in stats.items():
        if k != "label":
            log.info(f"  {k}: {v}")
    return stats


def audit_length_distribution(df, label="Dataset", bins=None):
    if bins is None:
        bins = DEFAULT_LENGTH_BINS
    len_col = find_column(df, "Length", "length")
    if not len_col:
        return {}
    log.info(f"\n--- Length Distribution: {label} ---")
    bin_counts = {}
    for lo, hi in bins:
        n = int(((df[len_col] >= lo) & (df[len_col] <= hi)).sum())
        pct = n / len(df) * 100 if len(df) > 0 else 0
        log.info(f"  {lo:3d}-{hi:3d}: {n:4d} ({pct:5.1f}%)")
        bin_counts[f"{lo}-{hi}"] = n
    return bin_counts


def audit_habitat_distribution(df, label="Dataset"):
    hab_col = find_column(df, "Habitat", "habitat")
    if not hab_col:
        return {}
    log.info(f"\n--- Habitat Distribution: {label} ---")
    result = {}
    for hab, count in df[hab_col].value_counts().items():
        pct = count / len(df) * 100
        log.info(f"  {hab:20s}: {count:4d} ({pct:5.1f}%)")
        result[hab] = {"count": int(count), "pct": round(pct, 1)}
    for habitat, threshold in [("marino", 15), ("terrestre", 15)]:
        pct = (df[hab_col] == habitat).sum() / len(df) * 100 if len(df) > 0 else 0
        if pct < threshold:
            log.warning(f"  *** {habitat} below {threshold}% threshold: {pct:.1f}% ***")
    return result


def audit_taxonomic_diversity(df, label="Dataset"):
    log.info(f"\n--- Taxonomic Diversity: {label} ---")
    result = {}
    grp_col = find_column(df, "Taxonomic_Group", "taxonomic")
    org_col = find_column(df, "Organism", "organism")
    if grp_col:
        log.info("  By taxonomic group:")
        for grp, count in df[grp_col].value_counts().items():
            pct = count / len(df) * 100
            log.info(f"    {grp:30s}: {count:4d} ({pct:5.1f}%)")
        shannon_grp = _shannon_index(df[grp_col])
        max_sh = np.log(df[grp_col].nunique()) if df[grp_col].nunique() > 1 else 1
        evenness = shannon_grp / max_sh if max_sh > 0 else 0
        log.info(f"\n  Shannon index (groups): {shannon_grp:.3f}")
        log.info(f"  Evenness (J'):         {evenness:.3f}")
        result["shannon_groups"] = round(shannon_grp, 3)
        result["evenness"] = round(evenness, 3)
        if evenness < 0.6:
            log.warning(f"  *** Low evenness ({evenness:.3f}) ***")
    if org_col:
        shannon_sp = _shannon_index(df[org_col])
        result["shannon_species"] = round(shannon_sp, 3)
        result["max_per_species"] = int(df[org_col].value_counts().max())
        log.info(f"  Shannon index (species): {shannon_sp:.3f}")
    return result


def audit_aa_composition(df, label="Dataset", df_compare=None, compare_label="Compare"):
    seq_col = find_column(df, "Sequence", "seq")
    if not seq_col:
        return {}
    log.info(f"\n--- AA Composition: {label} ---")
    freq1 = _compute_aa_freq(df[seq_col])
    result = {"frequencies": freq1}
    if df_compare is not None:
        seq_col2 = find_column(df_compare, "Sequence", "seq")
        if seq_col2:
            freq2 = _compute_aa_freq(df_compare[seq_col2])
            n1 = sum(len(str(s)) for s in df[seq_col])
            n2 = sum(len(str(s)) for s in df_compare[seq_col2])
            n_total = n1 + n2
            chi2 = 0
            if n_total > 0:
                for aa in STANDARD_AA_LIST:
                    o1 = freq1.get(aa, 0) * n1
                    o2 = freq2.get(aa, 0) * n2
                    row_total = o1 + o2
                    e1 = row_total * n1 / n_total
                    e2 = row_total * n2 / n_total
                    if e1 > 0:
                        chi2 += (o1 - e1)**2 / e1
                    if e2 > 0:
                        chi2 += (o2 - e2)**2 / e2
            result["chi2_vs_compare"] = round(chi2, 2)
            log.info(f"  Chi-squared vs {compare_label}: {chi2:.2f}")
            if chi2 > 40:
                log.warning(f"  *** Significant AA composition difference ***")
    return result


def audit_ks_length_test(df1, df2, label1="Positives", label2="Negatives"):
    try:
        from scipy import stats
    except ImportError:
        log.warning("  scipy not available - skipping KS test")
        return {}
    len_col1 = find_column(df1, "Length", "length")
    len_col2 = find_column(df2, "Length", "length")
    if not len_col1 or not len_col2:
        return {}
    ks_stat, p_value = stats.ks_2samp(df1[len_col1], df2[len_col2])
    log.info(f"\n--- KS Test: {label1} vs {label2} ---")
    log.info(f"  KS statistic: {ks_stat:.4f}")
    log.info(f"  p-value:      {p_value:.6f}")
    if p_value < 0.05:
        log.warning(f"  *** Significant difference in length distributions ***")
    return {"ks_statistic": round(ks_stat, 4), "p_value": round(p_value, 6)}


def audit_leakage_grades(leakage_csv, label="Dataset"):
    log.info(f"\n--- Leakage Grade Summary: {label} ---")
    df_leak = pd.read_csv(leakage_csv)
    grade_col = find_column(df_leak, "Grade", "grade")
    if not grade_col:
        return {}
    result = {}
    for grade in ["Gold", "Silver", "Bronze", "Red"]:
        count = int((df_leak[grade_col] == grade).sum())
        pct = count / len(df_leak) * 100 if len(df_leak) > 0 else 0
        marker = " ***" if grade == "Red" and pct > 10 else ""
        log.info(f"  {grade:8s}: {count:4d} ({pct:5.1f}%){marker}")
        result[grade] = {"count": count, "pct": round(pct, 1)}
    return result


def audit_sequence_validity(df, label="Dataset"):
    seq_col = find_column(df, "Sequence", "seq")
    if not seq_col:
        return {}
    log.info(f"\n--- Sequence Validity: {label} ---")
    invalid = 0
    non_standard = Counter()
    for seq in df[seq_col]:
        seq = str(seq).strip().upper()
        for c in seq:
            if c not in STANDARD_AA:
                non_standard[c] += 1
                invalid += 1
                break
    if invalid:
        log.warning(f"  *** {invalid} sequences with non-standard AAs ***")
    else:
        log.info(f"  All {len(df)} sequences valid")
    return {"invalid_count": invalid, "non_standard_chars": dict(non_standard.most_common(10))}


# ============================================================================
# MAIN
# ============================================================================

def run_audit(tool_id, pipeline_config_path, output_dir):
    cfg = load_pipeline_config(pipeline_config_path)
    tool_cfg = get_tool_config(tool_id, cfg)
    category = tool_cfg["category"]

    # Resolve paths relative to output_dir structure
    # output_dir = .../Tool_Audits/tool_id (from audit_pipeline.sh)
    tool_dir = output_dir
    base_dir = os.path.normpath(os.path.join(tool_dir, "..", ".."))
    pool_csv = os.path.join(base_dir, "Category_Pools", f"{category}_pool.csv")
    neg_csv = os.path.join(tool_dir, "test_negatives", f"negatives_{tool_id}.csv")
    leakage_csv = os.path.join(tool_dir, "leakage_report", f"leakage_{tool_id}_classifications.csv")

    log.info("=" * 60)
    log.info(f"VALIDATION AUDIT: {tool_cfg['display_name']} ({tool_id})")
    log.info(f"  Category: {category}")
    log.info(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    log.info("=" * 60)

    report = {
        "tool_id": tool_id,
        "display_name": tool_cfg["display_name"],
        "category": category,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Audit positives
    df_pos = None
    if os.path.exists(pool_csv):
        df_pos = pd.read_csv(pool_csv)
        report["positives_basic"] = audit_basic_stats(df_pos, "Positives")
        report["positives_validity"] = audit_sequence_validity(df_pos, "Positives")
        report["positives_length"] = audit_length_distribution(df_pos, "Positives")
        report["positives_habitat"] = audit_habitat_distribution(df_pos, "Positives")
        report["positives_taxonomy"] = audit_taxonomic_diversity(df_pos, "Positives")
        report["positives_aa"] = audit_aa_composition(df_pos, "Positives")
    else:
        log.warning(f"  Pool CSV not found: {pool_csv}")

    # Audit negatives
    df_neg = None
    if os.path.exists(neg_csv):
        df_neg = pd.read_csv(neg_csv)
        report["negatives_basic"] = audit_basic_stats(df_neg, "Negatives")
        report["negatives_length"] = audit_length_distribution(df_neg, "Negatives")
        report["negatives_habitat"] = audit_habitat_distribution(df_neg, "Negatives")
        report["negatives_taxonomy"] = audit_taxonomic_diversity(df_neg, "Negatives")

    # Cross-comparisons
    if df_pos is not None and df_neg is not None:
        report["aa_comparison"] = audit_aa_composition(df_pos, "Positives", df_neg, "Negatives")
        report["ks_test"] = audit_ks_length_test(df_pos, df_neg, "Positives", "Negatives")

    # Leakage grades
    if os.path.exists(leakage_csv):
        report["leakage_grades"] = audit_leakage_grades(leakage_csv, tool_cfg["display_name"])

    # Save report JSON
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"audit_report_{tool_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"\nAudit report saved: {report_path}")

    generate_provenance(
        output_dir=output_dir,
        script_name="auditoria_validation",
        tool_id=tool_id,
        parameters={"category": category},
        output_stats={"report_path": report_path},
    )

    log.info(f"\n{'='*60}")
    log.info("AUDIT COMPLETE")
    log.info(f"{'='*60}")
    return report


def parse_args():
    parser = argparse.ArgumentParser(description="Per-tool QC audit.")
    parser.add_argument("--tool", required=True, help="Tool ID to audit.")
    parser.add_argument("--config", default="pipeline_config.yaml",
                        help="Path to pipeline_config.yaml.")
    parser.add_argument("--output-dir", default=None, help="Output directory.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output_dir = args.output_dir or "."
    run_audit(args.tool, args.config, output_dir)
