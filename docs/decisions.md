---
description: Architectural Decision Records — por qué X y no Y.
related: [architecture.md]
last_updated: 2026-05-08T10:30:00Z
---

# Decisions

> Format por entrada:
> ### YYYY-MM-DD — Decision title
> **Context**: <situación>
> **Decision**: <qué se decidió>
> **Consequences**: <qué implica, trade-offs>

### 2026-05-08 — Arquitectura Híbrida y Despacho SSH

**Context**:
CD-HIT es un componente crítico para el análisis de leakage pero sus binarios precompilados suelen ser específicos para Linux. El desarrollo del pipeline ocurre principalmente en Windows, pero se dispone de un servidor Linux con los binarios instalados.

**Decision**:
Se implementó un sistema de **SSH Dispatch** en `audit_lib/cdhit_utils.py`. Si el orquestador detecta que está corriendo en Windows y no encuentra el binario local, despacha el comando a un nodo Linux remoto configurado en `pipeline_config.yaml`. La sincronización de archivos se asume vía SSHFS o una ruta compartida común.

**Consequences**:
- Permite la ejecución E2E del pipeline desde Windows sin portar binarios complejos de C++.
- Introduce una dependencia de red y configuración SSH.
- El despacho está limitado a CD-HIT; otras herramientas siguen ejecutándose localmente vía Micromamba.

### 2026-04-29 — Esquema de Manejo de Longitud por Herramienta

**Context**:
Diversas herramientas presentan comportamientos inconsistentes ante péptidos fuera de su rango de entrenamiento (crash, truncado silencioso o extrapolación).

**Decision**:
Se adoptó un esquema de 3 modos gestionado por el orquestador:
1.  **`hard_limit`**: Pre-filtrado obligatorio para evitar crashes.
2.  **`soft_truncate`**: Marcado de baja fiabilidad (`reliability="low"`) si ocurre truncado.
3.  **`soft_reliability`**: Advertencia de extrapolación si la secuencia es inusualmente larga/corta.

**Consequences**:
- Los detalles técnicos de cada herramienta se centralizan en `config/pipeline_config.yaml` y se resumen en `docs/data.md`.
- Mejora la transparencia del reporte final para el usuario.

---

## Decisiones Estadísticas y Heurísticas

### 1. Graduación de Leakage (CD-HIT-2D)
> ⚠️ Solo se aplica en el flujo de **auditoría científica (Fase 2)**
> — `bin/audit_pipeline.sh` y scripts asociados. **No** se aplica en
> el flujo de inferencia de usuario (`scripts/run_audit.py`), que
> no devuelve esta etiqueta. La integración en producción es trabajo
> futuro (ver `docs/roadmap.md`).

Se definen los siguientes grados basados en la similitud máxima con el training set:
- **Gold**: Sobrevive a CD-HIT-2D al 40% (novedad real).
- **Silver / Bronze**: Grados intermedios de similitud (60% / 80%).
- **Red**: Similaridad >80%. Indica péptido potencialmente filtrado (leaked).

### 2. Ranking Holístico y Structural Score
Sistema de ordenación en dos niveles:
1. **Structural Score**: Puntuación cualitativa (0-3) basada en la polaridad de las categorías.
2. **Holistic Score**: Puntuación cuantitativa agregada con bonificaciones por potencia y selectividad.

### 3. Manejo de Longitud (`Length_Status`)
Etiquetado informativo (`within_range`, `too_short`, `too_long`) basado en los metadatos de entrenamiento de cada herramienta.

---
[? Volver al �ndice](INDEX.md)
