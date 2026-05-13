#!/usr/bin/env python3
"""
generate_category_negatives.py
===============================
Generates negative (non-bioactive) peptide datasets matching the positive
dataset's length distribution. Per-tool specific: different tools may have
different training data, so the negative set will differ after CD-HIT-2D.

Called by audit_pipeline.sh as:
    python generate_category_negatives.py \\
        --tool TOOL_ID \\
        --config pipeline_config.yaml \\
        --categories-config categories_config.yaml \\
        --positives-csv pool.csv \\
        --output-dir /path/to/test_negatives

Pipeline:
    1. Load configs (pipeline + categories)
    2. Get tool's category from pipeline_config
    3. Load positive dataset from --positives-csv
    4. Get negative_config from categories_config for this category
    5. Download candidate negatives from UniProt per negative query group
    6. Filter: exclude bioactivity keywords, exclude positives, exclude subfragments
    7. Exclude sequences flagged by is_signaling_related on protein name/function
    8. Cap per species
    9. Match length distribution to positives using match_length_distribution
   10. Export CSV and FASTA
   11. Generate provenance
"""

import argparse
import logging
import os
import sys

import numpy as np
import pandas as pd

from audit_lib.config import load_pipeline_config, load_category_config, get_tool_config
from audit_lib.uniprot_client import download_uniprot
from audit_lib.sequence_utils import (
    validate_sequence,
    classify_habitat,
    find_column,
    remove_subfragments,
    cap_per_species,
    is_signaling_related,
)
from audit_lib.length_sampling import match_length_distribution
from audit_lib.provenance import generate_provenance

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_NAME = "generate_category_negatives"
SCRIPT_VERSION = "2.0.0"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def generate_negatives(tool_id, pipeline_cfg, category_cfg, positives_csv,
                       output_dir):
    """Generate negative dataset for *tool_id* matching positive distributions."""

    # -- 1. Resolve tool -> category -------------------------------------------
    tool_cfg = get_tool_config(tool_id, pipeline_cfg)
    category = tool_cfg.get("category")
    if not category:
        log.error("Tool '%s' has no 'category' in pipeline config.", tool_id)
        sys.exit(1)

    global_cfg = pipeline_cfg.get("global", {})
    seed = global_cfg.get("random_seed", 42)
    min_length = global_cfg.get("min_length", 5)
    max_length = global_cfg.get("max_length", 100)

    # -- 2. Get negative_config for category -----------------------------------
    categories = category_cfg.get("categories", {})
    cat_cfg = categories.get(category)
    if not cat_cfg or "negative_config" not in cat_cfg:
        log.error("No negative_config for category '%s' in categories_config.",
                  category)
        sys.exit(1)

    neg_cfg = cat_cfg["negative_config"]
    exclude_keywords = neg_cfg.get("exclude_keywords", [])
    ratio = neg_cfg.get("ratio", 1.0)
    neg_queries = neg_cfg.get("queries", {})

    if not neg_queries:
        log.error("No negative queries defined for category '%s'.", category)
        sys.exit(1)

    log.info("=" * 60)
    log.info("GENERATING NEGATIVES  tool=%s  category=%s", tool_id, category)
    log.info("=" * 60)

    # -- 3. Load positive dataset ----------------------------------------------
    df_pos = pd.read_csv(positives_csv)
    n_target = max(1, int(len(df_pos) * ratio))
    log.info("Positives loaded: %d  (from %s)", len(df_pos), positives_csv)
    log.info("Target negatives: %d  (ratio=%.2f)", n_target, ratio)

    seq_col_pos = find_column(df_pos, "Sequence") or "Sequence"
    pos_seqs = set(df_pos[seq_col_pos].str.strip().str.upper())

    # -- 4. Download candidate negatives from UniProt --------------------------
    os.makedirs(output_dir, exist_ok=True)
    checkpoint_dir = os.path.join(output_dir, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    log.info("--- Step 1: Downloading candidate negatives ---")
    all_candidates = []
    query_counts = {}

    for group_name, group_cfg in neg_queries.items():
        query_str = group_cfg.get("query", "")
        habitat_fallback = group_cfg.get("habitat", "desconocido")

        log.info("Group: %s", group_name)
        try:
            df_raw = download_uniprot(
                query=query_str,
                checkpoint_dir=checkpoint_dir,
                group_name=group_name,
            )
            query_counts[group_name] = len(df_raw)
            log.info("  Downloaded: %d records", len(df_raw))
        except Exception as exc:
            log.error("  Download error for %s: %s", group_name, exc)
            query_counts[group_name] = 0
            continue

        if df_raw.empty:
            continue

        # Resolve column names dynamically
        col_acc = find_column(df_raw, "Entry", "Accession") or df_raw.columns[0]
        col_seq = find_column(df_raw, "Sequence")
        col_org = find_column(df_raw, "Organism")
        col_lineage = find_column(df_raw, "Taxonomic lineage", "lineage")
        col_kw = find_column(df_raw, "Keyword", "keyword")
        col_name = find_column(df_raw, "Protein names", "protein_name")
        col_func = find_column(df_raw, "Function", "cc_function")

        for _, row in df_raw.iterrows():
            seq = str(row.get(col_seq, "")).strip().upper() if col_seq else ""
            if not validate_sequence(seq, min_length, max_length):
                continue

            # Exclude by bioactivity-related keywords
            kw_str = str(row.get(col_kw, "")) if col_kw else ""
            if any(ek in kw_str for ek in exclude_keywords):
                continue

            # Exclude positives
            if seq in pos_seqs:
                continue

            # Exclude signaling-related by protein name/function
            prot_name = str(row.get(col_name, "")) if col_name else ""
            func_text = str(row.get(col_func, "")) if col_func else ""
            if is_signaling_related(prot_name) or is_signaling_related(func_text):
                continue

            organism = str(row.get(col_org, "Unknown")) if col_org else "Unknown"
            lineage = str(row.get(col_lineage, "")) if col_lineage else ""
            habitat = classify_habitat(organism, lineage, fallback=habitat_fallback)
            accession = str(row.get(col_acc, ""))

            all_candidates.append({
                "ID": "NEG_%s_%s" % (group_name, accession),
                "Accession": accession,
                "Protein_Name": prot_name,
                "Sequence": seq,
                "Length": len(seq),
                "Organism": organism,
                "Lineage": lineage,
                "Habitat": habitat,
                "Source_Group": group_name,
                "Source_DB": "UniProt",
                "Bioactivity": "non_%s" % category,
            })

    if not all_candidates:
        log.error("No candidate negatives found after filtering!")
        sys.exit(1)

    df_cand = pd.DataFrame(all_candidates)
    df_cand = df_cand.drop_duplicates(subset=["Sequence"], keep="first")
    log.info("Total unique candidates after keyword/signaling filter: %d",
             len(df_cand))

    # -- 5. Remove subfragments of positives -----------------------------------
    log.info("--- Step 2: Removing subfragments of positives ---")
    before_subfrag = len(df_cand)
    mask_subfrag = pd.Series(True, index=df_cand.index)
    for idx, row in df_cand.iterrows():
        cand_seq = row["Sequence"]
        for pos_seq in pos_seqs:
            if cand_seq in pos_seq or pos_seq in cand_seq:
                mask_subfrag.at[idx] = False
                break
    df_cand = df_cand[mask_subfrag].copy()
    log.info("  Subfragment filter (vs positives): %d -> %d",
             before_subfrag, len(df_cand))

    # Also remove internal subfragments among candidates
    df_cand = remove_subfragments(df_cand, seq_col="Sequence", id_col="ID")
    log.info("  After internal subfragment removal: %d", len(df_cand))

    # -- 6. Cap per species ----------------------------------------------------
    log.info("--- Step 3: Capping per species ---")
    max_per_sp = max(5, n_target // 50)
    df_cand = cap_per_species(df_cand, max_per_species=max_per_sp,
                              organism_col="Organism", seed=seed)
    log.info("  After species cap (max %d): %d", max_per_sp, len(df_cand))

    # -- 7. Match length distribution ------------------------------------------
    log.info("--- Step 4: Matching length distribution to positives ---")
    df_neg = match_length_distribution(
        source_df=df_cand,
        target_df=df_pos,
        target_size=n_target,
        length_col="Length",
        bins=None,
        seed=seed,
    )
    log.info("  Selected negatives: %d", len(df_neg))

    # -- 8. Export CSV and FASTA -----------------------------------------------
    log.info("--- Step 5: Exporting ---")
    csv_path = os.path.join(output_dir, "negatives_%s.csv" % tool_id)
    df_neg.to_csv(csv_path, index=False)
    log.info("  CSV:   %s", csv_path)

    fasta_path = os.path.join(output_dir, "negatives_%s.fasta" % tool_id)
    with open(fasta_path, "w", encoding="utf-8") as fh:
        for _, row in df_neg.iterrows():
            fh.write(">%s\n%s\n" % (row["ID"], row["Sequence"]))
    log.info("  FASTA: %s", fasta_path)

    # -- 9. Provenance ---------------------------------------------------------
    log.info("--- Step 6: Provenance ---")
    generate_provenance(
        output_dir=output_dir,
        script_name=SCRIPT_NAME,
        category=category,
        tool_id=tool_id,
        parameters={
            "script_version": SCRIPT_VERSION,
            "random_seed": seed,
            "ratio": ratio,
            "min_length": min_length,
            "max_length": max_length,
            "exclude_keywords": exclude_keywords,
            "max_per_species": max_per_sp,
            "positives_csv": os.path.abspath(positives_csv),
        },
        queries=query_counts,
        counts={
            "positives_loaded": len(df_pos),
            "target_negatives": n_target,
            "candidates_after_filter": before_subfrag,
            "after_subfragment_removal": len(df_cand),
            "after_species_cap": len(df_cand),
            "final_selected": len(df_neg),
        },
        output_stats={
            "csv_path": csv_path,
            "fasta_path": fasta_path,
            "habitat_distribution": df_neg["Habitat"].value_counts().to_dict(),
            "length_mean": float(df_neg["Length"].mean()),
            "length_std": float(df_neg["Length"].std()),
        },
    )

    # -- Summary ---------------------------------------------------------------
    log.info("=" * 60)
    log.info("NEGATIVE DATASET SUMMARY: tool=%s  category=%s", tool_id, category)
    log.info("=" * 60)
    log.info("  Total negatives: %d", len(df_neg))
    log.info("  Habitat distribution:")
    for hab, count in df_neg["Habitat"].value_counts().items():
        pct = count / len(df_neg) * 100
        log.info("    %s: %d (%.1f%%)", hab, count, pct)
    log.info("  Length: mean=%.1f  std=%.1f",
             df_neg["Length"].mean(), df_neg["Length"].std())

    return df_neg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate negative peptide dataset matching positive "
                    "distributions (per-tool)."
    )
    parser.add_argument("--tool", required=True,
                        help="Tool ID from pipeline_config.yaml")
    parser.add_argument("--config", required=True,
                        help="Path to pipeline_config.yaml")
    parser.add_argument("--categories-config", required=True,
                        help="Path to categories_config.yaml")
    parser.add_argument("--positives-csv", required=True,
                        help="Path to positive dataset CSV")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for output negatives")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    pipeline_cfg = load_pipeline_config(args.config)
    category_cfg = load_category_config(args.categories_config)

    generate_negatives(
        tool_id=args.tool,
        pipeline_cfg=pipeline_cfg,
        category_cfg=category_cfg,
        positives_csv=args.positives_csv,
        output_dir=args.output_dir,
    )
