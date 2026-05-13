# Pointers Rápidos (INDEX_LOOKUP)

Tabla de salto directa a funciones y scripts reales de `audit_lib/` y `scripts/`.

---

## 1) Lookup de funciones canónicas (`audit_lib/`)

| Busco… | Archivo | Símbolo / firma exacta |
|---|---|---|
| Cargar `pipeline_config.yaml` | `audit_lib/config.py` | `load_pipeline_config(config_path="pipeline_config.yaml")` |
| Cargar `categories_config.yaml` | `audit_lib/config.py` | `load_category_config(config_path="categories_config.yaml")` |
| Config de un tool | `audit_lib/config.py` | `get_tool_config(tool_id, pipeline_config)` |
| Ejecutar un tool (runner Fase 1) | `audit_lib/tool_runner.py` | `run_tool(tool_id, peptides_fasta, output_dir, pipeline_config_path=..., timeout_seconds=None)` |
| CD-HIT intra-set | `audit_lib/cdhit_utils.py` | `run_cdhit_intraset(...)` |
| CD-HIT-2D train vs test | `audit_lib/cdhit_utils.py` | `run_cdhit2d(...)` |
| Clasificar Gold/Silver/Bronze/Red | `audit_lib/cdhit_utils.py` | `classify_leakage_grades(test_ids, results_by_threshold)` |
| Path mapping SSHFS→Linux | `audit_lib/cdhit_utils.py` | `_convert_path_for_linux(...)` |
| Rango de longitudes por training | `audit_lib/tool_length_range.py` | `compute_tool_length_range(...)` |
| Filtrar pool por longitud | `audit_lib/tool_length_range.py" | `filter_pool_by_length(...)` |
| Descargar UniProt | `audit_lib/uniprot_client.py` | `download_uniprot(...)` |
| Parsear CHAIN/PEPTIDE maduros | `audit_lib/uniprot_client.py` | `parse_mature_features(...)`, `extract_mature_subsequences(...)` |
| Estandarizar UniProt a schema | `audit_lib/uniprot_client.py` | `process_uniprot_dataframe(...)` |
| Validar secuencias AA | `audit_lib/sequence_utils.py` | `validate_sequence(seq, min_length=5, max_length=100)` |
| Clasificar hábitat | `audit_lib/sequence_utils.py` | `classify_habitat(organism_name, lineage_str, fallback="desconocido")` |
| Quitar subfragmentos | `audit_lib/sequence_utils.py` | `remove_subfragments(...)` |
| Cap por especie | `audit_lib/sequence_utils.py` | `cap_per_species(...)` |
| Muestreo por distribución | `audit_lib/length_sampling.py` | `sample_with_diversity(...)`, `match_length_distribution(...)` |
| Parsers DB extra | `audit_lib/db_parsers.py` | `parse_dbaasp`, `parse_apd3`, `parse_conoserver`, `parse_arachnoserver`, etc. |
| Estado incremental auditoría | `audit_lib/state_manager.py` | `class AuditStateManager` |
| Provenance JSON | `audit_lib/provenance.py` | `generate_provenance(...)` |
| Logging común | `audit_lib/logging_setup.py` | `configure_logging(...)` |

---

## 2) Lookup por script (`scripts/`)

| Paso del pipeline | Script | Función core | CLI mínima |
|---|---|---|---|
| Minar positivos por categoría | `scripts/mine_positives_per_bioactivity.py` | `mine_positives(...)` | `python scripts\mine_positives_per_bioactivity.py --category <cat> --config config\categories_config.yaml --output-dir Dataset_Bioactividad\Category_Pools` |
| Extraer training por tool | `scripts/extract_training_data.py` | `extract_training_data(...)` | `python scripts\extract_training_data.py --tool <tool_id> --config config\pipeline_config.yaml --output-dir Dataset_Bioactividad\Tool_Audits\<tool_id>\training_data` |
| Leakage CD-HIT-2D | `scripts/cdhit_leakage_analysis.py` | `run_leakage_analysis(...)` | `python scripts\cdhit_leakage_analysis.py --tool <tool_id> --config config\pipeline_config.yaml --test-fasta <pool.fasta> --training-fasta <training_positive.fasta> --output-dir Dataset_Bioactividad\Tool_Audits\<tool_id>\leakage_report` |
| Generar negativos | `scripts/generate_category_negatives.py` | `generate_negatives(...)` | `python scripts\generate_category_negatives.py --tool <tool_id> --config config\pipeline_config.yaml --categories-config config\categories_config.yaml --positives-csv Dataset_Bioactividad\Category_Pools\<cat>_pool.csv --output-dir Dataset_Bioactividad\Tool_Audits\<tool_id>\test_negatives` |
| Predicción + métricas por grade | `scripts/run_tool_prediction.py` | `prepare_input`, `run_prediction`, `compute_grade_metrics` | `python scripts\run_tool_prediction.py --tool <tool_id> --config config\pipeline_config.yaml --output-dir Dataset_Bioactividad\Tool_Audits\<tool_id>\predictions` |
| Sesgo taxonómico | `scripts/taxonomic_bias_analysis.py` | `run_taxonomic_bias_analysis(...)` | `python scripts\taxonomic_bias_analysis.py --tool <tool_id> --config config\pipeline_config.yaml --output-dir Dataset_Bioactividad\Tool_Audits\<tool_id>\predictions --grades Gold` |
| QC per-tool | `scripts/auditoria_validation.py` | `run_audit(...)` | `python scripts\auditoria_validation.py --tool <tool_id> --config config\pipeline_config.yaml --output-dir Dataset_Bioactividad\Tool_Audits\<tool_id>` |
| Reporte global | `scripts/final_audit_report.py` | `collect_tool_reports`, `generate_global_report` | `python scripts\final_audit_report.py --config config\pipeline_config.yaml --output-dir Dataset_Bioactividad\Global_Audit` |
| Orquestador E2E Fase 1 | `scripts/run_audit.py` | `main()`, `_run_tool_batched(...)` | `python scripts\run_audit.py --input <archivo.fasta> --tools all` |
| Wrapper BERT-AMPep60 | `wrappers/bert_ampep60_cli.py` | `main()` | `python wrappers\bert_ampep60_cli.py --input <fasta> --output <csv>` |

---

## 3) Mapeo estadístico (corrección importante)

| Métrica / test | Archivo correcto | Símbolos |
|---|---|---|
| Fisher exact (grupo vs resto) | `scripts/taxonomic_bias_analysis.py` | `_fisher_pair`, `scipy.stats.fisher_exact` |
| Wilson CI 95% | `scripts/taxonomic_bias_analysis.py` | `_wilson_ci` |
| BH-FDR | `scripts/taxonomic_bias_analysis.py" | `_bh_correction` |
| Bonferroni | `scripts/taxonomic_bias_analysis.py" | `_bonferroni` |
| KS test longitudes | `scripts/auditoria_validation.py` | `audit_ks_length_test` |
| Chi2 composición AA | `scripts/auditoria_validation.py` | `audit_aa_composition` |

> Fisher/Wilson **no** están en `auditoria_validation.py`; están implementados en `taxonomic_bias_analysis.py`.

---

## 4) Artefactos de salida por script

| Script | Salidas principales |
|---|---|
| `mine_positives_per_bioactivity.py` | `<category>_pool.csv`, `<category>_pool.fasta`, `PROVENANCE_*.json` |
| `extract_training_data.py` | `training_<tool>.fasta`, `training_<tool>_positive.fasta`, `training_<tool>_summary.csv`, `STANDBY_REPORT.json` (si aplica) |
| `cdhit_leakage_analysis.py` | `leakage_<tool>_classifications.csv`, `leakage_<tool>_report.json`, `<grade>_survivors_<tool>.fasta` |
| `generate_category_negatives.py` | `negatives_<tool>.csv`, `negatives_<tool>.fasta`, `PROVENANCE_*.json` |
| `run_tool_prediction.py` | `ground_truth_<tool>.csv`, `predictions_<tool>.*`, `grade_metrics_<tool>.json` |
| `taxonomic_bias_analysis.py` | `taxonomic_bias_<tool>_<GradeLabel>.json` |
| `auditoria_validation.py` | `audit_report_<tool>.json` |
| `final_audit_report.py` | `GLOBAL_AUDIT_REPORT.json`, `GLOBAL_AUDIT_SUMMARY.txt`, `GLOBAL_AUDIT_REPORT.xlsx` |
| `run_audit.py` | `consolidated.csv`, `consolidated.json`, `consolidated.xlsx`, `tool_health_report.json`, `REPORT.md`, `REPORT.html`, `per_tool/<tool>/...` |

---

## 5) Grep rápido sugerido

```bash
# Firmas clave en config
rg -n "def load_category_config|def get_tool_config" audit_lib/config.py

# Runner real (firma y ToolResult)
rg -n "class ToolResult|def run_tool" audit_lib/tool_runner.py

# Fisher/Wilson/BH en taxonomic bias
rg -n "_fisher_pair|_wilson_ci|_bh_correction|_bonferroni|fisher_exact" scripts/taxonomic_bias_analysis.py

# CLI args de cada script
rg -n "ArgumentParser|add_argument\\(\"--" scripts/*.py
```

---
[? Volver al �ndice](INDEX.md)
