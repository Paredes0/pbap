# Inputs/

This directory is where you drop the FASTA files you want to run through
the pipeline.

## Conventions

- **One FASTA per run**. Each file should contain one or more peptide
  sequences in standard FASTA format.
- **Filename = run name**. The orchestrator uses the filename (without
  `.fasta`) as the run identifier:
  `Outputs/<filename>_<timestamp>/`.
- **Length**. Peptides between 5 and 100 residues work best. Individual
  tools have their own range constraints — out-of-range peptides may be
  tagged with reduced reliability in the report.
- **Alphabet**. Standard 20 amino acids (`ACDEFGHIKLMNPQRSTVWY`). Other
  characters trigger a warning and may be filtered.

## Contents

- `example.fasta` — small set of canonical peptides (magainin-2,
  melittin, LL-37, α-MSH, indolicidin, …) plus negative controls.
  Use it to verify your setup with `python scripts/run_audit.py --input
  Inputs/example.fasta`.

## How files are tracked

`Inputs/*` is `.gitignored` — only `example.fasta` and this README are
committed. Anything else you drop here stays local to your machine.

## Examples of valid FASTA

```
>peptide_001 Short comment line
ACDEFGHIKLMNPQRSTVWY
>peptide_002
KLAKLAKLAKLAKLAKLAKLA
```

## Need help?

See [`docs/data.md`](../docs/data.md) for the full input format
specification.
