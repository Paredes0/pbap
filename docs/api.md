---
description: Referencia técnica de módulos, clases y funciones de audit_lib.
related: [architecture.md, conventions.md]
last_updated: 2026-05-08T13:55:00Z
---

# Referencia de API (`audit_lib`)

Documentación completa de los 12 módulos que componen la biblioteca compartida del pipeline.

> [!NOTE]
> Solo se documentan funciones **públicas** (sin prefijo `_`). Las funciones internas (`_build_command`, `_ssh_dispatch`, etc.) son detalles de implementación y pueden cambiar sin aviso.

---

## 🔧 `audit_lib/config.py`

Gestión de configuraciones YAML para el pipeline y herramientas.

| Función | Firma | Descripción |
|---|---|---|
| `load_pipeline_config` | `(config_path="pipeline_config.yaml")` | Carga la configuración global del pipeline (tools, environments, paths). |
| `load_category_config` | `(config_path="categories_config.yaml")` | Carga el mapeo de bioactividades y categorías. |
| `get_tool_config` | `(tool_id, pipeline_config)` | Extrae el bloque de configuración específico para una herramienta. |
| `get_tools_for_category` | `(category, pipeline_config)` | Devuelve la lista de tool_ids que pertenecen a una categoría dada. |
| `get_all_categories` | `(pipeline_config)` | Devuelve el set de todas las categorías únicas definidas en el config. |
| `get_base_output_dir` | `(pipeline_config)` | Obtiene el directorio base de outputs desde la configuración global. |

---

## 🚀 `audit_lib/tool_runner.py`

Motor de ejecución de herramientas mediante `micromamba run`.

| Símbolo | Tipo | Firma / Descripción |
|---|---|---|
| `ToolResult` | `class` | Encapsula el resultado de ejecución: `tool_id`, `output_path`, `exit_code`, `runtime`, `diagnosis`. |
| `run_tool` | `def` | `(tool_id, peptides_fasta, output_dir, pipeline_config_path=DEFAULT_CONFIG_PATH, timeout_seconds=None)` — Ejecuta un predictor en su entorno dedicado. Maneja `timeout` y captura de logs. |

---

## 📏 `audit_lib/tool_length_range.py`

Inferencia de rangos de longitud óptimos por herramienta a partir de datos de entrenamiento.

| Función | Firma | Descripción |
|---|---|---|
| `collect_training_lengths` | `(training_dir, sequence_column_hints=None)` | Recorre los archivos de training de un tool y extrae las longitudes de las secuencias. |
| `compute_tool_length_range` | `(tool_id, tool_cfg, training_dir=None, mode="robust", hard_min=5, hard_max=100)` | Calcula el rango min/max de longitudes aceptables para un tool. El modo `robust` usa percentiles para ignorar outliers. |
| `filter_pool_by_length` | `(pool_df, min_len, max_len, seq_col="Sequence", len_col="Length")` | Filtra un DataFrame de pool eliminando secuencias fuera del rango del tool. |

---

## 📥 `audit_lib/downloader.py`

Gestión de descarga y verificación de pesos de modelos desde repositorios externos.

| Función | Firma | Descripción |
|---|---|---|
| `ensure_weights` | `(tool_id, tool_cfg, repo_dir)` | Punto de entrada principal. Verifica si los pesos del modelo existen; si no, los descarga desde la plataforma configurada (Zenodo, HuggingFace, o manual). Valida integridad via MD5 cuando está disponible. |

> [!TIP]
> Las funciones internas `_download_zenodo`, `_download_huggingface`, `_check_manual_download`, `_download_file`, `_md5`, `_unzip` gestionan la descarga por plataforma. No están expuestas públicamente.

---

## 🧬 `audit_lib/sequence_utils.py`

Utilidades biológicas para validación y normalización de secuencias peptídicas.

