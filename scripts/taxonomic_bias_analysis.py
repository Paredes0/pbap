#!/usr/bin/env python3
"""
taxonomic_bias_analysis.py
==========================
Analyzes prediction performance stratified by taxonomic origin and habitat.

Answers the key question: does the tool perform differently on sequences from
different biological groups (vertebrate vs invertebrate, marine vs terrestrial,
and combinations thereof)? This reveals training-set biases that affect
generalization — critical when applying the tool to novel organisms like octopus
(invertebrate, marine).

Statistical approach
--------------------
- Fisher's exact test for each group vs rest (appropriate for small N).
- Within each comparison family (Taxonomic_Group, BroadGroup, Vert/Invert,
  Marine/Terrestre) all p-values are corrected for multiple comparisons via
  both Bonferroni (conservative) and Benjamini-Hochberg FDR (recommended).
- Groups with n < MIN_N_RELIABLE are flagged as LOW_POWER — their point
  estimates are shown but significance conclusions are unreliable.
- Wilson 95% CI for sensitivity proportions accounts for N without assuming
  normality.

Called standalone or from audit_pipeline.sh:
    python taxonomic_bias_analysis.py \\
        --tool toxinpred3 \\
        --config pipeline_config.yaml \\
        --output-dir Tool_Audits/toxinpred3/predictions
"""

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, chi2_contingency

from audit_lib.config import load_pipeline_config, get_tool_config
from audit_lib.provenance import generate_provenance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_NAME    = "taxonomic_bias_analysis.py"
SCRIPT_VERSION = "1.0.0"
MIN_N_RELIABLE = 10   # groups below this are flagged LOW_POWER


# =============================================================================
# Classification helpers
# =============================================================================

VERTEBRATA_MARKER = "Vertebrata"


def _is_vertebrate(lineage: str) -> bool:
    return isinstance(lineage, str) and VERTEBRATA_MARKER in lineage


def _derive_broad_group(row) -> str:
    hab = str(row.get("Habitat", "")).lower()
    tg  = str(row.get("Taxonomic_Group", ""))
    lin = str(row.get("Lineage", ""))

    if tg in ("Plantas_Hongos",):
        return "Plantas_Hongos"

    vert   = _is_vertebrate(lin)
    marine = (hab == "marino")

    if vert and not marine:
        return "Vert_Terrestre"
    if vert and marine:
        return "Vert_Marino"
    if not vert and marine:
        return "Invert_Marino"
    return "Invert_Terrestre"


# =============================================================================
# Statistical helpers
# =============================================================================

def _wilson_ci(successes: int, n: int, z: float = 1.96):
    """Wilson score 95% confidence interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p      = successes / n
    denom  = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (round(max(0.0, centre - margin), 4),
            round(min(1.0, centre + margin), 4))


def _safe_mcc(tp, tn, fp, fn):
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return (tp * tn - fp * fn) / denom if denom > 0 else 0.0


def _metrics_for_pos_neg(df_pos_sub, df_neg):
    """Metrics for df_pos_sub positives + df_neg negatives."""
    df_sub = pd.concat([df_pos_sub, df_neg], ignore_index=True)
    tp = int(((df_sub["True_Label"] == 1) & (df_sub["Predicted"] == 1)).sum())
    fn = int(((df_sub["True_Label"] == 1) & (df_sub["Predicted"] == 0)).sum())
    tn = int(((df_sub["True_Label"] == 0) & (df_sub["Predicted"] == 0)).sum())
    fp = int(((df_sub["True_Label"] == 0) & (df_sub["Predicted"] == 1)).sum())
    n_pos = tp + fn
    n_neg = tn + fp
    sens  = tp / n_pos if n_pos > 0 else 0.0
    spec  = tn / n_neg if n_neg > 0 else 0.0
    acc   = (tp + tn) / (n_pos + n_neg) if (n_pos + n_neg) > 0 else 0.0
    mcc   = _safe_mcc(tp, tn, fp, fn)
    ci    = _wilson_ci(tp, n_pos)
    return {
        "n_positives": n_pos,
        "n_negatives": n_neg,
        "TP": tp, "FN": fn, "TN": tn, "FP": fp,
        "sensitivity":       round(sens, 4),
        "sensitivity_ci95":  list(ci),
        "specificity":       round(spec, 4),
        "accuracy":          round(acc, 4),
        "mcc":               round(mcc, 4),
        "low_power":         n_pos < MIN_N_RELIABLE,
    }


def _fisher_pair(tp_a, fn_a, tp_b, fn_b):
    """Fisher's exact test on a 2x2 sensitivity table."""
    if (tp_a + fn_a) == 0 or (tp_b + fn_b) == 0:
        return None, None
    try:
        odds, p = fisher_exact([[tp_a, fn_a], [tp_b, fn_b]])
        return round(float(odds), 4), round(float(p), 8)
    except Exception:
        return None, None


