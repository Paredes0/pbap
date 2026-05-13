# Análisis de Leakage (CD-HIT-2D)

El corazón de la validación es el análisis de similitud entre el pool de prueba independiente y los datos de entrenamiento de cada herramienta.

## Metodología

Utilizamos `cd-hit-2d` para comparar nuestro pool contra el dataset de entrenamiento en tres umbrales de identidad de secuencia decrecientes: **80%, 60% y 40%**.

### Sistema de Graduación de Confianza

Cada péptido de nuestro pool recibe una etiqueta según su "supervivencia" al filtro de CD-HIT:

| Etiqueta | Condición de Supervivencia | Interpretación Científica |
| :--- | :--- | :--- |
| **Gold** | Sobrevive a 80%, 60% y 40% | **Confianza Máxima**: Secuencia totalmente nueva (<40% identidad). |
| **Silver** | Sobrevive a 80% y 60%, muere a 40% | **Confianza Alta**: Similaridad remota (40-60%) con el entrenamiento. |
| **Bronze** | Sobrevive a 80%, muere a 60% | **Confianza Media**: Similaridad moderada (60-80%). |
| **Red** | Muere al 80% | **Leakage Probable**: Alta identidad (>80%) o duplicado. |

## Análisis de Longitud (Robust Mode)

El script `cdhit_leakage_analysis.py` evalúa si los péptidos de prueba están dentro del rango operativo de la herramienta:

- **Robust Mode**: A diferencia de un rango simple min/max, el modo robusto calcula el rango basándose en la distribución real del entrenamiento para evitar que péptidos "outliers" contaminen la validez estadística.
- **Tagueo**: Cada péptido se marca como `within_range`, `too_short` o `too_long`.
- El análisis de benchmark posterior (FDR, Sensibilidad) se puede filtrar para considerar solo péptidos **Gold + within_range**, eliminando así el ruido por leakage y por longitudes no soportadas.

## Ejecución Técnica

El análisis se realiza mediante:
```bash
python cdhit_leakage_analysis.py --tool <ID> --test-fasta <POOL> --training-fasta <TRAIN>
```
Este script genera un archivo `leakage_<TOOL>_classifications.csv` que sirve de base para todos los cálculos estadísticos posteriores.

---
[? Volver al �ndice](INDEX.md)
