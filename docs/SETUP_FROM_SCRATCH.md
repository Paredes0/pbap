---
description: End-to-end install walkthrough — from `git clone` to a green smoke test.
audience: A new operator who has just cloned the public PBAP repo and wants to run Phase 1 locally.
last_updated: 2026-05-13
related: [deployment.md, pipeline_viability.md]
---

# Setup from scratch

This walkthrough takes you from a fresh `git clone` of
**[github.com/Paredes0/pbap](https://github.com/Paredes0/pbap)** to a
green smoke test of Phase 1 (user inference). Everything below is
scripted so the only manual step is the one external download that
isn't programmatic.

> **Scope**: Phase 1 only (`scripts/run_audit.py`). Phase 2 (the
> offline scientific audit under `bin/audit_pipeline.sh`) is **not
> reproducible from this repo** because some of its inputs are
> curated locally and not redistributed. Phase 1 is fully self-
> contained.

> **Target platform**: Linux (Ubuntu/Debian/Fedora/Arch all fine).
> macOS works but a couple of upstream tools have CUDA-only paths
> that fall back to CPU silently. Windows is supported as the
> *orchestrator* host (with WSL2 for the tools), but the path of
> least resistance is a single Linux box.

---

## Time and resources

| Phase | Time | Disk |
|---|---|---|
| Clone repo + tools (1 below) | 5–10 min | ~1.5 GB (clones) |
| Create 6 micromamba envs (2 below) | 20–40 min | 30–40 GB (envs) |
| Manual download of HemoPI2 weights (3 below) | 2 min | ~30 MB |
| Smoke test (4 below) | 1–3 min for 10 peptides | < 100 MB outputs |
| **Total** | **~30–60 min** | **~35–45 GB** |

CPU runs end-to-end. **A GPU is not required** for any of the 10
active tools — every one of them has CPU fallback. With a GPU
(>= 8 GB VRAM), Phase 1 is roughly 3–5× faster on PLM-heavy tools
(`hemopi2`, `hemodl`, `deepbp`, `bertaip`).

---

## Prerequisites

- `git`, `python3` (any ≥ 3.10), `bash`
- `micromamba` ([installation](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html))
- ~45 GB free disk
- Internet access (clones + first-run downloads of ESM-2 / ProtT5
  weights by `fair-esm` / `transformers`)

You do **not** need a GitHub account, an Anaconda account, or any
paid service.

---

## 1. Clone the repo and its tools

```bash
git clone https://github.com/Paredes0/pbap.git
cd pbap

# Clones the 10 upstream tools into Dataset_Bioactividad/Tool_Repos/
# and applies the 5 reproducibility patches that ship under patches/.
# Idempotent — re-running it on an existing tree is a no-op.
bash scripts/bootstrap_tools.sh
```

The summary at the end should read `OK (10): toxinpred3 antibp3 hemopi2 hemodl deepb3p deepbp apex perseucpp acp_dpe bertaip`. If any tool fails, the script names it and exits non-zero; re-running picks up where it left off.

**What this does:**

1. For each of the 10 active tools, reads `github_url` from
   `config/pipeline_config.yaml` and clones it into
   `Dataset_Bioactividad/Tool_Repos/<tool>/`.
2. If `patches/<tool>.patch` exists, applies it on top of the clone
   with `git apply`. See [`patches/README.md`](../patches/README.md)
   for the per-patch rationale (~100 lines of mechanical adapters in
   total; no model logic is altered).

---

## 2. Create the micromamba environments

```bash
# Creates the 6 envs needed to run the 10 tools, using the YAML
# manifests under envs/. Each YAML pins exact package versions
# (channels: bioconda, conda-forge) for reproducibility.
bash scripts/bootstrap_envs.sh
```

This step is the longest. It also depends on `bioconda` /
`conda-forge` mirrors being healthy — if it fails mid-way, rerun and
it picks up the missing envs (existing ones are skipped).

The 6 envs:

| Env | Python | Tools that use it |
|---|---|---|
| `ml` | 3.10 | toxinpred3, antibp3, hemodl |
| `torch` | 3.10 | hemopi2, perseucpp |
| `qsar` | 3.10 | apex |
| `torch_legacy` | 3.9 | deepbp, acp_dpe |
| `deepb3p_legacy` | 3.7 | deepb3p (legacy TF 1.14) |
| `pipeline_bertaip` | 3.10 | bertaip |

Disk footprint: ~30–40 GB total. If you only need a subset of tools,
pass the corresponding env names to the script:
`bash scripts/bootstrap_envs.sh ml torch qsar`.

You also need a small environment **for the orchestrator itself** —
plain Python + 5 deps:

```bash
micromamba create -y -n pbap_orchestrator python=3.11 pip
micromamba activate pbap_orchestrator
pip install -r requirements.txt
```

This is the env you'll be **in** when you invoke
`python scripts/run_audit.py`. It is separate from the 6 per-tool
envs (the orchestrator spawns subprocesses with
`micromamba run -n <env> python <tool>/predict.py` internally).

---

## What you have so far — expected tree

After steps 1 and 2 your working tree should look like this:

```
pbap/                                             ← git clone github.com/Paredes0/pbap
├── audit_lib/                                    ← orchestrator (in repo)
├── scripts/                                      ← run_audit.py + bootstrap_*.sh (in repo)
├── config/                                       ← pipeline_config.yaml + … (in repo)
├── docs/                                         ← documentation (in repo)
├── demo/                                         ← optional public-demo scaffold (in repo)
├── patches/                                      ← reproducibility patches (in repo)
├── envs/                                         ← env YAML manifests (in repo)
├── wrappers/                                     ← CLI adapters (in repo)
├── site/                                         ← GitHub Pages source (in repo)
├── test_data/                                    ← canonical FASTAs (in repo)
├── Inputs/example.fasta                          ← smoke-test FASTA (in repo)
│
└── Dataset_Bioactividad/Tool_Repos/              ← CREATED by bootstrap_tools.sh
    ├── toxinpred3/        ← clone of raghavagps/toxinpred3
    ├── antibp3/           ← clone of raghavagps/AntiBP3
    ├── hemopi2/           ← clone of raghavagps/hemopi2     ⚠ waiting on Model.zip (step 3)
    ├── hemodl/            ← clone of abcair/HemoDL          + hemodl.patch applied
    ├── deepb3p/           ← clone of GreatChenLab/deepB3P   + deepb3p.patch applied
    ├── deepbp/            ← clone of Zhou-Jianren/bioactive-peptides
    ├── apex/              ← clone of machine-biology-group-public/apex   + apex.patch applied
    ├── perseucpp/         ← clone of goalmeida05/PERSEU     + perseucpp.patch applied
    ├── acp_dpe/           ← clone of CYJ-sudo/ACP-DPE       + acp_dpe.patch applied
    └── bertaip/           ← clone of ying-jc/BertAIP
```

And in your micromamba envs folder (`~/micromamba/envs/` by default):

```
~/micromamba/envs/
├── ml/                    ← bootstrap_envs.sh, used by toxinpred3, antibp3, hemodl
├── torch/                 ← bootstrap_envs.sh, used by hemopi2, perseucpp
├── qsar/                  ← bootstrap_envs.sh, used by apex
├── torch_legacy/          ← bootstrap_envs.sh, used by deepbp, acp_dpe
├── deepb3p_legacy/        ← bootstrap_envs.sh, used by deepb3p (legacy TF 1.14)
└── pipeline_bertaip/      ← bootstrap_envs.sh, used by bertaip
```

A `pbap_orchestrator` env is created separately at the end of step 2
above; it is the env you'll be **in** when you run
`python scripts/run_audit.py`. It is independent of the six tool envs
listed here.

If your tree matches the structure above, only one thing is missing
before the smoke test can run cleanly: HemoPI2's weights.

---

## 3. One manual download — HemoPI2 weights

`HemoPI2`'s authors host the trained model outside their git repo.
The bootstrap script clones the code but the weights have to be
fetched manually:

1. Visit the HemoPI2 page on
   [raghavagps.github.io/hemopi2](https://webs.iiitd.edu.in/raghava/hemopi2/)
   and follow the **"Download"** link for the `Model.zip` file
   (~30 MB).
2. Extract it inside the tool clone:

   ```bash
   cd Dataset_Bioactividad/Tool_Repos/hemopi2
   unzip /path/to/Model.zip       # creates ./Model/ and ./model/
   cd -
   ```

If `Model.zip` ever moves, check the upstream repo
[`raghavagps/hemopi2`](https://github.com/raghavagps/hemopi2) — the
README there is the source of truth for the download location.

All other tools either ship their weights inside the git clone
(`toxinpred3`, `antibp3`, `apex`, `perseucpp`, `acp_dpe`, `deepb3p`) or
auto-download them on first run (`hemodl` → ESM-2 via `fair-esm`,
`deepbp` → ESM-2, `bertaip` → Hugging Face `yingjc/BertAIP`).

---

## 4. Smoke test

With the orchestrator env active:

```bash
# Tiny — 8 peptides, all 10 tools
python scripts/run_audit.py --input Inputs/example.fasta
```

First run will be slow (60–180 s) because `fair-esm` and
`transformers` are downloading ESM-2 and BertAIP weights into their
default cache. Subsequent runs are 10–30 s on the same input.

Result: `Outputs/example_<ISO_timestamp>/` with `REPORT.html`,
`consolidated.csv`, `consolidated.json`, `tool_health_report.json`
(see [`data.md`](data.md) for the schema).

A successful run prints `n_tools_ok=10` in
`tool_health_report.json`. If it says anything less, open that file
and look for the failing tool's `diagnosis` field. Common causes:

| `diagnosis` snippet | Likely fix |
|---|---|
| `launcher_missing: 'micromamba'` | `micromamba` not on `PATH` from the orchestrator's shell. Set `PBAP_MICROMAMBA_BIN=/absolute/path/to/micromamba` or extend `PATH`. |
| `exit_code=1` + `Model.zip` references | Step 3 above was skipped. |
| `numpy.AxisError: axis 1 is out of bounds` | You passed a single peptide. Most tools assume ≥ 2 sequences. Workaround: add a second peptide. |
| `output_missing` | The tool wrote results to an unexpected path. Open the per-tool log under `Outputs/<run>/per_tool/<tool>/run_<tool>.log`. |

Larger smoke test:

```bash
python scripts/run_audit.py --input test_data/AMPs_canonical.fasta
```

10 canonical AMPs (magainin, melittin, LL37, indolicidin, etc.). Same
machinery, more meaningful coverage.

---

## 5. (Optional) Host the public demo

If you want to expose your local installation as a free public web
demo (the [`demo/`](../demo/) folder), see
[`demo/api/README.md`](../demo/api/README.md) for the FastAPI
backend and [`demo/frontend/README.md`](../demo/frontend/README.md)
for the Hugging Face Space frontend.

---

## Troubleshooting cheatsheet

| Symptom | First thing to check |
|---|---|
| `bootstrap_tools.sh` says `patch X.patch does not apply cleanly` | The upstream of that tool changed its layout after our patch was authored. Open the patch, see what file it expects, manually adjust, or contact the maintainer to refresh the patch. |
| `bootstrap_envs.sh` fails with `unsatisfiable` | A pinned package was removed from `conda-forge`. Open the failing `envs/<env>.yaml`, find the offending line, and either bump or unpin it. |
| `consolidated.csv` is empty | Look at `tool_health_report.json`. If `n_tools_ok=0`, the orchestrator launched but every tool errored — usually means `micromamba` is not callable from inside the orchestrator subprocess (see PBAP_MICROMAMBA_BIN above). |
| Tool repos disk usage grows out of control | The `git clone --depth 1` flag in `bootstrap_tools.sh` keeps each clone shallow. If you ever full-cloned, `git -C <tool> gc --aggressive` reclaims space. |

For deeper issues, the full per-tool history of "what worked and
what didn't" is in [`pipeline_viability.md`](pipeline_viability.md).
