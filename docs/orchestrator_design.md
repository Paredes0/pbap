# Orchestrator design — heterogeneous outputs and intra-category aggregation

**Type**: orchestrator design rule (`scripts/run_audit.py` +
`audit_lib/tool_runner.py` + the parser config in
`pipeline_config.yaml`).
**Decisions recorded**: from 2026-04-25 onwards.
**Applies to**: the consolidator schema, the YAML parser config,
agreement-detection logic, and the Markdown / HTML / Excel reports.

---

## 1. Dual schema: binary axis + extra_metrics axis

The orchestrator supports two output axes per tool, **non-exclusive**:

### Binary axis (`class_norm`, `score`)
For tools that predict activity / non-activity.
- `class_norm ∈ {positive, negative, null}`.
- `score ∈ [0, 1] | null`.
- Feeds the cross-comparison matrix and the intra-category agreement
  detection.

### `extra_metrics` axis
Dict of additional measurements with a unit. Each entry is materialized
as an independent column in `consolidated.csv` with the pattern
`<tool_id>__<metric_name>__<unit>`.

### Why dual

Some tools (e.g. APEX → MIC for 34 strains) predict continuous or
target-specific magnitudes that **cannot be collapsed to binary**
without losing information or imposing an arbitrary threshold. Forcing
them into `class_norm` is misleading. But the binary axis is still
useful for cross-tool comparison between binary tools. Solution: both
coexist; each tool declares what it emits.

---

## 2. How it applies per tool type

| Type | Binary axis | extra_metrics | Example |
|---|---|---|---|
| Pure classifier | `class_norm + score` | empty | toxinpred3, antibp3, hemopi2, hemodl, deepb3p, deepbp |
| Continuous target-specific metric | `class_norm=null, score=null` | with entries | apex (34 MICs in µM) |
| Hybrid | both filled | with entries | (none currently) |

**Anti-confusion rule** for extra columns:
- Same magnitude + same target/strain + same unit → SAME column.
- Any difference in those three → SEPARATE column.
- Examples:
  - Two tools that predict `MIC_E_coli__uM` → share a column and enter
    the agreement layer.
  - One predicts `MIC_E_coli__uM`, another `MIC_S_aureus__uM` →
    separate columns.
  - One in µM and another in log10(µM) → different unit → separate
    (or normalize first).
- Naming: snake_case ASCII. Unit suffix `__<unit>` with standard
  notation (`uM`, `nM`, `percent`, `none`).

---

## 3. YAML — `output_parsing` extension and generic runner dimensions

Each entry in `pipeline_config.yaml` may include under
`output_parsing`:

```yaml
output_parsing:
  format: csv|tsv|stdout|...
  class_field: <colname or null>
  score_field: <colname or null>
  extra_metrics:
    - name: MIC_E_coli
      unit: uM
      field: <colname>
      transform: identity|log10|reciprocal
```

`extra_metrics` absent or empty = pure binary tool. With entries = the
fields are exposed as additional columns.

### Generic runner dimensions (`audit_lib/tool_runner.py`)

These dimensions live under `run_command` and are **always generic**
(no per-tool wrappers):

| Dimension | Values | When to use |
|---|---|---|
| `arg_style` | `flagged` (default), `positional` | flagged: `script -i in -o out`. positional: `script in` |
| `output_capture` | `file` (default), `hardcoded_file`, `stdout` | hardcoded_file: the script writes to `cwd/<name>` which the runner relocates. stdout: the script prints to stdout and the runner dumps it verbatim. |
| `hardcoded_output_name` | string (required if `output_capture=hardcoded_file`) | name of the cwd-bound file (e.g. `predictions_hemopi2.csv`, `Predicted_MICs.csv`, `Results.csv`) |
| `pre_command` | shell string | Runs in cwd before the script. Substitutes `${INPUT}` → absolute fasta. Use when the script hardcodes `./input.txt` or similar. APEX example: `awk '/^>/{next}{print}' ${INPUT} > test_seqs.txt` |
| `cwd_subdir` | subpath relative to `Tool_Repos/<tool>` | Use when the entry point lives in a subfolder and does bare-name imports of sibling modules (e.g. `bert_ampep60/predict/predict.py` imports `model_def`). |
| `extra_args` | list of strings | Extra args appended at the end of the command. Use to pin model variants or required flags (e.g. `toxinpred3` with `["-m", "2"]` to select the model variant, `hemopi2` with `["-m", "3", "-wd", "."]`). |

