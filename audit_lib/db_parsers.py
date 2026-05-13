"""
audit_lib.db_parsers - Parsers for additional peptide databases.
Each parser returns a standardized DataFrame.

Supported: DBAASP, APD3, ConoServer, ArachnoServer, Hemolytik, CancerPPD,
           CPPsite, BIOPEP, AVPdb
NOTE: Many require manual download. Parsers attempt auto-download where possible.
"""

import gzip
import logging
import os
import re

import pandas as pd

log = logging.getLogger(__name__)

STANDARD_COLUMNS = [
    "ID", "Accession", "Protein_Name", "Sequence", "Length",
    "Organism", "Organism_ID", "Lineage", "Habitat", "Taxonomic_Group",
    "Source_DB", "Bioactivity", "Evidence_Type", "PubMed_ID",
    "Date_Created", "Date_Modified",
]


# ---- FASTA helpers --------------------------------------------------------

def _open_maybe_gz(path):
    """Open a text file, transparently handling .gz."""
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def _iter_fasta(path):
    """Yield (header, sequence) from a FASTA file (transparently handles .gz)."""
    header, parts = None, []
    with _open_maybe_gz(path) as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(parts)
                header = line[1:]
                parts = []
            else:
                parts.append(line.strip())
        if header is not None:
            yield header, "".join(parts)


_VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _clean_sequence(seq: str) -> str:
    """Uppercase and drop non-standard residues (X, *, O, U, etc)."""
    s = re.sub(r"[^A-Za-z]", "", seq).upper()
    return "".join(c for c in s if c in _VALID_AA)


# Hydrophobic amino acids typical of signal peptides
_HYDROPHOBIC = set("AILMFWVC")


def _looks_like_signal_peptide(seq: str, window: int = 20, threshold: float = 0.65) -> bool:
    """
    Heuristic detection of signal peptide at N-terminus.

    Returns True if:
      - seq starts with M, AND
      - the next `window` residues (after M) have >= `threshold` fraction of hydrophobic AAs
    Typical signal peptides are 15-25 aa with a hydrophobic h-region.
    """
    if not seq or seq[0] != "M" or len(seq) < window + 1:
        return False
    h_region = seq[1:1 + window]
    if not h_region:
        return False
    h_count = sum(1 for c in h_region if c in _HYDROPHOBIC)
    return (h_count / len(h_region)) >= threshold


def _standardize_df(df, source_db, bioactivity):
    """Ensure DataFrame has all standard columns."""
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df["Source_DB"] = source_db
    df["Bioactivity"] = bioactivity
    return df[STANDARD_COLUMNS]


# ---- Parsers --------------------------------------------------------------

