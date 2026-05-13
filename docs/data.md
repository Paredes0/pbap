---
description: Data structures — inputs, outputs, databases.
related: [architecture.md]
last_updated: 2026-05-08T11:15:00Z
---

# Data Reference

Este documento detalla las estructuras de datos utilizadas y generadas por el pipeline, así como las fuentes de datos externas.

## 📥 Estructura de Inputs

### Archivos FASTA (`Inputs/`)
El pipeline acepta archivos FASTA estándar ubicados en el directorio `Inputs/`. Se recomienda que los encabezados sigan un patrón simple para facilitar el seguimiento:

```text
>peptide_001
GIGAVLKVLTTGLPALISWIKRKRQQ
>peptide_002
GIGKFLHSAKKFGKAFVGEIMNS
```

- **Rango de Longitud**: Generalmente entre 5 y 100 aminoácidos (depende de la herramienta).
- **Aminoácidos**: Se esperan los 20 aminoácidos estándar. Secuencias con caracteres ambiguos (X, B, Z) pueden ser marcadas como inválidas por algunos parsers.

## 📤 Estructura de Outputs (`Outputs/`) (Fase 1)

Los resultados de cada ejecución se almacenan en la carpeta correspondiente dentro de `Outputs/`.

### 1. `consolidated.csv` / `consolidated.xlsx`
Es la matriz principal de resultados. Contiene una fila por cada péptido evaluado. El esquema real extraído por el orquestador es:

| Columna | Descripción |
|---|---|
| `structural_score` | Puntuación entera basada en el perfil de actividad por categoría (ej. suma de polaridades: POS=3, SPLIT=2, NEG=1, NONE=0 para categorías deseables). |
| `structural_max` | Puntuación estructural máxima posible según las categorías evaluadas. |
| `holistic_score` | Puntuación continua agregada utilizada para el ranking cuantitativo (desempate de la puntuación estructural). |
| `n_categories_evaluated` | Número de categorías evaluadas para el péptido. |
| `apex_potency_tag` | Etiqueta cualitativa de potencia (ej. `POTENTE_AMP`, `MUY_POTENTE_AMP`). |
| `apex_potency_min_mic_uM` | El MIC mínimo (en µM) observado en cualquier cepa por APEX. |
| `peptide_id` | Identificador del péptido (extraído del FASTA). |
| `sequence` | Secuencia de aminoácidos. |
| `length` | Longitud de la secuencia de aminoácidos. |
| `<tool>__class` | Clasificación binaria (`positive`, `negative`, o nulo si hubo error o no aplica). |
| `<tool>__score` | Score de probabilidad emitido por la herramienta (0.0 a 1.0). |
| `<tool>__<metric>__<unit>` | Métricas adicionales específicas de la herramienta (ej. `apex__mean_mic_pathogen__uM`). |
| `<category>__consensus` | Consenso inter-herramienta para una categoría (`POS`, `NEG`, `SPLIT`, `NONE`). |
| `<category>__mean_score` | Score promedio de las herramientas que aportaron a dicha categoría. |
| `agreement_<category>` | Nivel de acuerdo para la categoría (`consensus_positive`, `consensus_negative`, `split`, `single_tool`, `no_call`). |

### 2. `REPORT.md` / `REPORT.html`
Reporte interactivo y estático standalone. Incluye:
- Ranking jerárquico de viabilidad terapéutica.
- Resumen por péptido y matriz de resultados.
- Filtros dinámicos por longitud y scores (en HTML).
- Desglose de métricas APEX por cepa bacteriana.
- Badges de potencia (`MUY POTENTE`, `POTENTE`, `PATHOGEN SPECIFIC`).
- Detalles de disagreements intra-categoría y métricas continuas extra.

### 3. `tool_health_report.json`
Indica el estado y rendimiento de cada herramienta durante la ejecución:
- `status`: `OK` (ejecución y parsing exitosos) o `PROBLEMATIC` (fallo en lotes).
- `runtime_seconds`: Tiempo de ejecución de la herramienta.
- `n_batches_ok` / `n_batches_failed`: Detalle de ejecución por lotes.
- `diagnosis`: Diagnóstico de fallos específicos.

## 📏 Manejo de Longitud por Herramienta

Cada herramienta tiene un rango de longitud óptimo basado en su set de entrenamiento. El orquestador gestiona las secuencias fuera de rango según su comportamiento técnico:

| Tool | Rango Óptimo | Modo de Fallo | Evidencia Técnica |
|---|---|---|---|
| `acp_dpe` | `[5, 50]` | **`hard_limit`** | `Test.py:152` (Embedding fijo) |
| `apex` | `[5, 100]` | **`soft_truncate`** | `predict.py:44` (Trunca a 52) |
| `deepb3p` | `[2, 50]` | **`soft_truncate`** | `amino_acid.py:78` (Trunca a 50) |
| `toxinpred3`| `[1, 35]` | `soft_reliability` | Basado en training set |
| `hemodl` | `[2, 133]` | `soft_reliability` | Basado en training set |
| `hemopi2` | `[2, 100]` | `soft_reliability` | Basado en training set |

---

## 🔍 Grados de Leakage (Confianza Científica)

Para evitar resultados inflados por secuencias ya conocidas por los modelos, el pipeline clasifica los péptidos en 4 niveles de "novedad":

- **🟢 Gold (Novedad Alta)**: Secuencias que sobreviven a CD-HIT-2D al 40% de identidad contra el training set. Son las predicciones más fiables.
- **🟡 Silver (Novedad Media)**: Similitud entre 40% y 60%.
- **🟠 Bronze (Novedad Baja)**: Similitud entre 60% y 80%.
- **🔴 Red (Leaked/Conocido)**: Similitud >80%. El modelo probablemente ya "conoce" esta secuencia o una muy parecida, por lo que el score está sesgado.

---

## 🗄️ Bases de Datos de Referencia

El pipeline utiliza datos de las siguientes fuentes para construir los pools de evaluación y detectar leakage:

| DB | Contenido Principal |
|---|---|
| **UniProt** | Secuencias anotadas con bioactividad y origen taxonómico. |
| **DBAASP** | Péptidos antimicrobianos con datos experimentales de MIC. |
| **APD3** | Antimicrobial Peptide Database. |
| **ConoServer** | Toxinas de caracoles cono. |
| **ArachnoServer** | Toxinas de arañas. |

Los datos crudos de estas bases se procesan y almacenan en `DATABASES_FASTA/` y se consolidan en `Dataset_Bioactividad/Category_Pools/`.

---
[← Volver al Índice](INDEX.md)