**Rule**: if a new tool requires something that doesn't fit the
existing dimensions, first verify whether a new generic dimension
would resolve N tools (not just that one). If it would only serve 1,
consider patching the tool's repo instead (light-adaptation boundary
of `verify_external_artifacts.md`).

---

## 4. Layer 2 — intra-category aggregation: state and future

### Current state: Option B (honest fallback)

When ≥2 tools cover the same category with a valid binary axis
(`class_norm` non-null):

- Both predictions are shown individually.
- `agreement_<category>` is computed ∈ {`consensus_positive`,
  `consensus_negative`, `split`, `single_tool`}.
- **NO** voting, averaging, or weighted ensemble is performed.
- The Markdown report highlights `split` items for human inspection.
- Tools with `class_norm=null` (e.g. APEX in multi-strain regression)
  do NOT participate in the binary agreement — correct, they are
  different axes.

Reason: without reliability data, assigning authority to one
prediction over another is arbitrary.

### Future target: Option E (weighted ensemble by reliability)

The user eventually wants the orchestrator to weight each prediction
by tool reliability (rather than simple vote). Conceptual example: if
hemopi2 says "non-hemolytic" and hemodl says "yes", and the data show
that hemodl has 80% leakage for peptides similar to the input while
hemopi2 is in Gold grade, hemopi2's prediction weighs more.

### Paths to obtain reliability weights

1. **Paper stats** (short path): extract from each tool's papers the
   metrics on its own splits — precision, recall, MCC, F1, AUC,
   n_train, n_test, data cutoff date, dataset used.
2. **Own audit (Phase 2)** (long, more reliable path): run the
   CD-HIT-2D grading already designed in the project (Gold / Silver /
   Bronze / Red by 40/60/80% bands) over each tool's training data
   vs. the user input.

### Pending task — collect reliability data

**STATUS**: pending until the full pipeline is functional with all
planned tools integrated. Do NOT execute earlier.

When activated, sub-tasks:
- Collect PDFs/preprints of each integrated tool (toxinpred3,
  antibp3, hemopi2, hemodl, deepb3p, deepbp, apex, perseucpp,
  acp_dpe, bertaip + future ones). Source: user provides, or web
  scraping with explicit consent.
- Per paper, extract a table with: training dataset, evaluation
  dataset, reported metrics (precision/recall/MCC/AUC), split sizes,
  data cutoff year, max identity allowed intra-train (if
  documented).
- If papers do not document novelty-stratified metrics, escalate to
  the project's own Phase 2 (CD-HIT-2D grading).
- Decide weight scheme: `weight ∈ [0, 1]` per (tool, leakage_band).
  Document the formula before applying it.
- Only then implement Option E in the consolidator. By default the
  orchestrator will still offer Option B for transparency (weights
  are an optional layer on top of the raw matrix).

### When to update this section
- When the user supplies the first batch of PDFs.
- When the decision is made to run our own Phase 2.
- When the tool pool is closed and the integration frozen.

---

## 5. Reports (Markdown + HTML + Excel)

`scripts/run_audit.py` generates three report formats at the end of
each run; all coexist. Folder convention: input in `Inputs/<name>.fasta`,
output auto-created in `Outputs/<input_stem>_<YYYY-MM-DDTHHMM>/` if
`--output` is not passed. If the timestamp collides, suffix `_2`, `_3`.

