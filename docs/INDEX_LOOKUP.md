# Quick pointers (INDEX_LOOKUP)

Jump table to the actual functions and scripts in `audit_lib/` and
`scripts/`.

---

## 1) Canonical function lookup (`audit_lib/`)

| I'm looking for… | File | Symbol / exact signature |
|---|---|---|
| Load `pipeline_config.yaml` | `audit_lib/config.py` | `load_pipeline_config(config_path="pipeline_config.yaml")` |
| Load `categories_config.yaml` | `audit_lib/config.py` | `load_category_config(config_path="categories_config.yaml")` |
| Config for one tool | `audit_lib/config.py` | `get_tool_config(tool_id, pipeline_config)` |
| Run one tool (Phase 1 runner) | `audit_lib/tool_runner.py` | `run_tool(tool_id, peptides_fasta, output_dir, pipeline_config_path=..., timeout_seconds=None)` |
| CD-HIT intra-set | `audit_lib/cdhit_utils.py` | `run_cdhit_intraset(...)` |
| CD-HIT-2D train vs. test | `audit_lib/cdhit_utils.py` | `run_cdhit2d(...)` |
| Classify Gold/Silver/Bronze/Red | `audit_lib/cdhit_utils.py` | `classify_leakage_grades(test_ids, results_by_threshold)` |
| Path mapping SSHFS → Linux | `audit_lib/cdhit_utils.py` | `_convert_path_for_linux(...)` |
| Length range from training | `audit_lib/tool_length_range.py` | `compute_tool_length_range(...)` |
| Filter pool by length | `audit_lib/tool_length_range.py` | `filter_pool_by_length(...)` |
| Download UniProt | `audit_lib/uniprot_client.py` | `download_uniprot(...)` |
| Parse CHAIN/PEPTIDE mature features | `audit_lib/uniprot_client.py` | `parse_mature_features(...)`, `extract_mature_subsequences(...)` |
| Standardize UniProt to schema | `audit_lib/uniprot_client.py` | `process_uniprot_dataframe(...)` |
| Validate AA sequence | `audit_lib/sequence_utils.py` | `validate_sequence(seq, min_length=5, max_length=100)` |
| Classify habitat | `audit_lib/sequence_utils.py` | `classify_habitat(organism_name, lineage_str, fallback="unknown")` |
| Remove sub-fragments | `audit_lib/sequence_utils.py` | `remove_subfragments(...)` |
| Per-species cap | `audit_lib/sequence_utils.py` | `cap_per_species(...)` |
| Distribution-aware sampling | `audit_lib/length_sampling.py` | `sample_with_diversity(...)`, `match_length_distribution(...)` |
| Extra DB parsers | `audit_lib/db_parsers.py` | `parse_dbaasp`, `parse_apd3`, `parse_conoserver`, `parse_arachnoserver`, … |
| Incremental audit state | `audit_lib/state_manager.py` | `class AuditStateManager` |
| Provenance JSON | `audit_lib/provenance.py` | `generate_provenance(...)` |

---

## 2) Lookup by script (`scripts/`)

