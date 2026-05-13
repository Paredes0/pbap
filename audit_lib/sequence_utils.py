"""
audit_lib.sequence_utils - Sequence validation, habitat classification, length binning.
Consolidated from mine_positives_per_bioactivity.py and generate_category_negatives.py.
"""

import re
import logging

log = logging.getLogger(__name__)

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")

# Default length bins (can be overridden by config)
DEFAULT_LENGTH_BINS = [
    (5, 10), (11, 20), (21, 30), (31, 40), (41, 50),
    (51, 60), (61, 70), (71, 80), (81, 90), (91, 100)
]

# Habitat classification by lineage text patterns
HABITAT_TEXT_MAP = [
    ("cnidaria", "marino"),
    ("mollusca", "marino"),
    ("echinodermata", "marino"),
    ("crustacea", "marino"),
    ("porifera", "marino"),
    ("tunicata", "marino"),
    ("chondrichthyes", "marino"),
    ("actinopteri", "marino"),
    ("actinopterygii", "marino"),
    ("mammalia", "terrestre"),
    ("amphibia", "terrestre"),
    ("reptilia", "terrestre"),
    ("lepidosauria", "terrestre"),
    ("serpentes", "terrestre"),
    ("aves", "terrestre"),
    ("araneae", "terrestre"),
    ("scorpiones", "terrestre"),
    ("arachnida", "terrestre"),
    ("insecta", "terrestre"),
    ("hymenoptera", "terrestre"),
    ("coleoptera", "terrestre"),
    ("diptera", "terrestre"),
    ("embryophyta", "planta"),
    ("viridiplantae", "planta"),
    ("streptophyta", "planta"),
    ("fungi", "hongo"),
    ("ascomycota", "hongo"),
    ("basidiomycota", "hongo"),
    ("bacteria", "microorganismo"),
    ("archaea", "microorganismo"),
]

# Signaling-related regex for filtering negatives
SIGNALING_RISK_REGEX = re.compile("|".join([
    r"\bhormone\b", r"\bneuropeptide\b", r"\bendocrine\b",
    r"\bcytokine\b", r"\bchemokine\b", r"\bgrowth factor\b",
    r"\binterleukin\b", r"\bdefensin\b", r"\binsulin\b",
    r"\bantimicrobial\b", r"\btoxin\b", r"\bvenom\b",
    r"\bhemolysin\b", r"\bhemolytic\b",
]), re.IGNORECASE)


def validate_sequence(seq, min_length=5, max_length=100):
    """Return True if sequence contains only standard amino acids and is in range."""
    if not seq or not isinstance(seq, str):
        return False
    seq = seq.strip().upper()
    if len(seq) < min_length or len(seq) > max_length:
        return False
    return all(c in STANDARD_AA for c in seq)


def classify_habitat(organism_name, lineage_str, fallback="desconocido"):
    """Classify organism habitat using lineage text patterns."""
    if not isinstance(lineage_str, str):
        lineage_str = ""
    if not isinstance(organism_name, str):
        organism_name = ""

    combined = (lineage_str + " " + organism_name).lower()

    for text, habitat in HABITAT_TEXT_MAP:
        if text in combined:
            return habitat

    return fallback


def get_length_bin(length, bins=None):
    """Return the bin index for a given peptide length. Returns -1 if outside all bins."""
    if bins is None:
        bins = DEFAULT_LENGTH_BINS
    for i, (lo, hi) in enumerate(bins):
        if lo <= length <= hi:
            return i
    return -1


def remove_subfragments(df, seq_col="Sequence", id_col="ID"):
    """Remove peptides that are exact subfragments of other peptides in the set."""
    if df.empty:
        return df

    sequences = df[seq_col].tolist()
    ids = df[id_col].tolist()
    to_remove = set()

    # Sort by length (shorter first) to catch subfragments efficiently
    indexed = sorted(zip(ids, sequences), key=lambda x: len(x[1]))

    for i in range(len(indexed)):
        if indexed[i][0] in to_remove:
            continue
        for j in range(i + 1, len(indexed)):
            if indexed[j][0] in to_remove:
                continue
            if indexed[i][1] in indexed[j][1]:
                to_remove.add(indexed[i][0])
                break

    if to_remove:
        log.info(f"  Subfragment filter: removing {len(to_remove)} peptides")
        df = df[~df[id_col].isin(to_remove)].copy()

    return df


def find_column(df, *keywords):
    """Dynamically find a column matching any of the given keywords (case-insensitive)."""
    for col in df.columns:
        for kw in keywords:
            if kw.lower() in col.lower():
                return col
    return None


def is_signaling_related(text):
    """Check if a protein name/function text indicates signaling activity."""
    if not text or not isinstance(text, str):
        return False
    return bool(SIGNALING_RISK_REGEX.search(text))


def cap_per_species(df, max_per_species, organism_col="Organism", seed=42):
    """Cap number of peptides per organism."""
    if df.empty:
        return df

    import numpy as np
    rng = np.random.RandomState(seed)

    capped = []
    for org, grp in df.groupby(organism_col):
        if len(grp) <= max_per_species:
            capped.append(grp)
        else:
            capped.append(grp.sample(n=max_per_species, random_state=rng))
            log.info(f"  Capped '{org}': {len(grp)} -> {max_per_species}")

    import pandas as pd
    return pd.concat(capped, ignore_index=True)
