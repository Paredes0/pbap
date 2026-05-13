#!/usr/bin/env python3
"""
mine_positives_per_bioactivity.py
=================================
Downloads positive peptide datasets per bioactivity category from UniProt and
additional databases. Applies taxonomic balancing, length stratification,
habitat diversity enforcement, intra-set CD-HIT redundancy reduction, and
sequence validation.

Refactored to use audit_lib shared modules.

Usage (called by audit_pipeline.sh):
    python mine_positives_per_bioactivity.py \
        --category toxicity \
        --config categories_config.yaml \
        --output-dir /path/to/Category_Pools

    python mine_positives_per_bioactivity.py \
        --category toxicity \
        --config categories_config.yaml \
        --output-dir /path/to/Category_Pools \
        --target-size 400
"""

import argparse
import logging
import os
import sys

import pandas as pd

# --- audit_lib imports ---
from audit_lib.config import load_category_config
from audit_lib.uniprot_client import download_uniprot, process_uniprot_dataframe
from audit_lib.sequence_utils import (
    validate_sequence,
    classify_habitat,
    find_column,
    remove_subfragments,
    cap_per_species,
    DEFAULT_LENGTH_BINS,
)
from audit_lib.cdhit_utils import run_cdhit_intraset
from audit_lib.length_sampling import sample_with_diversity
from audit_lib.provenance import generate_provenance
from audit_lib.db_parsers import get_parser

# ============================================================================
# CONSTANTS
# ============================================================================

RANDOM_SEED = 42
SCRIPT_NAME = "mine_positives_per_bioactivity.py"

EXPORT_COLUMNS = [
    "ID", "Accession", "Protein_Name", "Sequence", "Length",
    "Organism", "Organism_ID", "Lineage", "Habitat", "Taxonomic_Group",
    "Source_DB", "Bioactivity", "Evidence_Type", "PubMed_ID",
    "Date_Created", "Date_Modified",
]

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
# HABITAT ENFORCEMENT
# ============================================================================


def enforce_habitat_minimums(df, target_size, min_habitat_pct, seed=RANDOM_SEED):
    """Log habitat representation status before sampling.

    The actual enforcement happens via sample_with_diversity which respects
    the natural distribution. This function logs warnings if the available
    pool may not meet habitat minimums.
    """
    for habitat, min_pct in min_habitat_pct.items():
        min_count = int(target_size * min_pct)
        current_count = (df["Habitat"] == habitat).sum()

        if current_count < min_count:
            log.info(
                f"  Habitat '{habitat}': have {current_count}, "
                f"need {min_count} ({min_pct*100:.0f}%). Deficit noted."
            )
        else:
            log.info(
                f"  Habitat '{habitat}': have {current_count}, "
                f"need {min_count} ({min_pct*100:.0f}%). OK"
            )

    return df


# ============================================================================
# MAIN PIPELINE
# ============================================================================


