# Leakage Analysis (CD-HIT-2D) and Applicability Domain

> ⚠️ **Scope: Phase 2 (scientific audit) — NOT integrated in Phase 1**
>
> The Gold / Silver / Bronze / Red tagging system described in this
> document runs as part of the **scientific audit flow**
> (`bin/audit_pipeline.sh` and associated scripts in `scripts/`), NOT
> as part of the **user inference flow** (`scripts/run_audit.py`).
>
> When a user runs `python scripts/run_audit.py --input my.fasta`, the
> output **does not include** per-peptide tags. Applicability-domain
> calibration and per-peptide tagging in production are **future work**
> (see `docs/roadmap.md` § "Leakage analysis via CD-HIT-2D (Phase 2)").
>
> What already exists: `scripts/cdhit_leakage_analysis.py`,
> `scripts/auditoria_validation.py` and companion scripts generate the
> tags for offline analysis over independently built evaluation pools.

---

## Why this matters: the Applicability Domain

A trained model is only reliable inside the region of input space it
learned from. In QSAR / cheminformatics this region is called the
**Applicability Domain (AD)** (Tropsha & Golbraikh, 2010 and earlier;
OECD Principle 3). For sequence-based peptide models, a natural
distance metric for the AD is **maximum identity to any training
sequence**.

The intuition is simple:

- A peptide whose nearest training neighbor is at, say, 55% identity
  sits **inside the AD**: the model has seen something structurally
  similar and can interpolate.
- A peptide whose nearest neighbor is at 25% identity sits **outside
  the AD**: the model is extrapolating into territory it has never
  seen. Predictions may still be right, but on average they are less
  trustworthy.
- A peptide whose nearest neighbor is at 95% identity is **so close to
  a training example** that the prediction is essentially
  interpolation over known territory — informative for use, but not
  informative for measuring how good the model really is.

CD-HIT-2D operationalizes this distance: it compares each test
sequence against the entire training set and reports the
identity-survival bands.

---

## Methodology

We run `cd-hit-2d` to compare our test pool against the tool's training
dataset at three decreasing identity thresholds: **80%, 60% and 40%**.
A test sequence "survives" a threshold T if no training sequence has
identity ≥ T with it. The intersection of survival results across the
three thresholds yields four bands.

### The four bands

| Tag | Survival condition | Identity to nearest training neighbor |
| :--- | :--- | :--- |
| **Gold**   | survives 80%, 60% AND 40% | **< 40%** |
| **Silver** | survives 80% AND 60%, dies at 40% | **40 – 60%** |
| **Bronze** | survives 80%, dies at 60% | **60 – 80%** |
| **Red**    | dies at 80% | **≥ 80%** |

These four labels are **identity bands**, nothing more. The
interpretation depends on the question being asked.

---

## Two lenses for the same tags

The Gold/Silver/Bronze/Red labels have two distinct readings depending
on whether you want to (a) **benchmark a tool** (measure its true
predictive capacity) or (b) **trust a specific prediction** the tool
just made on a specific peptide.

| Tag | Distance to training | Lens A — Benchmarking the tool | Lens B — Trusting a prediction |
| :--- | :--- | :--- | :--- |
| **Red** ≥ 80% | very close | Uninformative — the prediction is **near-memorization** by interpolation from an almost-clone. Any decent model would be correct here, so the score does not measure capacity. Exclude from benchmark metrics. | **High** — the model has seen something nearly identical and will almost certainly call this peptide correctly. The prediction is trivially correct rather than insightful, but it is correct. |
| **Bronze** 60 – 80% | close | Mildly inflated — the model is recognizing a close neighbor more than generalizing. Read with caution; useful only when no further-away peptides are available. | **High** — solidly inside the applicability domain. The prediction is an interpolation from known territory. |
| **Silver** 40 – 60% | medium | Clean signal of generalization within the model's reasonable working range. Best balance between leakage and OOD risk for benchmarking. | **High** — still within the applicability domain. The prediction is reliable for a well-trained model. |
| **Gold** < 40% | far | The best signal of **true generalization** — uncontaminated test of whether the model works on novel chemistry. | **Low** — the peptide is **out-of-distribution** for this model. The prediction is extrapolation; the model may simply not know. Use for stress-testing, not for confident operational use. |

