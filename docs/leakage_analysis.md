# Leakage Analysis (CD-HIT-2D)

> ⚠️ **Scope: Phase 2 (scientific audit) — NOT integrated in Phase 1**
>
> The Gold / Silver / Bronze / Red grading system described in this
> document runs as part of the **scientific audit flow**
> (`bin/audit_pipeline.sh` and associated scripts in `scripts/`), NOT
> as part of the **user inference flow** (`scripts/run_audit.py`).
>
> When a user runs `python scripts/run_audit.py --input my.fasta`, the
> output **does not include** per-peptide confidence labels.
> Applicability-domain calibration and per-peptide labels in production
> are **future work** (see `docs/roadmap.md` § "Leakage analysis via
> CD-HIT-2D (Phase 2)").
>
> What already exists: `scripts/cdhit_leakage_analysis.py`,
> `scripts/auditoria_validation.py` and companion scripts generate the
> grades for offline analysis over evaluation pools built
> independently.

The core of validation is the similarity analysis between the
independent test pool and each tool's training data.

## Methodology

We use `cd-hit-2d` to compare our pool against the training dataset at
three decreasing sequence-identity thresholds: **80%, 60% and 40%**.

### Confidence grading system

Each peptide in our pool receives a tag based on its "survival" through
the CD-HIT filter:

| Tag | Survival condition | Scientific interpretation |
| :--- | :--- | :--- |
| **Gold** | Survives 80%, 60% and 40% | **Highest confidence**: completely novel sequence (<40% identity). |
| **Silver** | Survives 80% and 60%, dies at 40% | **High confidence**: remote similarity (40-60%) with training. |
| **Bronze** | Survives 80%, dies at 60% | **Medium confidence**: moderate similarity (60-80%). |
| **Red** | Dies at 80% | **Probable leakage**: high identity (>80%) or duplicate. |

## Length analysis (Robust Mode)

`cdhit_leakage_analysis.py` evaluates whether test peptides fall within
the tool's operational range:

- **Robust Mode**: unlike a simple min/max range, robust mode computes
  the range from the actual training distribution to prevent "outlier"
  peptides from contaminating statistical validity.
- **Tagging**: each peptide is marked `within_range`, `too_short` or
  `too_long`.
- The downstream benchmark analysis (FDR, sensitivity) can be filtered
  to consider only **Gold + within_range** peptides, removing both
  leakage noise and unsupported lengths.

## Technical execution

```bash
python cdhit_leakage_analysis.py --tool <ID> --test-fasta <POOL> --training-fasta <TRAIN>
```

This script generates a `leakage_<TOOL>_classifications.csv` file that
serves as the basis for all downstream statistical computations.

---
[← Back to Index](INDEX.md)
