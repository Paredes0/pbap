# Glossary — Project terms

This glossary defines the scientific, technical and operational terms
used in the Peptide Bioactivity Audit Pipeline.

## Scientific terms

- **Bioactivity**: capacity of a peptide to interact with a biological
  system and produce an effect (e.g. kill a bacterium, inhibit an
  enzyme).
- **MIC (Minimum Inhibitory Concentration)**: the lowest concentration
  of a peptide that prevents visible microbial growth. Typically
  measured in µM or µg/mL.
- **Peptide**: short amino-acid chain (typically <50–100 AA in this
  project).

- **Applicability Domain (AD)**: the region of input space where a
  trained model's predictions can be considered reliable. Formalized
  in QSAR / cheminformatics (Tropsha & Golbraikh; OECD Principle 3).
  For sequence-based peptide models, a natural AD distance is
  **maximum identity to any training sequence**: peptides close to
  training are inside the AD (interpolation, reliable), peptides far
  from training are outside the AD (extrapolation, less reliable).
  Implemented in this project via the CD-HIT-2D grading — see
  `docs/leakage_analysis.md`.

- **Leakage**: a sequence used to evaluate a model was already in (or
  near-identical to) the training set, so the reported metric
  partially measures memorization rather than predictive capacity.

- **Leakage grades (CD-HIT-2D bands)**: identity bands relative to the
  tool's training set, used for Phase-2 auditing. They are
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
  See `docs/leakage_analysis.md` for the full two-lens discussion.

## Technical terms (architecture)

- **Orchestrator**: master script (`run_audit.py`) that manages the
  sequential or parallel execution of multiple tools.
- **SSH dispatch**: technique to run heavy tasks (e.g. CD-HIT) on a
  remote Linux server via SSH, allowing the main orchestrator to run
  on Windows.
- **Layer 2 (Consensus)**: logic that compares the results of several
  tools in the same category to emit an agreement verdict
  (`consensus_positive`) or disagreement (`split`).
- **Tool health**: operational state of a tool during a run (`OK` or
  `PROBLEMATIC`).
- **Normalization**: process of converting the various tool output
  formats to a common schema (`class_norm`, `score`).

## Operational terms

- **Project memory**: the set of documents in `docs/` that serve as the
  "source of truth" for the project.
- **Index-first**: strategy of consulting indexes (`INDEX.md`,
  `INDEX_LOOKUP.md`) before reading large code files.
- **ADR (Architecture Decision Record)**: formal record of why a
  technical decision was made (in `docs/decisions.md`).

---
[← Back to Index](INDEX.md)