### The non-obvious point

If you only care about *how good the tool is* (paper-style
benchmarking), Gold is the cleanest signal — by construction it tests
generalization. If you instead care about *how much to trust this
specific prediction the tool just made on this specific peptide*,
**Bronze and Silver are the operational sweet spot**, and **Gold is
where the model is least trustworthy**. Red is correct but
uninformative.

In short: practical reliability roughly follows similarity to training
(excluding identicals). The closer the peptide is to the training
distribution — without being a duplicate — the more trustworthy the
prediction.

This is exactly what the applicability domain concept formalizes.

---

## Note on the "Red ≥ 80%" cutoff

The 80% identity threshold for the "Red" band is a **field convention**,
not a physical constant. Two notes:

1. A 50-aa peptide at 80% identity to a training neighbor differs in
   10 residues — it is **not the same sequence**. A model trained on
   the neighbor will not literally recall the test peptide; it will
   *predict* on it. But the local sequence fingerprint that ML models
   (especially PLM-based ones such as ESM-2 / ProtT5) actually use is
   largely preserved, so the prediction is dominated by proximity
   rather than by learned chemistry. That is why Red is treated as
   "near-memorization by interpolation" rather than as a true test of
   generalization.
2. Different sub-fields use different cutoffs: CD-HIT's default is
   0.9 for redundancy clustering, while many peptide benchmarks
   (Wood et al. 2019 and others) use 0.4 for independent evaluation.
   We adopted **0.8 / 0.6 / 0.4** as the three audit thresholds
   because they cover the most-used cutoffs in the literature for
   peptide-prediction tools and define the four bands cleanly.

---

## Length analysis (Robust Mode)

`cdhit_leakage_analysis.py` also evaluates whether test peptides fall
within the tool's operational length range:

- **Robust mode**: instead of a simple min/max, the range is computed
  from the actual training distribution (percentiles), so a few
  outlier-length training peptides do not inflate the bounds.
- **Tagging**: each peptide is marked `within_range`, `too_short` or
  `too_long`.
- Downstream benchmark analysis (FDR, sensitivity) can be filtered to
  consider only `within_range` peptides, eliminating length-driven
  noise on top of similarity-driven noise.

The length filter and the similarity grading are **independent
dimensions**: a Gold peptide can be too-long, a Red peptide can be
within-range, etc.

---

## Technical execution

```bash
python cdhit_leakage_analysis.py --tool <ID> \
    --test-fasta <POOL> \
    --training-fasta <TRAIN>
```

Generates `leakage_<TOOL>_classifications.csv`, which is the basis for
all downstream per-grade statistics in the audit pipeline (per-grade
sensitivity, specificity, MCC, etc.).

The audit reporting **does not collapse the bands into a single
"trust" verdict**. Per-grade metrics are reported side by side, so
that depending on your purpose (benchmarking vs. estimating practical
reliability) you can read the column that matches your question.

---

## References

- Tropsha, A. (2010). *Best practices for QSAR model development,
  validation, and exploitation*. **Molecular Informatics**, 29, 476-488.
- Tropsha, A. & Golbraikh, A. (2007). *Predictive QSAR modeling
  workflow, model applicability domains, and virtual screening*.
  **Current Pharmaceutical Design**, 13, 3494-3504.
- OECD (2007). *Guidance Document on the Validation of (Quantitative)
  Structure-Activity Relationships [(Q)SAR] Models* — Principle 3:
  "A defined domain of applicability".
- Wood, K. *et al.* (2019). *Peptide redundancy reduction* —
  representative cutoffs used in peptide benchmarks.

---
[← Back to Index](INDEX.md)
