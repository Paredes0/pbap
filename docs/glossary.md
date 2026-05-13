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
- **Leakage**: the problem where sequences used to evaluate a model
  were already present in its training set, artificially inflating
  accuracy.
- **Leakage grades**:
    - **Gold**: high novelty (<40% identity vs. training).
    - **Silver**: medium novelty (40-60%).
    - **Bronze**: low novelty (60-80%).
    - **Red**: probable leakage (>80% identity).
- **Peptide**: short amino-acid chain (typically <50-100 AA in this
  project).

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