### 5.1 REPORT.md (plain text, backup)

Pure Markdown with no external dependencies (no Jinja, no
`pandas.to_markdown`). Sections:

1. **Header**: input FASTA, n peptides, tools executed, total runtime,
   ISO date.
2. **Per-peptide summary (table)**: id, length, n_positive_binary,
   n_negative_binary, categories_covered, n_disagreements_binary, list
   of formatted extra_metrics (e.g. `apex MIC_E_coli=12.4 µM`).
3. **Binary disagreements**: peptides with `split` in some category,
   showing which tools said what.
4. **extra_metrics table**: one row per peptide × active extra
   columns, for quick inspection.
5. **Per-tool health**: table from `tool_health_report.json`.
6. **Footer**: relative links to `consolidated.csv` and
   `consolidated.json`.

### 5.2 REPORT.html (visual, primary for eyeballing)

Standalone HTML5 with inline CSS in `<style>` + **inline JS** in
`<script>`. **No CDN, no external libraries, no network.** Opens in
any modern browser. Expected size: 30–300 KB for FASTAs of 5–50
peptides. Operational cap 2 MB.

**Change 2026-05-01**: the original "no JS" prohibition was relaxed.
Inline JS is allowed for sort/filter on the main table (the
interactive matrix cannot be implemented without JS). External CDNs
remain forbidden — all code lives in the HTML file.

Sections (all wrapped in collapsible `<details class="section">`;
executive summary open by default, the rest collapsed):

1. **Header (metadata, not collapsible)** — metadata bar (input, n
   peptides, n tools, n categories, runtime, UTC date).
2. **Executive summary (interactive matrix)** — filter toolbar + main
   table:
   - **Fixed columns**: rank, peptide_id (with a gold
     `🏆 PATHOGEN SPECIFIC` badge if applicable), length, holistic
     (green/red color by sign).
   - **Per-category columns**: POS/NEG/SPLIT/— chip + mean_score
     below. Each cell carries `data-consensus`, `data-mean-score` and
     `data-tool-<tid>-class` / `data-tool-<tid>-score` for dynamic
     sort by specific tool.
   - **Sort**: click any header → toggle desc/asc/desc. Default sort:
     holistic_score desc.
   - **Category sort**: default order =
     `(consensus desc: POS=4, SPLIT=3, NEG=2, NONE=1) → (mean_score desc)`.
     Categories with >1 tool have a dropdown `<select class="col-sort">`
     to switch to per-tool sort.
   - **Filters (toolbar)**: holistic ≥ X, length between min and max,
     "only PATHOGEN SPECIFIC" checkbox, reset button.
3. **Disagreements** — only if there are splits. Yellow box, one row
   per (peptide × category × tool pair).
4. **Per-peptide drill-down** — `<details class="inline">` per
   peptide. Each block: pathogen_specific badge if applicable +
   sequence (monospace) + table `tool | category | class | score | extra_metrics`.
5. **Extra metrics** — APEX sub-block (4 count cards per tag + per-
   peptide table with 3 means `mean_mic_{pathogen,commensal,total}` +
   inline `<details>` with detail across the 34 strains, green row if
   MIC ≤ 32 µM) + generic table of other tools with extra_metrics
   (if any).
6. **Per-tool health** — table with runtime, status, batches OK/total,
   score_oor, diagnosis.
7. **Footer (not collapsible)** — links to `consolidated.csv`,
   `.json`, `.xlsx`, `REPORT.md`, `tool_health_report.json`.

Generated by `_render_report_html()` in `scripts/run_audit.py`. Built
with f-string + `"".join(parts)`. Inline JS defined as a constant
`_MATRIX_INTERACTIVE_JS` (~120 lines, auto-executed IIFE).

Style: white/light-gray/slate-blue palette, system-ui font, tables
with sticky headers, gold gradient badge for pathogen_specific.

---

