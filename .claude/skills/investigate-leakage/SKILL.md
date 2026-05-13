---
name: investigate-leakage
description: Diagnóstico estratificado del leakage y sesgos de una herramienta. Cruza Grade × Length_Status × Taxonomic_Group × Source_DB, detecta inflación Red-vs-Gold, puntos ciegos taxonómicos, y contamina con metadata del pool. Úsalo cuando el usuario pregunte "qué significan estos resultados", "por qué Gold tiene sens baja", "compara por taxón", "qué péptidos están en training", o cuando haya que interpretar métricas post-predicción.
---

# Playbook: Investigación estratificada de resultados

## Inputs necesarios (localizar con Glob, no leer enteros)

- `Dataset_Bioactividad/Tool_Audits/{tool}/predictions/predictions_{tool}.csv`
- `Dataset_Bioactividad/Tool_Audits/{tool}/predictions/ground_truth_{tool}.csv`
- `Dataset_Bioactividad/Tool_Audits/{tool}/leakage_report/leakage_{tool}_classifications.csv` (Grade + Length_Status)
- `Dataset_Bioactividad/Category_Pools/{category}_pool.csv` (Taxonomic_Group, Habitat, Source_DB)

## Análisis obligatorio

1. **Global**: Acc, MCC, Sens, Spec.
2. **Por Grade** (negativos compartidos):
   - Tabla: Grade | n_pos | TP | FN | Sens | Acc | MCC
   - **Ojo al artefacto**: MCC baja en grades con pocos positivos aunque sens sea alta, porque los FP compartidos pesan más. Reportar **precision per grade** junto al MCC.
3. **Por Length_Status**: within_range vs too_long (too_short suele ser n=0 o 1).
4. **Grade × Length_Status** (crítico): ¿Gold within_range tiene n suficiente? si n<30 → avisar insuficiencia estadística.
5. **Gold por taxón**: identificar grupos con sens < 0.3 → puntos ciegos.
6. **Red por taxón**: si sens es ~1.0 en todos, confirma leakage sistemático.
7. **Habitat × Grade**: ¿el tool solo funciona en un hábitat (p.ej. marino)?
8. **Source_DB × Grade**: ¿UniProt, ConoServer y ArachnoServer producen métricas distintas? si sí, sesgo de fuente.

## Leakage bias

Reportar siempre: **bias = MCC_Red − MCC_Gold**. Si bias > 0.2 → inflación significativa.

## Para detectar matches exactos con training

```
Dataset_Bioactividad/Tool_Audits/{tool}/training_data/training_{tool}.fasta
```

Cargar como set, intersectar con pool por secuencia. Reportar n_exact_matches y breakdown por Source_DB.

## Para detectar near-duplicates dentro del pool (si no se hizo dedup)

Ejecutar CD-HIT intra-set 95% vía SSH:
```
ssh <user>@<host> "/path/to/cd-hit -i <pool.fasta> -o <out> -c 0.95 -n 5 -l 4 -M 0 -T 4 -d 0"
```
Parsear `.clstr` → clusters de tamaño >1 son near-duplicates.

## Interpretación estándar (plantilla)

> El tool muestra MCC_Red=X vs MCC_Gold=Y (bias +Z). Esto indica {inflación/fidelidad real}. En sus secuencias de diseño (length within_range) y novel (Gold), la sensibilidad real es {value} (n={n}). Los puntos ciegos son: {lista de taxones con sens<0.3}.

Siempre distinguir claramente:
- **Gold = novel** (sobrevivió CD-HIT-2D, NO parecido a training)
- **Red = leaked** (filtrado por CD-HIT-2D, similar a training)

## Cross-reference

Decisiones metodológicas en `docs/decisions.md`.
Outputs del análisis siempre van a `Dataset_Bioactividad/Tool_Audits/{tool}/` o a `Global_Audit/`.
