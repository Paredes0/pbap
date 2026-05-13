---
description: Project-specific patterns and idioms — finer-grained que AGENTS.md.
related: [/AGENTS.md]
last_updated: 2026-05-08T10:45:00Z
---

# Conventions

Este documento detalla las convenciones de nomenclatura, organización de archivos y disciplina de desarrollo seguidas en este proyecto.

## 1. Nomenclatura

### Herramientas (Tools)
- **Identificadores**: Siempre en minúsculas y sin guiones (ej. `toxinpred3`, `hemopi2`, `hemodl`).
- **Directorios de Repos**: Ubicados en `Dataset_Bioactividad/Tool_Repos/<tool_id>/`.

### Columnas de Datos (Matrix)
- **Eje Binario**: Se normaliza a `class_norm` (0 o 1) y `score` (0.0 a 1.0).
- **Eje Extra**: Las métricas adicionales siguen el patrón `<tool_id>__<metrica>__<unidad>` (ej. `apex__mic_staph_aureus__uM`).
- **Diferenciación**: Misma magnitud + target + unidad → misma columna; cualquier diferencia → columna separada.

## 2. Organización de Archivos

### Inputs y Outputs
- **Inputs**: Los FASTAs de entrada se colocan en `Inputs/`.
- **Outputs**: El orchestrator crea una subcarpeta por ejecución: `Outputs/<input_stem>_<YYYY-MM-DDTHHMM>/`.
- **Colisión de Nombres**: Se añade un sufijo numérico (`_2`, `_3`) si el timestamp coincide.

### Documentación
- **Ubicación**: Toda la documentación canónica reside en `docs/`.
- **Archivo**: Los documentos obsoletos se mueven a `docs/_archive/YYYY-MM/`.
- **Índice**: `docs/INDEX_LOOKUP.md` sirve como tabla de saltos para localización rápida de funciones y archivos.

## 3. Disciplina de Desarrollo

### Actualización de Documentación (ex-Memoria)
Al finalizar una tarea que cambie el estado estable del proyecto, se debe actualizar el documento correspondiente:

| Tipo de Cambio | Documento a Actualizar |
|---|---|
| Nuevo umbral estadístico o heurística | `docs/decisions.md` |
| Bug fijado (lecciones aprendidas) | `docs/decisions.md` |
| Nuevo workaround de infraestructura/SSH | `docs/deployment.md` |
| Cambio arquitectural | `docs/architecture.md` |
| Nueva mejora planificada | `docs/roadmap.md` |

### 3.3. Lectura Eficiente de Código
Dada la extensión de algunos scripts (>500 líneas), se deben seguir estas reglas para ahorrar contexto:
- **Grep** → buscar literales, nombres de funciones o regex simples.
- **ast-grep (sg)** → buscar estructura sintáctica. Patrones útiles:
  - Llamadas a Fisher: `sg --lang python -p 'fisher_exact($$$)'`
  - Despacho SSH: `sg --lang python -p 'ssh_dispatch($$$)'`
  - Funciones con logs: `sg --lang python -p 'def $F($$$): $$$ log.debug($$$) $$$'`
- **Read** → Usar siempre con `offset` y `limit` (40-50 líneas) tras localizar el punto de interés.
- Evitar leer archivos completos salvo para refactorizaciones mayores.

## 4. Estándares de Código

### 4.1. Python
- **Versión**: Compatibilidad mínima con Python 3.8.
- **Indentación**: 4 espacios (PEP 8).
- **Docstrings**: Estilo Google. Todo módulo y función pública debe documentar parámetros y retorno.
- **Gestión de Errores**: Uso de `try/except` con logging detallado. Evitar `print()` para debugging; usar `log.debug()`.
- **Logging**: Configuración estándar en cada script: `logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")`.

### 4.2. Shell Scripts (Bash)
- **Seguridad**: Todos los scripts deben comenzar con `set -euo pipefail`.
- **Robustez**: Localizar rutas base mediante `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.
- **Compatibilidad Windows**: Incluir helpers de conversión de rutas (ej. `to_win_path`) si el script interactúa con binarios de Windows desde entornos Bash.

### 4.3. Git y Commits
- **Idioma**: Mensajes de commit en **español**.
- **Estilo**: Libre pero enfocado en el impacto del cambio.
- **Ramas**: Prefijos estándar: `feat/`, `fix/`, `chore/`, `docs/`.
- **Permisos**: Nunca usar `git commit` o `git push` sin permiso explícito del usuario.

### 4.4. Encabezados de Archivo
Todos los scripts core deben incluir un encabezado estructurado:
```python
"""
nombre_script.py
================
Descripción breve de la funcionalidad.
Contexto de uso y dependencias clave.
"""
```

## 5. Auditoría de Herramientas Externas

No se debe asumir que un repositorio de terceros es funcional por defecto. Antes de integrar una nueva herramienta:

1. **Pasada de viabilidad (15-30 min)**: Verificar existencia de script de inferencia, presencia de pesos del modelo, ausencia de rutas absolutas hardcoded y facilidad de instalación.
2. **Registro**: Documentar el veredicto en `docs/decisions.md` (o archivo temporal de tarea).
3. **Bloqueo**: Detenerse y consultar si >30% de las herramientas candidatas resultan `BLOCKED`.

---
[? Volver al �ndice](INDEX.md)