### 5.3 consolidated.xlsx (Excel, for interactive inspection/filtering)

Generated with **pure openpyxl** (not `pandas.to_excel` — pandas does
not support row-by-row conditional formatting well). Operational cap
2 MB for 10 peptides × 11 tools (expected <500 KB).

5 sheets in this order, all with freeze pane on row 1 and autofilter
active on the used range:

1. **Matrix** — one row per peptide **sorted by `holistic_score` desc**.
   Columns: `holistic_score`, `n_categories_evaluated`, `peptide_id`,
   `sequence`, `length`, `<tool>__class`, `<tool>__score` (alternating
   per tool), APEX selectivity 5 cols (if applicable),
   `<tool>__<metric>__<unit>` (extras including
   `apex__mean_mic_{pathogen,commensal,total}__uM`),
   `<cat>__consensus`, `<cat>__mean_score` (paired),
   `agreement_<category>`. Row-by-row conditional formatting (fill
   applied at cell-write time):
   - `<tool>__class == "positive"` → light-green fill `#d4edda` (also
     the adjacent score cell).
   - `<tool>__class == "negative"` → very-light-gray fill `#f8f9fa`.
   - `agreement_<category> == "split"` → yellow fill `#fff3cd`, bold
     font.
   - `agreement_<category> == "consensus_positive"` → green `#c3e6cb`.
   - `agreement_<category> == "consensus_negative"` → gray `#e2e3e5`.
   - Numeric scores formatted `0.0000`.
2. **Disagreements** — only peptides with any `split`. One row per
   (peptide × category × disagreeing-tool-pair). Columns:
   `peptide_id`, `sequence`, `category`, `tool_A`, `class_A`,
   `score_A`, `tool_B`, `class_B`, `score_B`. If the category has >2
   tools and >1 pair disagrees, as many rows are generated as
   disagreeing pairs. Orange header to stand out.
3. **Extra_Metrics** — `peptide_id` + `<tool>__<metric>__<unit>`
   columns. No conditional formatting. Floats with `0.0000`.
4. **Tool_Health** — `tool_id`, `category`, `runtime_s`, `status`,
   `score_out_of_range`, `diagnosis`. Full-row green fill `#d4edda`
   if `status == "OK"`, light-red `#f8d7da` if `PROBLEMATIC`.
5. **Run_Info** — key/value table: `input_file`, `n_peptides`,
   `n_tools`, `n_tools_ok`, `runtime_total_s`, `datetime_iso` (UTC),
   `tools_executed` (comma-separated list).

Implemented by `_write_consolidated_xlsx()` and helpers
`_xlsx_*_sheet()` in `scripts/run_audit.py`. openpyxl import is lazy:
if not installed, a warning is printed and the .xlsx is skipped
(CSV/JSON remain available).

---

## 6. Decisions by date

- **2026-04-25** — user rejects collapsing continuous MIC to binary.
  Accepts keeping it as an additional column. Allows future tools
  with target-specific metrics (other strains, IC50, etc.) to add
  their own columns following the "magnitude+target+unit unique per
  column" rule.
- **2026-04-30** — `eippred` retired from the pipeline at user
  request (will no longer be used). Local code preserved, env marked
  obsolete. References to "tool with `class_norm=null`" now use
  `apex` as the canonical example.
- **2026-04-30** — two changes added to the orchestrator (see §7 and
  §8): anti-OOM batch processing and APEX selectivity derivation.
- **2026-05-01** — major refactor (see new §9 + changes in §5.2 and
  §8): (a) APEX returns to `class_norm=None` (reverting the
  2026-04-30 override), but adds 3 aggregated means + enters the
  holistic adjustment; (b) `categories_config.yaml` extended with
  `polarity: good|bad|neutral` per category; (c) new column
  `holistic_score` (default sort in CSV/XLSX/HTML) computed as
  `good_mean − bad_mean + apex_adjustment`; (d) HTML becomes
  interactive with inline JS (sort/filter per column, ranking-by-tool
  dropdown for multi-tool categories); (e) HTML sections wrapped in
  collapsible `<details>`; (f) gold `🏆 PATHOGEN SPECIFIC` badge;
  (g) bertaip threshold 0.5 → 0.8.
