# Taxonomic Bias Analysis

The pipeline evaluates whether tool performance varies significantly
with biological origin. This is critical for generalization to
organisms underrepresented in training (e.g. octopus).

## Processing and stratification

1.  **Mining and lineage**: positive peptides preserve their full
    taxonomic metadata.
2.  **Broad groups**: cross-classification into 4 categories:
    - `Vert_Terrestrial` / `Vert_Marine`
    - `Invert_Terrestrial` / `Invert_Marine` (crucial for cephalopod
      peptides).
3.  **Gold-standard filtering**: the default analysis only uses
    **Gold** peptides. This prevents inflated performance (from
    already-seen sequences) from hiding failures in specific taxa.

## Statistical rigor

`scripts/taxonomic_bias_analysis.py` implements robust tests:

- **Fisher exact test**: compares each group against the rest to detect
  sensitivity deviations.
- **Multiple corrections**: Benjamini-Hochberg (FDR) and Bonferroni to
  avoid false positives when testing many taxa.
- **Wilson score interval**: 95% confidence intervals for sensitivity
  that remain accurate at small sample size (N).
- **Heterogeneity (chi-squared)**: a global χ² test to determine
  whether the distribution of correct predictions differs significantly
  across groups.

## Bias detection (interpretation)

- **LOW_POWER**: groups with **n < 10** are flagged as underpowered.
- **Interpretation for octopus**: the `Invert_Marine` group is analyzed
  specifically. If its sensitivity is significantly lower than other
  groups (p-adj < 0.05), it is documented as a generalization failure
  of the tool.

## Script usage

```bash
python taxonomic_bias_analysis.py --tool <ID> --grades Gold --output-dir <DIR>
```

The final report includes comparative bar charts per taxon, allowing
quick visualization of tool weaknesses in specific biological niches.

---
[← Back to Index](INDEX.md)
