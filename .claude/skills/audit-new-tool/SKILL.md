---
name: audit-new-tool
description: Playbook para auditar una nueva herramienta de predicción de bioactividad contra el pipeline. Ejecuta las 6 fases (extract training → leakage → negatives → predict → validate → global report) comprobando condiciones previas. Úsalo cuando el usuario diga "audita X", "correr el pipeline para X", "añadir el tool Y al audit", o cuando haya que replicar el flujo E2E con una herramienta nueva.
---

# Playbook: Auditar una herramienta

## 0. Condiciones previas

Comprueba en este orden antes de ejecutar nada:

1. El tool existe en `config/pipeline_config.yaml` → `Grep pattern="^  {tool_id}:"`.
2. Repo del tool clonado bajo `Dataset_Bioactividad/Tool_Repos/{tool_id}/` o con URL en el YAML.
3. El `category` del tool (p.ej. `toxicity`) tiene pool en `Dataset_Bioactividad/Category_Pools/{category}_pool.fasta`. Si no → corre Fase 1 primero.

Si falta algo, **para y reporta** antes de continuar.

## 1. Extracción de training data

```
scripts/extract_training_data.py --tool {tool_id} --config config/pipeline_config.yaml --output-dir Dataset_Bioactividad/Tool_Audits/{tool_id}/training_data
```

Si devuelve `STANDBY_REPORT.json` → parar, informar al usuario, pedir paths manuales.

## 2. Análisis de leakage (CD-HIT-2D)

```
scripts/cdhit_leakage_analysis.py --tool {tool_id} --config ... --test-fasta {pool.fasta} --training-fasta {training.fasta} --output-dir .../leakage_report
```

Ejecuta SSH dispatch automáticamente si estás en Windows. Verifica en el JSON:
- `summary.grades.Gold` > 0
- `summary.length_status_counts.within_range` > 0

Si Gold within_range < 30, avisa: "n insuficiente para significancia estadística".

## 3. Generación de negativos

```
scripts/generate_category_negatives.py --tool {tool_id} --config ... --categories-config ... --positives-csv {pool}.csv --output-dir .../test_negatives
```

Matchea distribución natural de longitudes de los positivos (KDE). Ratio 1:1.

## 4. Predicción del tool

```
scripts/run_tool_prediction.py --tool {tool_id} --config ... --output-dir .../predictions
```

Activa el `conda_env` del tool y ejecuta en local o vía SSH según `target_pc`. Genera `grade_metrics_{tool}.json` con métricas per-grade.

## 5. Auditoría per-tool

```
scripts/auditoria_validation.py --tool {tool_id} --config ... --output-dir .../
```

Fisher exact + BH + sesgo taxonómico.

## 6. Reporte global

```
scripts/final_audit_report.py --config ... --output-dir Dataset_Bioactividad/Global_Audit
```

Itera todos los `audit_report.json` y genera XLSX agregado.

## Checklist final a reportar al usuario

- Pool positivos: {n} secuencias, {k} Gold within_range
- Leakage bias (Red MCC − Gold MCC): {value}
- Puntos ciegos taxonómicos (Gold sens < 0.3): lista de grupos
- Quality warnings del reporte global

## Patrón de invocación Python (SSHFS + audit_lib)

```python
python -c "
import sys; sys.path.insert(0,'Z:/work/pipeline_Work/pipeline_Work')
sys.argv=['<script>','--tool','{tool_id}', ...]
exec(open('Z:/work/pipeline_Work/pipeline_Work/scripts/<script>').read())
"
```

Ver `docs/INDEX_LOOKUP.md` para paths completos de inputs/outputs.