- **2026-04-25** — user confirms target Option E (weighted ensemble
  by reliability) but defers it until the pipeline is complete and
  tools are integrated. Until then, Option B (explicit
  agreement/disagreement, no voting) is the stable behavior.
  Reliability-data collection (paper stats or our own Phase 2) is a
  pending task recorded in §4.
- **2026-04-27** — `REPORT.html` standalone added (inline CSS, no JS,
  no CDN) as the primary report for eyeballing. Structure in §5.2.
  `REPORT.md` is kept as plain-text backup.
- **2026-04-28** — `consolidated.xlsx` added (5 sheets, pure
  openpyxl, row-by-row conditional formatting, autofilter, freeze
  pane). Structure in §5.3. Folder convention `Inputs/` (drop FASTA)
  and `Outputs/<input_stem>_<ISO_ts>/` (auto-created per run): the
  orchestrator resolves `--input` from `Inputs/` when given a bare
  name and creates `--output` automatically if unspecified.

---

## 7. Batch processing (anti-OOM)

`scripts/run_audit.py` splits the input FASTA into batches and runs
each tool over the batches serially, concatenating outputs.

### Configuration

- **Global CLI**: `--batch-size N` (default 100, minimum 1).
- **Per-tool override**: `batch_size_override` field in
  `pipeline_config.yaml` per tool block. Absent → uses the global
  value.

### Mechanics

For each tool and each batch `b`:

1. Write
   `Outputs/<run>/per_tool/<tool>/_batches/batch_NNN/input_<tool>_batch_NNN.fasta`
   with the peptides of the batch.
2. `audit_lib.tool_runner.run_tool` runs the tool on that FASTA;
   canonical output in `batch_dir`.
3. The orchestrator parses THAT batch's output (not the aggregate)
   and appends the normalized records.
4. After the tool finishes, raw outputs are concatenated into
   `Outputs/<run>/per_tool/<tool>/predictions_<tool>.<ext>` (for
   human inspection only — the parser already consumed each batch
   independently).
5. Temporary sub-FASTAs (`input_<tool>_batch_NNN.fasta`) are DELETED
   at the end of the run. The `_batches/batch_NNN/` folders with
   outputs and logs REMAIN for debugging.

### Policy for failed batches

A batch fails when: timeout, exit_code ≠ 0, empty/missing output, or
`parse_error`. Policy:

- **The run is NOT aborted.** The orchestrator continues with the
  next batch.
- Peptides in the failed batch receive a record with:
  - `class_norm = None`
  - `score = None`
  - `raw_class = "error_batch_failed"`
  - `error_batch_failed = True`
- In `consolidated.csv` and `consolidated.xlsx`, the
  `<tool>__class` cell shows `"error_batch_failed"` for those
  peptides (overrides None).
- In `consolidated.json`, the `predictions[<tool>]` entry includes
  `"error_batch_failed": true`.
- In `tool_health_report.json` and the MD/HTML reports, `n_batches`,
  `n_batches_ok`, `n_batches_failed` are reported.

### Tool status after mixed batches

| Result | `health[tool].status` | `diagnosis` |
|---|---|---|
| All batches OK | `OK` | `null` |
| No batch OK | `PROBLEMATIC` | `"all batches failed: …"` |
| Mixed (≥1 OK, ≥1 failed) | `OK` (with `partial` label) | `"partial: X/N batches failed: …"` |

The reason `partial` is labeled `OK` is that the tool produced useful
predictions for most peptides; the report makes it clear which
peptides have no prediction.

---

## 8. APEX selectivity (pathogenic vs. commensal)

