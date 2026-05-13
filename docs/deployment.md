# Despliegue y Configuracion del Pipeline

Este documento detalla la configuracion del sistema, el inventario de dependencias y el estado actual de los entornos de ejecucion para el pipeline de bioactividad.

## 1. Configuracion del Sistema

El sistema opera bajo un modelo de **ejecucion local**. El orquestador gestiona la activacion de entornos Micromamba especificos para cada herramienta, garantizando que cada una se ejecute en su stack tecnologico verificado.

### Archivos de Configuracion

#### 1. `config/pipeline_config.yaml`
Define los parametros globales y el catalogo de herramientas.
- `global`: Semillas, rangos de longitud por defecto, umbrales de CD-HIT.
- `ssh`: Configuracion de acceso al servidor Linux. **Importante**: En la arquitectura actual, la ejecucion via SSH se reserva **exclusivamente para el proceso de CD-HIT** (eliminacion de redundancia). Todas las herramientas de prediccion se ejecutan localmente en la maquina host.
- `tools`: Catalogo de herramientas. Cada herramienta tiene asignado un `conda_env` que el orquestador activa antes de la ejecucion.

#### 2. `config/categories_config.yaml`
Define las bioactividades auditadas y las consultas UniProt para la construccion de pools positivos.

---

## 2. Inventario de Dependencias (Technical Mapping)

Este inventario mapea los requisitos tecnicos identificados para cada herramienta. Debido a las incompatibilidades severas entre librerias (ej. numpy 2.0 vs versiones antiguas de tensorflow), el sistema utiliza una estrategia de aislamiento por entornos.

| # | tool_id | Env / Stack | Python | Principales Librerías |
|---|---|---|---|---|
| 1 | **toxinpred3** | `ml` | 3.10+ | sklearn 1.0.2, blastp |
| 2 | **hemodl** | `ml` | 3.8 | tensorflow 2.13, lightgbm 4.0.0 |
| 3 | **hemopi2** | `torch` | 3.10+ | torch 2.x, esm, transformers |
| 4 | **plm4alg** | `torch_legacy`| -- | (Standby) Jupyter-based |
| 5 | **bert_ampep60** | `torch` | 3.10+ | torch 2.x, transformers |
| 6 | **apex** | `qsar` | 3.10+ | rdkit, torch 2.x |
| 7 | **antibp3** | `ml` | 3.10+ | sklearn, blastp (Linux) |
| 8 | **deepbp** | `torch_legacy`| 3.7/3.8 | keras, tensorflow (legacy) |
| 9 | **acp_dpe** | `torch_legacy`| 3.7/3.8 | torch 1.x, keras |
| 10 | **avppred_bwr** | `torch` | -- | (Standby) No inference script |
| 11 | **bertaip** | `pipeline_bertaip`| 3.10+ | simpletransformers, transformers |
| 12 | **antifungipept**| `ml_legacy_py38` | 3.8 | sklearn, numpy old |
| 13 | **deepb3p** | `deepb3p_legacy` | 3.7 | tensorflow 1.14.0, rdkit |
| 14 | **perseucpp** | `torch` | 3.10+ | torch 2.x, sklearn |

---

## 3. Estado de Herramientas Auditadas

| Tool ID | Categoria | Estado | Notas |
| :--- | :--- | :--- | :--- |
| `toxinpred3` | Toxicity | Active | Ejecucion local en env `ml`. |
| `hemodl` | Hemolytic | Active | Modelo basado en ESM-2 + ProtT5. |
| `hemopi2` | Hemolytic | Active | Modo `-m 3` (ESM2 solo). |
| `bert_ampep60` | Antimicrobial | Active | Regresión multi-target (E. coli, S. aureus). |
| `apex` | Antimicrobial | Active | 34 cepas. Ejecucion local en env `qsar`. |
| `antibp3` | Antimicrobial | Active | Modelos sklearn + blastp. Solo Linux. |
| `deepbp` | Anticancer | Active | Basado en ESM-2 (Meta). |
| `acp_dpe` | Anticancer | Active | Ensemble CNN/GRU (Patched). |
| `bertaip` | Anti-inflammatory | Active | Sustituye a aip_tranlac. BERT-based. |
| `antifungipept` | Antifungal | Active | Ejecución en `ml_legacy_py38`. |
| `deepb3p` | BBB | Active | Python 3.7 + TF 1.14 (Legacy). |
| `perseucpp` | CPP | Active | Clasificación 2-stage (CPP + Eficiencia). |
| `plm4alg` | Allergenicity | Standby | Basado en Jupyter/Colab. Requiere refactorización. |
| `avppred_bwr` | Antiviral | Standby | Falta script de inferencia y pesos accesibles. |

