# Project Context and Objective

> ⚠️ **Scope note**: this document describes the **full project goals**.
> Some of them (notably the Gold / Silver / Bronze / Red grading system)
> are only implemented in the **scientific audit flow (Phase 2)**, not
> in the **user inference flow (Phase 1)** that runs
> `scripts/run_audit.py`. See `docs/architecture.md` for the phase
> separation and `docs/leakage_analysis.md` for the detail.

## Motivation

In peptide bioinformatics, many published prediction tools report
extremely high performance metrics (Accuracy, MCC, AUC). However, these
metrics are often inflated due to:

1.  **Data leakage**: the benchmarks used to validate the tool contain
    sequences that are identical or very similar to those used during
    training.
2.  **Taxonomic bias**: a tool may work very well on peptides from
    certain taxa (e.g. bacteria) but fail on others, limiting its
    general clinical or biotechnological utility.
3.  **Length overfitting**: tools may be optimized for a very narrow
    length range.

## Objectives

The main objective of this pipeline is to perform an **independent
external audit** of these tools in order to:

- **Quantify leakage**: use CD-HIT-2D to see how many "real-world"
  sequences have already been seen by each model.
- **Evaluate robustness**: determine whether predictions are consistent
  across different taxonomic groups.
- **Map predictions to the applicability domain**: tag every
  evaluation peptide by its similarity to the tool's training set
  (Gold / Silver / Bronze / Red identity bands) and report per-grade
  metrics separately, so the right reading lens can be picked for the
  question being asked — benchmarking the tool vs. trusting a specific
  prediction. See `docs/leakage_analysis.md`.
- **Provide an independent dataset**: build a pool of positive and
  negative peptides not influenced by the biases of the original
  authors.

## Types of bias analyzed

### 1. Sequence-similarity bias
Analyzed via `cd-hit-2d`, comparing our independent dataset against the
training dataset extracted from each tool's repository.

### 2. Taxonomic bias
Analyzed by comparing prediction metrics (Sensitivity, False Positives)
across different taxonomic origins (Animalia, Plantae, Fungi, Bacteria,
etc.) to ensure that the tool does not depend on a specific taxonomic
signature.

---
[← Back to Index](INDEX.md)
