# Pipeline Deployment and Configuration

This document describes system configuration, the dependency inventory
and the current state of the execution environments for the bioactivity
pipeline.

## 1. System configuration

The system operates under a **local execution** model. The orchestrator
activates a specific Micromamba environment for each tool, ensuring
that each one runs in its verified technology stack.

### Configuration files

#### 1. `config/pipeline_config.yaml`
Defines global parameters and the tool catalog.
- `global`: seeds, default length ranges, CD-HIT thresholds.
- `ssh`: configuration for the Linux server. **Important**: in the
  current architecture, SSH execution is reserved **exclusively for the
  CD-HIT process** (redundancy filtering). All prediction tools run
  locally on the host machine.
- `tools`: catalog of tools. Each tool has an assigned `conda_env` that
  the orchestrator activates before execution.

#### 2. `config/categories_config.yaml`
Defines the audited bioactivities and the UniProt queries used to build
positive pools.

---

## 2. Dependency inventory (technical mapping)

This inventory maps the technical requirements identified for each
tool. Because of severe inter-library incompatibilities (e.g. numpy
2.0 vs. legacy TensorFlow versions), the system uses an
environment-based isolation strategy.

| # | tool_id | Env / Stack | Python | Main libraries |
|---|---|---|---|---|
| 1 | **toxinpred3** | `ml` | 3.10+ | sklearn 1.0.2, blastp |
| 2 | **hemodl** | `ml` | 3.8 | tensorflow 2.13, lightgbm 4.0.0 |
| 3 | **hemopi2** | `torch` | 3.10+ | torch 2.x, esm, transformers |
| 4 | **plm4alg** | `torch_legacy`| -- | (Standby) Jupyter-based |
| 5 | **bert_ampep60** | `torch` | 3.10+ | torch 2.x, transformers |
| 6 | **apex** | `qsar` | 3.10+ | rdkit, torch 2.x |
| 7 | **antibp3** | `ml` | 3.10+ | sklearn, blastp (Linux) |
| 8 | **deepbp** | `torch_legacy`| 3.7/3.8 | keras, tensorflow (legacy) |
| 9 | **acp_dpe** | `torch_legacy`| 3.7/3.8 | torch 1.x, keras |
| 10 | **avppred_bwr** | `torch` | -- | (Standby) no inference script |
| 11 | **bertaip** | `pipeline_bertaip`| 3.10+ | simpletransformers, transformers |
| 12 | **antifungipept**| `ml_legacy_py38` | 3.8 | sklearn, legacy numpy |
| 13 | **deepb3p** | `deepb3p_legacy` | 3.7 | tensorflow 1.14.0, rdkit |
| 14 | **perseucpp** | `torch` | 3.10+ | torch 2.x, sklearn |

---

## 3. Audited-tool status

| Tool ID | Category | Status | Notes |
| :--- | :--- | :--- | :--- |
| `toxinpred3` | Toxicity | Active | Local execution in env `ml`. |
| `hemodl` | Hemolytic | Active | Model based on ESM-2 + ProtT5. |
| `hemopi2` | Hemolytic | Active | Mode `-m 3` (ESM2 only). |
| `bert_ampep60` | Antimicrobial | Active | Multi-target regression (E. coli, S. aureus). |
| `apex` | Antimicrobial | Active | 34 strains. Local execution in env `qsar`. |
| `antibp3` | Antimicrobial | Active | sklearn models + blastp. Linux only. |
| `deepbp` | Anticancer | Active | Based on ESM-2 (Meta). |
| `acp_dpe` | Anticancer | Active | CNN/GRU ensemble (patched). |
| `bertaip` | Anti-inflammatory | Active | Replaces aip_tranlac. BERT-based. |
| `antifungipept` | Antifungal | Active | Runs in `ml_legacy_py38`. |
| `deepb3p` | BBB | Active | Python 3.7 + TF 1.14 (legacy). |
| `perseucpp` | CPP | Active | 2-stage classification (CPP + Efficiency). |
| `plm4alg` | Allergenicity | Standby | Jupyter/Colab-based. Requires refactor. |
| `avppred_bwr` | Antiviral | Standby | Missing inference script and accessible weights. |

