---
description: Technical reference for modules, classes and functions of audit_lib.
related: [architecture.md, conventions.md]
last_updated: 2026-05-13
---

# API Reference (`audit_lib`)

Full documentation of the 12 modules that compose the pipeline's shared
library.

> [!NOTE]
> Only **public** functions (no `_` prefix) are documented here. Internal
> functions (`_build_command`, `_ssh_dispatch`, etc.) are implementation
> details and may change without notice.

---

## 🔧 `audit_lib/config.py`

YAML configuration management for the pipeline and tools.

| Function | Signature | Description |
|---|---|---|
| `load_pipeline_config` | `(config_path="pipeline_config.yaml")` | Loads the global pipeline configuration (tools, environments, paths). |
| `load_category_config` | `(config_path="categories_config.yaml")` | Loads the bioactivity-to-category mapping. |
| `get_tool_config` | `(tool_id, pipeline_config)` | Extracts the configuration block for a specific tool. |
| `get_tools_for_category` | `(category, pipeline_config)` | Returns the list of `tool_id`s belonging to a given category. |
| `get_all_categories` | `(pipeline_config)` | Returns the set of all unique categories defined in the config. |
| `get_base_output_dir` | `(pipeline_config)` | Reads the base output directory from the global config. |

---

## 🚀 `audit_lib/tool_runner.py`

Tool-execution engine using `micromamba run`.

| Symbol | Type | Signature / Description |
|---|---|---|
| `ToolResult` | `class` | Wraps the execution result: `tool_id`, `output_path`, `exit_code`, `runtime`, `diagnosis`. |
| `run_tool` | `def` | `(tool_id, peptides_fasta, output_dir, pipeline_config_path=DEFAULT_CONFIG_PATH, timeout_seconds=None)` — runs a predictor in its dedicated environment. Handles timeouts and log capture. |

---

## 📏 `audit_lib/tool_length_range.py`

Inference of optimal length ranges per tool from training data.

| Function | Signature | Description |
|---|---|---|
| `collect_training_lengths` | `(training_dir, sequence_column_hints=None)` | Walks the training files of a tool and extracts sequence lengths. |
| `compute_tool_length_range` | `(tool_id, tool_cfg, training_dir=None, mode="robust", hard_min=5, hard_max=100)` | Computes the acceptable length range for a tool. The `robust` mode uses percentiles to ignore outliers. |
| `filter_pool_by_length` | `(pool_df, min_len, max_len, seq_col="Sequence", len_col="Length")` | Filters a pool DataFrame by length range. |

---

## 🧬 `audit_lib/sequence_utils.py`

Biological utilities for sequence validation and normalization.

| Function | Signature | Description |
|---|---|---|
| `validate_sequence` | `(seq, min_length=5, max_length=100)` | Checks that the sequence contains only standard amino acids and fits the length range. |
| `classify_habitat` | `(organism_name, lineage_str, fallback="unknown")` | Heuristic mapping from taxonomic lineage to habitat categories (soil, marine, etc.). |
| `get_length_bin` | `(length, bins=None)` | Assigns a sequence to a length bin. |
| `remove_subfragments` | `(df, seq_col="Sequence", id_col="ID")` | Removes sequences that are exact substrings of others in the same set. |
| `find_column` | `(df)` | Heuristic to detect the sequence column in a DataFrame with heterogeneous names. |
| `is_signaling_related` | `(text)` | Detects whether an annotation text indicates a signal peptide or propeptide (to exclude it). |
| `cap_per_species` | `(df, max_per_species, organism_col="Organism", seed=42)` | Caps the number of sequences per species to avoid taxonomic bias. |

---

## 🔬 `audit_lib/cdhit_utils.py`

CD-HIT integration for redundancy and leakage analysis. **The only
module with SSH dispatch capability**.

| Function | Signature | Description |
|---|---|---|
| `get_word_size` | `(identity)` | Computes the optimal CD-HIT word size for a given identity threshold. |
| `find_cdhit_binary` | `(name="cd-hit")` | Locates the CD-HIT binary on the system PATH. |
| `write_fasta` | `(df, fasta_path, id_col="ID", seq_col="Sequence")` | Exports a DataFrame to FASTA. |
| `parse_fasta_ids` | `(fasta_path)` | Extracts IDs from a FASTA file. |
| `run_cdhit_intraset` | `(df, identity=0.9, output_dir=None, id_col="ID", seq_col="Sequence", ssh_host=None)` | Removes intra-set redundancy at the given identity threshold. |
| `run_cdhit2d` | `(training_fasta, test_fasta, output_path, identity=0.8, ssh_host=None, ssh_user=None, cdhit_binary=None, sshfs_mount=None, linux_base=None)` | Compares a test pool against training data to detect leakage. Supports SSH dispatch to run on a Linux server. |
| `classify_leakage_grades` | `(test_ids, results_by_threshold)` | Classifies sequences into Gold/Silver/Bronze/Red grades based on CD-HIT-2D results at multiple thresholds. |