def _bh_correction(p_values):
    """
    Benjamini-Hochberg FDR correction.
    Returns array of adjusted p-values (same order as input).
    Handles None values by passing them through unchanged.
    """
    n      = len(p_values)
    valid  = [(i, p) for i, p in enumerate(p_values) if p is not None]
    adj    = [None] * n
    if not valid:
        return adj
    idxs, pvals = zip(*valid)
    pvals  = np.array(pvals, dtype=float)
    order  = np.argsort(pvals)
    ranks  = np.empty_like(order)
    ranks[order] = np.arange(1, len(order) + 1)
    bh     = np.minimum(1.0, pvals * len(pvals) / ranks)
    # Enforce monotonicity (BH requires cumulative min from right)
    for i in range(len(bh) - 2, -1, -1):
        bh[order[i]] = min(bh[order[i]], bh[order[i + 1]])
    for orig_i, bh_val in zip(idxs, bh):
        adj[orig_i] = round(float(bh_val), 8)
    return adj


def _bonferroni(p_values):
    n_valid = sum(1 for p in p_values if p is not None)
    return [
        round(min(1.0, p * n_valid), 8) if p is not None else None
        for p in p_values
    ]


def _chi2_across_groups(df_pos, group_col):
    """Chi-squared heterogeneity test across all groups (min 5 per cell)."""
    table = []
    for grp in df_pos[group_col].unique():
        sub = df_pos[df_pos[group_col] == grp]
        if len(sub) < 5:
            continue
        tp = int((sub["Predicted"] == 1).sum())
        fn = int((sub["Predicted"] == 0).sum())
        if tp + fn > 0:
            table.append([tp, fn])
    if len(table) < 2:
        return None, None, None
    try:
        chi2, p, dof, _ = chi2_contingency(table)
        return round(float(chi2), 3), round(float(p), 6), int(dof)
    except Exception:
        return None, None, None


def _sig_label(p_adj):
    if p_adj is None:
        return ""
    if p_adj < 0.001: return "***"
    if p_adj < 0.01:  return "**"
    if p_adj < 0.05:  return "*"
    return ""


# =============================================================================
# Per-family analysis with correction
# =============================================================================

def _analyze_family(df_pos_full, df_neg, group_col, label, order=None):
    """
    For a given grouping column: compute per-group metrics, Fisher vs rest,
    and apply Bonferroni + BH correction within the family.

    Returns dict of {group_name: {metrics + fisher_raw + fisher_bonf + fisher_bh}}.
    """
    groups  = order if order else sorted(df_pos_full[group_col].unique())
    groups  = [g for g in groups if g in df_pos_full[group_col].values]

    # Pass 1: compute metrics and raw p-values
    entries   = {}
    raw_p     = []
    raw_or    = []

    for grp in groups:
        sub = df_pos_full[df_pos_full[group_col] == grp]
        m   = _metrics_for_pos_neg(sub, df_neg)

        # Fisher: group vs all other positives
        tp_in  = m["TP"]
        fn_in  = m["FN"]
        other  = df_pos_full[df_pos_full[group_col] != grp]
        tp_out = int((other["Predicted"] == 1).sum())
        fn_out = int((other["Predicted"] == 0).sum())
        or_, p_ = _fisher_pair(tp_in, fn_in, tp_out, fn_out)

        entries[grp]  = {**m, "fisher_or": or_, "fisher_p_raw": p_}
        raw_p.append(p_)
        raw_or.append(or_)

    # Pass 2: apply corrections
    bonf = _bonferroni(raw_p)
    bh   = _bh_correction(raw_p)

    for i, grp in enumerate(groups):
        entries[grp]["fisher_p_bonferroni"] = bonf[i]
        entries[grp]["fisher_p_bh"]         = bh[i]

    # Chi2 heterogeneity
    chi2, pchi, dof = _chi2_across_groups(df_pos_full, group_col)

    return entries, {"chi2": chi2, "p": pchi, "dof": dof}