| Función | Firma | Descripción |
|---|---|---|
| `validate_sequence` | `(seq, min_length=5, max_length=100)` | Verifica que la secuencia solo contenga aminoácidos estándar y cumpla el rango de longitud. |
| `classify_habitat` | `(organism_name, lineage_str, fallback="desconocido")` | Mapeo heurístico de linaje taxonómico a categorías de hábitat (suelo, marino, etc.). |
| `get_length_bin` | `(length, bins=None)` | Asigna una secuencia a un bin de longitud. |
| `remove_subfragments` | `(df, seq_col="Sequence", id_col="ID")` | Elimina secuencias que son sub-strings exactos de otras en el mismo set. |
| `find_column` | `(df)` | Heurística para detectar la columna de secuencia en un DataFrame con nombres heterogéneos. |
| `is_signaling_related` | `(text)` | Detecta si un texto de anotación indica péptido señal o propéptido (para excluirlo). |
| `cap_per_species` | `(df, max_per_species, organism_col="Organism", seed=42)` | Limita el número máximo de secuencias por especie para evitar sesgos taxonómicos. |

---

## 🔬 `audit_lib/cdhit_utils.py`

Integración con CD-HIT para análisis de redundancia y leakage. **Único módulo con capacidad de despacho SSH**.

| Función | Firma | Descripción |
|---|---|---|
| `get_word_size` | `(identity)` | Calcula el word size óptimo de CD-HIT para un umbral de identidad dado. |
| `find_cdhit_binary` | `(name="cd-hit")` | Localiza el binario de CD-HIT en el PATH del sistema. |
| `write_fasta` | `(df, fasta_path, id_col="ID", seq_col="Sequence")` | Exporta un DataFrame a formato FASTA. |
| `parse_fasta_ids` | `(fasta_path)` | Extrae los IDs de un archivo FASTA. |
| `run_cdhit_intraset` | `(df, identity=0.9, output_dir=None, id_col="ID", seq_col="Sequence", ssh_host=None)` | Elimina redundancia interna en un set al umbral de identidad dado. |
| `run_cdhit2d` | `(training_fasta, test_fasta, output_path, identity=0.8, ssh_host=None, ssh_user=None, cdhit_binary=None, sshfs_mount=None, linux_base=None)` | Compara un pool de test contra training para detectar leakage. Soporta despacho SSH para ejecución en servidor Linux. |
| `classify_leakage_grades` | `(test_ids, results_by_threshold)` | Clasifica secuencias en grados Gold/Silver/Bronze/Red según resultados de CD-HIT-2D a múltiples umbrales. |

---

## 🌐 `audit_lib/uniprot_client.py`

Cliente para descarga y procesamiento de datos de UniProt/Swiss-Prot con paginación, reintentos y checkpointing.

| Función | Firma | Descripción |
|---|---|---|
| `download_uniprot` | `(query, fields=None, checkpoint_dir=None, group_name="", max_retries=MAX_RETRIES, retry_delays=RETRY_DELAYS)` | Descarga resultados de búsqueda UniProt en formato TSV con reintentos automáticos. |
| `parse_mature_features` | `(feature_str)` | Extrae coordenadas de `CHAIN` y `PEPTIDE` del campo `Features` de UniProt. |
| `extract_mature_subsequences` | `(full_seq, features, min_length=5, max_length=100)` | Genera las subsecuencias maduras a partir de las coordenadas de features. |
| `process_uniprot_dataframe` | `(df, group_name, habitat, bioactivity, min_length=5, max_length=100, strict_mature=True)` | Pipeline completo: extrae, filtra y estandariza un DataFrame de UniProt al esquema interno del pipeline. |

---

## 📊 `audit_lib/length_sampling.py`

Muestreo de secuencias respetando distribuciones naturales de longitud.

| Función | Firma | Descripción |
|---|---|---|
| `compute_length_distribution` | `(df, length_col="Length", bins=None)` | Calcula la distribución de longitudes de un DataFrame en bins. |
| `sample_with_diversity` | `(df, target_size, length_col="Length", bins=None, min_bin_pct=0.03, seed=42)` | Muestreo estratificado por longitud con garantía de representación mínima por bin. |
| `match_length_distribution` | `(source_df, target_df, target_size, length_col="Length", bins=None, seed=42)` | Muestrea de `source_df` para que la distribución de longitudes replique la de `target_df`. |

