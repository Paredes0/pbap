---
description: Public roadmap — community-facing ideas and milestones.
related: [todo.md, decisions.md]
---

# Roadmap — Peptide Bioactivity Audit Pipeline

This is the **public** roadmap: ideas, milestones and improvements that are open for community discussion or contribution. The list is intentionally light on dates — it describes what *could* happen, not committed deadlines.

> Contributors welcome. Open an issue or a draft PR for any of these items, or propose new ones via GitHub Discussions.

## Status conventions

- `idea` — open, no commitment.
- `planned` — design agreed, looking for someone to implement.
- `in progress` — actively being worked on (link the PR/issue).
- `done` — completed and verified.
- `parked` — paused (state the blocker).

---

## Short term — usability and packaging

### Docker image (one-command setup)
**What**: bundle the orchestrator, the 6 micromamba environments and the tool repositories into a single Docker image.
**Why**: even with `bootstrap_tools.sh` + `bootstrap_envs.sh`, the disk and time cost (~35–45 GB, ~30–60 min) keeps the barrier high. A pre-built image would drop it to "docker pull + run".
**Status**: `idea`.

### Public demo (Gradio)
**What**: a small hosted page where anyone can paste a peptide sequence, run the pipeline and see the HTML report.
**Why**: lower the activation energy for evaluating the pipeline.
**Status**: `done` — live at [huggingface.co/spaces/Paredes-0/pbap-demo](https://huggingface.co/spaces/Paredes-0/pbap-demo). Operator-side scaffold in [`demo/`](../demo/), ADR `2026-05-13` in [`decisions.md`](decisions.md).

### Bootstrap scripts (reproducibility from `git clone`)
**What**: scripts that clone the 10 upstream tools, apply the 5 reproducibility patches, and create the 6 micromamba envs — so a third party can recreate the pipeline without access to the maintainer's internal tree.
**Why**: previously the public repo carried only orchestrator code; the 10 tools and the envs were assumed to "be there", which they aren't on a fresh machine.
**Status**: `done` — see `scripts/bootstrap_tools.sh`, `scripts/bootstrap_envs.sh`, [`SETUP_FROM_SCRATCH.md`](SETUP_FROM_SCRATCH.md), and [`patches/`](../patches/) + [`envs/`](../envs/).

### Demo video (≤ 90 seconds)
**What**: screen recording — drop FASTA → run pipeline → open HTML report.
**Why**: README screenshots help, but a short video is the fastest "what does this thing do".
**Status**: `idea`.

---

## Medium term — pipeline robustness

### Per-tool length validation
**What**: every tool accepts a different peptide-length range. Validate before running and warn (or skip with a clear message) when a peptide falls outside the trained range.
**Why**: today an out-of-range peptide silently produces garbage in some tools and a crash in others.
**Status**: `idea`.

### Prediction cache
**What**: hash each peptide sequence and store its predictions per tool on disk. Re-running the same peptide skips the inference.
**Why**: useful when datasets overlap across runs.
**Status**: `idea`.

### Friendlier error messages on tool failure
**What**: translate raw stderr/tracebacks into human-readable diagnoses ("model file missing", "env broken", "invalid input").
**Why**: today the user has to read the Python traceback to know what to fix.
**Status**: `idea`.

### Reference validation benchmark
**What**: a small set of 20-50 peptides with experimentally validated bioactivity, plus a script that reports current metrics. Regression test for tool integrations.
**Why**: when someone adds a new tool, this catches obvious breakage.
**Status**: `idea`.

---

## Longer term — analytical depth

### Leakage analysis via CD-HIT-2D (Phase 2)
**What**: for every tool, compute CD-HIT-2D similarity between the user input and the tool's training set. Tag every peptide with `Gold` / `Silver` / `Bronze` / `Red` to indicate how novel it is for that specific tool.
**Why**: reframes the output as "this prediction is reliable because the peptide is similar to what the tool was trained on" vs. "this is extrapolation". Empirical applicability-domain calibration.
**Status**: `done` (Phase 2 audit pipeline) — implemented in `scripts/cdhit_leakage_analysis.py` and orchestrated by `bin/audit_pipeline.sh`. Reframed as Applicability Domain bands in 2026-05 (ADR in [`decisions.md`](decisions.md)). **Not integrated into Phase 1 user inference** — its outputs are offline validation artifacts, not per-peptide labels in the user report. See [`leakage_analysis.md`](leakage_analysis.md).

### Phase-2 integration into Phase-1 reports
**What**: surface CD-HIT-2D AD bands and reliability stratification into the user-facing `REPORT.html` (today they live only in offline Phase-2 outputs).
**Why**: the user inferring on novel peptides today has no visibility into how reliable each tool's verdict is for *their specific input*.
**Status**: `idea`. Builds on the now-complete Phase-2 leakage analysis.

### Reliability curves stratified by leakage grade
**What**: for each tool and each grade, compute sensitivity/specificity/MCC/AUC against an independent ground-truth dataset. Result: a "trust this tool this much, when the peptide is this far from its training".
**Why**: turns each tool from a black-box vote into a calibrated reliability signal.
**Status**: `idea`.

### Taxonomic bias analysis
**What**: stratify per-tool metrics by taxonomic origin (bacteria / fungi / plants / animals / etc).
**Why**: a tool that excels on bacterial AMPs may flop on fungal peptides — the user should be told.
**Status**: `done` (Phase 2) — implemented in `scripts/taxonomic_bias_analysis.py` with Fisher exact + Wilson CI + Benjamini–Hochberg FDR. See [`taxonomic_analysis.md`](taxonomic_analysis.md). Same caveat: Phase-2 only.

### Weighted ensemble by reliability
**What**: instead of equal-vote consensus, weight each tool's prediction by its calibrated reliability for the specific peptide.
**Why**: better integration of heterogeneous predictors.
**Status**: `idea`. Depends on the reliability curves item above. Documented as "Option E" in [`orchestrator_design.md`](orchestrator_design.md) §4 — current consensus layer is "Option B" (agreement only, no voting).

---

## Coverage — adding more tools / categories

### Unblock tools currently marked BLOCKED or DEFERRED
**What**: revisit `docs/pipeline_viability.md`. Tools currently blocked because of training-script-as-inference patterns or missing feature extractors can be partially salvaged with wrappers.
**Why**: every unblocked tool extends coverage.
**Status**: `idea`. Tracked per-tool.

### New bioactivity categories
**What**: currently uncovered categories include allergenicity, antifungal, antiviral, hypotensive, anti-aging. Look for tools that satisfy the 5 viability criteria (`docs/pipeline_viability.md`).
**Why**: aim for breadth.
**Status**: `idea`.

### Richer HTML report
**What**: sortable tables, filters, side-by-side comparison of peptides, per-peptide drill-down, APEX heatmap and disagreement view.
**Why**: navigating a report with 100+ peptides gets tedious.
**Status**: partially `done` — current `REPORT.html` already supports sortable tables, filters, per-peptide drill-down, an APEX 34-strain block and a disagreement section. Remaining `idea` items: PDF export, side-by-side peptide comparison view, persistent column-pinning across reloads.

---

## How to contribute to this roadmap

1. To **claim an item**, open an issue or comment in an existing one. We'll mark it `in progress` with your handle.
2. To **propose a new item**, open a Discussion (or an issue tagged `roadmap`) describing what, why and a rough estimate of effort.
3. To **change an item's status**, open a PR editing this file.

---

## Related docs

- `docs/todo.md` — short-term technical debt and known issues.
- `docs/decisions.md` — architectural decisions and trade-offs.
- `docs/pipeline_viability.md` — per-tool viability status.
- `docs/architecture.md` — system architecture and components.

---
[← Back to Index](INDEX.md)