APEX (Penn) predicts MIC against 34 bacterial strains/species — some
pathogenic (S. aureus, P. aeruginosa, K. pneumoniae, MRSA, VRE,
Salmonella, Listeria) and some gut-microbiome commensals
(Akkermansia, Bacteroides, Eubacterium, Ruminococcus, E. coli
Nissle). APEX has **no native flag** to distinguish the two groups
in its output (single column per strain).

The orchestrator post-processes APEX records to derive 5 additional
columns in the consolidated:

| Column | Type | Definition |
|---|---|---|
| `apex__pathogenic_active` | binary 0/1 | 1 if MIC ≤ T on ≥1 pathogenic strain |
| `apex__commensal_active` | binary 0/1 | 1 if MIC ≤ T on ≥1 commensal strain |
| `apex__pathogenic_strains_hit__count` | int | # pathogenic strains with MIC ≤ T |
| `apex__commensal_strains_hit__count` | int | # commensal strains with MIC ≤ T |
| `apex__selectivity_tag` | enum | `pathogen_specific` (path=1, comm=0) / `commensal_specific` (path=0, comm=1) / `broad_spectrum` (both 1) / `non_active` (both 0) |

Threshold T configurable in `config/apex_strain_classification.yaml`
(default 32 µM).

### Strain classification

`config/apex_strain_classification.yaml` maps the 34 strains to 3
lists: `pathogenic` (15), `commensal` (19), `ambiguous` (0 after the
2026-04-30 reclassification — `E. coli ATCC11775` moved to commensal
and `C. spiroforme ATCC29900` moved to pathogenic by maintainer
decision). `ambiguous` entries, if added back, are exported as
individual columns but **do NOT count** towards the aggregate
(neither `apex__pathogenic_active` nor `apex__commensal_active`).
To reclassify an ambiguous strain, move its entry to one of the two
previous lists.

### APEX and class_norm (reverted 2026-05-01)

APEX **does NOT enter** the binary `class_norm` axis (`class_norm =
None` always, pure `extra_only`). Decision 2026-05-01:

- The 32 µM threshold is subjective and forcing POS/NEG in the cross
  matrix distorted the `antimicrobial` category.
- The category remains with `antibp3` as the sole binary provider
  (`single_tool` in agreement) — clean and honest.
- APEX still contributes the `selectivity_tag` (critical biological
  descriptor) + 3 aggregated means, both extremely useful for
  ranking even though they don't enter POS/NEG.

### Derived means + ranking impact

`_apply_apex_selectivity` adds to APEX's `extra_metrics`:

- `mean_mic_pathogen` (µM) — mean MIC over pathogenic strains
  (excludes None)
- `mean_mic_commensal` (µM) — mean over commensals
- `mean_mic_total` (µM) — combined mean

These three are materialized as
`apex__mean_mic_{pathogen,commensal,total}__uM` columns in the
consolidated output.

The `selectivity_tag` additionally contributes to the
**holistic_score** (see §9) as an adjustment:

| Tag | Adjustment |
|---|---|
| `pathogen_specific` | +0.15 (therapeutic bonus) |
| `broad_spectrum` | +0.05 (still AMP) |
| `non_active` | 0.0 |
| `commensal_specific` | −0.20 (harms microbiome → penalty) |

### Reports

- **HTML**: sub-block inside "Extra metrics" with 4 count cards per
  tag + per-peptide table (3 means + inline `<details>` for 34
  strains, green row if MIC ≤ 32 µM). Gold `🏆 PATHOGEN SPECIFIC`
  badge in executive summary and drill-down.
- **MD**: simplified — APEX info only inside "Extra metrics" (no
  standalone section).
- **Excel `Matrix` sheet**: 5 APEX-selectivity columns + 3
  mean_mic columns + 34 raw MIC columns.
- **JSON**: each APEX prediction includes
  `apex_selectivity: {..., mean_mic_pathogen_uM,
  mean_mic_commensal_uM, mean_mic_total_uM}`.

