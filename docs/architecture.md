---
description: System architecture - components, dependencies, data flow.
related: [decisions.md, api.md]
last_updated: 2026-05-08T13:55:00Z
---

# Arquitectura del Sistema

## Descripcion General

El sistema es un ecosistema de auditoria y prediccion de bioactividad de peptidos que opera mediante una orquestacion en Python. Su arquitectura se basa en un **modelo de ejecucion local distribuido por entornos**, donde un orquestador central gestiona sub-procesos aislados.

---

## 1. Estructura de Directorios

```text
.
|-- bin/                            # Orquestadores de alto nivel
|   `-- audit_pipeline.sh          # Script maestro de auditoria cientifica (Fase 2)
|-- config/                         # Configuraciones YAML
|   |-- pipeline_config.yaml       # Configuracion de 26 herramientas, SSH y entornos
|   |-- categories_config.yaml     # Bioactividades, queries UniProt, polaridades
|   `-- apex_strain_classification.yaml  # Clasificacion de cepas APEX (pathogen/commensal)
|-- scripts/                        # Logica core del pipeline (Python)
|   |-- run_audit.py               # Orquestador E2E Fase 1 (Inferencia de Usuario)
|   |-- run_tool_prediction.py     # Ejecutor de benchmarking individual por tool
|   |-- cdhit_leakage_analysis.py  # Leakage analysis via CD-HIT-2D
|   |-- extract_training_data.py   # Extraccion de datos de entrenamiento desde repos
|   |-- mine_positives_per_bioactivity.py  # Mineria de positivos por categoria (UniProt + DBs)
|   |-- generate_category_negatives.py     # Generacion de negativos por tool
|   |-- auditoria_validation.py    # QC per-tool (stats, distribuciones, AA composition)
|   |-- taxonomic_bias_analysis.py # Sesgo taxonomico (Fisher, Wilson CI, BH-FDR)
|   `-- final_audit_report.py      # Reporte global cross-tool (JSON, TXT, XLSX)
|-- wrappers/                       # Adaptadores robustos para herramientas no estandar
|   `-- bert_ampep60_cli.py        # Wrapper CLI para BERT-AMPep60
|-- audit_lib/                      # Biblioteca compartida (12 modulos — ver api.md)
|   |-- config.py                  # Carga de YAML
|   |-- tool_runner.py             # Motor de ejecucion (micromamba run)
|   |-- tool_length_range.py       # Rangos de longitud por herramienta
|   |-- downloader.py              # Descarga de pesos (Zenodo, HuggingFace, manual)
|   |-- cdhit_utils.py             # CD-HIT con SSH dispatch
|   |-- uniprot_client.py          # Cliente UniProt REST
|   |-- sequence_utils.py          # Validacion y normalizacion de secuencias
|   |-- db_parsers.py              # Parsers para DBAASP, APD3, ConoServer, etc.
|   |-- length_sampling.py         # Muestreo estratificado por longitud
|   |-- state_manager.py           # Estado incremental de auditoria
|   |-- provenance.py              # Metadatos de trazabilidad JSON
|   `-- logging_setup.py           # Configuracion estandar de logging
|-- Inputs/                         # Archivos FASTA de entrada para usuarios
|-- Outputs/                        # Resultados de predicciones (HTML, XLSX, CSV, JSON)
`-- Dataset_Bioactividad/           # Salidas del pipeline Fase 2 (Pools, Audits, Reports)
```

---

## 2. Componentes Principales

### 1. Orquestador E2E — Fase 1 (`scripts/run_audit.py`)
Punto de entrada principal para el usuario. Gestiona el ciclo de vida completo de una prediccion:
- **Batching**: Fragmenta el FASTA de entrada para evitar errores de memoria.
- **Normalizacion**: Consolida resultados de herramientas heterogeneas en un esquema comun.
- **Ranking**: Calcula `structural_score` + `holistic_score` para priorizar peptidos.
- **Reportes**: Genera HTML interactivo, XLSX con formatting, CSV, JSON y Markdown.

### 2. Orquestador de Auditoria — Fase 2 (`bin/audit_pipeline.sh`)
Script maestro Bash que ejecuta la auditoria cientifica completa por herramienta:
1. **Mining de positivos** (`mine_positives_per_bioactivity.py`)
2. **Extraccion de training** (`extract_training_data.py`)
3. **Leakage analysis** (`cdhit_leakage_analysis.py`)
4. **Generacion de negativos** (`generate_category_negatives.py`)
5. **Prediccion y benchmarking** (`run_tool_prediction.py`)
6. **Sesgo taxonomico** (`taxonomic_bias_analysis.py`)
7. **QC per-tool** (`auditoria_validation.py`)
8. **Reporte global** (`final_audit_report.py`)

### 3. Motor de Ejecucion (`audit_lib/tool_runner.py`)
Abstrae la invocacion de herramientas externas:
- **Micromamba Run**: Ejecuta los scripts de las herramientas dentro de sus entornos especificos (`torch`, `ml`, `pipeline_bertaip`, etc.) de forma local.
- **Captura de Salida**: Traduce logs y archivos CSV/txt de las herramientas al formato interno.
- **Retorno**: Objeto `ToolResult` con `tool_id`, `output_path`, `exit_code`, `runtime`, `diagnosis`.

### 4. Utilidades de Bioinformatica (`audit_lib/`)
- **`cdhit_utils.py`**: Gestiona el analisis de redundancia. Es el **unico componente con capacidad de despacho SSH**. Permite ejecutar CD-HIT en un servidor Linux remoto si el orquestador principal corre en Windows.
- **`uniprot_client.py`**: Cliente para mineria de datos en UniProt con paginacion, reintentos y checkpointing.
- **`db_parsers.py`**: 9 parsers para bases de datos externas (DBAASP, APD3, ConoServer, ArachnoServer, Hemolytik, CancerPPD, CPPsite, BIOPEP, AVPdb).
- **`downloader.py`**: Gestion de descarga de pesos de modelos desde Zenodo, HuggingFace o plataformas con descarga manual.
- **`tool_length_range.py`**: Inferencia de rangos de longitud optimos por herramienta a partir de datos de entrenamiento.

> Referencia de API completa con firmas: ver [`api.md`](api.md).

---

## 3. Flujo de Datos y Ejecucion

### Modelo de Ejecucion Local
A diferencia de versiones preliminares, el sistema actual **no realiza despacho generalizado** de procesos. Todas las herramientas de prediccion se ejecutan en la misma maquina donde reside el orquestador. El aislamiento se logra mediante **Conda/Micromamba**, no mediante hardware separado.

### Excepcion: Satelite SSH (CD-HIT)
Debido a la intensidad computacional del filtrado de redundancia y la dependencia de binarios Linux nativos, el modulo de CD-HIT puede configurarse para:
1.  **Ejecucion Local**: Si el host es Linux y tiene `cd-hit` instalado.
2.  **Despacho SSH**: Si el host es Windows, el orquestador sube los archivos temporalmente a un servidor Linux via SSH, ejecuta el comando y descarga los resultados.

---

## 4. Dependencias Criticas

- **Micromamba**: Gestor de entornos ultra-rapido para el aislamiento de herramientas.
- **Python Stack**: pandas, numpy, scipy, pyyaml, openpyxl, requests.
- **CD-HIT**: Binario externo para analisis de leakage y redundancia.

---
[<- Volver al Indice](INDEX.md)
