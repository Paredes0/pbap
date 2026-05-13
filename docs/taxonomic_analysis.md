# Análisis de Sesgo Taxonómico

El pipeline evalúa si el rendimiento de las herramientas varía significativamente según el origen biológico, lo cual es crítico para la generalización en organismos no representados en el entrenamiento (ej. pulpo).

## Procesamiento y Estratificación

1.  **Minería y Linajes**: Los péptidos positivos mantienen su metadata taxonómica completa.
2.  **Grupos Amplios (BroadGroups)**: Clasificación cruzada en 4 categorías:
    - `Vert_Terrestre` / `Vert_Marino`
    - `Invert_Terrestre` / `Invert_Marino` (Crucial para péptidos de cefalópodos).
3.  **Filtrado Gold-Standard**: El análisis por defecto solo usa péptidos **Gold**. Esto evita que el rendimiento inflado por secuencias ya "vistas" oculte fallos en taxones específicos.

## Rigor Estadístico

El script `taxonomic_bias_analysis.py` implementa pruebas robustas para validar los hallazgos:

- **Test Exacto de Fisher**: Compara cada grupo contra el resto para detectar desviaciones en la sensibilidad.
- **Correcciones Múltiples**: Implementa **Benjamini-Hochberg (FDR)** y Bonferroni para evitar falsos positivos al testear muchos taxones.
- **Wilson Score Interval**: Intervalos de confianza al 95% para la sensibilidad que son precisos incluso con tamaños de muestra (N) pequeños.
- **Heterogeneidad (Chi-cuadrado)**: Una prueba global de χ² para determinar si existe una diferencia significativa en la distribución de predicciones correctas a través de todos los grupos.

## Detección de Sesgo (Interpretación)
- **LOW_POWER**: Grupos con **n < 10** se marcan como bajo poder estadístico.
- **Interpretación para Pulpo**: Se analiza específicamente el grupo `Invert_Marino`. Si su sensibilidad es significativamente inferior a la media de otros grupos (p-adj < 0.05), se documenta como un fallo de generalización de la herramienta.

## Uso del Script

```bash
python taxonomic_bias_analysis.py --tool <ID> --grades Gold --output-dir <DIR>
```

El reporte final incluye gráficos de barras comparativos por taxón, permitiendo visualizar rápidamente flaquezas de la herramienta en nichos biológicos específicos.

---
[? Volver al �ndice](INDEX.md)
