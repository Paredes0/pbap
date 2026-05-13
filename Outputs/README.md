# Outputs/

This directory is auto-populated by `scripts/run_audit.py` after each
pipeline run.

## Per-run layout

```
Outputs/
└── <input_name>_<YYYY-MM-DDTHHMM>/
    ├── REPORT.html             Interactive HTML5 report (primary artifact)
    ├── REPORT.md               Plain-text Markdown summary
    ├── consolidated.csv        Wide CSV (one row per peptide, all tools)
    ├── consolidated.json       Nested JSON of the same data
    ├── consolidated.xlsx       5-sheet Excel (formatting + autofilter)
    ├── tool_health_report.json Per-tool runtime, status, diagnosis
    └── per_tool/
        └── <tool_id>/
            ├── predictions_<tool_id>.<ext>   Concatenated raw output
            └── _batches/
                └── batch_NNN/
                    ├── input_<tool_id>_batch_NNN.fasta  (deleted at run end)
                    ├── completed.stdout / .stderr
                    └── (raw tool output, kept for debugging)
```

## What to open first

Open `REPORT.html` in any modern browser. It includes:

- **Top-level matrix**: sortable, filterable, one row per peptide,
  one column per category.
- **Drill-down** per peptide with the full per-tool detail.
- **APEX selectivity** section (pathogen / commensal / broad-spectrum
  tags) with per-strain MIC table.
- **Tool health**: which tools succeeded, runtime, partial failures.

## Tracking

`Outputs/*` is `.gitignored` — your run artifacts stay local. Only this
README is committed (plus a `.gitkeep`).

If you want to publish a specific run as a worked example, add a
dedicated entry to this README pointing to the artifacts you upload
elsewhere (e.g. Zenodo, OSF) — please don't commit large run folders
to the repository.

## Cleaning up

Old runs can be deleted safely; the orchestrator does not depend on any
previous run.

```bash
# Remove runs older than 30 days (example, careful)
find Outputs/ -maxdepth 1 -type d -mtime +30 -name "*_2*" -print
```

## Need help?

See [`docs/orchestrator_design.md`](../docs/orchestrator_design.md)
for the full output schema specification, and
[`docs/api.md`](../docs/api.md) for the parser/exporter contracts.
