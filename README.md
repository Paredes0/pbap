# 🧬 Peptide Bioactivity Audit Pipeline (PBAP)

![Status](https://img.shields.io/badge/status-Phase_1_operational-success)
![License](https://img.shields.io/badge/license-PolyForm_Noncommercial_1.0.0-blue)
![Tools](https://img.shields.io/badge/integrated_tools-10_of_26-orange)
![Categories](https://img.shields.io/badge/bioactivity_categories-7-blueviolet)
![Environments](https://img.shields.io/badge/conda_envs-9-yellow)

**PBAP** is a modular orchestrator that audits the reusability of published
peptide-bioactivity prediction tools and coordinates them under a **unified
output schema**, adding analytical layers (concordance, pathogen / commensal
selectivity, hierarchical multi-criteria ranking) that are absent from
individual tools.

Out of **26 prediction tools** published between 2023 and 2025 that we
systematically evaluated, **10 are currently integrated and operational**,
spanning **7 bioactivity categories**: toxicity, hemolytic, antimicrobial,
anti-inflammatory, anticancer, blood-brain-barrier, cell-penetrating peptides.

> **License at a glance**: this orchestrator is released under the
> [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)
> license. Free for research, academic and personal use. **Commercial use
> requires a separate license** — see [LICENSE](LICENSE) for contact info.
>
> The 26 third-party tools are NOT bundled and each has its own license —
> see [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## Why this project

Most peptide-bioactivity prediction tools published in the literature report
high in-paper metrics, but the practical reality is fragmented:

- ~60% of evaluated tools cannot be run as-is (training scripts published as
  if they were inference, missing weights, feature pipelines without an
  orchestrator, login walls, etc.).
- Each runnable tool uses a different input format, output format and
  environment.
- No published platform coordinates them under a single schema, with
  bacterial-selectivity tagging and a multi-criteria ranking.

PBAP fills that gap. It is also designed as a **platform of tools** rather
than a monolithic predictor: adding, replacing or disabling a tool is a
YAML edit, not a code change. This makes it sustainable in a field where
dozens of new tools are published every year.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Paredes0/pipeline_Work---copia.git pbap
cd pbap

# 2. Install micromamba (per-tool environment manager)
# See https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html

# 3. Create the orchestrator's own environment (Python ≥ 3.10)
micromamba create -n pbap_orchestrator python=3.11 pyyaml pandas numpy openpyxl requests
micromamba activate pbap_orchestrator

# 4. (Optional but typical) Clone the prediction tools you want to use
#    into Dataset_Bioactividad/Tool_Repos/<tool_name>/
#    See docs/pipeline_viability.md for the upstream URLs and per-tool notes.

# 5. Run the smoke test with the bundled example FASTA
python scripts/run_audit.py --input Inputs/example.fasta

# 6. Open the interactive HTML report
# Result: Outputs/example_<timestamp>/REPORT.html
```

📖 Full setup: [`docs/deployment.md`](docs/deployment.md).
📖 Architecture: [`docs/architecture.md`](docs/architecture.md).
📖 Doc index: [`docs/INDEX.md`](docs/INDEX.md).

---

## What you get per run

For every batch of input peptides, the orchestrator produces under
`Outputs/<input>_<timestamp>/`:

| File | What it contains |
|---|---|
| **REPORT.html** | Interactive HTML5 (sortable matrix + filters + per-peptide drill-down). No external dependencies. The primary artefact for eye-balling results. |
| **REPORT.md** | Plain-text Markdown summary (6 sections). |
| **consolidated.csv** / **.json** | Wide (CSV) and nested (JSON) data, every prediction with score, agreement flags and extra metrics. |
| **consolidated.xlsx** | 5-sheet Excel workbook with conditional formatting, autofilter and frozen panes. |
| **tool_health_report.json** | Per-tool runtime, status and diagnosis (catches partial failures). |

---

## Integrated tools (10 active)

| Category | Tool | Notes |
|---|---|---|
| Toxicity | ToxinPred3 | SVM + molecular features |
| Antimicrobial (binary) | AntiBP3 | sklearn + blastp |
| Antimicrobial (34 strains, MIC µM) | APEX | + pathogen / commensal / broad-spectrum selectivity tagging |
| Hemolytic | HemoPI2 | ESM-2 fine-tuned |
| Hemolytic | HemoDL | ESM-2 + ProtT5 ensemble |
| Anticancer | DeepBP | ESM-2 deep ensemble |
| Anticancer | ACP-DPE | CNN + GRU dual-path |
| Blood-brain barrier | DeepB3P | Transformer-based |
| Cell-penetrating peptides | PerseuCPP | Two-stage (CPP + efficiency) |
| Anti-inflammatory | BertAIP | BERT-based, threshold 0.8 |

Plus 5 tools currently parked (waiting on RAM, login walls or LFS hydration)
and 10 evaluated but structurally blocked (training-script-as-inference,
missing weights, etc.). See [`docs/pipeline_viability.md`](docs/pipeline_viability.md)
for the per-tool verdict.

---

## Adding your own tools

The pipeline is intentionally a **platform**. Adding a new tool is a YAML
edit, not a Python change. The architecture supports two configuration
files coordinated by state:

- `config/pipeline_config.yaml` — active tools + standby tools (~14 entries).
- `config/pipeline_config_blocked.yaml` — tools evaluated and blocked, kept
  for traceability without polluting the productive config.

A minimal YAML block looks like:

```yaml
tools:
  your_tool_id:
    display_name: Your Tool
    category: antimicrobial
    conda_env: torch
    script: predict.py
    arg_style: flagged           # or: positional
    input_flag: -i
    output_flag: -o
    output_capture: file         # or: hardcoded_file | stdout
    output_parsing:
      format: csv
      prediction_column: Prediction
      positive_label: 1
      score_column: Probability
      score_threshold: 0.5
```

Full guide and dimensions: see [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/orchestrator_design.md`](docs/orchestrator_design.md).

---

## Working with AI agents on this repository

This repository follows the **AGENTS.md convention**: a root file
([`AGENTS.md`](AGENTS.md)) defines the operating manual for AI agents
working on the code, and the doc directory ([`docs/INDEX.md`](docs/INDEX.md))
serves as their navigation entry point. Compatible agents include Claude
Code, Gemini CLI, Cursor, GitHub Copilot Workspace and similar.

If you clone this repository and open it with an AI assistant, it will pick
up the project's full context (architecture, decisions, conventions,
glossary, pipeline viability) **without any manual setup**. This was a
deliberate design choice: lowering the barrier to entry for contributors
who use AI assistance but have no formal programming background, and
making the project sustainable beyond its original author.

If you contribute via AI assistance, your PRs are reviewed against the same
quality bar as manual contributions.

---

## Project structure

```
.
├── bin/                          # Bash entry points (audit_pipeline.sh)
├── scripts/                      # Python orchestrator and helpers
│   └── run_audit.py              # End-to-end inference orchestrator
├── audit_lib/                    # Shared library (config, runner, parsers, ...)
├── wrappers/                     # Tiny CLI adapters for specific tools
├── config/
│   ├── pipeline_config.yaml          # Active + standby tools (~14)
│   ├── pipeline_config_blocked.yaml  # Blocked / inactive tools (~12)
│   ├── categories_config.yaml        # Bioactivity categories + polarities
│   └── apex_strain_classification.yaml  # Pathogen / commensal mapping
├── docs/                         # Project documentation (INDEX.md is the entry)
├── Inputs/                       # Drop your FASTA files here (gitignored)
├── Outputs/                      # Auto-created per run (gitignored)
├── test_data/                    # Tiny FASTA samples for smoke tests
├── AGENTS.md                     # AI agent operating manual
├── CLAUDE.md / GEMINI.md         # Agent-specific entrypoints (import AGENTS.md)
├── LICENSE                       # PolyForm Noncommercial 1.0.0
├── NOTICE                        # What is and is not distributed here
├── THIRD_PARTY_LICENSES.md       # License status of the 26 third-party tools
└── CITATION.cff                  # How to cite this work
```

Folders excluded from the repository (see `.gitignore`):

- `Dataset_Bioactividad/` — local clones of third-party tools (see
  `docs/pipeline_viability.md` for upstream URLs).
- `DATABASES_FASTA/` — external peptide databases (download yourself from
  DBAASP, APD3, ConoServer, etc.).
- `Inputs/*` / `Outputs/*` — user data and run artefacts (folders kept via
  `.gitkeep`).

---

## Roadmap and contributing

- 🗺️ **Roadmap**: [`docs/roadmap.md`](docs/roadmap.md) — community-facing
  ideas, open for contribution.
- 🐛 **Known issues / tech debt**: [`docs/todo.md`](docs/todo.md).
- 🤝 **How to contribute**: [`CONTRIBUTING.md`](CONTRIBUTING.md) — includes
  the YAML template for adding new tools.
- 📜 **Code of Conduct**: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
  (Contributor Covenant 2.1).

---

## Citation

If you use this pipeline in academic work, please cite it as described
in [`CITATION.cff`](CITATION.cff). When the accompanying manuscript is
published, a BibTeX entry will be added here.

Each integrated tool has its own primary citation — please cite the tools
you actually used, in addition to the pipeline. See
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) for per-tool references.

---

## License summary

This software is licensed under the **PolyForm Noncommercial License 1.0.0**.

- ✅ Free for: academic research, teaching, personal projects, public-
     research organisations, non-profit organisations, government use.
- ❌ Not allowed without a separate license: paid SaaS deployment,
     commercial product integration, any revenue-generating use.

If you want to deploy PBAP commercially, please contact the author via the
address in [`LICENSE`](LICENSE). The author is generally happy to grant
commercial licenses on reasonable terms.

The 26 third-party prediction tools are **not** redistributed by this
repository; each has its own upstream license that you must satisfy
separately. See [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