| Pipeline step | Script | Core function | Minimal CLI |
|---|---|---|---|
| Mine positives per category | `scripts/mine_positives_per_bioactivity.py` | `mine_positives(...)` | `python scripts/mine_positives_per_bioactivity.py --category <cat> --config config/categories_config.yaml --output-dir Dataset_Bioactividad/Category_Pools` |
| Extract per-tool training data | `scripts/extract_training_data.py` | `extract_training_data(...)` | `python scripts/extract_training_data.py --tool <tool_id> --config config/pipeline_config.yaml --output-dir Dataset_Bioactividad/Tool_Audits/<tool_id>/training_data` |
| Leakage analysis (CD-HIT-2D) | `scripts/cdhit_leakage_analysis.py` | `run_leakage_analysis(...)` | `python scripts/cdhit_leakage_analysis.py --tool <tool_id> --config config/pipeline_config.yaml --test-fasta <pool.fasta> --training-fasta <training_positive.fasta> --output-dir Dataset_Bioactividad/Tool_Audits/<tool_id>/leakage_report` |
| Generate negatives | `scripts/generate_category_negatives.py` | `generate_negatives(...)` | `python scripts/generate_category_negatives.py --tool <tool_id> --config config/pipeline_config.yaml --categories-config config/categories_config.yaml --positives-csv Dataset_Bioactividad/Category_Pools/<cat>_pool.csv --output-dir Dataset_Bioactividad/Tool_Audits/<tool_id>/test_negatives` |
| Prediction + per-grade metrics | `scripts/run_tool_prediction.py` | `prepare_input`, `run_prediction`, `compute_grade_metrics` | `python scripts/run_tool_prediction.py --tool <tool_id> --config config/pipeline_config.yaml --output-dir Dataset_Bioactividad/Tool_Audits/<tool_id>/predictions` |
| Taxonomic bias | `scripts/taxonomic_bias_analysis.py` | `run_taxonomic_bias_analysis(...)` | `python scripts/taxonomic_bias_analysis.py --tool <tool_id> --config config/pipeline_config.yaml --output-dir Dataset_Bioactividad/Tool_Audits/<tool_id>/predictions --grades Gold` |
| Per-tool QC | `scripts/auditoria_validation.py` | `run_audit(...)` | `python scripts/auditoria_validation.py --tool <tool_id> --config config/pipeline_config.yaml --output-dir Dataset_Bioactividad/Tool_Audits/<tool_id>` |
| Global report | `scripts/final_audit_report.py` | `collect_tool_reports`, `generate_global_report` | `python scripts/final_audit_report.py --config config/pipeline_config.yaml --output-dir Dataset_Bioactividad/Global_Audit` |
| E2E Phase 1 orchestrator | `scripts/run_audit.py` | `main()`, `_run_tool_batched(...)` | `python scripts/run_audit.py --input <file.fasta> --tools all` |
| BERT-AMPep60 wrapper | `wrappers/bert_ampep60_cli.py` | `main()` | `python wrappers/bert_ampep60_cli.py --input <fasta> --output <csv>` |

---

## 3) Statistical mapping (important correction)

| Metric / test | Correct file | Symbols |
|---|---|---|
| Fisher exact (group vs. rest) | `scripts/taxonomic_bias_analysis.py` | `_fisher_pair`, `scipy.stats.fisher_exact` |
| Wilson CI 95% | `scripts/taxonomic_bias_analysis.py` | `_wilson_ci` |
| BH-FDR | `scripts/taxonomic_bias_analysis.py` | `_bh_correction` |
| Bonferroni | `scripts/taxonomic_bias_analysis.py` | `_bonferroni` |
| KS test on lengths | `scripts/auditoria_validation.py` | `audit_ks_length_test` |
| Chi² on AA composition | `scripts/auditoria_validation.py` | `audit_aa_composition` |

> Fisher/Wilson are **not** in `auditoria_validation.py`; they live in
> `taxonomic_bias_analysis.py`.

---

## 4) Output artifacts per script

| Script | Main outputs |
|---|---|
| `mine_positives_per_bioactivity.py` | `<category>_pool.csv`, `<category>_pool.fasta`, `PROVENANCE_*.json` |
| `extract_training_data.py` | `training_<tool>.fasta`, `training_<tool>_positive.fasta`, `training_<tool>_summary.csv`, `STANDBY_REPORT.json` (if applicable) |
| `cdhit_leakage_analysis.py` | `leakage_<tool>_classifications.csv`, `leakage_<tool>_report.json`, `<grade>_survivors_<tool>.fasta` |
| `generate_category_negatives.py` | `negatives_<tool>.csv`, `negatives_<tool>.fasta`, `PROVENANCE_*.json` |
| `run_tool_prediction.py` | `ground_truth_<tool>.csv`, `predictions_<tool>.*`, `grade_metrics_<tool>.json` |
| `taxonomic_bias_analysis.py` | `taxonomic_bias_<tool>_<GradeLabel>.json` |
| `auditoria_validation.py` | `audit_report_<tool>.json` |
| `final_audit_report.py` | `GLOBAL_AUDIT_REPORT.json`, `GLOBAL_AUDIT_SUMMARY.txt`, `GLOBAL_AUDIT_REPORT.xlsx` |
| `run_audit.py` | `consolidated.csv`, `consolidated.json`, `consolidated.xlsx`, `tool_health_report.json`, `REPORT.md`, `REPORT.html`, `per_tool/<tool>/...` |

---

## 5) Suggested quick grep

```bash
# Key signatures in config
rg -n "def load_category_config|def get_tool_config" audit_lib/config.py

# Real runner (signature and ToolResult)
rg -n "class ToolResult|def run_tool" audit_lib/tool_runner.py

# Fisher/Wilson/BH in taxonomic bias
rg -n "_fisher_pair|_wilson_ci|_bh_correction|_bonferroni|fisher_exact" scripts/taxonomic_bias_analysis.py

# CLI args for each script
rg -n "ArgumentParser|add_argument\(\"--" scripts/*.py
```

---
[← Back to Index](INDEX.md)