def _log_family(entries, chi2_result, title, group_width=26):
    log.info("\n--- %s ---", title)
    w = group_width
    log.info("  %-*s %5s  %7s  %12s  %7s  %6s  %10s  %10s",
             w, "Group", "n", "Sens", "CI-95%", "MCC",
             "OR", "p_raw", "p_BH")
    log.info("  " + "-" * (w + 72))
    for grp, m in entries.items():
        ci   = m["sensitivity_ci95"]
        lp   = " [LOW_POWER]" if m["low_power"] else ""
        sig  = _sig_label(m["fisher_p_bh"])
        or_s = f"{m['fisher_or']:.3f}" if m["fisher_or"] is not None else "  N/A"
        pr_s = f"{m['fisher_p_raw']:.5f}"  if m["fisher_p_raw"]  is not None else "      N/A"
        pb_s = f"{m['fisher_p_bh']:.5f}"   if m["fisher_p_bh"]   is not None else "      N/A"
        log.info("  %-*s %5d  %7.4f  [%5.3f-%5.3f]  %7.4f  %6s  %10s  %10s  %s%s",
                 w, grp, m["n_positives"], m["sensitivity"],
                 ci[0], ci[1], m["mcc"],
                 or_s, pr_s, pb_s, sig, lp)
    if chi2_result["chi2"] is not None:
        log.info("  Chi2 heterogeneity: χ²=%.3f  p=%.6f  dof=%s",
                 chi2_result["chi2"], chi2_result["p"], chi2_result["dof"])
    else:
        log.info("  Chi2 heterogeneity: N/A (insufficient groups)")


# =============================================================================
# Main analysis
# =============================================================================