---

## 💾 `audit_lib/state_manager.py`

Gestión de estado incremental para evitar re-auditorías innecesarias.

| Símbolo | Tipo | Firma / Descripción |
|---|---|---|
| `AuditStateManager` | `class` | Persiste en `.audit_state.json`. Constructor: `AuditStateManager(state_file)`. |
| `.save` | método | `()` — Escribe el estado actual a disco. |
| `.compute_tool_hash` | método | `(tool_id, tool_config)` — Genera un hash determinista de la configuración de un tool. |
| `.needs_audit` | método | `(tool_id, current_hash)` — Retorna `True` si el tool necesita re-auditoría. |
| `.mark_step_complete` | método | `(tool_id, hash_val, step)` — Marca un paso intermedio como completado. |
| `.mark_complete` | método | `(tool_id, hash_val)` — Marca la auditoría completa para un tool. |
| `.get_completed_steps` | método | `(tool_id)` — Retorna los pasos completados para un tool. |
| `.mark_category_pool` | método | `(category, n_sequences, pool_hash=None)` — Registra un pool de categoría generado. |
| `.has_category_pool` | método | `(category)` — Verifica si un pool ya existe para una categoría. |
| `.reset_tool` | método | `(tool_id)` — Resetea el estado de un tool (fuerza re-auditoría). |

---

## 📜 `audit_lib/provenance.py`

Generación de metadatos de trazabilidad en formato JSON.

| Función | Firma | Descripción |
|---|---|---|
| `generate_provenance` | `(output_dir, script_name, category=None, tool_id=None, parameters=None, queries=None, counts=None, output_stats=None, errors=None, extra=None)` | Crea un archivo `PROVENANCE_<script>_<timestamp>.json` con información completa del origen de los datos, parámetros de ejecución y estadísticas de output. |

---

## 🗄️ `audit_lib/db_parsers.py`

Parsers para bases de datos externas de péptidos bioactivos. Cada parser devuelve un DataFrame estandarizado con columnas `[ID, Sequence, Length, Source_DB, Bioactivity, ...]`.

| Función | Firma | Descripción |
|---|---|---|
| `parse_dbaasp` | `(data_path=None, bioactivity="antimicrobial")` | Parser para DBAASP (antimicrobianos con MICs). |
| `parse_apd3` | `(data_path=None, bioactivity="antimicrobial")` | Parser para APD3 (Antimicrobial Peptide Database). |
| `parse_conoserver` | `(data_path=None, bioactivity="toxicity", min_length=5, max_length=100, exclude_precursors=True)` | Parser para ConoServer (toxinas de caracoles cono). |
| `parse_arachnoserver` | `(data_path=None, bioactivity="toxicity", min_length=5, max_length=100)` | Parser para ArachnoServer (toxinas de arañas). |
| `parse_hemolytik` | `(data_path=None, bioactivity="hemolytic")` | Parser para Hemolytik (péptidos hemolíticos). |
| `parse_cancerppd` | `(data_path=None, bioactivity="anticancer")` | Parser para CancerPPD (péptidos anticancerígenos). |
| `parse_cppsite` | `(data_path=None, bioactivity="cpp")` | Parser para CPPsite (cell-penetrating peptides). |
| `parse_biopep` | `(data_path=None, bioactivity="antioxidant")` | Parser para BIOPEP (péptidos antioxidantes). |
| `parse_avpdb` | `(data_path=None, bioactivity="antiviral")` | Parser para AVPdb (péptidos antivirales). |
| `get_parser` | `(db_name)` | Factory: devuelve la función parser para un nombre de base de datos. |

---

## 📝 `audit_lib/logging_setup.py`

Configuración estándar de logging para todos los scripts del pipeline.

| Función | Firma | Descripción |
|---|---|---|
| `configure_logging` | `(log_dir=None, script_name="audit", level=logging.INFO)` | Configura el logger raíz con formato estándar, rotación de archivos (si `log_dir` es proporcionado) y salida a consola. |

---
[← Volver al Índice](INDEX.md)