def mine_positives(category, config_path, output_dir, target_size_override=None):
    """Main pipeline: download, process, balance, deduplicate, export."""

    # ---- Load config ----
    full_cfg = load_category_config(config_path)
    all_categories = full_cfg.get("categories", {})

    if category not in all_categories:
        log.error(
            f"Unknown category: '{category}'. "
            f"Available: {list(all_categories.keys())}"
        )
        sys.exit(1)

    cat_cfg = all_categories[category]
    target_size = target_size_override or cat_cfg.get("target_pool_size", 1500)
    cdhit_identity = cat_cfg.get("internal_cdhit_identity", 0.90)
    min_habitat_pct = cat_cfg.get("min_habitat_pct", {})
    taxonomic_queries = cat_cfg.get("taxonomic_queries", {})
    additional_dbs = cat_cfg.get("additional_databases", {})

    # --- Pool mature peptide length range (category-wide union of tool training ranges) ---
    pool_length_range = cat_cfg.get("pool_length_range", [5, 100])
    pool_min_len = int(pool_length_range[0])
    pool_max_len = int(pool_length_range[1])
    log_msg_range = f"pool mature length range: [{pool_min_len}, {pool_max_len}]"

    # Output directory
    os.makedirs(output_dir, exist_ok=True)
    checkpoint_dir = os.path.join(output_dir, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)

    errors = []
    counts_per_group = {}

    log.info("=" * 60)
    log.info(f"MINING POSITIVES: {category.upper()}")
    log.info(f"Target pool size: {target_size}")
    log.info(log_msg_range)
    log.info(f"CD-HIT identity: {cdhit_identity}")
    log.info(f"Config: {config_path}")
    log.info(f"Output: {output_dir}")
    log.info("=" * 60)

    # ---- Step 1: Download from UniProt per taxonomic group ----
    log.info("\n--- Step 1: Downloading from UniProt ---")
    all_dfs = []

    for group_name, group_cfg in taxonomic_queries.items():
        query = group_cfg["query"]
        habitat = group_cfg.get("habitat", "desconocido")
        log.info(f"\nGroup: {group_name} (habitat: {habitat})")

        try:
            df_raw = download_uniprot(
                query=query,
                checkpoint_dir=checkpoint_dir,
                group_name=group_name,
            )
            counts_per_group[group_name] = len(df_raw)
            log.info(f"  Downloaded: {len(df_raw)} raw records")

            df_proc = process_uniprot_dataframe(
                df_raw,
                group_name=group_name,
                habitat=habitat,
                bioactivity=category,
                min_length=pool_min_len,
                max_length=pool_max_len,
            )
            log.info(f"  After processing: {len(df_proc)} valid peptides")
            all_dfs.append(df_proc)

        except Exception as e:
            msg = f"Error downloading group '{group_name}': {e}"
            log.error(f"  {msg}")
            errors.append(msg)
            counts_per_group[group_name] = 0

    # ---- Step 2: Parse additional databases ----
    if additional_dbs:
        log.info("\n--- Step 2: Parsing additional databases ---")
        for db_name, db_cfg in additional_dbs.items():
            log.info(f"\nAdditional DB: {db_name}")
            try:
                parser_name = db_cfg.get("parser", db_name)
                parser_fn = get_parser(parser_name)
                if parser_fn is None:
                    log.warning(f"  No parser found for '{parser_name}', skipping.")
                    continue

                data_path = db_cfg.get("data_path", None)
                df_extra = parser_fn(
                    data_path=data_path,
                    bioactivity=category,
                    min_length=pool_min_len,
                    max_length=pool_max_len,
                )
                if not df_extra.empty:
                    counts_per_group[f"db_{db_name}"] = len(df_extra)
                    log.info(f"  Loaded {len(df_extra)} records from {db_name}")
                    all_dfs.append(df_extra)
                else:
                    log.info(f"  No records from {db_name}")
                    counts_per_group[f"db_{db_name}"] = 0

            except Exception as e:
                msg = f"Error parsing additional DB '{db_name}': {e}"
                log.error(f"  {msg}")
                errors.append(msg)
                counts_per_group[f"db_{db_name}"] = 0
    else:
        log.info("\n--- Step 2: No additional databases configured ---")

    if not all_dfs:
        log.error("No data downloaded from any source. Aborting.")
        sys.exit(1)

    df_all = pd.concat(all_dfs, ignore_index=True)
    log.info(f"\nTotal raw peptides (all sources): {len(df_all)}")

    # ---- Step 3: Remove exact duplicates by sequence ----
    log.info("\n--- Step 3: Removing exact duplicates ---")
    before = len(df_all)
    df_all = df_all.drop_duplicates(subset=["Sequence"], keep="first")
    log.info(f"  Duplicates removed: {before} -> {len(df_all)}")

    # ---- Step 4: Remove subfragments ----
    log.info("\n--- Step 4: Removing subfragments ---")
    df_all = remove_subfragments(df_all, seq_col="Sequence", id_col="ID")
    log.info(f"  After subfragment filter: {len(df_all)}")

    # ---- Step 5: Cap per species ----
    log.info("\n--- Step 5: Capping per species ---")
    num_species = df_all["Organism"].nunique()
    max_per_species = max(5, target_size // max(num_species, 1))
    log.info(f"  Species: {num_species}, max_per_species: {max_per_species}")
    df_all = cap_per_species(
        df_all, max_per_species, organism_col="Organism", seed=RANDOM_SEED
    )
    log.info(f"  After capping: {len(df_all)}")

    # ---- Step 6: CD-HIT intra-set redundancy reduction ----
    log.info("\n--- Step 6: CD-HIT intra-set redundancy reduction ---")
    df_all = run_cdhit_intraset(
        df_all,
        identity=cdhit_identity,
        output_dir=output_dir,
        id_col="ID",
        seq_col="Sequence",
    )
    log.info(f"  After CD-HIT: {len(df_all)}")

    # ---- Step 7: Habitat diversity check ----
    log.info("\n--- Step 7: Habitat diversity check ---")
    df_all = enforce_habitat_minimums(
        df_all, target_size, min_habitat_pct, seed=RANDOM_SEED
    )

    # ---- Step 8: Balanced selection with natural length distribution ----
    log.info("\n--- Step 8: Balanced selection (sample_with_diversity) ---")
    df_final = sample_with_diversity(
        df_all,
        target_size=target_size,
        length_col="Length",
        bins=DEFAULT_LENGTH_BINS,
        min_bin_pct=0.03,
        seed=RANDOM_SEED,
    )
    log.info(f"  Final selection: {len(df_final)}")

    # ---- Step 9: Final validation ----
    log.info("\n--- Step 9: Final validation ---")
    valid_mask = df_final["Sequence"].apply(
        lambda s: validate_sequence(s, min_length=5, max_length=100)
    )
    if not valid_mask.all():
        n_invalid = (~valid_mask).sum()
        log.warning(f"  Removing {n_invalid} invalid sequences in final check")
        df_final = df_final[valid_mask].copy()

    # Verify habitat minimums in final set
    if len(df_final) > 0:
        for habitat, min_pct in min_habitat_pct.items():
            count = (df_final["Habitat"] == habitat).sum()
            pct = count / len(df_final)
            status = "OK" if pct >= min_pct else "BELOW"
            log.info(
                f"  Habitat '{habitat}': {count} "
                f"({pct*100:.1f}%) - min {min_pct*100:.0f}% [{status}]"
            )

    # ---- Print summary stats ----
    log.info(f"\n{'=' * 60}")
    log.info(f"FINAL DATASET SUMMARY: {category}")
    log.info(f"{'=' * 60}")
    log.info(f"  Total peptides: {len(df_final)}")

    if not df_final.empty:
        log.info(f"  Unique organisms: {df_final['Organism'].nunique()}")
        log.info(
            f"  Length range: {df_final['Length'].min()}-{df_final['Length'].max()}"
        )
        log.info(f"  Mean length: {df_final['Length'].mean():.1f}")

        log.info("\n  Habitat distribution:")
        for hab, count in df_final["Habitat"].value_counts().items():
            pct = count / len(df_final) * 100
            log.info(f"    {hab}: {count} ({pct:.1f}%)")

        log.info("\n  Taxonomic group distribution:")
        for grp, count in df_final["Taxonomic_Group"].value_counts().items():
            pct = count / len(df_final) * 100
            log.info(f"    {grp}: {count} ({pct:.1f}%)")

        log.info("\n  Length bin distribution:")
        for lo, hi in DEFAULT_LENGTH_BINS:
            n = ((df_final["Length"] >= lo) & (df_final["Length"] <= hi)).sum()
            log.info(f"    {lo}-{hi}: {n}")

    # ---- Step 10: Export CSV and FASTA ----
    log.info("\n--- Step 10: Exporting ---")

    # Ensure all export columns exist
    for col in EXPORT_COLUMNS:
        if col not in df_final.columns:
            df_final[col] = ""

    csv_path = os.path.join(output_dir, f"{category}_pool.csv")
    df_final[EXPORT_COLUMNS].to_csv(csv_path, index=False)
    log.info(f"  CSV saved: {csv_path}")

    fasta_path = os.path.join(output_dir, f"{category}_pool.fasta")
    with open(fasta_path, "w") as f:
        for _, row in df_final.iterrows():
            f.write(f">{row['ID']}\n{row['Sequence']}\n")
    log.info(f"  FASTA saved: {fasta_path}")

    # ---- Step 11: Generate provenance ----
    log.info("\n--- Step 11: Generating provenance ---")

    queries_info = {}
    for name, q in taxonomic_queries.items():
        queries_info[name] = {
            "query": q["query"],
            "habitat": q.get("habitat", "desconocido"),
            "records_downloaded": counts_per_group.get(name, 0),
        }
    for db_name in additional_dbs:
        key = f"db_{db_name}"
        queries_info[key] = {
            "source": db_name,
            "records_loaded": counts_per_group.get(key, 0),
        }

    output_stats = {}
    if not df_final.empty:
        output_stats = {
            "total_peptides": len(df_final),
            "unique_organisms": int(df_final["Organism"].nunique()),
            "habitat_distribution": df_final["Habitat"].value_counts().to_dict(),
            "length_stats": {
                "min": int(df_final["Length"].min()),
                "max": int(df_final["Length"].max()),
                "mean": round(float(df_final["Length"].mean()), 2),
            },
            "taxonomic_group_distribution": (
                df_final["Taxonomic_Group"].value_counts().to_dict()
            ),
        }

    prov_path = generate_provenance(
        output_dir=output_dir,
        script_name=SCRIPT_NAME,
        category=category,
        parameters={
            "random_seed": RANDOM_SEED,
            "target_pool_size": target_size,
            "internal_cdhit_identity": cdhit_identity,
            "min_habitat_pct": min_habitat_pct,
            "length_bins": DEFAULT_LENGTH_BINS,
            "config_path": str(config_path),
        },
        queries=queries_info,
        counts=counts_per_group,
        output_stats=output_stats,
        errors=errors,
    )
    log.info(f"  Provenance saved: {prov_path}")

    log.info(f"\n{'=' * 60}")
    log.info("DONE")
    log.info(f"{'=' * 60}")

    return df_final


# ============================================================================
# CLI
# ============================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mine positive peptide datasets per bioactivity category."
    )
    parser.add_argument(
        "--category",
        required=True,
        help="Bioactivity category to mine (e.g. toxicity, hemolytic).",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to categories_config.yaml.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for pool files.",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=None,
        help="Override target pool size from config.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    mine_positives(
        category=args.category,
        config_path=args.config,
        output_dir=args.output_dir,
        target_size_override=args.target_size,
    )