def run_taxonomic_bias_analysis(tool_id, pipeline_config, output_dir,
                                grade_filter=("Gold",)):
    cfg      = load_pipeline_config(pipeline_config)
    tool_cfg = get_tool_config(tool_id, cfg)
    category = tool_cfg["category"]

    # --- Locate required files ---
    pred_path  = os.path.join(output_dir, f"predictions_{tool_id}.csv")
    truth_path = os.path.join(output_dir, f"ground_truth_{tool_id}.csv")
    tool_dir   = os.path.dirname(output_dir)
    base_dir   = os.path.normpath(os.path.join(tool_dir, "../.."))
    pool_path  = os.path.join(base_dir, "Category_Pools", f"{category}_pool.csv")

    for label, path in [("predictions", pred_path),
                        ("ground_truth", truth_path),
                        ("pool_csv",     pool_path)]:
        if not os.path.isfile(path):
            log.error("Missing file (%s): %s", label, path)
            return {"status": "error", "message": f"Missing {label}: {path}"}

    # --- Load & merge ---
    pred_cfg  = tool_cfg.get("run_command", {}).get("output_parsing", {})
    id_col    = pred_cfg.get("id_column",         "Subject")
    pred_col  = pred_cfg.get("prediction_column", "Prediction")
    pos_label = pred_cfg.get("positive_label",    "Toxin")

    df_truth = pd.read_csv(truth_path)
    df_pred  = pd.read_csv(pred_path)
    df_pool  = pd.read_csv(pool_path)

    df = df_truth.merge(
        df_pred[[id_col, pred_col]].rename(columns={id_col: "ID"}),
        on="ID", how="left"
    )
    df["Predicted"] = (df[pred_col] == pos_label).astype(int)

    # All positives enriched with pool metadata + grade column
    df_pos_all = df[df["True_Label"] == 1].merge(
        df_pool[["ID", "Organism", "Habitat", "Taxonomic_Group", "Lineage"]],
        on="ID", how="left"
    ).copy()
    df_neg = df[df["True_Label"] == 0].copy()

    # Derived columns
    df_pos_all["BroadGroup"]   = df_pos_all.apply(_derive_broad_group, axis=1)
    df_pos_all["IsVertebrate"] = df_pos_all["Lineage"].apply(_is_vertebrate)
    df_pos_all["IsMarine"]     = df_pos_all["Habitat"].str.lower() == "marino"

    n_pos_all = len(df_pos_all)

    # --- Grade filter (default: Gold only) ---
    # Only Gold sequences are independent of training data; Silver/Bronze/Red
    # are similar to training and inflate sensitivity artificially.
    # Taxonomic bias measured on all grades would confound leakage with taxonomy.
    if grade_filter and "Grade" in df_pos_all.columns:
        df_pos_full = df_pos_all[df_pos_all["Grade"].isin(grade_filter)].copy()
        grade_label = "+".join(sorted(grade_filter))
        n_excluded  = n_pos_all - len(df_pos_full)
        log.info("  Grade filter: %s  (%d/%d positivos, %d excluidos por leakage)",
                 grade_label, len(df_pos_full), n_pos_all, n_excluded)
    else:
        df_pos_full = df_pos_all.copy()
        grade_label = "All"
        log.info("  Grade filter: None (usando todos los positivos — incluye secuencias con leakage)")

    n_pos = len(df_pos_full)
    n_neg = len(df_neg)
    log.info("=" * 70)
    log.info("TAXONOMIC BIAS ANALYSIS: %s  [grades=%s]", tool_id, grade_label)
    log.info("  Positivos usados: %d/%d  |  Negativos: %d", n_pos, n_pos_all, n_neg)
    log.info("  Corrección múltiples comparaciones: Bonferroni + BH-FDR")
    log.info("  Umbral baja potencia: n < %d  (Wilson CI-95%%)", MIN_N_RELIABLE)
    log.info("=" * 70)

    results = {
        "grade_filter":    list(grade_filter) if grade_filter else "All",
        "n_positives_used": n_pos,
        "n_positives_total": n_pos_all,
        "n_negatives":       n_neg,
        "n_excluded_by_leakage": n_pos_all - n_pos,
    }

    # ==========================================================================
    # 1. Per Taxonomic_Group
    # ==========================================================================
    tg_entries, tg_chi2 = _analyze_family(
        df_pos_full, df_neg, "Taxonomic_Group", "Taxonomic_Group"
    )
    _log_family(tg_entries, tg_chi2, "1. Por Taxonomic_Group", group_width=26)
    results["per_taxonomic_group"] = tg_entries
    results["chi2_taxonomic_group"] = tg_chi2

    # ==========================================================================
    # 2. BroadGroup (4-way + Plantas_Hongos)
    # ==========================================================================
    BROAD_ORDER = ["Vert_Terrestre", "Vert_Marino", "Invert_Terrestre",
                   "Invert_Marino", "Plantas_Hongos"]
    broad_entries, broad_chi2 = _analyze_family(
        df_pos_full, df_neg, "BroadGroup", "BroadGroup", order=BROAD_ORDER
    )
    _log_family(broad_entries, broad_chi2,
                "2. Grupo amplio (Vert/Invert × Marino/Terrestre)", group_width=20)
    results["per_broad_group"] = broad_entries
    results["chi2_broad_group"] = broad_chi2

    # ==========================================================================
    # 3. Vertebrata vs Invertebrata (binary, single Fisher, no multi-correction)
    # ==========================================================================
    log.info("\n--- 3. Vertebrata vs Invertebrata ---")
    vert_results = {}
    for label_k, mask in [("Vertebrata",   df_pos_full["IsVertebrate"]),
                          ("Invertebrata", ~df_pos_full["IsVertebrate"])]:
        sub = df_pos_full[mask]
        m   = _metrics_for_pos_neg(sub, df_neg)
        vert_results[label_k] = m
        ci  = m["sensitivity_ci95"]
        lp  = " [LOW_POWER]" if m["low_power"] else ""
        log.info("  %-16s n=%4d  Sens=%.4f [%.3f-%.3f]  MCC=%.4f%s",
                 label_k, m["n_positives"], m["sensitivity"],
                 ci[0], ci[1], m["mcc"], lp)

    v  = df_pos_full[df_pos_full["IsVertebrate"]]
    iv = df_pos_full[~df_pos_full["IsVertebrate"]]
    tp_v, fn_v = int((v["Predicted"]==1).sum()),  int((v["Predicted"]==0).sum())
    tp_i, fn_i = int((iv["Predicted"]==1).sum()), int((iv["Predicted"]==0).sum())
    or_vi, p_vi = _fisher_pair(tp_v, fn_v, tp_i, fn_i)
    sig = _sig_label(p_vi)
    log.info("  Fisher (Vert vs Invert): OR=%.3f  p=%.6f  %s  (sin corrección — test único)",
             or_vi or 0, p_vi or 1, sig)
    results["vertebrata_vs_invertebrata"] = vert_results
    results["fisher_vert_vs_invert"] = {"or": or_vi, "p": p_vi, "note": "single test, no correction needed"}

    # ==========================================================================
    # 4. Marino vs Terrestre (binary)
    # ==========================================================================
    log.info("\n--- 4. Marino vs Terrestre ---")
    hab_results = {}
    mar_sub  = df_pos_full[df_pos_full["IsMarine"]]
    terr_sub = df_pos_full[df_pos_full["Habitat"].str.lower() == "terrestre"]
    for label_k, sub in [("Marino", mar_sub), ("Terrestre", terr_sub)]:
        if len(sub) == 0:
            continue
        m  = _metrics_for_pos_neg(sub, df_neg)
        hab_results[label_k] = m
        ci = m["sensitivity_ci95"]
        lp = " [LOW_POWER]" if m["low_power"] else ""
        log.info("  %-12s n=%4d  Sens=%.4f [%.3f-%.3f]  MCC=%.4f%s",
                 label_k, m["n_positives"], m["sensitivity"],
                 ci[0], ci[1], m["mcc"], lp)
    tp_m, fn_m = int((mar_sub["Predicted"]==1).sum()),  int((mar_sub["Predicted"]==0).sum())
    tp_t, fn_t = int((terr_sub["Predicted"]==1).sum()), int((terr_sub["Predicted"]==0).sum())
    or_mt, p_mt = _fisher_pair(tp_m, fn_m, tp_t, fn_t)
    sig = _sig_label(p_mt)
    log.info("  Fisher (Marino vs Terrestre): OR=%.3f  p=%.6f  %s  (sin corrección — test único)",
             or_mt or 0, p_mt or 1, sig)
    results["marino_vs_terrestre"] = hab_results
    results["fisher_marino_vs_terrestre"] = {"or": or_mt, "p": p_mt, "note": "single test, no correction needed"}

    # ==========================================================================
    # 5. Detalle Invertebrado Marino (relevancia pulpo)
    # ==========================================================================
    log.info("\n--- 5. Detalle Invertebrado Marino [relevante para pulpo] ---")
    inv_mar = df_pos_full[df_pos_full["BroadGroup"] == "Invert_Marino"]
    log.info("  Total Inv_Marino: %d  (grupos: %s)",
             len(inv_mar), list(inv_mar["Taxonomic_Group"].unique()))

    if len(inv_mar) > 0 and inv_mar["Taxonomic_Group"].nunique() > 1:
        im_entries, im_chi2 = _analyze_family(inv_mar, df_neg, "Taxonomic_Group",
                                               "Inv_Marino detail")
        _log_family(im_entries, im_chi2,
                    "  Subgrupos Inv_Marino (corrección dentro del subgrupo)", group_width=26)
        results["invert_marino_detail"] = im_entries
        results["chi2_invert_marino"] = im_chi2
    else:
        # Single group or too few — no correction needed
        im_entries = {}
        for grp in inv_mar["Taxonomic_Group"].unique() if len(inv_mar) > 0 else []:
            sub = inv_mar[inv_mar["Taxonomic_Group"] == grp]
            m   = _metrics_for_pos_neg(sub, df_neg)
            ci  = m["sensitivity_ci95"]
            log.info("  %-26s n=%4d  Sens=%.4f [%.3f-%.3f]  MCC=%.4f%s",
                     grp, m["n_positives"], m["sensitivity"], ci[0], ci[1],
                     m["mcc"], " [LOW_POWER]" if m["low_power"] else "")
            im_entries[grp] = m
        results["invert_marino_detail"] = im_entries

    # ==========================================================================
    # 6. Grade × BroadGroup distribution (interaction leakage × taxonomía)
    # ==========================================================================
    if "Grade" in df_pos_full.columns:
        log.info("\n--- 6. Leakage Grade × BroadGroup ---")
        cross = df_pos_full.groupby(["BroadGroup", "Grade"]).size().unstack(fill_value=0)
        for row_label in cross.index:
            parts = "  ".join(f"{g}={cross.loc[row_label, g]:3d}"
                              for g in cross.columns)
            log.info("  %-20s  %s", row_label, parts)
        results["grade_x_broadgroup"] = cross.to_dict()

    # ==========================================================================
    # 7. Summary interpretation
    # ==========================================================================
    log.info("\n=== INTERPRETACIÓN PARA APLICACIÓN A PULPO ===")
    # Overall mean sensitivity (Gold positives)
    overall_sens = (
        df_pos_full["Predicted"].mean() if len(df_pos_full) > 0 else 0.0
    )
    log.info("  Sensibilidad media global (Gold): %.4f", overall_sens)

    # Per-group interpretation relative to global mean
    for broad_grp, label_es in [
        ("Invert_Marino",    "Invertebrado Marino [PULPO]"),
        ("Vert_Terrestre",   "Vertebrado Terrestre"),
        ("Invert_Terrestre", "Invertebrado Terrestre"),
        ("Vert_Marino",      "Vertebrado Marino"),
    ]:
        m = broad_entries.get(broad_grp)
        if not m or m["n_positives"] == 0:
            log.info("  %-30s — sin secuencias Gold (100%% leakage)", broad_grp)
            continue
        s    = m["sensitivity"]
        ci   = m["sensitivity_ci95"]
        p_bh = m.get("fisher_p_bh")
        sig  = _sig_label(p_bh)
        diff = s - overall_sens
        direction = "SUPERIOR" if diff > 0.05 else ("INFERIOR" if diff < -0.05 else "similar")
        lp = " [LOW_POWER]" if m["low_power"] else ""
        log.info("  %-30s Sens=%.4f [%.3f-%.3f]  %+.3f vs media  p_BH=%s %s%s",
                 label_es, s, ci[0], ci[1], diff,
                 f"{p_bh:.5f}" if p_bh is not None else "N/A",
                 sig, lp)
        if broad_grp == "Invert_Marino":
            if direction == "INFERIOR" and p_bh is not None and p_bh < 0.05:
                log.warning(
                    "  [SESGO CONFIRMADO] ToxinPred3 rinde PEOR en Inv_Marino (Sens=%.4f) "
                    "que la media Gold (%.4f). Los péptidos de pulpo u otros Inv_Marino "
                    "serán predichos con menor sensibilidad — mayor tasa de falsos negativos.",
                    s, overall_sens
                )
            elif direction == "SUPERIOR" and p_bh is not None and p_bh < 0.05:
                log.warning(
                    "  [LEAKAGE RESIDUAL] ToxinPred3 rinde MEJOR en Inv_Marino incluso en Gold. "
                    "Posible leakage no detectado a 40%% identidad o sesgo real de entrenamiento."
                )
            else:
                log.info(
                    "  [OK] Inv_Marino no muestra sesgo significativo respecto a la media Gold."
                )

    # ==========================================================================
    # Save JSON
    # ==========================================================================
    payload = {
        "script":         SCRIPT_NAME,
        "script_version": SCRIPT_VERSION,
        "tool":           tool_id,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "min_n_reliable": MIN_N_RELIABLE,
        "results":        results,
    }

    out_path = os.path.join(output_dir, f"taxonomic_bias_{tool_id}_{grade_label}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    log.info("\n  JSON guardado: %s", out_path)

    generate_provenance(
        output_dir=output_dir,
        script_name=SCRIPT_NAME,
        tool_id=tool_id,
        parameters={"category": category, "min_n_reliable": MIN_N_RELIABLE},
        output_stats={"output": out_path},
    )

    return {"status": "success", "output_path": out_path}


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Análisis de sesgo taxonómico y de hábitat en resultados de predicción."
    )
    parser.add_argument("--tool",       required=True, dest="tool_id")
    parser.add_argument("--config",     required=True, dest="pipeline_config")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--grades",
        default="Gold",
        help=(
            "Comma-separated leakage grades to include as positives "
            "(default: Gold). Use 'All' to include all grades. "
            "Example: --grades Gold,Silver"
        ),
    )
    args = parser.parse_args()

    if args.grades.strip().lower() == "all":
        grade_filter = None
    else:
        grade_filter = tuple(g.strip() for g in args.grades.split(","))

    result = run_taxonomic_bias_analysis(
        args.tool_id, args.pipeline_config, args.output_dir,
        grade_filter=grade_filter,
    )
    if result["status"] != "success":
        log.error("Análisis fallido: %s", result.get("message"))
        sys.exit(1)


if __name__ == "__main__":
    main()
