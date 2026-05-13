---
description: Architectural Decision Records — why X and not Y.
related: [architecture.md]
last_updated: 2026-05-13
---

# Decisions

> Entry format:
> ### YYYY-MM-DD — Decision title
> **Context**: <situation>
> **Decision**: <what was decided>
> **Consequences**: <implications, trade-offs>

### 2026-05-13 — Applicability-domain framing of CD-HIT-2D leakage grades

**Context**: the original documentation framed the four CD-HIT-2D
bands (Gold / Silver / Bronze / Red) as a confidence ladder, with
"Gold = highest confidence" and "Red = leaked, discard". That framing
is correct only for one purpose — measuring a tool's true
generalization capacity — and is **inverted** for the other purpose:
estimating the reliability of a specific prediction the tool just
made on a specific peptide. A peptide far from training (Gold) is
out-of-distribution and *least* trustworthy for practical use; the
operational sweet spot is Bronze/Silver, where the peptide is inside
the model's applicability domain.

This ambiguity has propagated through the docs and is being copied by
other agents reading them.

**Decision**: re-frame the leakage grades around the **Applicability
Domain (AD)** concept from QSAR (Tropsha & Golbraikh; OECD Principle 3).
The four bands remain *identity bands*, with two explicit reading
lenses:

| Tag | Identity | Lens A — Benchmarking | Lens B — Trusting a prediction |
|---|---|---|---|
| Red | ≥80% | uninformative (near-memorization by interpolation) | high but trivial |
| Bronze | 60–80% | mildly inflated | high (in-domain) |
| Silver | 40–60% | clean | high (in-domain) |
| Gold | <40% | best signal of generalization | low (out-of-distribution) |

The labels Gold / Silver / Bronze / Red are kept (already embedded in
code: `classify_leakage_grades` in `audit_lib/cdhit_utils.py`, output
filenames `<grade>_survivors_<tool>.fasta`, CSV columns,
configurations). Only the **interpretation** changes, in the docs.

**Consequences**:
- `docs/leakage_analysis.md` rewritten as the source of truth with
  the two-lens table and a formal AD introduction.
- `docs/glossary.md` adds an "Applicability Domain" entry and rewrites
  the "Leakage grades" entry to drop the value-laden "confidence"
  ladder.
- `docs/data.md` "Leakage grades" section reflects the two-lens
  table.
- `docs/context_objective.md` reframes the "establish confidence
  levels" objective.
- No code changes in this iteration — purely documentation /
  conceptual framing.
- Out-of-scope but on the horizon: future Phase-2 reporting should
  publish per-grade metrics side by side (not a single "trust"
  verdict), and any future weighted-ensemble layer (Option E in
  `orchestrator_design.md` §4) should weight predictions higher when
  the input is in Silver/Bronze and lower when it is in Gold — which
  is the inverse of what a naive reading of "Gold = best" would
  suggest.

### 2026-05-13 — Public release under PolyForm Noncommercial 1.0.0

**Context**: the project is mature enough to be shared publicly. We want
researchers without a programming background to use the pipeline, but we
want to retain commercial-use rights so any SaaS or company integration
must request explicit permission.

**Decision**: release under PolyForm Noncommercial 1.0.0 at
`https://github.com/Paredes0/pbap`. Tag v0.1.0. Contact for commercial
licensing: Noé Paredes Alfaro <noeparedesalf@gmail.com>. A minimal CI
smoke workflow is added, with a personal-data leak check enforced in
CI. Branch protection on `main` keeps `enforce_admins=false` so hotfix
flow is preserved.

**Consequences**:
- Free for academic and non-commercial research use.
- Commercial deployments (SaaS, productization) require explicit
  permission.
- Third-party tool licenses still apply on top — see
  `docs/licenses_audit.md` and `THIRD_PARTY_LICENSES.md`.
- The CI guard prevents accidental commits of personal paths, secrets
  or local-system metadata into the public repository.

### 2026-05-08 — Hybrid architecture and SSH dispatch

**Context**: CD-HIT is critical for leakage analysis but its
pre-compiled binaries are typically Linux-specific. The pipeline is
developed mainly on Windows, but a Linux server with CD-HIT installed
is available.

**Decision**: implement an **SSH dispatch** system in
`audit_lib/cdhit_utils.py`. If the orchestrator detects that it is
running on Windows and cannot find the local binary, it dispatches the
command to a remote Linux node configured in `pipeline_config.yaml`.
File synchronization is assumed via SSHFS or a common shared path.

**Consequences**:
- Enables E2E pipeline execution from Windows without porting complex
  C++ binaries.
- Introduces a network and SSH configuration dependency.
- Dispatch is limited to CD-HIT; other tools still run locally via
  Micromamba.

### 2026-04-29 — Per-tool length-handling scheme

**Context**: tools behave inconsistently with peptides outside their
training range (crash, silent truncation, or extrapolation).

**Decision**: adopt a 3-mode scheme managed by the orchestrator:
1.  **`hard_limit`**: mandatory pre-filtering to avoid crashes.
2.  **`soft_truncate`**: low-reliability marking (`reliability="low"`)
    if truncation occurs.
3.  **`soft_reliability`**: extrapolation warning if the sequence is
    unusually long/short.

**Consequences**:
- Per-tool technical details are centralized in
  `config/pipeline_config.yaml` and summarized in `docs/data.md`.
- Improves report transparency for the user.

### 2026-04-25 — Dual schema (binary axis + extra_metrics)

**Context**: tools have heterogeneous outputs. Some emit a single
class/score (toxinpred3, antibp3, hemopi2…). Others emit continuous
per-target measures (APEX → 34 MICs in µM). Forcing the latter into
binary class loses information.

**Decision**: support two output axes per tool, non-exclusive. Each
tool declares what it emits in `pipeline_config.yaml :: output_parsing`.
The orchestrator materializes extras as `<tool_id>__<metric>__<unit>`
columns. APEX is `extra_only` (no class_norm).

**Consequences**:
- Comparison across binary tools remains intact for the agreement
  layer.
- Continuous metrics surface in their own columns and are not coerced
  to POS/NEG with an arbitrary threshold.

---

## Statistical and heuristic decisions

### 1. Leakage grading (CD-HIT-2D)
> ⚠️ Applied only in the **scientific audit flow (Phase 2)** —
> `bin/audit_pipeline.sh` and associated scripts. **Not** applied in
> the user inference flow (`scripts/run_audit.py`), which does not
> return this tag. Production integration is future work (see
> `docs/roadmap.md`).

Grades based on maximum identity vs. the training set:
- **Gold**: survives CD-HIT-2D at 40% (true novelty).
- **Silver / Bronze**: intermediate similarity (60% / 80%).
- **Red**: similarity > 80%. Likely leaked peptide.

### 2. Hierarchical ranking: structural + holistic

Two-level ordering system used as the default sort across CSV / XLSX /
HTML reports:

1. **Structural score**: integer score derived from the polarity of the
   evaluated categories (POS=3, SPLIT=2, NEG=1, NONE=0 on `good`
   categories; inverted on `bad`).
2. **Holistic score**: continuous aggregate
   `good_mean − bad_mean + apex_adjustment + potency_adjustment`,
   used as the tiebreaker within the same structural tier.

### 3. Length handling (`Length_Status`)

Informative labeling (`within_range`, `too_short`, `too_long`) based on
each tool's training metadata.

---
[← Back to Index](INDEX.md)
