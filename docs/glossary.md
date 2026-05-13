# Glossary — Project terms

This glossary defines the scientific, technical and operational terms
used in the Peptide Bioactivity Audit Pipeline. Entries are ordered
alphabetically within each section. Most entries are cross-linked to
the canonical doc where the concept is discussed in depth.

---

## Scientific terms

- **Applicability Domain (AD)**: the region of input space where a
  trained model's predictions can be considered reliable. Formalized
  in QSAR / cheminformatics (Tropsha & Golbraikh; OECD Principle 3).
  For sequence-based peptide models, a natural AD distance is
  **maximum identity to any training sequence**: peptides close to
  training are inside the AD (interpolation, reliable), peptides far
  from training are outside the AD (extrapolation, less reliable).
  Implemented in this project via the CD-HIT-2D grading — see
  [`leakage_analysis.md`](leakage_analysis.md).

- **APEX strain classification**: tagging system that assigns each of
  the 34 strains predicted by the APEX tool to one of three buckets —
  **pathogen**, **commensal**, or **broad-spectrum / other** — so the
  pipeline can compute selectivity scores (e.g. "active against
  pathogens but spares commensals"). Defined in
  `config/apex_strain_classification.yaml`; methodology in
  [`orchestrator_design.md`](orchestrator_design.md) §8.

- **Bioactivity**: capacity of a peptide to interact with a biological
  system and produce an effect (e.g. kill a bacterium, inhibit an
  enzyme). The orchestrator groups bioactivities into **7
  categories**: toxicity, hemolytic, antimicrobial, anti-inflammatory,
  anticancer, blood-brain barrier (BBB), cell-penetrating (CPP).

- **CD-HIT / CD-HIT-2D**: redundancy-clustering tool used in Phase-2
  leakage analysis. CD-HIT-2D compares a query set against a reference
  set; for PBAP, query = evaluation peptides, reference = the tool's
  training set. See [`leakage_analysis.md`](leakage_analysis.md).

- **Leakage**: a sequence used to evaluate a model was already in (or
  near-identical to) the training set, so the reported metric
  partially measures memorization rather than predictive capacity.

- **Leakage grades (CD-HIT-2D bands)**: identity bands relative to
  the tool's training set, used for Phase-2 auditing. They are
  **identity bands, not value judgments**; the right interpretation
  depends on whether you are benchmarking the tool or trusting a
  specific prediction.
    - **Gold** — <40% identity. Far from training. Best for measuring
      generalization; least reliable for practical predictions
      (out-of-distribution).
    - **Silver** — 40–60% identity. Inside the AD. Clean benchmark
      signal and reliable predictions.
    - **Bronze** — 60–80% identity. Inside the AD, close to training.
      Reliable predictions; slightly inflated as benchmark signal.
    - **Red** — ≥80% identity. Near-duplicate of a training neighbor.
      Predictions are near-memorization by interpolation: practically
      correct but uninformative for benchmarking. Excluded from
      benchmark metrics.
  See [`leakage_analysis.md`](leakage_analysis.md) for the full
  two-lens discussion.

- **MIC (Minimum Inhibitory Concentration)**: the lowest
  concentration of a peptide that prevents visible microbial growth.
  Typically measured in µM or µg/mL. APEX returns 34 MICs per
  peptide (one per strain).

- **Peptide**: short amino-acid chain (typically 5–100 AA in this
  project, with hard limits enforced per-tool via `length_range` in
  `config/pipeline_config.yaml`).

---

## Technical terms — schema and orchestration

- **Agreement layer / consensus**: logic that compares the results
  of several tools in the same bioactivity category to emit an
  intra-category verdict — `consensus_positive`, `consensus_negative`,
  `split` (tools disagree), or `single_tool` (only one tool covers
  this category in this run). No voting, no weighted average — see
  ADR `2026-04-25` in [`decisions.md`](decisions.md).

- **`arg_style`**: dimension in `pipeline_config.yaml` that tells
  the runner how to invoke a tool's CLI. One of four modes:
    - `flagged` (default) — `--input FILE --output FILE`.
    - `positional` — input is a positional arg.
    - With `pre_command` / `cwd_subdir` — tool writes to a hardcoded
      filename; runner relocates the output.
    - `wrapper` — invoke a custom adapter under
      [`wrappers/`](../wrappers/) (use only when the other three
      modes are insufficient — see
      [`wrappers/README.md`](../wrappers/README.md)).

- **Dual schema (binary + extra_metrics)**: every tool can emit two
  parallel outputs into the orchestrator, non-exclusive:
    - **Binary axis**: `class_norm ∈ {positive, negative, None}` and
      `score ∈ [0,1] | None`. Used for classification-style tools
      (toxinpred3, antibp3, hemopi2, …).
    - **`extra_metrics` axis**: per-tool dict of continuous measures
      like `{MIC_E_coli: {value: 1.2, unit: µM}}`. APEX (34 strains)
      and DeepBP (E. coli / S. aureus regressors) use this.
  Both can coexist on the same tool. APEX is `extra_only` (no
  class_norm). See ADR `2026-04-25` in
  [`decisions.md`](decisions.md).

- **Holistic score**: continuous tiebreaker within a structural
  tier, computed as
  `good_mean − bad_mean + apex_adjustment + potency_adjustment`.
  See [`orchestrator_design.md`](orchestrator_design.md) §9.

- **Normalization**: process of converting heterogeneous tool
  outputs to the common schema above. Per-tool rules are declared in
  the tool's `output_parsing:` block in `pipeline_config.yaml`.

- **Orchestrator**: the master Python script
  [`scripts/run_audit.py`](../scripts/run_audit.py) that drives an
  end-to-end run: FASTA in → per-tool subprocesses → consolidated
  schema → reports.

- **Patch (interoperability patch)**: a small text diff under
  [`patches/`](../patches/) that adapts an upstream tool to the
  PBAP runner. Contains only mechanical adapters (argparse,
  `__main__` blocks, FASTA→CSV converters); never model
  architecture or weights. Authored by the PBAP maintainer; applied
  on top of an unmodified `git clone` of the upstream. Legal
  posture documented in [`patches/README.md`](../patches/README.md).

- **SSH dispatch**: technique used by `audit_lib/cdhit_utils.py` to
  run CD-HIT on a remote Linux node when the orchestrator runs on
  Windows. Only CD-HIT uses SSH dispatch — all prediction tools run
  locally to the orchestrator. ADR `2026-05-08` in
  [`decisions.md`](decisions.md).

- **Structural score**: integer ranking score per peptide, derived
  from the polarity of evaluated categories: positive
  (`POS=3`, `SPLIT=2`, `NEG=1`, `NONE=0`) on "good" categories,
  inverted on "bad" categories. Primary sort key in all reports.
  See [`orchestrator_design.md`](orchestrator_design.md) §9.

- **Tool health**: operational state of a tool during a run
  (`OK` / `PROBLEMATIC`) plus diagnosis fields (timeout, missing
  output, etc.). Reported in `tool_health_report.json`.

- **Wrapper (CLI wrapper)**: Python file under
  [`wrappers/`](../wrappers/) that implements a standard
  `--input FASTA --output CSV` interface around a tool whose own
  entry point is incompatible with the four runner modes. Wrappers
  are 100% PBAP-maintainer code; they **read** the upstream tool's
  files at runtime but never redistribute them. See
  [`wrappers/README.md`](../wrappers/README.md).

---

## Operational terms — repo, demo, contributors

- **ADR (Architecture Decision Record)**: formal record of why a
  technical or strategic decision was made. Lives in
  [`decisions.md`](decisions.md), one entry per decision dated in
  reverse chronological order.

- **Allow-list / kill switch**: in the public demo (`demo/api/`),
  the `ALLOWED_TOOLS` env var is the **single configuration point**
  that controls which tools the backend will run. Setting it to a
  subset of the 10 active tool IDs disables the rest without code
  changes. Used as the immediate response to a takedown request
  (see *Mitigation shield* below).

- **Bootstrap scripts**: the two idempotent bash scripts under
  [`scripts/`](../scripts/) that let a third party reproduce the
  setup from a fresh `git clone`:
    - [`bootstrap_tools.sh`](../scripts/bootstrap_tools.sh) — clones
      the 10 upstream tools and applies the 5 patches.
    - [`bootstrap_envs.sh`](../scripts/bootstrap_envs.sh) — creates
      the 6 micromamba envs from the manifests under
      [`envs/`](../envs/).
  Full walkthrough in
  [`SETUP_FROM_SCRATCH.md`](SETUP_FROM_SCRATCH.md).

- **Cloudflare Quick Tunnel**: zero-config exposure mechanism used
  by the public demo to expose the operator's local FastAPI backend
  to the internet over HTTPS without opening router ports or
  requiring a domain. URL changes on every restart; managed via
  `cloudflared.service` on the operator's host.

- **Contract (docs ↔ code)**: the table in
  [`ONBOARDING.md`](../ONBOARDING.md) §4 that pairs each code path
  with the doc that must be updated alongside it. Enforced softly
  by the CI workflow `.github/workflows/docs-sync.yml`.

- **Demo** (the public web demo): the optional layer under
  [`demo/`](../demo/) that exposes the pipeline as a free,
  non-commercial web service. Two halves: `demo/api/` (FastAPI
  backend on operator's Linux host, behind a Cloudflare Tunnel) and
  `demo/frontend/` (Gradio app deployed as a Hugging Face Space).
  Separate from the pipeline core — see ADR `2026-05-13 — Public
  demo as a separate layer` in [`decisions.md`](decisions.md).

- **End-of-task checklist**: the list in
  [`ONBOARDING.md`](../ONBOARDING.md) §5 that any contributor
  (human or AI) runs before declaring a task complete: verify
  contract obligations, append to changelog, update ADRs if
  decisions changed, etc.

- **Index-first**: strategy of consulting indexes
  ([`INDEX.md`](INDEX.md), [`INDEX_LOOKUP.md`](INDEX_LOOKUP.md))
  before reading large code files. Required of AI agents in
  [`AGENTS.md`](../AGENTS.md) Rule #1.

- **Mitigation shield**: the operator-side posture under which the
  public demo runs without prior permission from each upstream tool
  author. Six commitments enforced in code and docs: (1) clear
  attribution per tool in every result, (2) takedown email visible
  on every page (`noeparedesalf@gmail.com`), (3) operator commits
  to a 24-hour response window, (4) no model weights served, (5)
  no login / tracking / per-user storage, (6) `ALLOWED_TOOLS`
  allow-list as a single kill switch. Documented in
  [`demo/api/README.md`](../demo/api/README.md) §"Mitigation
  shield" and justified in ADR `2026-05-13` in
  [`decisions.md`](decisions.md).

- **Phase 1 / Phase 2**: the two execution modes of the pipeline.
  Phase 1 (`scripts/run_audit.py`) is the user-facing inference flow
  that produces a `REPORT.html` per input FASTA. Phase 2
  (`bin/audit_pipeline.sh`) is the offline scientific audit that
  produces leakage / bias / QC reports per tool. Phase 2's outputs
  are **not** integrated into Phase 1 — they live in
  `Dataset_Bioactividad/` and are not redistributed publicly.

- **Project memory**: the set of canonical documents in `docs/`
  that serve as the durable source of truth for the project.
  Distinct from session memory (an AI agent's per-conversation
  state) and from the changelog (which is append-only history).

- **Repro gaps**: shorthand for the three deliverables added in
  commit `1d9dad9` that let a third party recreate the pipeline
  setup without access to the maintainer's internal tree:
  reproducibility **patches** under `patches/`, **env manifests**
  under `envs/`, and the end-to-end **walkthrough**
  [`SETUP_FROM_SCRATCH.md`](SETUP_FROM_SCRATCH.md). The term comes
  from the audit that named them — see the changelog entry of
  2026-05-13.

- **Takedown**: a request from an upstream tool author (or anyone
  with legal standing) to remove a patch, disable a tool in the
  demo, or otherwise withdraw a piece of distribution. Channeled
  to `noeparedesalf@gmail.com` with a documented 24-hour SLA.
  Mechanism is the `ALLOWED_TOOLS` allow-list (demo) or removal of
  a `.patch` file (repo).

---
[← Back to Index](INDEX.md)
