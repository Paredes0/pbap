---
description: System architecture — components, dependencies, data flow.
related: [decisions.md, api.md]
last_updated: 2026-05-13
---

# System Architecture

## Overview

The system is an ecosystem for peptide-bioactivity auditing and
prediction, orchestrated in Python. The architecture is based on a
**local execution model distributed across environments**, where a
central orchestrator manages isolated sub-processes.

---

## 1. Directory structure

```text
.
|-- bin/                            # High-level orchestrators
|   `-- audit_pipeline.sh          # Master script for scientific audit (Phase 2)
|-- config/                         # YAML configuration
|   |-- pipeline_config.yaml       # 26-tool catalog, SSH, environments
|   |-- categories_config.yaml     # Bioactivities, UniProt queries, polarities
|   `-- apex_strain_classification.yaml  # APEX strain classification (pathogen/commensal)
|-- scripts/                        # Pipeline core logic (Python)
|   |-- run_audit.py               # E2E Phase 1 orchestrator (user inference)
|   |-- run_tool_prediction.py     # Per-tool benchmark runner
|   |-- cdhit_leakage_analysis.py  # Leakage analysis via CD-HIT-2D
|   |-- extract_training_data.py   # Extract training data from repos
|   |-- mine_positives_per_bioactivity.py  # Positive mining per category (UniProt + DBs)
|   |-- generate_category_negatives.py     # Per-tool negative generation
|   |-- auditoria_validation.py    # Per-tool QC (stats, distributions, AA composition)
|   |-- taxonomic_bias_analysis.py # Taxonomic bias (Fisher, Wilson CI, BH-FDR)
|   `-- final_audit_report.py      # Global cross-tool report (JSON, TXT, XLSX)
|-- wrappers/                       # Robust adapters for non-standard tools
|   `-- bert_ampep60_cli.py        # CLI wrapper for BERT-AMPep60
|-- audit_lib/                      # Shared library (12 modules — see api.md)
|   |-- config.py                  # YAML loading
|   |-- tool_runner.py             # Execution engine (micromamba run)
|   |-- tool_length_range.py       # Per-tool length ranges
|   |-- downloader.py              # Weights download (Zenodo, HuggingFace, manual)
|   |-- cdhit_utils.py             # CD-HIT with SSH dispatch
|   |-- uniprot_client.py          # UniProt REST client
|   |-- sequence_utils.py          # Sequence validation and normalization
|   |-- db_parsers.py              # Parsers for DBAASP, APD3, ConoServer, etc.
|   |-- length_sampling.py         # Length-stratified sampling
|   |-- state_manager.py           # Incremental audit state
|   |-- provenance.py              # JSON provenance metadata
|   `-- logging_setup.py           # Standard logging setup
|-- Inputs/                         # User input FASTA files
|-- Outputs/                        # Prediction results (HTML, XLSX, CSV, JSON)
`-- Dataset_Bioactividad/           # Phase 2 pipeline outputs (Pools, Audits, Reports)
```

---

## 2. Main components

### 1. E2E orchestrator — Phase 1 (`scripts/run_audit.py`)
Main entry point for the user. Manages the full lifecycle of a
prediction run:
- **Batching**: splits the input FASTA to avoid memory errors.
- **Normalization**: consolidates heterogeneous tool outputs into a
  common schema.
- **Ranking**: computes `structural_score` + `holistic_score` to
  prioritize peptides.
- **Reports**: generates interactive HTML, formatted XLSX, CSV, JSON
  and Markdown.

### 2. Audit orchestrator — Phase 2 (`bin/audit_pipeline.sh`)
Master Bash script that runs the full scientific audit per tool:
1. **Positive mining** (`mine_positives_per_bioactivity.py`)
2. **Training extraction** (`extract_training_data.py`)
3. **Leakage analysis** (`cdhit_leakage_analysis.py`)
4. **Negative generation** (`generate_category_negatives.py`)
5. **Prediction and benchmarking** (`run_tool_prediction.py`)
6. **Taxonomic bias** (`taxonomic_bias_analysis.py`)
7. **Per-tool QC** (`auditoria_validation.py`)
8. **Global report** (`final_audit_report.py`)

### 3. Execution engine (`audit_lib/tool_runner.py`)
Abstracts external-tool invocation:
- **Micromamba run**: executes each tool's scripts inside its specific
  environment (`torch`, `ml`, `pipeline_bertaip`, etc.) locally.
- **Output capture**: translates tool logs and CSV/txt files into the
  internal format.
- **Return value**: a `ToolResult` object with `tool_id`, `output_path`,
  `exit_code`, `runtime`, `diagnosis`.

### 4. Bioinformatics utilities (`audit_lib/`)
- **`cdhit_utils.py`**: handles redundancy analysis. **Only component
  with SSH dispatch capability**. Allows CD-HIT to run on a remote
  Linux server when the main orchestrator runs on Windows.
- **`uniprot_client.py`**: UniProt mining with pagination, retries and
  checkpointing.
- **`db_parsers.py`**: 9 parsers for external databases (DBAASP, APD3,
  ConoServer, ArachnoServer, Hemolytik, CancerPPD, CPPsite, BIOPEP,
  AVPdb).
- **`downloader.py`**: weights download from Zenodo, HuggingFace or
  platforms requiring manual download.
- **`tool_length_range.py`**: inference of optimal length ranges per
  tool from training data.

> Full API reference with signatures: see [`api.md`](api.md).

---

## 3. Data flow and execution

### Local execution model
Unlike preliminary versions, the current system performs **no general
process dispatch**. All prediction tools run on the same machine as the
orchestrator. Isolation is achieved via **Conda/Micromamba**, not
hardware separation.

### Exception: SSH satellite (CD-HIT)
Because of the computational cost of redundancy filtering and the
dependency on native Linux binaries, the CD-HIT module can be
configured to:
1.  **Local execution**: if the host is Linux and has `cd-hit`
    installed.
2.  **SSH dispatch**: if the host is Windows, the orchestrator uploads
    files temporarily to a Linux server via SSH, runs the command and
    downloads the results.

---

## 4. Critical dependencies

- **Micromamba**: ultra-fast environment manager used to isolate tools.
- **Python stack**: pandas, numpy, scipy, pyyaml, openpyxl, requests.
- **CD-HIT**: external binary for leakage and redundancy analysis.

---
[← Back to Index](INDEX.md)