def parse_dbaasp(data_path=None, bioactivity="antimicrobial", **kwargs):
    """Parse DBAASP database export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading DBAASP: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "DBAASP", bioactivity)
    log.warning("  DBAASP: no data path. Download from https://dbaasp.org/")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def parse_apd3(data_path=None, bioactivity="antimicrobial", **kwargs):
    """Parse APD3 (Antimicrobial Peptide Database) export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading APD3: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "APD3", bioactivity)
    log.warning("  APD3: no data path. Download from https://aps.unmc.edu/")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def parse_conoserver(data_path=None, bioactivity="toxicity",
                     min_length=5, max_length=100,
                     exclude_precursors=True, **kwargs):
    """
    Parse ConoServer FASTA (conoserver_protein.fa or .fa.gz).

    Header format (pipe-delimited):
      P00001|SI|Conus striatus|Wild type|conotoxin|A superfamily|alpha conotoxin|I|protein level
      [0]=ID  [1]=name  [2]=organism  [3]=type  [4]=bioactivity  [5]=superfamily
      [6]=subfamily  [7]=class  [8]=evidence

    Filters:
      - Drops entries whose 'type' field is 'Precursor' (contains signal peptide).
      - Drops sequences outside [min_length, max_length] after cleaning.
      - Drops sequences containing no-standard residues (after cleaning == empty).
    """
    if not data_path or not os.path.exists(data_path):
        log.warning("  ConoServer: no data path. Download from https://www.conoserver.org/")
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    log.info(f"  Loading ConoServer: {data_path}")
    records = []
    n_total = 0
    n_precursor = 0
    n_bad_seq = 0
    n_out_of_range = 0

    for header, raw_seq in _iter_fasta(data_path):
        n_total += 1
        fields = header.split("|")
        def _g(i):
            return fields[i].strip() if i < len(fields) else ""

        cono_id = _g(0)
        name = _g(1)
        organism = _g(2) or "Conus sp."
        type_field = _g(3)
        cono_bioact = _g(4)
        superfamily = _g(5)
        subfamily = _g(6)
        cls = _g(7)
        evidence = _g(8) or "unknown"

        if exclude_precursors and "precursor" in type_field.lower():
            n_precursor += 1
            continue

        seq = _clean_sequence(raw_seq)
        if not seq:
            n_bad_seq += 1
            continue
        if not (min_length <= len(seq) <= max_length):
            n_out_of_range += 1
            continue

        rec = {
            "ID": f"CON_{cono_id}" if cono_id else f"CON_{n_total}",
            "Accession": cono_id,
            "Parent_Accession": cono_id,
            "Protein_Name": name or f"{superfamily} {cls}".strip(),
            "Sequence": seq,
            "Length": len(seq),
            "Organism": organism,
            "Organism_ID": "",
            "Lineage": "",
            "Habitat": "marino",
            "Taxonomic_Group": "Gastropoda_Cone",
            "Source_DB": "ConoServer",
            "Bioactivity": bioactivity,
            "Evidence_Type": evidence or type_field or "curated_mature",
            "Mature_Source": "DB_CURATED",
            "PubMed_ID": "",
            "Date_Created": "",
            "Date_Modified": "",
        }
        records.append(rec)

    log.info(
        "  [conoserver] total=%d kept=%d precursors_dropped=%d "
        "bad_seq=%d out_of_range=%d",
        n_total, len(records), n_precursor, n_bad_seq, n_out_of_range,
    )

    df = pd.DataFrame(records)
    return _standardize_df(df, "ConoServer", bioactivity) if not df.empty else df


