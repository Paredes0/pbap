"""
audit_lib.uniprot_client - UniProt REST API client with pagination, retry, checkpointing.

Supports extraction of mature CHAIN/PEPTIDE regions from UniProt feature annotations
to avoid treating full precursor proteins (signal peptide + propeptide + mature chain)
as if they were mature bioactive peptides.
"""

import os
import re
import time
import logging
from io import StringIO

import pandas as pd
import requests

log = logging.getLogger(__name__)

UNIPROT_API_BASE = "https://rest.uniprot.org/uniprotkb"
DEFAULT_FIELDS = (
    "accession,id,protein_name,gene_names,organism_name,organism_id,"
    "lineage,keyword,sequence,length,ft_signal,ft_transit,ft_propep,"
    "ft_chain,ft_peptide,"
    "cc_subcellular_location,cc_function,date_created,date_modified,"
    "lit_pubmed_id,reviewed"
)
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 45]


def download_uniprot(query, fields=None, checkpoint_dir=None, group_name="",
                     max_retries=MAX_RETRIES, retry_delays=RETRY_DELAYS):
    """Download entries from UniProt REST API with pagination, retry, checkpointing."""
    if fields is None:
        fields = DEFAULT_FIELDS

    all_records = []
    page_size = 500
    url = f"{UNIPROT_API_BASE}/search"
    params = {"query": query, "format": "tsv", "fields": fields, "size": page_size}

    # Check for checkpoint
    checkpoint_file = None
    if checkpoint_dir:
        os.makedirs(checkpoint_dir, exist_ok=True)
        safe_name = re.sub(r"[^\w]", "_", group_name)
        checkpoint_file = os.path.join(checkpoint_dir, f"checkpoint_{safe_name}.csv")
        if os.path.exists(checkpoint_file):
            log.info(f"  Resuming from checkpoint: {checkpoint_file}")
            return pd.read_csv(checkpoint_file)

    page = 0
    next_link = None

    while True:
        page += 1
        for attempt in range(max_retries):
            try:
                if next_link:
                    resp = requests.get(next_link, timeout=60)
                else:
                    resp = requests.get(url, params=params, timeout=60)
                resp.raise_for_status()
                break
            except (requests.RequestException, requests.Timeout) as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    log.warning(f"  API error (attempt {attempt+1}): {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    log.error(f"  API failed after {max_retries} attempts: {e}")
                    if all_records and checkpoint_file:
                        df_partial = pd.concat(all_records, ignore_index=True)
                        df_partial.to_csv(checkpoint_file, index=False)
                    raise

        text = resp.text.strip()
        if not text:
            break

        df_page = pd.read_csv(StringIO(text), sep="\t")
        if df_page.empty:
            break

        all_records.append(df_page)
        log.info(f"  Page {page}: {len(df_page)} records (group: {group_name})")

        link_header = resp.headers.get("Link", "")
        match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
        if match:
            next_link = match.group(1)
        else:
            break

    if not all_records:
        log.warning(f"  No records found for group '{group_name}'")
        return pd.DataFrame()

    df_combined = pd.concat(all_records, ignore_index=True)

    if checkpoint_file:
        df_combined.to_csv(checkpoint_file, index=False)
        log.info(f"  Checkpoint saved: {len(df_combined)} records")

    return df_combined


# ==== Feature parsing (CHAIN, PEPTIDE) ============================================

# UniProt feature string format (from REST API TSV with fields ft_chain/ft_peptide):
#   CHAIN 24..73; /note="Alpha-elapitoxin-Aa2b"; /id="PRO_0000035295"
#   CHAIN 75..95; /note="..."; /id="PRO_..."
#   PEPTIDE 44..82; /note="Exendin-3"; /id="PRO_..."
# Multiple features are separated by "; " between records (UniProt joins them with ";")
# We parse pairs of (start..end, note) robustly.

_FEATURE_RANGE_RE = re.compile(
    r"(CHAIN|PEPTIDE)\s+(\d+|\?)?\.?\.?(\d+|\?)?\s*;?\s*"
    r"(?:/note=\"([^\"]*)\")?"
    r"(?:\s*;\s*/id=\"([^\"]*)\")?",
    re.IGNORECASE,
)


def parse_mature_features(feature_str: str) -> list:
    """
    Parse a UniProt ft_chain / ft_peptide string into a list of
    (feature_type, start, end, note, feat_id) tuples (1-indexed, inclusive).

    Returns [] if feature_str is empty/NaN or unparseable.
    Skips features with unknown boundaries (? in coords).
    """
    if not feature_str or (isinstance(feature_str, float) and pd.isna(feature_str)):
        return []
    s = str(feature_str).strip()
    if not s or s.lower() == "nan":
        return []

    out = []
    for m in _FEATURE_RANGE_RE.finditer(s):
        ftype = m.group(1).upper()
        start_s = m.group(2)
        end_s = m.group(3)
        note = (m.group(4) or "").strip()
        feat_id = (m.group(5) or "").strip()

        if not start_s or not end_s or start_s == "?" or end_s == "?":
            continue
        try:
            start = int(start_s)
            end = int(end_s)
        except (ValueError, TypeError):
            continue
        if end < start or start < 1:
            continue
        out.append((ftype, start, end, note, feat_id))
    return out


def extract_mature_subsequences(full_seq: str, features: list,
                                 min_length: int = 5, max_length: int = 100) -> list:
    """
    Given a full precursor sequence and list of features (from parse_mature_features),
    return list of dicts: {subseq, ftype, start, end, note, feat_id}
    Only returns mature regions whose length is within [min_length, max_length].
    Coordinates are 1-based inclusive (standard UniProt).
    """
    if not full_seq or not features:
        return []
    L = len(full_seq)
    out = []
    for ftype, start, end, note, feat_id in features:
        if start > L or end > L:
            continue
        sub = full_seq[start - 1:end]  # 1-indexed to Python slice
        sub = sub.upper().strip()
        if not (min_length <= len(sub) <= max_length):
            continue
        out.append({
            "subseq": sub,
            "ftype": ftype,
            "start": start,
            "end": end,
            "note": note,
            "feat_id": feat_id,
        })
    return out


# ==== Standardization ============================================================

def process_uniprot_dataframe(df, group_name, habitat, bioactivity,
                               min_length=5, max_length=100,
                               strict_mature=True):
    """
    Standardize UniProt DataFrame to common schema.

    When strict_mature=True (default), only entries with annotated
    CHAIN/PEPTIDE features are kept, and ONE RECORD PER MATURE REGION
    is emitted (not per parent accession). This avoids treating full
    precursor proteins as mature bioactive peptides.

    When strict_mature=False, falls back to the canonical sequence
    when no features are present (previous behavior, kept for categories
    like "antimicrobial" where many entries lack feature annotation).
    """
    from audit_lib.sequence_utils import validate_sequence, classify_habitat, find_column

    if df.empty:
        return df

    col_acc = find_column(df, "Entry", "Accession") or df.columns[0]
    col_name = find_column(df, "Protein names", "protein_name")
    col_org = find_column(df, "Organism", "organism_name")
    col_org_id = find_column(df, "Organism (ID)", "organism_id")
    col_lineage = find_column(df, "Taxonomic lineage", "lineage")
    col_seq = find_column(df, "Sequence", "sequence")
    col_len = find_column(df, "Length", "length")
    col_pubmed = find_column(df, "PubMed", "lit_pubmed")
    col_created = find_column(df, "Date of creation", "date_created")
    col_modified = find_column(df, "Date of last modification", "date_modified")
    col_chain = find_column(df, "Chain", "ft_chain")
    col_peptide = find_column(df, "Peptide", "ft_peptide")

    records = []
    prefix = bioactivity[:3].upper()

    # Telemetry: how many entries have/haven't mature features
    n_total = 0
    n_with_features = 0
    n_mature_records = 0
    n_fallback_used = 0
    n_skipped_no_features = 0

    for _, row in df.iterrows():
        n_total += 1
        seq = str(row.get(col_seq, "")).strip().upper() if col_seq else ""
        if not seq or seq == "NAN":
            continue

        organism = str(row.get(col_org, "Unknown")) if col_org else "Unknown"
        lineage = str(row.get(col_lineage, "")) if col_lineage else ""
        detected_habitat = classify_habitat(organism, lineage, fallback=habitat)
        accession = str(row.get(col_acc, ""))
        protein_name = str(row.get(col_name, "")) if col_name else ""

        # ---- Collect features: CHAIN first, then PEPTIDE ----
        chain_feats = parse_mature_features(row.get(col_chain, "")) if col_chain else []
        pep_feats = parse_mature_features(row.get(col_peptide, "")) if col_peptide else []
        all_feats = chain_feats + pep_feats
        has_features = len(all_feats) > 0
        if has_features:
            n_with_features += 1

        # ---- Extract mature regions ----
        mature_regions = extract_mature_subsequences(
            seq, all_feats, min_length=min_length, max_length=max_length
        )

        if mature_regions:
            # Emit one record per mature region
            for i, region in enumerate(mature_regions):
                sub = region["subseq"]
                if not validate_sequence(sub, min_length, max_length):
                    continue
                suffix = f"_{region['ftype']}_{region['start']}-{region['end']}"
                mature_id = f"{prefix}_{group_name}_{accession}{suffix}"
                record = {
                    "ID": mature_id,
                    "Accession": f"{accession}{suffix}",
                    "Parent_Accession": accession,
                    "Protein_Name": (region["note"] or protein_name),
                    "Sequence": sub,
                    "Length": len(sub),
                    "Organism": organism,
                    "Organism_ID": str(row.get(col_org_id, "")) if col_org_id else "",
                    "Lineage": lineage,
                    "Habitat": detected_habitat,
                    "Taxonomic_Group": group_name,
                    "Source_DB": "UniProt",
                    "Bioactivity": bioactivity,
                    "Evidence_Type": "reviewed_mature",
                    "Mature_Source": region["ftype"],
                    "Mature_Feature_ID": region["feat_id"],
                    "PubMed_ID": str(row.get(col_pubmed, "")) if col_pubmed else "",
                    "Date_Created": str(row.get(col_created, "")) if col_created else "",
                    "Date_Modified": str(row.get(col_modified, "")) if col_modified else "",
                }
                records.append(record)
                n_mature_records += 1
        else:
            # No usable mature regions (feature present but out-of-range, OR no features)
            if strict_mature:
                n_skipped_no_features += 1
                continue
            # Lenient fallback: use canonical sequence (old behavior)
            if not validate_sequence(seq, min_length, max_length):
                continue
            n_fallback_used += 1
            record = {
                "ID": f"{prefix}_{group_name}_{accession}",
                "Accession": accession,
                "Parent_Accession": accession,
                "Protein_Name": protein_name,
                "Sequence": seq,
                "Length": len(seq),
                "Organism": organism,
                "Organism_ID": str(row.get(col_org_id, "")) if col_org_id else "",
                "Lineage": lineage,
                "Habitat": detected_habitat,
                "Taxonomic_Group": group_name,
                "Source_DB": "UniProt",
                "Bioactivity": bioactivity,
                "Evidence_Type": "reviewed_fulllength",
                "Mature_Source": "FULL",
                "Mature_Feature_ID": "",
                "PubMed_ID": str(row.get(col_pubmed, "")) if col_pubmed else "",
                "Date_Created": str(row.get(col_created, "")) if col_created else "",
                "Date_Modified": str(row.get(col_modified, "")) if col_modified else "",
            }
            records.append(record)

    log.info(
        "  [uniprot mature] group=%s: raw=%d with_features=%d mature_records=%d "
        "fallback=%d skipped_no_features=%d strict=%s",
        group_name, n_total, n_with_features, n_mature_records,
        n_fallback_used, n_skipped_no_features, strict_mature,
    )

    return pd.DataFrame(records)
