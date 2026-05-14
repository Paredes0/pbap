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
| `bert_ampep60` | Antimicrobial | Standby (DEFERRED_USER) | Multi-target regression (E. coli, S. aureus). Weights on institutional MPU SharePoint behind a login wall — `onedrivedownloader` receives an HTML page instead of the `.pkl`. Re-activate once weights are hosted at a programmatically reachable URL. |
| `apex` | Antimicrobial | Active | 34 strains. Local execution in env `qsar`. |
| `antibp3` | Antimicrobial | Active | sklearn models + blastp. Linux only. |
| `deepbp` | Anticancer | Active | Based on ESM-2 (Meta). |
| `acp_dpe` | Anticancer | Active | CNN/GRU ensemble (patched). |
| `bertaip` | Anti-inflammatory | Active | Replaces aip_tranlac. BERT-based. |
| `antifungipept` | Antifungal | Standby (DEFERRED_USER) | Model pkls (`cmodel.pkl`, `rmodel_C_a.pkl`) shipped as git-lfs pointer files, not hydrated. Requires `git lfs pull` on the upstream clone; `ml_legacy_py38` env not redistributed in `envs/`. |
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

## 4. Micromamba environment inventory

### 4.1 — Core envs for the 10 active tools (recreatable from this repo)

These six environments are required to run the active pipeline and
are **redistributed as YAML manifests** under `envs/`. A third party
recreates them with `bash scripts/bootstrap_envs.sh` (see
[`SETUP_FROM_SCRATCH.md`](SETUP_FROM_SCRATCH.md) §2).

- **ml** (Python 3.10): general classic ML stack (sklearn, xgboost,
  blastp, biopython). Used by `toxinpred3`, `antibp3`, `hemodl`.
- **torch** (Python 3.10): modern PyTorch 2.x + Transformers + `fair-esm`.
  Used by `hemopi2`, `perseucpp`.
- **qsar** (Python 3.10): RDKit and cheminformatics descriptors. Used
  by `apex`.
- **torch_legacy** (Python 3.9): PyTorch tools with older Keras / TF
  shims. Used by `deepbp`, `acp_dpe`.
- **deepb3p_legacy** (Python 3.7): TensorFlow 1.14 legacy stack. Used
  by `deepb3p`. The only Python 3.7 env needed.
- **pipeline_bertaip** (Python 3.10): BertAIP-specific Transformers /
  simpletransformers config, kept independent to avoid version
  collisions. Used by `bertaip`.

### 4.2 — Historical envs for parked / blocked tools (not redistributed)

These environments exist on the original development host because
they were used during the 2026-04 viability audit (see
[`pipeline_viability.md`](pipeline_viability.md)), but the tools that
need them are currently in `STANDBY` / `BLOCKED` state and **no YAML
manifest is shipped** for them. Operators who want to reactivate one
of these tools must recreate the env themselves:

- **ml_deepforest**: CascadeForest libraries. Used by `deepforest_htp`
  (BLOCKED).
- **ml_legacy_py38** (Python 3.8): used by `antifungipept` (active in
  the audit history but currently inactive in the public release).
- **ml_pycaret**: PyCaret API. Used by tools no longer in the active set.

### 4.3 — Auxiliary envs (created on demand, not for tool execution)

- **pbap_orchestrator** *(required for Phase 1 CLI)*: tiny env with
  the orchestrator's 5 dependencies (`pyyaml`, `pandas`, `numpy`,
  `openpyxl`, `requests`). Created manually in step 4 of
  [`SETUP_FROM_SCRATCH.md`](SETUP_FROM_SCRATCH.md); not redistributed
  as a YAML because `requirements.txt` already pins it.
- **pbap_demo_api** *(optional, demo only)*: backend env for the
  public web demo under `demo/api/`. Contains only `fastapi`,
  `uvicorn`, `pydantic` and `python-multipart`. **Not** required for
  CLI use; only relevant when hosting the public Gradio + FastAPI
  demo. Setup in [`../demo/api/README.md`](../demo/api/README.md)
  §"Deployment".

**Conflict isolation**: each env is independent of the others to
prevent transitive dependency collisions (numpy 2.0 vs. legacy
TensorFlow versions, modern Transformers vs. simpletransformers,
etc.). Tools never share an interpreter at runtime.

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