---

## 9. Hierarchical ranking: structural_score + holistic_score (2026-05-03)

Default sort of the consolidated output (CSV/XLSX/HTML). Two tiers so
that the user prioritizes peptides without high-magnitude false
positives inflating a structurally weak profile.

### Polarity per category

`config/categories_config.yaml` adds a `polarity ∈ {good, bad, neutral}`
field per category:

| Polarity | Categories |
|---|---|
| `bad` | toxicity, hemolytic, allergenicity |
| `good` | antimicrobial, anticancer, antiviral, anti_inflammatory, antifungal, anti_angiogenic, hypotensive, ecoli_inhibitor, antioxidant, anti_aging, tumor_homing, **bbb**, cpp |
| `neutral` | (none currently) |

`bbb=good` by user decision 2026-05-01: broadens the therapeutic
range (not always desirable, but opens brain-targeting treatments). A
category without explicit polarity is treated as `neutral` (no
contribution).

### Level 1 — `structural_score` (integer, POS/NEG/SPLIT profile, no averaging)

For each evaluated category in the run:

| Polarity | POS | SPLIT | NEG | NONE |
|---|---:|---:|---:|---:|
| `good` | 3 | 2 | 1 | 0 |
| `bad`  | 1 | 2 | 3 | 0 |
| `neutral` | 0 | 0 | 0 | 0 |

`structural_max = 3 × n_cats_good_bad_evaluated`. Categories without
score (all tools failed / no tool of that category ran) add 0 —
penalizes partially evaluated peptides.

SPLIT is worth **2** because it sits exactly between POS and NEG: in
a good category it is worse than POS (not all tools agree) but
better than NEG (some tool already believes yes); in a bad category
it is worse than NEG but better than POS.

### Level 2 — `holistic_score` (quantitative tiebreaker)

```
holistic_score = good_mean − bad_mean + apex_adjustment + potency_adjustment
```

- `good_mean` = mean of `<cat>__mean_score` for cats with
  polarity=good and non-None mean_score
- `bad_mean` = mean of `<cat>__mean_score` for cats with
  polarity=bad and non-None mean_score
- `apex_adjustment`:

| APEX Tag | Adjustment |
|---|---:|
| `pathogen_specific` | +0.15 |
| `broad_spectrum` | +0.05 |
| `non_active` | 0.0 |
| `commensal_specific` | −0.20 |

- `potency_adjustment` (based on min(MIC) on any strain, pathogen or
  commensal):

| Potency tag | MIC threshold | Adjustment |
|---|---:|---:|
| `MUY_POTENTE_AMP` | ≤ 5 µM | +0.20 |
| `POTENTE_AMP` | ≤ 10 µM | +0.10 |

Mutually exclusive (only the highest). Independent of
`selectivity_tag`. If the most-sensitive strain is a commensal, the
per-strain detail marks that row red (visual alert), but the badge
is retained.

### Hierarchical sort

```
sort key = (structural_score desc, holistic_score desc)
```

A peptide with structural=15/21 ALWAYS ranks above one with 13/21.
The holistic_score only breaks ties within the same tier.

### Handling missing data

Categories without a score are EXCLUDED from the average (do not
count as 0). A failed tool does not penalize the peptide. The
`n_categories_evaluated` column reports the count for transparency.

### Derived columns in consolidated

| Column | Type | Definition |
|---|---|---|
| `structural_score` | int | Level 1 of the sort |
| `structural_max` | int | 3 × n cats good+bad evaluated |
| `holistic_score` | float, 4 dp | Level 2 of the sort |
| `n_categories_evaluated` | int | # categories with ≥1 tool with non-None score |
| `apex_potency_tag` | str/null | MUY_POTENTE_AMP / POTENTE_AMP / null |
| `apex_potency_min_mic_uM` | float/null | minimum MIC across any classified strain |
| `<cat>__consensus` | enum | POS / NEG / SPLIT / NONE |
| `<cat>__mean_score` | float | mean of non-None scores from binary tools in that cat |