---

## 🌐 `audit_lib/uniprot_client.py`

Client for downloading and processing UniProt/Swiss-Prot data with
pagination, retries and checkpointing.

| Function | Signature | Description |
|---|---|---|
| `download_uniprot` | `(query, fields=None, checkpoint_dir=None, group_name="", max_retries=MAX_RETRIES, retry_delays=RETRY_DELAYS)` | Downloads UniProt search results in TSV format with automatic retries. |
| `parse_mature_features` | `(feature_str)` | Extracts `CHAIN` and `PEPTIDE` coordinates from the UniProt `Features` field. |
| `extract_mature_subsequences` | `(full_seq, features, min_length=5, max_length=100)` | Generates mature subsequences from feature coordinates. |
| `process_uniprot_dataframe` | `(df, group_name, habitat, bioactivity, min_length=5, max_length=100, strict_mature=True)` | Full pipeline: extracts, filters and standardizes a UniProt DataFrame to the internal schema. |

---

## 📊 `audit_lib/length_sampling.py`

Sequence sampling that respects natural length distributions.

| Function | Signature | Description |
|---|---|---|
| `compute_length_distribution` | `(df, length_col="Length", bins=None)` | Computes the length distribution of a DataFrame in bins. |
| `sample_with_diversity` | `(df, target_size, length_col="Length", bins=None, min_bin_pct=0.03, seed=42)` | Length-stratified sampling with a minimum-representation guarantee per bin. |
| `match_length_distribution` | `(source_df, target_df, target_size, length_col="Length", bins=None, seed=42)` | Samples from `source_df` so that the length distribution matches `target_df`. |

---

## 💾 `audit_lib/state_manager.py`

Incremental state management to avoid unnecessary re-audits.

| Symbol | Type | Signature / Description |
|---|---|---|
| `AuditStateManager` | `class` | Persists to `.audit_state.json`. Constructor: `AuditStateManager(state_file)`. |
| `.save` | method | `()` — Writes the current state to disk. |
| `.compute_tool_hash` | method | `(tool_id, tool_config)` — Produces a deterministic hash of a tool's configuration. |
| `.needs_audit` | method | `(tool_id, current_hash)` — Returns `True` if the tool needs re-auditing. |
| `.mark_step_complete` | method | `(tool_id, hash_val, step)` — Marks an intermediate step as complete. |
| `.mark_complete` | method | `(tool_id, hash_val)` — Marks the audit as complete for a tool. |
| `.get_completed_steps` | method | `(tool_id)` — Returns the steps already completed for a tool. |
| `.mark_category_pool` | method | `(category, n_sequences, pool_hash=None)` — Records a generated category pool. |
| `.has_category_pool` | method | `(category)` — Verifies whether a pool already exists for a category. |
| `.reset_tool` | method | `(tool_id)` — Resets a tool's state (forces re-audit). |

---

## 📜 `audit_lib/provenance.py`

Generation of traceability metadata in JSON format.

| Function | Signature | Description |
|---|---|---|
| `generate_provenance` | `(output_dir, script_name, category=None, tool_id=None, parameters=None, queries=None, counts=None, output_stats=None, errors=None, extra=None)` | Creates a `PROVENANCE_<script>_<timestamp>.json` file with full information about data origin, execution parameters and output statistics. |

---

## 🗄️ `audit_lib/db_parsers.py`

Parsers for external databases of bioactive peptides. Each parser
returns a standardized DataFrame with columns
`[ID, Sequence, Length, Source_DB, Bioactivity, ...]`.

| Function | Signature | Description |
|---|---|---|
| `parse_dbaasp` | `(data_path=None, bioactivity="antimicrobial")` | DBAASP parser (antimicrobials with MICs). |
| `parse_apd3` | `(data_path=None, bioactivity="antimicrobial")` | APD3 parser (Antimicrobial Peptide Database). |
| `parse_conoserver` | `(data_path=None, bioactivity="toxicity", min_length=5, max_length=100, exclude_precursors=True)` | ConoServer parser (cone-snail toxins). |
| `parse_arachnoserver` | `(data_path=None, bioactivity="toxicity", min_length=5, max_length=100)` | ArachnoServer parser (spider toxins). |
| `parse_hemolytik` | `(data_path=None, bioactivity="hemolytic")` | Hemolytik parser (hemolytic peptides). |
| `parse_cancerppd` | `(data_path=None, bioactivity="anticancer")` | CancerPPD parser (anticancer peptides). |
| `parse_cppsite` | `(data_path=None, bioactivity="cpp")` | CPPsite parser (cell-penetrating peptides). |
| `parse_biopep` | `(data_path=None, bioactivity="antioxidant")` | BIOPEP parser (antioxidant peptides). |
| `parse_avpdb` | `(data_path=None, bioactivity="antiviral")` | AVPdb parser (antiviral peptides). |
| `get_parser` | `(db_name)` | Factory: returns the parser function for a given DB name. |

---
[← Back to Index](INDEX.md)
