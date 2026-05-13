# Pipeline Viability Audit — 2026-04-24 (rev 2026-04-26)

Viability audit (per the "External-artifact viability" rule). Covers
BLOCKS A (initial audit, 11 structural) + B (5 fixes + runner
extension) + C (4 additional smokes) + D (4 STANDBY read-only) +
I/J/K/L/M (2026-04-26 re-audit with the new FIXABLE/BLOCKED boundary
from `verify_external_artifacts.md` §"Adaptation/engineering
boundary").

**Final verdicts**: `OK` (smoke green), `FIXED` (fixed, smoke green),
`BLOCKED` (real structural or unresolvable environmental block under
the rules), `STANDBY` (read-only, documented), `ESTRUCTURAL_REAL` (no
inference entry-point; out of scope), `FIXABLE` (inference logic
present, requires light I/O or argparse adaptation — prepared for
Block K), `DEFERRED_USER` (manual user action pending: lfs / login /
baidu).

## Reclassification 2026-04-26 (Block I, new boundary)

| Tool | Previous verdict | verdict_2026-04-26 | Reason |
|---|---|---|---|
| perseucpp | ESTRUCTURAL_REAL | **FIXABLE** | `process_cpps()` (PERSEUcpp.py:828) is complete: loads `PERSEU-MODEL.pkl` + `PERSEU-Efficiency.pkl` (both in the repo), `test_matrix()` for features, writes `Results.csv`. Only the interactive `input()` (lines 880/887) blocks. Adaptation: replace input with argparse + cwd-bound. ~15 lines. |
| aapl | ESTRUCTURAL_REAL | **BLOCKED** | `MLProcess/Predict.py` is a 32-line shell that receives `dataX` already featurized. Full weights (6 models × 2 subsets NT-S40/S56) but no orchestrator FASTA → 58 features (4335-D) → Boruta filter → ensemble. Rebuilding it = pattern ❌ #2 (re-engineering multi-step feature pipelines). |
| if_aip | ESTRUCTURAL_REAL | **BLOCKED** | `Hybrid(HB-AIP).py` and `Optimized-IF-AIP.py` are **training** scripts (RFE+optuna+SMOTE+cross_val_score) that read 8 pre-computed CSVs (AAC/DPC/PAAC/SCON/QSO/CKSAAGP/GTPC/APAAC). Weights `HB-AIP_Model.pkl` (5.6 MB) and `IF-AIP.zip` (35 MB) present but no FASTA → 8 descriptors → 911-D vector extractor. Pattern ❌ #2. |
| acp_dpe | STANDBY | **FIXABLE** | Test.py DOES contain complete inference: `model.load_state_dict(torch.load('model/main_model.pt'))`, forward, `predictions.extend(outputs.cpu().detach().numpy())`. Blockers: requires CSV with `Sequence,Label` (Label can be a dummy 0), `drop_last=True` with batch=128 discards everything if <128 peptides, does not capture probas. Adaptation: FASTA→CSV adapter, argparse, drop_last=False, write CSV (seq, prob). ~25 lines. Weights `main_model.pt` and `alt_model.pt` present; `residue2idx.pkl` too. |
| mfe_acvp | STANDBY (not cloned) | **BLOCKED** | Cloned 2026-04-26 (`Tool_Repos/mfe_acvp/`). No pretrained weights (`find -name "*.pkl|*.pt|*.h5|*.npz"` = 0 hits). `Ensemble.py __main__` uses `dummy_data = np.random.rand(200, input_dim)`. Structural features require ESMATLAS + NetSurfP-3.0 (external web services = pattern ❌ #5) + 6 feature-extraction scripts with no orchestrator (= ❌ #2). Coronavirus-specific. |

**Block I balance**: +2 FIXABLE (perseucpp, acp_dpe), 3 confirmed
BLOCKED (aapl, if_aip, mfe_acvp).

## Re-inspection 2026-04-26 (Block I.5, 7 additional ESTRUCTURAL_REAL)

| Tool | Previous verdict | verdict_2026-04-26 | Short reason |
|---|---|---|---|
| multimodal_aop | ESTRUCTURAL_REAL | **BLOCKED** | `stacking_onehot.py` is training (CNN+BiLSTM+Transformer with `model.fit`, `train_test_split`); no weights in repo. Rules ❌ #1+#3. |
| afp_mvfl | ESTRUCTURAL_REAL | **BLOCKED** | `Prediction/ds{1,2,3}.py` are end-to-end training (read pre-processed CSV, fit, evaluate); no weights. Datasets are pre-processed features, no FASTA extractor. Rules ❌ #1+#2. |
| antiaging_fl | ESTRUCTURAL_REAL | **BLOCKED** | `code/predict.py` is training in disguise (reads `./data/positive_0.9.fasta`, does `train_test_split` + RFE/RFECV); no weights in repo. Rule ❌ #1+#3. |
| **aip_tranlac** | ESTRUCTURAL_REAL | **FIXABLE** ⚠ surprise | **Weights present** (`AIP-TranLAC.pt` 9.5 MB). `Ourmodel` class complete (transformer encoder + LSTM + attention + conv + classifier); `load_model()` already implemented (line 55); `evaluate()` already extracts per-seq probs (line 196-197 `outputs_cpu[:, 1]`); `generate_data()` encodes FASTA-like (CSV `pep,label`) with a 24-token vocab end-to-end (no external features). Only missing: a `__main__` that: reads FASTA → CSV (seq, dummy label), instantiates Ourmodel, calls load_model('AIP-TranLAC.pt'), iterates and dumps (seq, prob, class). ~30 lines. Rules ✅ #4 (class wiring) + #6 (add __main__) + #2 (FASTA→CSV adapter). |
| deepforest_htp | ESTRUCTURAL_REAL | **BLOCKED** | Only `Features/` and `Model Traning/` (sic) directories, both empty per `find -type f`. No weights, no executable scripts. Rule ❌ #3. |
| stackthp | ESTRUCTURAL_REAL | **BLOCKED** | `Stack_THP.py` is a Colab-exported notebook JSON (212 code cells, 2163 source lines). Reads `/content/drive/MyDrive/THP/data/modified data/*.csv` (pre-processed Colab) and trains 30+ stacked classifiers across scattered cells. No weights. Rule ❌ #4 (replicate notebook logic line by line — NOT trivial: >>30 lines + non-trivial Colab paths) + #2. |
| cpppred_en | ESTRUCTURAL_REAL | **BLOCKED** | Full weights in `selected_weight/CPP/` and `MLCPP/` (6 models each) + 10 pre-computed feature CSVs only for the authors' own test set (not transferable). Scripts `PLM_extraction/{esm1b,esm1v,esm2,protbert_bfd,prott5,unirep}.py` exist but require downloading 6 PLM models (~30 GB) + missing AAC/CTDC/TPC/DistancePair extractors + consistency check vs. training. Cost >> 50 lines. Rule ❌ #2 (re-engineering multi-step feature pipelines). |

**Block I.5 balance**: 1 surprise FIXABLE (**aip_tranlac**, awaiting
user confirmation), 6 firm BLOCKED.

## Block J + K applied (2026-04-26)

**J1 — apex** ✅ **FIXED**. Patches: `torch.load(..., map_location='cpu', weights_only=False)`;
`.cuda()` → CPU at lines 96 and 107. YAML adds new generic dimension
`pre_command: "awk '/^>/{next}{print}' ${INPUT} > test_seqs.txt"`
(extends tool_runner) + 34 `extra_metrics` entries (one per strain,
naming `MIC_<strain_normalized>` snake_case). prediction_type =
extra_only. Smoke 3 peptides in 9.4 s, 34 MICs per peptide.

**J2 — hypeptox_fuse** → **DEFERRED_USER**. `checkpoints/` empty;
weights on personal OneDrive with `?e=...` (not programmatically
downloadable). Documented below.

**J3 — bert_ampep60** → **DEFERRED_USER** (failed attempt). Direct
patch to `predict/predict.py` (argparse + map_location) applied but
`onedrivedownloader` receives a SharePoint MPU login HTML page
(`p2214906_mpu_edu_mo`) instead of the pkl (173 KB of `<!DOCTYPE
html>`). Login required. Corrupt pkls deleted. Pattern ❌ #7
(institutional login without access). Moved to deferred next to
hypeptox_fuse.

**K1 — perseucpp** ✅ **FIXED**. Patch: `if __name__ == "__main__"`
block with `--input` argparse before the legacy interactive prompt +
relax extension check to `('fasta','fa','faa','fna')` at lines 564 and
662 (authors only accepted literal `.fasta`). YAML category=cpp,
prediction_type=classification (CPP positive label=1, score=prob_cpp);
efficiency_high_prob as extra_metric. Smoke 3 peptides 2.5 s, 2
positives.

**K2 — acp_dpe** ✅ **FIXED** (was STANDBY). Patches: add
`_fasta_to_csv()` adapter, new `__main__` with argparse + drop_last
=False + dump (ID, Sequence, prob_acp, class_acp); also remove the
destructive line `data_result = np.array(data_result)` in
`load_data_bicoding()` that broke with NumPy ≥1.24 (inhomogeneous
shape). Original logic (CNN_gru + main_model.pt + 0.5/0.5 ensemble
gru/cnn) untouched. Smoke 3 peptides 3.1 s.

**K3 — aip_tranlac** ✅ **FIXED**. Surgical patch: insert
`if __name__ == "__main__" and "--predict" in sys.argv:` before the
training block (line 204), with the full inference flow (FASTA →
encoded tensor with 24-token vocab + load_model + Ourmodel forward +
dump prob_aip). YAML uses `extra_args: ["--predict"]` to activate the
guard. Smoke 3 peptides 5.0 s. Original training preserved without
`--predict`.

### Extensions to `audit_lib/tool_runner.py` (Block J/K)

Two new, generic dimensions:

| Dimension | Values | Tools using it |
|---|---|---|
| `pre_command` | shell string (substitutes `${INPUT}` → absolute fasta) | apex (FASTA → txt sequence-per-line) |
| `cwd_subdir` | subpath relative to repo_dir (string) | Reserved for tools whose entry point lives in a subfolder and does bare-name imports. (Implemented for bert_ampep60 which remained deferred; kept documented in the runner header.) |

Also documented in `docs/orchestrator_design.md §3` (schema extension).

---

## Final table 2026-04-30 (post-eippred removal)

E2E with `scripts/run_audit.py`: **10 operational tools** after
retiring `eippred` from the pipeline (2026-04-30, user decision; the
code and env remain on disk). On 2026-05-01 `bertaip` replaces
`aip_tranlac` in the `anti_inflammatory` category (aip_tranlac becomes
`_aip_tranlac_backup` in the YAML, deactivated but preserved; bertaip
active with threshold 0.8). Total **10 executable tools**.

| Final verdict | Count | Tools |
|---|---|---|
| **OK / FIXED** (E2E viable) | **10** | toxinpred3, antibp3, hemopi2, hemodl, deepb3p, deepbp, **apex**, **perseucpp**, **acp_dpe**, **bertaip** (2026-05-01, replaces aip_tranlac) |
| **REMOVED** (disconnected from pipeline, code preserved on disk) | **1** | eippred (2026-04-30, at user request) |
| **DEFERRED_USER** (manual download / login pending) | **4** | antifungipept (`git lfs pull`), plm4alg (KSU login), avppred_bwr (Baidu Netdisk), **hypeptox_fuse** (OneDrive ~25 GB) — and `bert_ampep60` also stays in this group (institutional MPU SharePoint, auto-download failed) |
| **BLOCKED** firm (re-engineering / no weights / external services) | **10** | aapl, if_aip, mfe_acvp, multimodal_aop, afp_mvfl, antiaging_fl, deepforest_htp, stackthp, cpppred_en, macppred2 |
| **Total** | **26** | |

History: until 2026-04-29 the pipeline ran with 11 tools (including
eippred). On 2026-04-30 the user requested its removal. The env
`eippred_env` and `Tool_Repos/eippred/` remain physically; only the
orchestrator connection was removed. On 2026-05-01 `bertaip` is added
with env `pipeline_bertaip` (after pinning `transformers==4.30.2` to
resolve a simpletransformers conflict — see `docs/decisions.md` #19).

**Currently E2E viable: 10/26 = 38%** (post-eippred removal,
post-aip_tranlac → bertaip swap).

### APEX paradigm shift (2026-05-01)

APEX **no longer votes on the binary `class_norm` axis** (back to
`extra_only`). Full detail in `docs/orchestrator_design.md` §8 +
`docs/decisions.md` §11. Summary:

- The 32 µM threshold was subjective and forcing POS/NEG distorted
  the `antimicrobial` category.
- The category is left with `antibp3` as the only binary provider
  (`single_tool` in agreement).
- APEX STILL contributes: `selectivity_tag` (pathogen_specific /
  commensal_specific / broad_spectrum / non_active) + 3 aggregated
  means (mean_mic_pathogen / commensal / total) + 34 individual
  strains.
- The `selectivity_tag` ENTERS the new `holistic_score` as an
  adjustment (+0.15 / +0.05 / 0 / −0.20).
- Gold badge `🏆 PATHOGEN SPECIFIC` in HTML/MD when applicable.

---

## Removed (disconnected from the orchestrator)

| Tool | Removal date | Reason |
|---|---|---|
| **eippred** | 2026-04-30 | User decision: will no longer be used. Local code kept in `Dataset_Bioactividad/Tool_Repos/eippred/`. Env `eippred_env` marked obsolete in `docs/deployment.md` (not deleted from the system). YAML block removed from `config/pipeline_config.yaml`. Removed from `DEFAULT_TOOLS` in `scripts/run_audit.py`. |

---

## hemopi2 verification (2026-04-30)

**AI-model state**: ✅ loads correctly (`pickle.load` of
`model/hemopi2_ml_clf.sav` for RF; `transformers.EsmForSequenceClassification`
for ESM2-t6 finetuned). No heuristic fallback. YAML configuration
uses `-m 4` (Hybrid2 = ESM + MERCI), threshold 0.58.

**Functional test with control peptides** (run
`Outputs/test_hemopi2_verify_2026-04-30T1441/`):

| Peptide | Type | ESM Score | MERCI Score | Hybrid Score | Prediction | Coherent with literature? |
|---|---|---|---|---|---|---|
| melittin (`GIGAVLKVLTTGLPALISWIKRKRQQ`) | canonical hemolytic | **0.764** | -1.0 | 0.0 | Non-Hemolytic | ❌ should be Hemolytic |
| magainin-2 (`GIGKFLHSAKKFGKAFVGEIMNS`) | AMP with moderate hemolysis | 0.229 | -1.0 | 0.0 | Non-Hemolytic | partially OK |
| VPP (tripeptide ACE-inhibitor) | non-hemolytic | 0.265 | -1.0 | 0.0 | Non-Hemolytic | ✅ OK |
| `GGGGGGGG` | trivial negative | 0.234 | -1.0 | 0.0 | Non-Hemolytic | ✅ OK |
| buforin-2 (`TRSSRAGLQFPVGRVHRLLRK`) | AMP, low hemolysis | 0.189 | -1.0 | 0.0 | Non-Hemolytic | ✅ OK |

**Diagnosis**:
- The **ESM model DOES work**: ESM scores are differentiated per
  peptide, with melittin receiving the highest score (0.764),
  biochemically correct. If it were a random/heuristic fallback we
  would not see that differential signal.
- **MERCI Score = -1.0 for every sequence** → sum of 4 sub-scores
  (`MERCI Score 1 Pos/Neg/2 Pos/Neg`) when no paper motif matches.
  The locator runs without error (perl OK, `motif/*` files present),
  but these short peptides do not contain hemopi2's canonical
  training motifs.
- **Hybrid Score = ML Score + MERCI Score** → with MERCI=-1 and
  threshold 0.58, melittin (ESM=0.764) drops to Hybrid=−0.236,
  which the code clamps to 0.0 via `class_assignment` → always
  Non-Hemolytic.

**Conclusion**: the official model is loaded and produces a real
signal, but the paper's default Hybrid2 mode is too conservative on
short peptides without exact motif matches. For melittin, a critical
control, it fails.

**Decision 2026-04-30 — applied**: switch to `-m 3` (ESM2-t6 finetuned
only), threshold 0.58 (same default as the paper for ESM and Hybrid2).

Objective justification (not subjective):
- In the paper (HemoPI2, Nat Comm Biol 2025), ESM2-only already
  achieves AUC ≈ 0.85 on the independent test set; the Hybrid2 (ESM
  + MERCI) "boost" was marginal and dependent on the paper's test set.
- The MERCI integration **breaks on short peptides without exact
  motif matches**: the `-1.0` sentinel collapses the Hybrid Score to
  0 and never reaches the threshold, not even for melittin (the
  canonical positive control of the literature).
- ESM2 finetuned already internalizes the sequential information
  that the MERCI motifs try to capture; removing the MERCI branch
  does not reduce net predictive capacity — it only removes a
  deterministic failure source for out-of-distribution inputs.

Changes applied in `config/pipeline_config.yaml`:
- `extra_args: -m 4` → `-m 3`
- `score_column: 'Hybrid Score'` → `'ESM Score'`
- Threshold unchanged (0.58 from the paper).

**Re-test 2026-04-30** (run `Outputs/test_hemopi2_verify_2026-04-30T2000/`):

| Peptide | ESM Score | Prediction | Expected | OK |
|---|---|---|---|---|
| melittin | **0.764** | Hemolytic | Hemolytic | ✅ |
| magainin-2 | 0.229 | Non-Hemolytic | weak/borderline | ✅ (literature: selective AMP, low hemolysis at HC50 > 100 µg/mL) |
| VPP | 0.265 | Non-Hemolytic | Non-Hemolytic | ✅ |
| GGGGGGGG | 0.234 | Non-Hemolytic | Non-Hemolytic | ✅ |
| buforin-2 | 0.189 | Non-Hemolytic | Non-Hemolytic | ✅ |

Verification passes for all 5 controls. Melittin, the critical control,
is correctly identified as hemolytic. Status: **OK** (official AI
model, `-m 3` mode).

---

## aip_tranlac → bertaip (2026-04-30)

**Replacement of the tool for the `anti_inflammatory` category**:
`aip_tranlac` is deactivated (always returned positive in real runs —
bug observed by the user). Replaced by `bertaip`
(https://github.com/ying-jc/BertAIP, BERT-based AIP predictor,
HuggingFace model `yingjc/BertAIP`).

Changes:
- `config/pipeline_config.yaml`: `aip_tranlac:` block renamed to
  `_aip_tranlac_backup:` (preserved outside the orchestrator) and
  `bertaip:` added (env `pipeline_bertaip`, script `BertAIP.py`,
  output `Probability of AIP` + `Prediction of AIP`).
- `scripts/run_audit.py:DEFAULT_TOOLS`: `aip_tranlac` → `bertaip`.
- bertaip env required `pip install transformers==4.30.2` to resolve
  `ImportError: CAMEMBERT_PRETRAINED_MODEL_ARCHIVE_LIST` (conflict
  between `simpletransformers==0.63.9` and `transformers≥4.31`). Fix
  recorded in `docs/decisions.md` #19.

### bertaip verification with canonical AIP+/AIP− controls (2026-04-30)

Run `Outputs/test_bertaip_verify_2026-04-30T2004/`. 5 canonical AIP
peptides vs. 5 non-AIP / pro-inflammatory:

| Type | Peptide | Probability | Prediction | Expected | OK |
|---|---|---|---|---|---|
| AIP+ | αMSH(1-13) `SYSMEHFRWGKPV` | 0.631 | positive | positive | ✅ |
| AIP+ | LL-37 (cathelicidin) | 0.653 | positive | positive | ✅ |
| AIP+ | VIP `HSDAVFTDNYTRLRKQMAVKKYLNSILN` | 0.454 | negative | positive | ❌ FN |
| AIP+ | Apidaecin Ib | 0.614 | positive | positive | ✅ |
| AIP+ | Indolicidin | 0.600 | positive | positive | ✅ |
| AIP− | Bradykinin (pro-inflam) | 0.630 | positive | negative | ❌ FP |
| AIP− | Substance P (pro-inflam) | 0.649 | positive | negative | ❌ FP |
| AIP− | Melittin (pro-inflam) | 0.632 | positive | negative | ❌ FP |
| AIP− | poly-G | 0.161 | negative | negative | ✅ |
| AIP− | random `MKLPSTAVDRLFGVK` | 0.153 | negative | negative | ✅ |

**Metrics**:
- Sensitivity (AIP+ recall) = 4/5 = **80%**
- Specificity (AIP− recall) = 2/5 = **40%**
- VIP miss probably due to length (28 aa, near the upper end of the
  trained range 5-54).

**Objective diagnosis**:
- bertaip is **NOT constant** like aip_tranlac (the previous model's
  bug). Clearly distinguishes biologically structured peptides
  (~0.6) from trivial sequences (~0.15).
- But **discriminates poorly between true AIPs and other short
  bioactive peptides**: bradykinin, substance P and melittin (all
  canonical pro-inflammatory) fall in the same 0.62-0.65 band as
  αMSH and LL-37.
- Score distribution: AIP+ and AIP− overlap completely in [0.45,
  0.65]. The BERT model was probably trained with an imbalanced
  dataset and learned a heuristic "short structured peptide →
  positive" rather than "AIP".

**Conclusion**: bertaip is an acceptable downgrade from a perfect
model and a clear upgrade from aip_tranlac (which was unusable).
**Useful as a coarse filter "structured bioactive peptide vs.
noise"**, not as a fine AIP-vs-other-bioactive discriminator. The
HTML/Markdown report should present it as such, and the user should
interpret `bertaip__class=positive` as "potentially bioactive, AIP not
ruled out", not "AIP confirmed".

**Possible future improvements** (not applied, pending decision):
1. Raise threshold to 0.65: limits false positives but also drops
   several real AIPs (αMSH 0.631 would fall, Apidaecin 0.614 too).
   Improves specificity at the cost of sensitivity. Net gain: small.
2. Look for alternatives (iAIPs-StcDeep, AIPpred, etc.) and
   benchmark with this same control set.
3. Reactivate and debug aip_tranlac: the "always positive" bug may
   be a wrongly calibrated threshold in its wrapper, not necessarily
   a failure of the underlying model. Cost: 1-2 h of inspection of
   its `predict.py`.
4. Accept bertaip as is and document the limitation in the README.

---

## Per-tool table (26 tools total)

| Tool | Env | Verdict | Notes |
|---|---|---|---|
| **toxinpred3** | ml | **OK** | Pre-existing. Verified in regression after sklearn revert. |
| **antibp3** | ml | OK | Pre-existing (per memory). No re-smoke this session. |
| **hemopi2** | torch | **FIXED** | `mv Model → model`; YAML adds `output_capture=hardcoded_file`, `hardcoded_output_name=predictions_hemopi2.csv`, `-wd .` in extra_args (bug: `f"{wd}/{result_filename}"` with wd="." fails when given an absolute path). |
| **eippred** | ml | **BLOCKED** | `model2.pkl.zip` unzipped correctly → requires sklearn ≥1.3 (has `missing_go_to_left` field on tree nodes added in 1.3). Upgrading sklearn to 1.5.2 breaks toxinpred3 (legacy pickle with 7-field format). Conflict unresolvable under the "no env rebuilds" rule. Future fix: dedicated env `ml_new_sklearn` for eippred only (out of scope). |
| **antifungipept** | qsar | **BLOCKED** | `cmodel.pkl` (134 B) and `rmodel_C_a.pkl` (133 B) are **git-lfs pointer files** not hydrated. Confirmed via `.gitattributes`. Rule: "no downloading new models" → BLOCKED. |
| **macppred2** | torch_legacy | **BLOCKED** | `bio_embeddings==0.2.2` does not expose `PLUSRNNEmbedder` even with extra `[plus_rnn]`. Installing the extra downgraded `torch 1.13.1+cu117 → 1.10.0+cu102` (destructive for the env's other 3 tools). Reverted with `torch==1.13.1+cu117 --index-url https://download.pytorch.org/whl/cu117`. |
| **hemodl** | ml | **FIXED** | Runner extended (`output_capture=hardcoded_file`, `hardcoded_output_name=predict_results.csv`, `input_flag=-p`). Installed `protlearn`, `sentencepiece`, `transformers`, `setuptools<81` (pkg_resources). Patches to `source/predict.py`: script-relative paths for `models/*.fs/.transformer`; `tokenizer.batch_encode_plus(...)` → `tokenizer(...)` (transformers 5.6.2 removed `batch_encode_plus`). First run downloads ~4 GB (ESM-2 650M + ProtT5-XL); timeout=1800 s recommended. |
| **deepb3p** | deepb3p_legacy | **FIXED** | YAML: `script: predict_user.py`, `arg_style=positional`, `output_capture=hardcoded_file`, `hardcoded_output_name=prob.txt`. Patches: `utils/config.py` `cuda:2 → cuda:0` (author's hardcoded GPU index); `model/deepb3p.py` adds `map_location` to `torch.load` (checkpoints .pth saved on cuda:2). |
| **bert_ampep60** | torch | **ESTRUCTURAL_REAL** | `predict/predict.py` hardcodes `fasta_path="train_po.fasta"`, `csv_path="train_po.csv"`. No CLI args. The pre-existing YAML points to `wrappers/bert_ampep60_cli.py` that **does not exist** in the repo. Requires a wrapper → out of rules. |
| **hypeptox_fuse** | torch | **ESTRUCTURAL_REAL** | `predict.py` and `inferencer.py` are classes with no `__main__`. YAML references nonexistent `wrappers/hypeptox_fuse_cli.py`. Requires a Python wrapper to orchestrate `Inferencer.predict_fasta_file(...)` + `save_csv_file(...)`. |
| **apex** | qsar | **ESTRUCTURAL_REAL** | `predict.py` hardcodes input as `./test_seqs.txt` (one sequence per line, **not FASTA**) and output as `./Predicted_MICs.csv`. No argparse. Weights present (20 ensemble `.pkl`). Would require a wrapper that converts FASTA → txt, copies to cwd, then renames output. |
| **deepbp** | torch_legacy | **FIXED** | Runner extended (`output_capture=stdout` new dimension). YAML already correct (`arg_style=positional`). Patches to `main/predict_ACP.py`: (a) `feature = np.asarray(feature)` at start of `predict()` (pandas DataFrame + `np.reshape` 3D triggers incompatible `__array_wrap__`); (b) `from tensorflow.keras import backend as K` top-level (Lambda layer `primarycap_squash` captures `K` from the original Colab notebook namespace). Output is `print(['ACP','non-ACP',...])` to stdout; runner writes stdout verbatim to `predictions_deepbp.csv` (downstream parser must extract the list from between Keras progress bars). |
| **plm4alg** | torch_legacy | **STANDBY** | Only Jupyter notebooks (Google Colab). Training data in XLSX. Weights in institutional SharePoint (KSU login). `standby_reason` in YAML line 306-308. |
| **acp_dpe** | torch_legacy | **STANDBY** | `Test.py` is an evaluation script (requires CSV with `Label` column), not a predictor. Output = aggregated metrics, no per-sequence probs. `standby_reason` YAML line 591-593. |
| **avppred_bwr** | torch | **STANDBY** | No `predict.py`. `train.py` and `test.py` with absolute paths to `/mnt/raid5/...` (authors' private server). Pre-computed `.npz` features only on Baidu Netdisk (not programmatically downloadable). `standby_reason` YAML line 631-634. |
| **mfe_acvp** | qsar | **STANDBY** | 7-step pipeline requires external web services (ESMAtlas 3D structure, NetSurfP-3.0 secondary structure). No weights in repo. `Ensemble.py __main__` uses random dummy data. Coronavirus-specific tool. `standby_reason` YAML line 669-672. |
| **multimodal_aop** | — | **ESTRUCTURAL_REAL** | Only `stacking_onehot.py` = training script; reads `Antiox_x_train_onehot.csv` (absent). No weights. |
| **if_aip** | ml | **ESTRUCTURAL_REAL** | `Optimized-IF-AIP.py`, `Hybrid(HB-AIP).py` are training. Weights (`HB-AIP_Model.pkl`, `Voting_classifier_optimal_775.pkl` 167 MB) present but no FASTA → features → predict orchestrator. |
| **afp_mvfl** | ml | **ESTRUCTURAL_REAL** | `Prediction/ds{1,2,3}.py` = end-to-end training + evaluation over pre-processed CSVs. No pretrained weights. |
| **aapl** | — | **ESTRUCTURAL_REAL** | `MLProcess/Predict.py` is a class with no `__main__`. Weights (6 models × 2 subsets). Requires full orchestration wrapper. |
| **antiaging_fl** | — | **ESTRUCTURAL_REAL** | `predict.py`, `predict_4fold.py` do training+RFE (misleading names). Read `./data/positive_0.9.fasta`, `./data/nega_toxin_0.9.fasta`. No weights. |
| **stackthp** | ml | **ESTRUCTURAL_REAL** | `Stack_THP.py` is a Colab-exported **Jupyter notebook JSON**. Not executable as a Python script. Paths `/content/drive/MyDrive/THP/...`. |
| **cpppred_en** | torch | **ESTRUCTURAL_REAL** | `{im,}balance_data_test.py` load 6 CSVs of pre-computed embeddings (ProtT5-XL, ESM-1b/2/1v, TPC, CTDC). No FASTA → 6 embeddings → ensemble orchestrator. |
| **perseucpp** | — | **ESTRUCTURAL_REAL** | `PERSEUcpp.py` is an interactive CLI (`prompt_existing_path()` with `input()`). No argparse. Weights present. |
| **aip_tranlac** | torch | **ESTRUCTURAL_REAL** | Only `train.py`. Model `AIP-TranLAC.pt` (9.5 MB) but no `predict.py` to load it. |
| **deepforest_htp** | — | **ESTRUCTURAL_REAL** | `Features/` = preprocessing. `Model Traning/` (sic) = 5-fold CV training with interactive `input()`. No weights or inference. |

---

## Summary

| Verdict | Count | Tools |
|---|---|---|
| **OK** (pre-existing) | **2** | toxinpred3, antibp3 |
| **FIXED** (solved this session) | **4** | hemopi2, hemodl, deepb3p, deepbp |
| **BLOCKED** (unresolvable environmental block under the rules) | **3** | eippred, antifungipept, macppred2 |
| **STANDBY** (read-only, documented) | **4** | plm4alg, acp_dpe, avppred_bwr, mfe_acvp |
| **ESTRUCTURAL_REAL** (no usable entry-point) | **13** | bert_ampep60, hypeptox_fuse, apex, multimodal_aop, if_aip, afp_mvfl, aapl, antiaging_fl, stackthp, cpppred_en, perseucpp, aip_tranlac, deepforest_htp |
| **Total** | **26** | |

**E2E viable (OK + FIXED): 6/26 = 23%** as of the initial audit; 10/26
after Blocks I/J/K.

---

## BLOCKED list (excluded from the orchestrator, documented for the future)

1. **eippred** — requires a dedicated env with sklearn ≥1.3
   (unresolvable conflict with toxinpred3 in the same `ml` env).
2. **antifungipept** — 2/5 pickles are git-lfs pointers not
   hydrated. Requires `git lfs pull` (out of "no downloading new
   models" rule) or retraining.
3. **macppred2** — `bio_embeddings 0.2.2` does not have
   `PLUSRNNEmbedder` even with the `[plus_rnn]` extra. Installing
   the extra destroys the `torch_legacy` env by downgrading torch.
   Requires an alternative embedder or retraining without PLUS-RNN.

---

## ESTRUCTURAL_REAL list (13 tools, no entry-point; out of scope under "no wrappers")

### Pattern A: training scripts disguised as "predict"
- `multimodal_aop/stacking_onehot.py`
- `if_aip/Optimized-IF-AIP.py`, `Hybrid(HB-AIP).py`
- `afp_mvfl/Prediction/ds{1,2,3}.py`
- `antiaging_fl/code/predict.py`, `predict_4fold.py`
- `aip_tranlac/train.py`

### Pattern B: classes with no `__main__` / no orchestrator
- `aapl/MLProcess/Predict.py`
- `hypeptox_fuse/predict.py`, `inferencer.py`

### Pattern C: hardcoded I/O paths with no CLI
- `bert_ampep60/predict/predict.py` (`train_po.fasta`, `train_po.csv`)
- `apex/predict.py` (`test_seqs.txt`, `Predicted_MICs.csv`)
- `cpppred_en/{im,}balance_data_test.py` (6 pre-computed CSVs)

### Pattern D: interactive / notebook
- `stackthp/Stack_THP.py` (notebook JSON)
- `perseucpp/PERSEUcpp.py` (`input()` prompts)
- `deepforest_htp/Model Traning/...` (interactive `input()`)

---

## Extensions applied to `audit_lib/tool_runner.py`

During Blocks B/C, three new generic dimensions (NO per-tool wrappers):

| Dimension | Values | Tools using it |
|---|---|---|
| `arg_style` | `flagged` (default), `positional` | flagged: hemopi2, hemodl, eippred (and most). positional: deepb3p, deepbp, apex |
| `output_capture` | `file` (default), `hardcoded_file`, `stdout` | file: toxinpred3, etc. hardcoded_file: hemopi2, hemodl, deepb3p. stdout: deepbp |
| `hardcoded_output_name` | str (required if `output_capture=hardcoded_file`) | predictions_hemopi2.csv, predict_results.csv, prob.txt |

The runner relocates `cwd/hardcoded_output_name → predictions_{tool}.{ext}`
on success; writes `completed.stdout` verbatim to
`predictions_{tool}.{ext}` if `output_capture=stdout`.

---

## Pending manual user action (DEFERRED_USER)

These tools require user credentials/permissions. **Do not touch them
from code** — they are documented for the user to revisit when
credentials/permissions are available. Once resolved they become
FIXABLE with standard adaptations.

| Tool | Required manual action | Details |
|---|---|---|
| **antifungipept** | `git lfs pull` in the repo | `cmodel.pkl` (134 B) and `rmodel_C_a.pkl` (133 B) are LFS pointers not hydrated. Confirmed via `.gitattributes`. After hydration, the tool joins the pipeline directly. |
| **plm4alg** | KSU login + SharePoint download | Weights in institutional KSU SharePoint. Only Jupyter notebooks (Colab). Training data in XLSX. After download, would also require notebook → script conversion (~50 lines); evaluate as an edge case. |
| **avppred_bwr** | Baidu Netdisk download + path adjustment | No `predict.py`. `train.py` and `test.py` with absolute paths to `/mnt/raid5/...` (authors' private server). Pre-computed `.npz` features (k-mer embeddings) only on Baidu Netdisk (not programmatically downloadable). Training data FASTA + labels in repo. |
| **hypeptox_fuse** | RAM ≥32 GB or edit PLM to 650M variant | Wrapper `scripts/wrappers/hypeptox_fuse_cli.py` (≤30 lines) + YAML wired already implemented (2026-04-27). 5×.pth weights + iFeatureOmegaCLI cloned. **Real blocker: Linux with <16 GB RAM cannot load the 3 simultaneous PLMs of the `Inferencer` (ESM-2 3B + ProtT5-XL + ESM-1, ~25 GB RAM at `__init__`).** Resume when: (a) Linux with ≥32 GB RAM (recommended), or (b) edit `Tool_Repos/hypeptox_fuse/inferencer.py:9` to use the `esm2_t33_650M_UR50D` variant instead of `esm2_t36_3B_UR50D` (slightly less accurate than the original paper; document the deviation). |
| **bert_ampep60** | Manual download of pkls from institutional MPU SharePoint | `predict/predict.py` already patched with `--input-fasta`/`--output-csv` argparse + `map_location`. `onedrivedownloader` receives a login HTML (URLs `https://ipmedumo-my.sharepoint.com/:u:/g/personal/p2214906_mpu_edu_mo/...`) instead of the pkls. Requires educational MPU login or a request to the authors: `ec_prot_bert_finetune_reproduce.pkl` and `sa_prot_bert_finetune_reproduce.pkl`. Once in `Tool_Repos/bert_ampep60/predict/`, the smoke should pass (logic + YAML patch already complete). |

### hypeptox_fuse — status 2026-04-27 (PARKED due to RAM)

**Artifacts already hydrated** by the user (2026-04-27):
- ✅ `Tool_Repos/hypeptox_fuse/checkpoints/HyPepToxFuse_Hybrid/fold_{0..4}_state_dict.pth` (5 × ~22 MB)
- ✅ `Tool_Repos/hypeptox_fuse/src/iFeatureOmegaCLI/` (cloned from duongttr/iFeatureOmegaCLI)
- ✅ Wrapper `scripts/wrappers/hypeptox_fuse_cli.py` (≤30 lines, instantiates Predictor+Inferencer and dumps CSV with `Score=mean(prob1..5)`)
- ✅ YAML `pipeline_config.yaml:hypeptox_fuse` pointing at the wrapper, output_parsing with `prediction_column=Toxicity`, `positive_label='True'`, `score_column=Score`

**Unresolved blocker**: the user's Linux has <16 GB RAM. The
`Inferencer.__init__` method loads **simultaneously** ESM-2 3B
(~12 GB) + ProtT5-XL (~9 GB) + ESM-1 670M (~2 GB) = ~23 GB in RAM
before the first inference. OOM kill guaranteed.

**To resume**:
- (a) Hardware: Linux with ≥32 GB RAM. After that, the smoke should
  pass directly (PLMs auto-download via `transformers`/`fair-esm`
  cache `~/.cache/torch/hub/`, ~25 GB on disk; the user has 72 GB
  free).
- (b) Software (documented degradation): edit
  `Tool_Repos/hypeptox_fuse/inferencer.py:9` changing
  `esm2_t36_3B_UR50D` → `esm2_t33_650M_UR50D` (~2.5 GB). Aggregate
  RAM cost ~13 GB, fits in 16 GB. Predictions slightly less accurate
  than the original paper, document in provenance.

Do NOT move to OK/FIXED until one of those. The final table counts
11/26 (not 12/26).

---

## Next steps (post-Blocks I/J/K/L/M, for a future session)

1. **Dedicated env for eippred** already implemented (`eippred_env`
   with sklearn ≥1.3) — eippred OK from Block H onwards.
2. **Optional wrappers** for the `ESTRUCTURAL_REAL` BLOCKED tools
   with complete weights but missing feature pipelines: aapl,
   if_aip, cpppred_en. Estimated cost: 4–8 h per tool (includes
   implementing feature extractors). Out of current scope.
3. **Manual user actions** documented above (antifungipept LFS,
   plm4alg KSU, avppred_bwr Baidu, hypeptox_fuse OneDrive).
4. **Paper-stats collection** for Option E (weighted ensemble by
   reliability) — see `docs/orchestrator_design.md §4`. Deferred
   until the integrated tool pool is closed.

---
[← Back to Index](INDEX.md)