### Ranking-by-tool dropdown in HTML

For category columns with >1 tool, the header includes a `<select>`
with options:

- `consensus + mean score` (default) — sort by
  `(CONSENSUS_ORDER[consensus], mean_score)` desc
- `by <tool_id>` (one per tool) — sort by
  `(TOOL_CLASS_ORDER[tool.class_norm], tool.score)` desc

Data is exposed as `data-tool-<tid>-class` / `data-tool-<tid>-score`
on each cell — JS reads them without re-parsing the DOM.

### HTML toolbar filters

`structural ≥`, `holistic ≥`, `length between min and max`,
checkboxes `only 🏆 PATHOGEN SPECIFIC` and `only 💪/🔥 POTENT`,
reset button. Implemented as `display:none` on rows (does not remove
from the DOM; sort keeps working over the full set).

### Decision: Python (data) vs. JS (view)

Hybrid. The **data** (structural, holistic, consensus, mean_score,
badges) is computed in Python and persisted to CSV/JSON/XLSX so that
Excel also works as a ranking surface. The **interactive view**
(dynamic sort, filters) lives in inline JS. If the user opens only
the Excel, they already get the sorted ranking and all auxiliary
columns.

---

## 10. APEX per-strain color + potency badges (2026-05-03)

### Potency badges (independent of selectivity_tag)

Computed on min(MIC) over any CLASSIFIED strain (pathogen OR
commensal — ambiguous excluded). User decision 2026-05-03: accept
potency even when it comes from a commensal strain, but raise a
visual alert.

| Tag | Trigger | Holistic bonus | CSS class |
|---|---|---:|---|
| `MUY_POTENTE_AMP` | min MIC ≤ 5 µM | +0.20 | `.badge-very-potent` (🔥 orange) |
| `POTENTE_AMP` | min MIC ≤ 10 µM | +0.10 | `.badge-potent` (💪 blue) |

Tooltip includes "⚠️ via COMMENSAL strain" when applicable. Stack with
`pathogen_specific` (a peptide can carry 🏆 + 🔥 at the same time).

### Strain coloring in APEX detail

Each row of the per-peptide `<details>` is colored according to the
strain's classification AND the MIC:

| Classification | MIC ≤ 32 µM (active) | MIC > 32 µM |
|---|---|---|
| `pathogen` | `.strain-pathogen-active` (green — desirable) | no color |
| `commensal` | `.strain-commensal-active` (red — undesirable, harms microbiome) | no color |
| `ambiguous` | `.strain-ambiguous-active` (yellow) | no color |

Legend shown at the start of the APEX section. Helps to read at a
glance whether a peptide is therapeutically selective (greens >>
reds) or whether a POTENT_AMP earns its tag by killing commensals
(red rows + potency badge).

---

## 11. YAML threshold actually applied: `prefer_threshold_over_raw_class` (2026-05-03)

Bug detected in E2E #1 of 2026-05-02: raising `score_threshold` in a
tool's YAML had no effect if the tool also emitted `prediction_column`
(raw_class). The `_derive_class_norm` function gave priority to
raw_class over score+threshold.

**Fix**: optional flag in `output_parsing` per tool:

```yaml
output_parsing:
  prediction_column: Prediction of AIP
  positive_label: 1
  score_column: Probability of AIP
  score_threshold: 0.8
  prefer_threshold_over_raw_class: true   # ← NEW
```

When `true`, the orchestrator ignores the class emitted by the tool
and re-evaluates with `score >= threshold`. Useful when a tool has its
own hardcoded cutoff (e.g. bertaip with 0.5 fixed in `BertAIP.py`) and
you want to raise the bar without patching the external script.

Applied to bertaip on 2026-05-03. Other tools keep prior behavior.

---
[← Back to Index](INDEX.md)
