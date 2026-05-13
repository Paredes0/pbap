# Known Issues & Technical Debt

Public list of known issues, technical debt and small improvements. Long-term ideas live in `roadmap.md`.

> Contributors welcome. Pick anything in this list, open an issue claiming it, and submit a PR.

## High priority

- [ ] **Post-bootstrap end-to-end verification**: run `scripts/run_audit.py` on a clean machine against `Inputs/example.fasta` and confirm the deployment guide in `deployment.md` is 100% accurate. Report any gaps.
- [ ] **Threshold sync**: cross-check that thresholds documented in `decisions.md` (CD-HIT bands, MIC cutoffs, score thresholds per tool) exactly match the values in `pipeline_config.yaml`.

## Medium priority

- [ ] **`tool_runner` refactor**: extract the `pre_command` substitution logic into its own module so it can be unit-tested independently.
- [ ] **Parser examples**: add input/output examples for each parser in `audit_lib/db_parsers.py` to `api.md` or `data.md`.

## Technical debt

- [ ] **Configurable paths**: a few entries in `pipeline_config.yaml` still hold installation-specific paths (SSH-related fields marked `CHANGE_ME`). These should be either fully driven from environment variables or split into a layered config (`pipeline_config.yaml` for defaults + `pipeline_config.local.yaml` gitignored for overrides).
- [ ] **Parser deduplication**: `db_parsers.py` for DBAASP and APD3 share sequence-cleaning logic that could move into `sequence_utils.py`.
- [ ] **Lazy imports for optional outputs**: `openpyxl` import is already lazy; do the same for any other optional dependency to keep the bare install minimal.

## Documentation

- [ ] **`docs/add_a_tool.md`** (NEW): a short, opinionated guide showing how to add a new prediction tool to the pipeline by writing a YAML block — no Python changes needed. The "how to contribute a tool" content of `CONTRIBUTING.md` should link here.
- [ ] **`docs/glossary.md`**: extend with all the abbreviations used in the HTML report (POS/NEG/SPLIT, structural/holistic, MIC, APEX, ESKAPE, PLM, etc.).

---
[← Back to Index](INDEX.md)