def parse_arachnoserver(data_path=None, bioactivity="toxicity",
                        min_length=5, max_length=100, **kwargs):
    """
    Parse ArachnoServer FASTA (arachno_db_all_pep.fa).

    Header format (pipe-delimited):
      as:Bradykinin-1-Lycosa erythrognatha|sp:P0C7S8|1 BPP-S from venom of the spider...
      [0]=as:NAME  [1]=sp:UNIPROT_ACC  [2]=INDEX DESCRIPTION

    All entries are already mature toxin peptides (ArachnoServer stores mature only).
    """
    if not data_path or not os.path.exists(data_path):
        log.warning("  ArachnoServer: no data path. Download from http://www.arachnoserver.org/")
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    log.info(f"  Loading ArachnoServer: {data_path}")
    records = []
    n_total = 0
    n_bad_seq = 0
    n_out_of_range = 0

    n_precursor_keyword = 0
    n_signal_peptide = 0

    for header, raw_seq in _iter_fasta(data_path):
        n_total += 1
        fields = header.split("|")

        name = ""
        uniprot_acc = ""
        description = ""
        for f in fields:
            f = f.strip()
            if f.startswith("as:"):
                name = f[3:].strip()
            elif f.startswith("sp:"):
                uniprot_acc = f[3:].strip()
            else:
                # First non-tagged field; strip leading index number
                description = re.sub(r"^\d+\s*", "", f).strip()

        # ---- Precursor detection (skip these) ----
        header_low = (name + " " + description).lower()
        if "precursor" in header_low:
            n_precursor_keyword += 1
            continue

        # Try to guess organism from name (e.g., "Bradykinin-1-Lycosa erythrognatha" -> "Lycosa erythrognatha")
        organism = "Spider sp."
        m = re.search(r"-([A-Z][a-z]+ [a-z]+)$", name)
        if m:
            organism = m.group(1)

        seq = _clean_sequence(raw_seq)
        if not seq:
            n_bad_seq += 1
            continue

        # ---- Signal peptide heuristic (only on full-length precursors) ----
        # Short mature peptides (< max_length) almost never contain a 20aa
        # hydrophobic signal region. Apply heuristic only on long sequences.
        if len(seq) > max_length and _looks_like_signal_peptide(seq):
            n_signal_peptide += 1
            continue

        if not (min_length <= len(seq) <= max_length):
            n_out_of_range += 1
            continue

        acc = uniprot_acc or f"ARA_{n_total}"
        rec = {
            "ID": f"ARA_{acc}",
            "Accession": acc,
            "Parent_Accession": acc,
            "Protein_Name": name or description[:80],
            "Sequence": seq,
            "Length": len(seq),
            "Organism": organism,
            "Organism_ID": "",
            "Lineage": "",
            "Habitat": "terrestre",
            "Taxonomic_Group": "Arachnida",
            "Source_DB": "ArachnoServer",
            "Bioactivity": bioactivity,
            "Evidence_Type": "curated_mature",
            "Mature_Source": "DB_CURATED",
            "PubMed_ID": "",
            "Date_Created": "",
            "Date_Modified": "",
        }
        records.append(rec)

    log.info(
        "  [arachnoserver] total=%d kept=%d precursor_kw=%d signal_pep=%d "
        "bad_seq=%d out_of_range=%d",
        n_total, len(records), n_precursor_keyword, n_signal_peptide,
        n_bad_seq, n_out_of_range,
    )

    df = pd.DataFrame(records)
    return _standardize_df(df, "ArachnoServer", bioactivity) if not df.empty else df


def parse_hemolytik(data_path=None, bioactivity="hemolytic", **kwargs):
    """Parse Hemolytik database export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading Hemolytik: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "Hemolytik", bioactivity)
    log.warning("  Hemolytik: no data path provided.")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def parse_cancerppd(data_path=None, bioactivity="anticancer", **kwargs):
    """Parse CancerPPD database export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading CancerPPD: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "CancerPPD", bioactivity)
    log.warning("  CancerPPD: no data path provided.")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def parse_cppsite(data_path=None, bioactivity="cpp", **kwargs):
    """Parse CPPsite database export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading CPPsite: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "CPPsite", bioactivity)
    log.warning("  CPPsite: no data path provided.")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def parse_biopep(data_path=None, bioactivity="antioxidant", **kwargs):
    """Parse BIOPEP database export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading BIOPEP: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "BIOPEP", bioactivity)
    log.warning("  BIOPEP: no data path provided.")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


def parse_avpdb(data_path=None, bioactivity="antiviral", **kwargs):
    """Parse AVPdb database export."""
    if data_path and os.path.exists(data_path):
        log.info(f"  Loading AVPdb: {data_path}")
        df = pd.read_csv(data_path)
        return _standardize_df(df, "AVPdb", bioactivity)
    log.warning("  AVPdb: no data path provided.")
    return pd.DataFrame(columns=STANDARD_COLUMNS)


DB_PARSERS = {
    "dbaasp": parse_dbaasp,
    "apd3": parse_apd3,
    "conoserver": parse_conoserver,
    "arachnoserver": parse_arachnoserver,
    "hemolytik": parse_hemolytik,
    "cancerppd": parse_cancerppd,
    "cppsite": parse_cppsite,
    "biopep": parse_biopep,
    "avpdb": parse_avpdb,
}


def get_parser(db_name):
    """Get parser function by database name."""
    parser = DB_PARSERS.get(db_name.lower())
    if parser is None:
        log.warning(f"  No parser for database: {db_name}")
    return parser