### 3.1 Blocked and inactive tools (`config/pipeline_config_blocked.yaml`)

These tools have been discarded or moved to an inactive state after
the viability audit (`docs/pipeline_viability.md`).

| Tool ID | Category | Status | Reason |
| :--- | :--- | :--- | :--- |
| `aapl` | Anti-angiogenic | **Blocked** | Structural failure or external dependency. |
| `if_aip` | Anti-inflammatory | **Blocked** | Structural failure or external dependency. |
| `mfe_acvp` | Antiviral | **Blocked** | Requires external web services (ESMAtlas, NetSurfP-3.0). |
| `multimodal_aop` | Antioxidant | **Blocked** | Structural failure or external dependency. |
| `afp_mvfl` | Antifungal | **Blocked** | Structural failure or external dependency. |
| `antiaging_fl` | Anti-aging | **Blocked** | Structural failure or external dependency. |
| `deepforest_htp` | Hypotensive | **Blocked** | Structural failure or external dependency. |
| `stackthp` | Tumor-homing | **Blocked** | Structural failure or external dependency. |
| `cpppred_en` | CPP | **Blocked** | Structural failure or external dependency. |
| `macppred2` | Anticancer | **Blocked** | Structural failure or external dependency. |
| `_aip_tranlac_backup` | Anti-inflammatory | **Inactive** | Replaced by `bertaip`. |
| `hypeptox_fuse` | Toxicity | **Inactive** | Excessive RAM consumption (≥ 32 GB). |

---

## 4. Real Micromamba environment inventory

To guarantee reproducibility and avoid dependency conflicts, the
following environments are maintained on the system:

- **deepb3p_legacy**: DeepB3P-specific (Python 3.7, TensorFlow 1.14).
- **ml**: general environment for classic ML tools (sklearn, xgboost,
  etc.).
- **ml_deepforest**: dedicated to DeepForest-HTP (CascadeForest
  libraries).
- **ml_legacy_py38**: for tools that require Python 3.8 and old
  package versions.
- **ml_pycaret**: dedicated to tools depending on the PyCaret API.
- **pipeline_bertaip**: BertAIP-specific environment to avoid conflicts
  with other Transformers implementations.
- **qsar**: RDKit and cheminformatics descriptors.
- **torch**: main environment with modern PyTorch and Transformers.
- **torch_legacy**: PyTorch tools with legacy dependencies (e.g. older
  CUDA).
- **pbap_demo_api** *(optional, demo only)*: backend env for the
  public web demo under `demo/api/`. Contains only `fastapi`,
  `uvicorn`, `pydantic` and `python-multipart` (see
  `demo/api/requirements.txt`). **Not** required for CLI use of the
  pipeline; only needed when an operator wants to host the public
  Gradio + FastAPI demo themselves. Setup steps live in
  `demo/api/README.md` §"Deployment".

**Conflict isolation**: dedicated environments (e.g.
`pipeline_bertaip`, `pbap_demo_api`) are kept independent to prevent
version collisions.

---

## 5. Limitations and operation

### Execution
- **Local vs. SSH**: 100% of the tool prediction logic is **local**.
  No process dispatch to other PCs.
- **CD-HIT**: the only component that uses **SSH** to run redundancy
  filtering on a Linux node.

### Memory and resources
- The orchestrator uses `--batch-size` to manage RAM/VRAM consumption.

---

## 6. Quick execution guide

### User prediction
```bash
python scripts/run_audit.py --input Inputs/my_peptides.fasta --name experiment_1
```

### Scientific audit
```bash
./bin/audit_pipeline.sh --tool toxinpred3
```

---
[← Back to Index](INDEX.md)