### 3.1 Herramientas Bloqueadas e Inactivas (`config/pipeline_config_blocked.yaml`)

Estas herramientas han sido descartadas o movidas a un estado inactivo tras la auditoría de viabilidad (`docs/pipeline_viability.md`).

| Tool ID | Categoria | Estado | Razón del Bloqueo / Inactividad |
| :--- | :--- | :--- | :--- |
| `aapl` | Anti-angiogenic | **Blocked** | Fallos estructurales o dependencia externa. |
| `if_aip` | Anti-inflammatory | **Blocked** | Fallos estructurales o dependencia externa. |
| `mfe_acvp` | Antiviral | **Blocked** | Requiere servicios web externos (ESMAtlas, NetSurfP-3.0). |
| `multimodal_aop` | Antioxidant | **Blocked** | Fallos estructurales o dependencia externa. |
| `afp_mvfl` | Antifungal | **Blocked** | Fallos estructurales o dependencia externa. |
| `antiaging_fl` | Anti-aging | **Blocked** | Fallos estructurales o dependencia externa. |
| `deepforest_htp` | Hypotensive | **Blocked** | Fallos estructurales o dependencia externa. |
| `stackthp` | Tumor-homing | **Blocked** | Fallos estructurales o dependencia externa. |
| `cpppred_en` | CPP | **Blocked** | Fallos estructurales o dependencia externa. |
| `macppred2` | Anticancer | **Blocked** | Fallos estructurales o dependencia externa. |
| `_aip_tranlac_backup` | Anti-inflammatory | **Inactive** | Reemplazado por `bertaip`. |
| `hypeptox_fuse` | Toxicity | **Inactive** | Consumo excesivo de RAM (>= 32GB). |

---

## 4. Inventario Real de Entornos Micromamba

Para garantizar la reproducibilidad y evitar conflictos de dependencias, se mantienen los siguientes entornos reales en el sistema:

- **deepb3p_legacy**: Especifico para DeepB3P (Python 3.7, TensorFlow 1.14).
- **ml**: Entorno general para herramientas basadas en Machine Learning clasico (sklearn, xgboost, etc.).
- **ml_deepforest**: Entorno para DeepForest-HTP (especifico para librerias CascadeForest).
- **ml_legacy_py38**: Para herramientas que requieren Python 3.8 y versiones antiguas.
- **ml_pycaret**: Entorno dedicado a herramientas que dependen de la API de PyCaret.
- **pipeline_bertaip**: Entorno especifico para BertAIP para evitar conflictos con otras implementaciones de Transformers.
- **qsar**: Entorno con RDKit y herramientas de quimioinformatica/descriptores.
- **torch**: Entorno principal con PyTorch y Transformers modernos.
- **torch_legacy**: Para herramientas PyTorch con dependencias heredadas (ej. CUDA antiguo).

**Aislamiento de Conflictos**: Se mantienen entornos especificos (como `pipeline_bertaip`) de forma independiente para prevenir colisiones de versiones.

---

## 5. Limitaciones y Operacion

### Ejecucion
- **Local vs SSH**: El 100% de la logica de prediccion de las herramientas es **local**. No se utiliza despacho a otros PCs.
- **CD-HIT**: Es el unico componente que utiliza **SSH** para realizar el filtrado de redundancia en un nodo Linux.

### Memoria y Recursos
- El orquestador usa `--batch-size` para gestionar el consumo de RAM/VRAM.

---

## 6. Guia de Ejecucion Rapida

### Prediccion de Usuario
```bash
python scripts/run_audit.py --input Inputs/mis_peptidos.fasta --name experimento_1
```

### Auditoria Cientifica
```bash
./bin/audit_pipeline.sh --tool toxinpred3
```

---
[<- Volver al Indice](INDEX.md)
