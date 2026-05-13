# Contexto y Objetivo del Proyecto

## Motivación
En el campo de la bioinformática de péptidos, muchas herramientas de predicción publicadas en la literatura científica reportan métricas de rendimiento (Exactitud, MCC, AUC) extremadamente altas. Sin embargo, estas métricas a menudo están infladas debido a:

1.  **Data Leakage (Fuga de datos)**: Los benchmarks utilizados para validar la herramienta contienen secuencias que son idénticas o muy similares a las usadas durante el entrenamiento.
2.  **Sesgo Taxonómico**: La herramienta puede funcionar muy bien para péptidos de ciertos taxones (ej. bacterias) pero fallar en otros, lo que limita su utilidad clínica o biotecnológica general.
3.  **Sobreajuste a Longitudes**: Las herramientas pueden estar optimizadas para un rango de longitud muy estrecho.

## Objetivos
El objetivo principal de este pipeline es realizar un **auditoría externa independiente** de estas herramientas para:

- **Cuantificar el Leakage**: Usar CD-HIT-2D para ver cuántas secuencias del "mundo real" ya han sido vistas por el modelo.
- **Evaluar Robustez**: Determinar si la predicción es consistente a través de diferentes grupos taxonómicos.
- **Establecer Niveles de Confianza**: Etiquetar los resultados de predicción según su cercanía a los datos de entrenamiento (Sistema Gold/Silver/Bronze/Red).
- **Proveer un Dataset Independiente**: Construir un pool de péptidos positivos y negativos que no haya sido influenciado por los sesgos de los autores originales.

## Tipos de Sesgos Analizados

### 1. Sesgo por Similitud de Secuencia
Se analiza mediante `cd-hit-2d`, comparando nuestro dataset independiente contra el dataset de entrenamiento extraído de los repositorios de las herramientas.

### 2. Sesgo Taxonómico
Se analiza comparando las métricas de predicción (Sensibilidad, Falsos Positivos) entre diferentes orígenes taxonómicos (Animalia, Plantae, Fungi, Bacteria, etc.) para asegurar que la herramienta no dependa de una firma taxonómica específica.

---
[? Volver al �ndice](INDEX.md)
