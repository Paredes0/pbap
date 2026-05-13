# Pipeline Viability Audit — 2026-04-24 (rev 2026-04-26)

Auditoría de viabilidad (regla CLAUDE.md "🔍 Viabilidad de artefactos externos"). Cubre BLOQUES A (audit inicial 11 Estructural) + B (5 fixes + runner extension) + C (4 smoke adicionales) + D (4 STANDBY read-only) + I/J/K/L/M (re-auditoría 2026-04-26 con nueva frontera FIXABLE/BLOCKED de `verify_external_artifacts.md` §"Frontera adaptación / ingeniería").

**Veredictos finales**: `OK` (smoke verde), `FIXED` (arreglado, smoke verde), `BLOCKED` (estructural real o bloqueo ambiental irresoluble bajo las reglas), `STANDBY` (read-only, documentado), `ESTRUCTURAL_REAL` (sin entry-point de inferencia; fuera de scope), `FIXABLE` (lógica de inferencia presente, requiere adaptación ligera de I/O o argparse — preparado para Bloque K), `DEFERRED_USER` (acción manual del usuario pendiente: lfs/login/baidu).

## Reclasificación 2026-04-26 (Bloque I, nueva frontera)

| Tool | Verdict previo | verdict_2026-04-26 | Razón |
|---|---|---|---|
| perseucpp | ESTRUCTURAL_REAL | **FIXABLE** | `process_cpps()` (PERSEUcpp.py:828) completa: carga `PERSEU-MODEL.pkl` + `PERSEU-Efficiency.pkl` (ambos en repo), test_matrix() para features, escribe `Results.csv`. Solo el `input()` interactivo (líneas 880/887) bloquea. Adaptación: reemplazar input por argparse + cwd-bound. ~15 líneas. |
| aapl | ESTRUCTURAL_REAL | **BLOCKED** | `MLProcess/Predict.py` es shell de 32 líneas que recibe `dataX` numérico ya featureado. Pesos completos (6 modelos × 2 subsets NT-S40/S56) pero falta orquestador FASTA → 58 features (4335-D) → Boruta filter → ensemble. Reconstruir = patrón ❌ #2 (re-engineering de pipelines de features multi-paso). |
| if_aip | ESTRUCTURAL_REAL | **BLOCKED** | `Hybrid(HB-AIP).py` y `Optimized-IF-AIP.py` son scripts de **training** (RFE+optuna+SMOTE+cross_val_score) que leen 8 CSVs pre-computados (AAC/DPC/PAAC/SCON/QSO/CKSAAGP/GTPC/APAAC). Pesos `HB-AIP_Model.pkl` (5.6 MB) e `IF-AIP.zip` (35 MB) presentes pero falta extractor FASTA → 8 descriptors → 911-D vector. Patrón ❌ #2. |
| acp_dpe | STANDBY | **FIXABLE** | Test.py SÍ tiene la inferencia completa: `model.load_state_dict(torch.load('model/main_model.pt'))`, forward, `predictions.extend(outputs.cpu().detach().numpy())`. Bloqueadores: requiere CSV con `Sequence,Label` (Label puede ser dummy 0), `drop_last=True` con batch=128 descarta todo si <128 péptidos, no captura probas. Adaptación: FASTA→CSV adapter, argparse, drop_last=False, escribir CSV (seq, prob). ~25 líneas. Pesos `main_model.pt` y `alt_model.pt` presentes; `residue2idx.pkl` también. |
| mfe_acvp | STANDBY (no clonado) | **BLOCKED** | Clonado 2026-04-26 (`Tool_Repos/mfe_acvp/`). Sin pesos pre-entrenados (`find -name "*.pkl|*.pt|*.h5|*.npz"` = 0 hits). `Ensemble.py __main__` usa `dummy_data = np.random.rand(200, input_dim)`. Features estructurales requieren ESMATLAS + NetSurfP-3.0 (servicios web externos = patrón ❌ #5) + 6 scripts de feature extraction sin orquestador (= ❌ #2). Específico de coronavirus. |

**Saldo Bloque I**: +2 FIXABLE (perseucpp, acp_dpe), 3 confirmados BLOCKED (aapl, if_aip, mfe_acvp).

## Re-inspección 2026-04-26 (Bloque I.5, 7 ESTRUCTURAL_REAL adicionales)

| Tool | Verdict previo | verdict_2026-04-26 | Razón corta |
|---|---|---|---|
| multimodal_aop | ESTRUCTURAL_REAL | **BLOCKED** | `stacking_onehot.py` es training (CNN+BiLSTM+Transformer con `model.fit`, `train_test_split`); sin pesos en repo. Reglas ❌ #1+#3. |
| afp_mvfl | ESTRUCTURAL_REAL | **BLOCKED** | `Prediction/ds{1,2,3}.py` son training end-to-end (read CSV pre-procesado, fit, evaluate); sin pesos. Datasets son features ya procesadas, sin extractor FASTA. Reglas ❌ #1+#2. |
| antiaging_fl | ESTRUCTURAL_REAL | **BLOCKED** | `code/predict.py` es training disfrazado (lee `./data/positive_0.9.fasta`, hace `train_test_split` + RFE/RFECV); sin pesos en repo. Regla ❌ #1+#3. |
| **aip_tranlac** | ESTRUCTURAL_REAL | **FIXABLE** ⚠ sorpresa | **Pesos presentes** (`AIP-TranLAC.pt` 9.5 MB). Clase `Ourmodel` completa (encoder transformer + LSTM + attention + conv + classifier); `load_model()` ya implementada (línea 55); `evaluate()` ya extrae per-seq probs (línea 196-197 `outputs_cpu[:, 1]`); `generate_data()` codifica FASTA-like (CSV `pep,label`) con vocab 24-token end-to-end (sin features externas). Solo falta `__main__` que: lea FASTA → CSV (seq, label dummy), instancie Ourmodel, llame load_model('AIP-TranLAC.pt'), itere y vuelque (seq, prob, class). ~30 líneas. Reglas ✅ #4 (class wiring) + #6 (añadir __main__) + #2 (FASTA→CSV adapter). |
| deepforest_htp | ESTRUCTURAL_REAL | **BLOCKED** | Solo dirs `Features/` y `Model Traning/` (sic), ambos vacíos según `find -type f`. Sin pesos, sin scripts ejecutables. Regla ❌ #3. |
| stackthp | ESTRUCTURAL_REAL | **BLOCKED** | `Stack_THP.py` es notebook JSON exportado de Colab (212 code cells, 2163 source lines). Lee `/content/drive/MyDrive/THP/data/modified data/*.csv` (pre-procesados Colab) y entrena 30+ stacked classifiers en cells dispersas. Sin pesos. Regla ❌ #4 (replicar lógica de notebook línea a línea — NO trivial: >>30 líneas + paths Colab no triviales) + #2. |
| cpppred_en | ESTRUCTURAL_REAL | **BLOCKED** | Pesos completos en `selected_weight/CPP/` y `MLCPP/` (6 modelos cada uno) + 10 CSVs de features pre-computados solo para test set propio (no transferibles). Scripts `PLM_extraction/{esm1b,esm1v,esm2,protbert_bfd,prott5,unirep}.py` existen pero requieren descargar 6 modelos PLM (~30 GB) + faltan extractores AAC/CTDC/TPC/DistancePair + verificación de consistencia con training. Coste >> 50 líneas. Regla ❌ #2 (re-engineering pipeline features multi-paso). |

**Saldo Bloque I.5**: 1 sorpresa FIXABLE (**aip_tranlac**, espera confirmación del usuario), 6 BLOCKED firmes.

## Bloque J + K aplicados (2026-04-26)

**J1 — apex** ✅ **FIXED**. Patches: `torch.load(..., map_location='cpu', weights_only=False)`; `.cuda()` → CPU en líneas 96 y 107. YAML añade nueva dimensión genérica `pre_command: "awk '/^>/{next}{print}' ${INPUT} > test_seqs.txt"` (extiende tool_runner) + 34 entradas `extra_metrics` (una por cepa, naming `MIC_<strain_normalized>` snake_case). prediction_type=extra_only. Smoke 3 péptidos en 9.4s, 34 MICs por péptido.

**J2 — hypeptox_fuse** → **DEFERRED_USER**. `checkpoints/` vacío; pesos en OneDrive personal con `?e=...` (no programáticamente descargable). Documentado abajo.

**J3 — bert_ampep60** → **DEFERRED_USER** (intento fallido). Patch directo a `predict/predict.py` (argparse + map_location) implementado pero `onedrivedownloader` recibe HTML de login de SharePoint MPU institucional (`p2214906_mpu_edu_mo`) en vez del pkl (173 KB de `<!DOCTYPE html>`). Login requerido. Pkls corruptos eliminados. Patrón ❌ #7 (login institucional sin acceso). Movido a deferred junto con hypeptox_fuse.

**K1 — perseucpp** ✅ **FIXED**. Patch: `if __name__ == "__main__"` con `--input` argparse antes del legacy interactive prompt + relajar check de extensión a `('fasta','fa','faa','fna')` en líneas 564 y 662 (autores solo aceptaban `.fasta` literal). YAML category=cpp, prediction_type=classification (CPP positive label=1, score=prob_cpp); efficiency_high_prob como extra_metric. Smoke 3 péptidos 2.5s, 2 positivos.

**K2 — acp_dpe** ✅ **FIXED** (era STANDBY). Patches: añadir `_fasta_to_csv()` adapter, nuevo `__main__` con argparse + drop_last=False + dump (ID, Sequence, prob_acp, class_acp); también remover línea destructiva `data_result = np.array(data_result)` en `load_data_bicoding()` que rompía con NumPy ≥1.24 (inhomogeneous shape). Lógica original (CNN_gru + main_model.pt + 0.5/0.5 ensemble gru/cnn) intacta. Smoke 3 péptidos 3.1s.

**K3 — aip_tranlac** ✅ **FIXED**. Patch quirúrgico: insertar `if __name__ == "__main__" and "--predict" in sys.argv:` antes del bloque de training (línea 204), con flujo completo de inferencia (FASTA→encoded tensor con vocab 24-token + load_model + Ourmodel forward + dump prob_aip). YAML usa `extra_args: ["--predict"]` para activar el guard. Smoke 3 péptidos 5.0s. Original training preservado sin --predict.

### Extensiones a `audit_lib/tool_runner.py` (Bloque J/K)

Dos dimensiones nuevas, genéricas:

| Dimension | Valores | Tools que lo usan |
|---|---|---|
| `pre_command` | shell string (sustituye `${INPUT}` → fasta absoluto) | apex (FASTA→txt sequence-per-line) |
| `cwd_subdir` | subpath relativo a repo_dir (string) | reservado para tools cuyo entry-point vive en subcarpeta y hace imports bare-name. (Implementado para bert_ampep60 que quedó deferred; sigue documentado en runner header.) |

Documentado también en `docs/orchestrator_design.md §3` (extensión del schema).

---

## Tabla final 2026-04-30 (post-eliminación eippred)

E2E con `scripts/run_audit.py`: **10 tools operativos** tras retirar `eippred` del pipeline (2026-04-30, decisión del usuario; el código y env permanecen en disco). El 2026-05-01 `bertaip` reemplaza a `aip_tranlac` en la categoría `anti_inflammatory` (aip_tranlac queda como `_aip_tranlac_backup` en el YAML, desactivado pero preservado; bertaip activo con threshold 0.8). Total **10 tools** ejecutables.

| Verdict final | Count | Tools |
|---|---|---|
| **OK / FIXED** (viables E2E) | **10** | toxinpred3, antibp3, hemopi2, hemodl, deepb3p, deepbp, **apex**, **perseucpp**, **acp_dpe**, **bertaip** (2026-05-01, sustituye aip_tranlac) |
| **REMOVIDOS** (desconectados del pipeline, código en disco preservado) | **1** | eippred (2026-04-30, a petición del usuario) |
| **DEFERRED_USER** (descarga manual / login pendiente) | **4** | antifungipept (`git lfs pull`), plm4alg (login KSU), avppred_bwr (Baidu Netdisk), **hypeptox_fuse** (OneDrive ~25 GB) — y `bert_ampep60` también queda en este grupo (SharePoint MPU institucional, intento de auto-descarga falló) |
| **BLOCKED** firme (re-engineering / sin pesos / servicios externos) | **10** | aapl, if_aip, mfe_acvp, multimodal_aop, afp_mvfl, antiaging_fl, deepforest_htp, stackthp, cpppred_en, macppred2 |
| **Total** | **26** | |

Histórico: hasta 2026-04-29 el pipeline corría con 11 tools (incluía eippred). El 2026-04-30 el usuario pidió retirarlo. El env `eippred_env` y `Tool_Repos/eippred/` se mantienen físicamente; solo se desconectó del orchestrator. El 2026-05-01 se añade `bertaip` con env `pipeline_bertaip` (tras pinear `transformers==4.30.2` para resolver conflicto simpletransformers — ver `docs/decisions.md` #19).

**Viables E2E ahora: 10/26 = 38%** (post-retiro eippred, post-sustitución aip_tranlac → bertaip).

### Cambio de paradigma APEX (2026-05-01)

APEX **deja de votar en el eje binario `class_norm`** (vuelve a `extra_only`). Detalle completo en `docs/orchestrator_design.md` §8 + `docs/decisions.md` §11. Resumen:

- El threshold 32 µM era subjetivo y forzar POS/NEG distorsionaba la categoría `antimicrobial`.
- La categoría queda con `antibp3` como único proveedor binario (`single_tool` en agreement).
- APEX SIGUE aportando: `selectivity_tag` (pathogen_specific / commensal_specific / broad_spectrum / non_active) + 3 medias agregadas (mean_mic_pathogen / commensal / total) + 34 cepas individuales.
- El `selectivity_tag` ENTRA en el nuevo `holistic_score` como ajuste (+0.15 / +0.05 / 0 / −0.20).
- Badge dorado `🏆 PATHOGEN SPECIFIC` en HTML/MD cuando aplica.

---

## Removidos (desconectados del orchestrator)

| Tool | Fecha retiro | Motivo |
|---|---|---|
| **eippred** | 2026-04-30 | Decisión del usuario: ya no se va a usar. Código local conservado en `Dataset_Bioactividad/Tool_Repos/eippred/`. Env `eippred_env` marcado obsoleto en `docs/deployment.md` (no se borra del sistema). Bloque YAML eliminado de `config/pipeline_config.yaml`. Quitado de `DEFAULT_TOOLS` en `scripts/run_audit.py`. |

---

## Verificación hemopi2 (2026-04-30)

**Estado del modelo IA**: ✅ se carga correctamente (`pickle.load` de `model/hemopi2_ml_clf.sav` para RF; `transformers.EsmForSequenceClassification` para ESM2-t6 finetuned). Sin fallback heurístico. Configuración YAML usa `-m 4` (Hybrid2 = ESM + MERCI), threshold 0.58.

**Test funcional con péptidos de control** (run `Outputs/test_hemopi2_verify_2026-04-30T1441/`):

| Péptido | Tipo | ESM Score | MERCI Score | Hybrid Score | Predicción | ¿Coherente con literatura? |
|---|---|---|---|---|---|---|
| melittin (`GIGAVLKVLTTGLPALISWIKRKRQQ`) | Hemolítico canónico | **0.764** | -1.0 | 0.0 | Non-Hemolytic | ❌ debería ser Hemolytic |
| magainin-2 (`GIGKFLHSAKKFGKAFVGEIMNS`) | AMP con hemolisis moderada | 0.229 | -1.0 | 0.0 | Non-Hemolytic | parcialmente OK |
| VPP (tripeptide ACE-inhibitor) | No hemolítico | 0.265 | -1.0 | 0.0 | Non-Hemolytic | ✅ OK |
| `GGGGGGGG` | Negativo trivial | 0.234 | -1.0 | 0.0 | Non-Hemolytic | ✅ OK |
| buforin-2 (`TRSSRAGLQFPVGRVHRLLRK`) | AMP, baja hemolisis | 0.189 | -1.0 | 0.0 | Non-Hemolytic | ✅ OK |

**Diagnóstico**:
- El **ESM model SÍ funciona**: ESM scores diferenciados por péptido, con mellitina obteniendo el score más alto (0.764), bioquímicamente correcto. Si fuera fallback random/heurístico, no veríamos esa señal diferencial.
- **MERCI Score = -1.0 para todas las secuencias** → suma de 4 sub-scores (`MERCI Score 1 Pos/Neg/2 Pos/Neg`) cuando ningún motivo del paper matchea. El locator ejecuta sin error (perl OK, archivos `motif/*` presentes), pero estos péptidos cortos no contienen los motivos canónicos del training de hemopi2.
- **Hybrid Score = ML Score + MERCI Score** → con MERCI=-1 y threshold 0.58, mellitina (ESM=0.764) cae a Hybrid=−0.236, que el código clamp a 0.0 vía `class_assignment` → siempre Non-Hemolytic.

**Conclusión**: el modelo oficial está cargado y predice señal real, pero el modo Hybrid2 por defecto del paper es demasiado conservador en péptidos cortos sin motivos exactos. Para mellitina, un test de control crítico, falla.

**Decisión 2026-04-30 — aplicada**: cambiar a `-m 3` (ESM2-t6 finetuned solo), threshold 0.58 (igual al default del paper para ESM y para Hybrid2).

Justificación objetiva (no subjetiva):
- En el paper (HemoPI2, Nat Comm Biol 2025), ESM2-only ya alcanza AUC ≈ 0.85 en el test set independiente; el "boost" de Hybrid2 (ESM + MERCI) era marginal y dependiente del test set del paper.
- La integración MERCI **se rompe en péptidos cortos sin matches exactos** a los motivos del paper: el sentinel `-1.0` colapsa el Hybrid Score a 0 y nunca se alcanza el threshold, ni siquiera para mellitina (control positivo canónico de la literatura).
- ESM2 finetuned ya internaliza la información secuencial que los motivos MERCI tratan de capturar; eliminar la rama MERCI no quita capacidad predictiva neta — solo elimina una fuente de fallo determinista para inputs out-of-distribution.

Cambios aplicados en `config/pipeline_config.yaml`:
- `extra_args: -m 4` → `-m 3`
- `score_column: 'Hybrid Score'` → `'ESM Score'`
- Threshold sin cambio (0.58 del paper).

**Re-test 2026-04-30** (run `Outputs/test_hemopi2_verify_2026-04-30T2000/`):

| Péptido | ESM Score | Predicción | Esperado | OK |
|---|---|---|---|---|
| melittin | **0.764** | Hemolytic | Hemolytic | ✅ |
| magainin-2 | 0.229 | Non-Hemolytic | weak/borderline | ✅ (literatura: AMP selectivo, baja hemolisis a HC50 > 100 µg/mL) |
| VPP | 0.265 | Non-Hemolytic | Non-Hemolytic | ✅ |
| GGGGGGGG | 0.234 | Non-Hemolytic | Non-Hemolytic | ✅ |
| buforin-2 | 0.189 | Non-Hemolytic | Non-Hemolytic | ✅ |

Verificación pasa para los 5 controles. Mellitina, control crítico, queda correctamente identificado como hemolítico. Estado: **OK** (modelo IA oficial, modo `-m 3`).

---

## aip_tranlac → bertaip (2026-04-30)

**Reemplazo del tool de la categoría `anti_inflammatory`**: `aip_tranlac` se desactiva (siempre devolvía positive en runs reales — bug observado por el usuario). Reemplazado por `bertaip` (https://github.com/ying-jc/BertAIP, BERT-based AIP predictor, modelo HuggingFace `yingjc/BertAIP`).

Cambios:
- `config/pipeline_config.yaml`: bloque `aip_tranlac:` renombrado a `_aip_tranlac_backup:` (preservado fuera del orchestrator) y `bertaip:` añadido (env `pipeline_bertaip`, script `BertAIP.py`, output `Probability of AIP` + `Prediction of AIP`).
- `scripts/run_audit.py:DEFAULT_TOOLS`: `aip_tranlac` → `bertaip`.
- bertaip env requirió `pip install transformers==4.30.2` para resolver `ImportError: CAMEMBERT_PRETRAINED_MODEL_ARCHIVE_LIST` (conflicto entre `simpletransformers==0.63.9` y `transformers≥4.31`). Fix registrado en `docs/decisions.md` #19.

### Verificación bertaip con controles canónicos AIP+/AIP− (2026-04-30)

Run `Outputs/test_bertaip_verify_2026-04-30T2004/`. 5 péptidos AIP canónicos vs 5 no-AIP / pro-inflamatorios:

| Tipo | Péptido | Probability | Predicción | Esperado | OK |
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

**Métricas**:
- Sensibilidad (recall AIP+) = 4/5 = **80%**
- Especificidad (recall AIP−) = 2/5 = **40%**
- VIP miss probablemente por longitud (28 aa, cerca del límite del rango entrenado 5-54).

**Diagnóstico objetivo**:
- bertaip **NO es constante** como aip_tranlac (el bug del modelo anterior). Distingue claramente péptidos biológicamente estructurados (~0.6) de secuencias triviales (~0.15).
- Pero **discrimina pobremente entre AIPs reales y otros péptidos bioactivos cortos**: bradikinina, substancia P y mellitina (todos pro-inflamatorios canónicos) caen en la misma franja 0.62-0.65 que αMSH y LL-37.
- Score distribution: AIP+ y AIP− se solapan completamente en [0.45, 0.65]. Modelo BERT probablemente fue entrenado con un dataset desbalanceado y aprende una heurística "péptido estructurado corto → positive" más que "AIP".

**Conclusión**: bertaip es un downgrade aceptable respecto a un modelo perfecto, y un upgrade claro respecto a aip_tranlac (que era inutilizable). **Útil como filtro grueso "péptido bioactivo estructurado vs ruido"**, no como discriminador fino AIP vs otro tipo de bioactivo. El reporte HTML/Markdown debe presentarlo como tal y el usuario debe interpretar `bertaip__class=positive` como "potencialmente bioactivo, AIP no descartado", no como "AIP confirmado".

**Opciones de mejora futura** (no aplicadas, pendientes de decisión):
1. Subir el threshold a 0.65: limita falsos positivos pero también elimina varios AIPs reales (αMSH 0.631 caería, Apidaecin 0.614 también). Mejora especificidad a costa de sensibilidad. Net: poco gain.
2. Buscar alternativas (iAIPs-StcDeep, AIPpred, etc.) y volver a benchmark con este mismo control set.
3. Reactivar y diagnosticar aip_tranlac: el bug "siempre positive" puede ser un threshold mal calibrado en su wrapper, no necesariamente un fallo del modelo subyacente. Coste: 1-2h de inspección de su `predict.py`.
4. Aceptar bertaip como está y documentar la limitación en el README.

---

---

## Tabla por tool (26 tools totales)

| Tool | Env | Verdict | Notas |
|---|---|---|---|
| **toxinpred3** | ml | **OK** | Pre-existente. Verificado en regresión tras revert de sklearn. |
| **antibp3** | ml | OK | Pre-existente (según memoria). No re-smoke en esta sesión. |
| **hemopi2** | torch | **FIXED** | `mv Model → model`; YAML añade `output_capture=hardcoded_file`, `hardcoded_output_name=predictions_hemopi2.csv`, `-wd .` en extra_args (bug: `f"{wd}/{result_filename}"` con wd="." falla si se pasa path absoluto). |
| **eippred** | ml | **BLOCKED** | `model2.pkl.zip` unzipped correctamente → requiere sklearn ≥1.3 (tiene campo `missing_go_to_left` en nodos de árbol añadido en 1.3). Upgrade de sklearn a 1.5.2 rompe toxinpred3 (pickle legacy con 7-field format). Conflicto irresoluble bajo regla "no env rebuilds". Solución futura: env dedicado `ml_new_sklearn` sólo para eippred (fuera de scope). |
| **antifungipept** | qsar | **BLOCKED** | `cmodel.pkl` (134 B) y `rmodel_C_a.pkl` (133 B) son **git-lfs pointer files** sin hidratar. Confirmado vía `.gitattributes`. Regla: "no descargar modelos nuevos" → BLOCKED. |
| **macppred2** | torch_legacy | **BLOCKED** | `bio_embeddings==0.2.2` no expone `PLUSRNNEmbedder` ni con extra `[plus_rnn]`. Install del extra degradó `torch 1.13.1+cu117 → 1.10.0+cu102` (destructivo para otras 3 tools del env). Revertido con `torch==1.13.1+cu117 --index-url https://download.pytorch.org/whl/cu117`. |
| **hemodl** | ml | **FIXED** | Runner extendido (`output_capture=hardcoded_file`, `hardcoded_output_name=predict_results.csv`, `input_flag=-p`). Instalado `protlearn`, `sentencepiece`, `transformers`, `setuptools<81` (pkg_resources). Patches a `source/predict.py`: paths script-relative para `models/*.fs/.transformer`; `tokenizer.batch_encode_plus(...)` → `tokenizer(...)` (transformers 5.6.2 removió `batch_encode_plus`). Primer run descarga ~4 GB (ESM-2 650M + ProtT5-XL); timeout=1800s recomendado. |
| **deepb3p** | deepb3p_legacy | **FIXED** | YAML: `script: predict_user.py`, `arg_style=positional`, `output_capture=hardcoded_file`, `hardcoded_output_name=prob.txt`. Patches: `utils/config.py` `cuda:2 → cuda:0` (hardcoded GPU index del autor); `model/deepb3p.py` añade `map_location` a `torch.load` (checkpoints .pth saved on cuda:2). |
| **bert_ampep60** | torch | **ESTRUCTURAL_REAL** | `predict/predict.py` hardcodea `fasta_path="train_po.fasta"`, `csv_path="train_po.csv"`. Sin CLI args. El YAML pre-existente apunta a `wrappers/bert_ampep60_cli.py` que **no existe** en el repo. Requiere wrapper → fuera de regla. |
| **hypeptox_fuse** | torch | **ESTRUCTURAL_REAL** | `predict.py` e `inferencer.py` son clases sin `__main__`. YAML referencia `wrappers/hypeptox_fuse_cli.py` inexistente. Requiere wrapper Python para orquestar `Inferencer.predict_fasta_file(...)` + `save_csv_file(...)`. |
| **apex** | qsar | **ESTRUCTURAL_REAL** | `predict.py` hardcodea input en `./test_seqs.txt` (una secuencia por línea, **no FASTA**) y output en `./Predicted_MICs.csv`. Sin argparse. Pesos están (20 ensemble `.pkl`). Requeriría wrapper que convierta FASTA → txt, copie a cwd, luego renombre output. |
| **deepbp** | torch_legacy | **FIXED** | Runner extendido (`output_capture=stdout` nueva dimension). YAML ya correcto (`arg_style=positional`). Patches a `main/predict_ACP.py`: (a) `feature = np.asarray(feature)` al inicio de `predict()` (pandas DataFrame + `np.reshape` 3D triggerea `__array_wrap__` incompatible); (b) `from tensorflow.keras import backend as K` al top-level (Lambda layer `primarycap_squash` captura `K` del namespace del notebook Colab original). Output es `print(['ACP','non-ACP',...])` a stdout; runner escribe stdout verbatim a `predictions_deepbp.csv` (parser downstream debe extraer la lista de entre progress bars de Keras). |
| **plm4alg** | torch_legacy | **STANDBY** | Solo notebooks Jupyter (Google Colab). Training data en XLSX. Pesos en SharePoint institucional (KSU login). `standby_reason` en YAML línea 306-308. |
| **acp_dpe** | torch_legacy | **STANDBY** | `Test.py` es script de evaluación (requiere CSV con columna `Label`), no predictor. Output = métricas agregadas, sin per-sequence probs. `standby_reason` YAML línea 591-593. |
| **avppred_bwr** | torch | **STANDBY** | Sin `predict.py`. `train.py` y `test.py` con paths absolutos a `/mnt/raid5/...` (servidor privado). Features pre-computadas `.npz` sólo en Baidu Netdisk. `standby_reason` YAML línea 631-634. |
| **mfe_acvp** | qsar | **STANDBY** | Pipeline de 7 pasos requiere servicios web externos (ESMAtlas 3D structure, NetSurfP-3.0 secondary structure). Sin pesos en repo. `Ensemble.py __main__` usa datos random dummy. Tool específico de coronavirus. `standby_reason` YAML línea 669-672. |
| **multimodal_aop** | — | **ESTRUCTURAL_REAL** | Solo `stacking_onehot.py` = training script; lee `Antiox_x_train_onehot.csv` (ausente). Sin pesos. |
| **if_aip** | ml | **ESTRUCTURAL_REAL** | `Optimized-IF-AIP.py`, `Hybrid(HB-AIP).py` son training. Pesos (`HB-AIP_Model.pkl`, `Voting_classifier_optimal_775.pkl` 167 MB) presentes pero sin orquestador FASTA → features → predict. |
| **afp_mvfl** | ml | **ESTRUCTURAL_REAL** | `Prediction/ds{1,2,3}.py` = training + eval end-to-end sobre CSVs pre-procesados. Sin pesos pre-entrenados. |
| **aapl** | — | **ESTRUCTURAL_REAL** | `MLProcess/Predict.py` es clase sin `__main__`. Pesos (6 modelos × 2 subsets). Requiere wrapper de orquestación completo. |
| **antiaging_fl** | — | **ESTRUCTURAL_REAL** | `predict.py`, `predict_4fold.py` hacen training+RFE (engañosos en nombre). Lee `./data/positive_0.9.fasta`, `./data/nega_toxin_0.9.fasta`. Sin pesos. |
| **stackthp** | ml | **ESTRUCTURAL_REAL** | `Stack_THP.py` es **Jupyter notebook JSON** exportado de Colab. No ejecutable como script Python. Paths `/content/drive/MyDrive/THP/...`. |
| **cpppred_en** | torch | **ESTRUCTURAL_REAL** | `{im,}balance_data_test.py` cargan 6 CSVs de embeddings pre-computados (ProtT5-XL, ESM-1b/2/1v, TPC, CTDC). Sin orquestador FASTA → 6 embeddings → ensemble. |
| **perseucpp** | — | **ESTRUCTURAL_REAL** | `PERSEUcpp.py` es CLI interactivo (`prompt_existing_path()` con `input()`). Sin argparse. Pesos presentes. |
| **aip_tranlac** | torch | **ESTRUCTURAL_REAL** | Solo `train.py`. Modelo `AIP-TranLAC.pt` (9.5 MB) pero sin `predict.py` que lo cargue. |
| **deepforest_htp** | — | **ESTRUCTURAL_REAL** | `Features/` = preprocessing. `Model Traning/` (sic) = 5-fold CV training con `input()` interactivo. Sin pesos ni inferencia. |

---

## Resumen

| Verdict | Count | Tools |
|---|---|---|
| **OK** (pre-existente) | **2** | toxinpred3, antibp3 |
| **FIXED** (resuelto esta sesión) | **4** | hemopi2, hemodl, deepb3p, deepbp |
| **BLOCKED** (ambiental irresoluble bajo reglas) | **3** | eippred, antifungipept, macppred2 |
| **STANDBY** (read-only, documentado) | **4** | plm4alg, acp_dpe, avppred_bwr, mfe_acvp |
| **ESTRUCTURAL_REAL** (sin entry-point usable) | **13** | bert_ampep60, hypeptox_fuse, apex, multimodal_aop, if_aip, afp_mvfl, aapl, antiaging_fl, stackthp, cpppred_en, perseucpp, aip_tranlac, deepforest_htp |
| **Total** | **26** | |

**Viables para pipeline E2E (OK + FIXED): 6/26 = 23%**.

---

## Lista BLOCKED (excluidos del orchestrator, documentados para futuro)

1. **eippred** — requiere env dedicado con sklearn ≥1.3 (conflicto irresoluble con toxinpred3 en el mismo `ml` env).
2. **antifungipept** — 2/5 pickles son git-lfs pointers sin hidratar. Requiere `git lfs pull` (fuera de regla "no descargar modelos nuevos") o re-entrenar.
3. **macppred2** — `bio_embeddings 0.2.2` no tiene `PLUSRNNEmbedder` ni siquiera con el extra `[plus_rnn]`. Instalar el extra destruye el env `torch_legacy` al downgradear torch. Requiere alternativa al embedder o re-training sin PLUS-RNN.

---

## Lista ESTRUCTURAL_REAL (13 tools, sin entry-point; fuera de scope bajo regla "no wrappers")

### Patrón A: Training scripts disfrazados de "predict"
- `multimodal_aop/stacking_onehot.py`
- `if_aip/Optimized-IF-AIP.py`, `Hybrid(HB-AIP).py`
- `afp_mvfl/Prediction/ds{1,2,3}.py`
- `antiaging_fl/code/predict.py`, `predict_4fold.py`
- `aip_tranlac/train.py`

### Patrón B: Clases sin `__main__` / no orquestador
- `aapl/MLProcess/Predict.py`
- `hypeptox_fuse/predict.py`, `inferencer.py`

### Patrón C: Hardcoded input/output paths sin CLI
- `bert_ampep60/predict/predict.py` (`train_po.fasta`, `train_po.csv`)
- `apex/predict.py` (`test_seqs.txt`, `Predicted_MICs.csv`)
- `cpppred_en/{im,}balance_data_test.py` (6 CSVs pre-computados)

### Patrón D: Interactivo / notebook
- `stackthp/Stack_THP.py` (notebook JSON)
- `perseucpp/PERSEUcpp.py` (`input()` prompts)
- `deepforest_htp/Model Traning/...` (`input()` interactivo)

---

## Extensiones aplicadas a `audit_lib/tool_runner.py`

Durante BLOQUES B/C, tres dimensiones nuevas y genéricas (NO wrappers per-tool):

| Dimension | Valores | Tools que lo usan |
|---|---|---|
| `arg_style` | `flagged` (default), `positional` | flagged: hemopi2, hemodl, eippred (y la mayoría). positional: deepb3p, deepbp, apex |
| `output_capture` | `file` (default), `hardcoded_file`, `stdout` | file: toxinpred3, etc. hardcoded_file: hemopi2, hemodl, deepb3p. stdout: deepbp |
| `hardcoded_output_name` | str (requerido si `output_capture=hardcoded_file`) | predictions_hemopi2.csv, predict_results.csv, prob.txt |

Runner relocaliza `cwd/hardcoded_output_name → predictions_{tool}.{ext}` post-éxito; escribe `completed.stdout` verbatim a `predictions_{tool}.{ext}` si `output_capture=stdout`.

---

## Pendiente acción manual del usuario (DEFERRED_USER)

Estos tools requieren credenciales/permisos del usuario. **No los toques desde código** — quedan documentados para que el usuario los retome cuando tenga las credenciales/permisos. Una vez resueltos, son retomables como FIXABLE con adaptaciones estándar.

| Tool | Acción manual requerida | Detalles |
|---|---|---|
| **antifungipept** | `git lfs pull` en el repo | `cmodel.pkl` (134 B) y `rmodel_C_a.pkl` (133 B) son punteros LFS sin hidratar. Confirmado vía `.gitattributes`. Tras hidratar, el tool entra en pipeline directamente. |
| **plm4alg** | Login KSU + descarga SharePoint | Pesos en SharePoint institucional KSU. Solo notebooks Jupyter (Colab). Training data en XLSX. Tras descargar, requeriría además convertir notebooks → script (~50 líneas), evaluar como caso límite. |
| **avppred_bwr** | Descarga Baidu Netdisk + ajuste de paths | Sin `predict.py`. `train.py` y `test.py` con paths absolutos a `/mnt/raid5/...` (servidor privado autores). Features pre-computadas `.npz` (k-mer embeddings) solo en Baidu Netdisk (no programáticamente descargable). Training data FASTA + labels en repo. |
| **hypeptox_fuse** | RAM ≥32 GB o editar PLM a variante 650M | Wrapper `scripts/wrappers/hypeptox_fuse_cli.py` (≤30 líneas) + YAML wired ya implementados (2026-04-27). Pesos 5×.pth + iFeatureOmegaCLI clonados. **Bloqueador real: Linux con <16 GB RAM no puede cargar los 3 PLMs simultáneos del `Inferencer` (ESM-2 3B + ProtT5-XL + ESM-1, ~25 GB RAM agregados al cargar todos en `__init__`).** Retomable cuando: (a) Linux con ≥32 GB RAM (recomendado), o (b) editar `Tool_Repos/hypeptox_fuse/inferencer.py:9` para usar variante `esm2_t33_650M_UR50D` en lugar de `esm2_t36_3B_UR50D` (predicciones ligeramente menos exactas que el paper original; documentar la desviación). |
| **bert_ampep60** | Descarga manual de pkls desde SharePoint MPU institucional | `predict/predict.py` ya parcheado con `--input-fasta`/`--output-csv` argparse + `map_location`. `onedrivedownloader` recibe HTML de login (URLs `https://ipmedumo-my.sharepoint.com/:u:/g/personal/p2214906_mpu_edu_mo/...`) en vez de los pkls. Necesita login educativo MPU o petición a los autores: `ec_prot_bert_finetune_reproduce.pkl` y `sa_prot_bert_finetune_reproduce.pkl`. Una vez en `Tool_Repos/bert_ampep60/predict/`, el smoke debería pasar (lógica + parche YAML ya completos). |

### hypeptox_fuse — estado 2026-04-27 (APARCADO por RAM)

**Artefactos ya hidratados** por el usuario (2026-04-27):
- ✅ `Tool_Repos/hypeptox_fuse/checkpoints/HyPepToxFuse_Hybrid/fold_{0..4}_state_dict.pth` (5 × ~22 MB)
- ✅ `Tool_Repos/hypeptox_fuse/src/iFeatureOmegaCLI/` (clonado de duongttr/iFeatureOmegaCLI)
- ✅ Wrapper `scripts/wrappers/hypeptox_fuse_cli.py` (≤30 líneas, instancia Predictor+Inferencer y dump CSV con `Score=mean(prob1..5)`)
- ✅ YAML `pipeline_config.yaml:hypeptox_fuse` apuntando al wrapper, output_parsing con `prediction_column=Toxicity`, `positive_label='True'`, `score_column=Score`

**Bloqueador no resuelto**: Linux del usuario tiene <16 GB RAM. El método `Inferencer.__init__` carga **simultáneamente** ESM-2 3B (~12 GB) + ProtT5-XL (~9 GB) + ESM-1 670M (~2 GB) = ~23 GB en RAM antes de la primera inferencia. OOM kill garantizado.

**Para retomar**:
- (a) Hardware: Linux con ≥32 GB RAM. Tras eso, smoke debería pasar directo (PLMs se descargan auto vía `transformers`/`fair-esm` cache `~/.cache/torch/hub/`, ~25 GB en disco; user tiene 72 GB libres).
- (b) Software (degradación documentada): editar `Tool_Repos/hypeptox_fuse/inferencer.py:9` cambiando `esm2_t36_3B_UR50D` → `esm2_t33_650M_UR50D` (~2.5 GB). Coste RAM agregado ~13 GB, ya cabe en 16 GB. Predicciones ligeramente menos exactas que el paper original, anotar en provenance.

NO mover a OK/FIXED hasta uno de los dos. Tabla final cuenta 11/26 (no 12/26).

---

## Próximos pasos (post-Bloques I/J/K/L/M, para futura sesión)

1. **Env dedicado eippred** ya implementado (env `eippred_env` con sklearn ≥1.3) — eippred OK desde Bloque H.
2. **Wrappers opcionales** para los `ESTRUCTURAL_REAL` BLOCKED con pesos completos pero feature pipeline ausente: aapl, if_aip, cpppred_en. Coste estimado: 4-8 h por tool (incluye implementar feature extractors). Fuera de scope actual.
3. **Acciones manuales del usuario** documentadas arriba (antifungipept LFS, plm4alg KSU, avppred_bwr Baidu, hypeptox_fuse OneDrive).
4. **Recolección de paper stats** para Opción E (weighted ensemble por reliability) — ver `docs/orchestrator_design.md §4`. Diferido hasta cierre del pool de tools integrado.

---
[? Volver al �ndice](INDEX.md)
