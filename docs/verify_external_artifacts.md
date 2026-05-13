# Regla — Verificar artefactos externos ANTES de construir infraestructura

**Tipo**: regla obligatoria de planificación.
**Establecida**: 2026-04-22.
**Última revisión**: 2026-04-26 (clarificación de la frontera patch/wrapper).
**Aplica a**: cualquier tarea que dependa de N artefactos externos (repos de terceros, modelos publicados, datasets descargables, APIs).

---

## Regla

**Antes de construir infraestructura que dependa de artefactos externos, verifica uno por uno que cada artefacto existe, es utilizable en modo inferencia, y tiene los pesos / datos necesarios cargables.**

No asumas que porque una repo tiene un `README`, un `environment.yml` o un paper publicado, el código es plug-and-play. En bioinformática open-source eso es la excepción, no la norma.

---

## Por qué (incidente de referencia 2026-04-22)

Tras construir 8 entornos conda (~2h de trabajo), clonar 22 repos y editar 24 entradas YAML, el smoke bulk reveló que **11 de 22 tools (50%) no tenían script de inferencia utilizable**: solo código de entrenamiento, notebooks, rutas hardcoded, o pesos no incluidos. Este gasto de trabajo y tokens era evitable con una auditoría de viabilidad de 15-30 min al inicio.

Tras una segunda iteración (BLOQUE B-D del plan posterior) la cifra inicial quedó en 6/26 tools viables E2E. La revisión 2026-04-26 amplió el criterio a 11-13/26 al definir mejor la frontera patch/wrapper (ver §"Frontera adaptación / ingeniería").

---

## Cómo aplicar

### Antes de tocar envs, clones o YAML

Por cada repo externo previsto, verifica:

1. ¿Existe un script de inferencia (`predict.py`, `infer.py`, `main.py` con flag `--predict`) **O una clase con un método de predicción que acepte FASTA/secuencias y devuelva resultados**?
2. ¿El `__main__` o el método admite input peptídico (FASTA/CSV/TSV) y produce output parseable?
3. ¿Los pesos/modelos están incluidos en el repo, o documentados para descarga? ¿La URL funciona?
4. ¿Hay rutas hardcoded (`./Model/`, `/home/<autor>/...`) que rompan fuera del contexto original?
5. ¿La licencia/acceso permite uso?

### Registro

Graba el resultado en una tabla `docs/<tarea>_viability.md` con columnas:

```
tool | has_inference | weights_available | hardcoded_paths | verdict (OK / FIXABLE / BLOCKED) | reason
```

### Decisión

- Solo entonces diseña la infraestructura (envs, runner, config) para el subconjunto `OK + FIXABLE`.
- Los `BLOCKED` van a lista de exclusión con razón documentada.
- Si la auditoría pre-viabilidad revela >30% de tools `BLOCKED`, **detente y consúltalo con el usuario** antes de seguir — probablemente la estrategia necesita ajuste (standby, reemplazos, renegociar scope).

---

## 🔧 Frontera adaptación ligera (PERMITIDA) / ingeniería de inferencia (PROHIBIDA)

**Esta es la sección clave para clasificar correctamente como FIXABLE vs BLOCKED.** Se añadió 2026-04-26 tras detectar que la regla "no wrappers" se había aplicado de forma inconsistente — se aceptaron patches a `hemodl`, `deepb3p`, `deepbp` mientras se rechazaron adaptaciones equivalentes en `apex`, `hypeptox_fuse`, `bert_ampep60`.

### Principio

**La lógica de inferencia del autor debe existir en el repo, completa y ejecutable. Solo la conectamos al pipeline. Si tendríamos que reescribir la inferencia, queda fuera de scope.**

### ✅ Adaptaciones PERMITIDAS (cuentan como FIXABLE)

Cualquiera de estas modificaciones es válida si la lógica de predicción del autor ya está completa:

1. **Patches a scripts existentes**: arreglar paths (script-relative en vez de cwd-relative), migración de API (p. ej. `tokenizer.batch_encode_plus()` → `tokenizer()`), cambiar índices GPU hardcoded (`cuda:2 → cuda:0`), añadir `map_location` a `torch.load`, normalizar case sensitivity (`Model → model`).
2. **Adaptación de formato I/O**: convertir FASTA → formato esperado por el tool (txt una secuencia por línea, CSV con columna específica, etc.) y mapear el output de vuelta.
3. **Añadir argparse al `__main__`**: cuando la función `predict()` ya está parametrizada pero el `__main__` hardcodea paths.
4. **Class wiring**: cuando la lógica completa de inferencia está en una clase con método tipo `predict_fasta_file()`. Instanciar + llamar = ~20-30 líneas de glue.
5. **Reemplazar input interactivo**: `input()` → argparse cuando la lógica subyacente es completa.
6. **Añadir `__main__` a un módulo**: si todas las funciones de inferencia existen pero el módulo no es ejecutable directamente.
7. **Configurar `cwd` para scripts cwd-bound**: ejecutar el script desde su propio directorio cuando hardcodea `./relative_path`.
8. **`git lfs pull`**: hidratar archivos LFS si el usuario autoriza.
9. **Auto-descarga de pesos**: si el script ya implementa la descarga (URLs en código), confiar en eso.

**Coste típico**: 10-50 líneas por tool. Mismo nivel que los patches ya aplicados a `hemodl`/`deepb3p`/`deepbp`.

### ❌ Trabajo PROHIBIDO (clasificar como BLOCKED)

Cualquiera de estas situaciones = repo no es viable bajo nuestras reglas:

1. **Implementar inferencia desde cero**: solo existe `train.py`, no hay flujo de predicción reusable. El modelo está pero la lógica de cargarlo + extraer features + predecir no está escrita.
2. **Re-engineering de pipelines de features multi-paso**: tool requiere 6+ embeddings pre-computados (ProtT5, ESM-1b/2/1v, etc.) sin orquestador, y no existe un `extract_all_features.py` o equivalente.
3. **Entrenar nuevos modelos**: pesos pre-entrenados no existen y no se pueden descargar.
4. **Replicar lógica de notebook línea a línea**: el código vive solo en `.ipynb` con paths Colab (`/content/drive/...`).
5. **Servicios externos no disponibles**: requiere ESMAtlas, NetSurfP, BLAST contra bases privadas, sin alternativa local.
6. **Dependencias incompatibles destructivas**: instalar la librería requerida rompe otros tools del mismo env y no hay env aislado viable.
7. **Pesos detrás de login institucional sin acceso**: SharePoint con login, Baidu Netdisk, FTPs privados.

**Coste típico**: horas a días de ingeniería. Fuera del scope de un audit pipeline.

### Heurística de decisión rápida

> "Si después del cambio, el código que predice sigue siendo del autor y solo cambia cómo lo invoco o qué le paso por entrada/salida → FIXABLE.
> Si tendría que escribir yo la lógica que carga el modelo y produce predicciones → BLOCKED."

### Casos límite

- **Repo solo tiene notebook pero la lógica es lineal y trivial de extraer**: caso por caso. Si convertir el notebook a script es <30 líneas Y los paths Colab se reemplazan trivialmente, FIXABLE. Si el notebook depende de magic commands o estado de Colab, BLOCKED.
- **Pesos descargables pero la URL es inestable** (Google Drive con captcha, Dropbox temporal): documentar en YAML como `manual_download_required` con la URL y dejar instrucciones; clasificar FIXABLE solo si el usuario confirma que descargará.

---

## Red flags que disparan esta regla

Cualquiera de estas señales en una repo externa = NO asumir que funciona:

- Repo solo tiene notebooks (`.ipynb`) sin `.py` ejecutable.
- `README` solo describe training, no inference.
- Modelos referenciados como `model.pkl` / `checkpoint.pt` pero el archivo no está en el repo ni hay enlace de descarga.
- Rutas absolutas tipo `/home/<autor>/...` o relativas tipo `./Model/` (case-sensitive en Linux).
- Dependencias pinned a versiones antiguas sin `environment.yml` reproducible.
- Último commit >3 años sin mantenimiento.
- Imports a paquetes privados, internos, o no publicados en PyPI.
- Paper citado pero no hay tag/release que coincida con la versión del paper.

---

## Anti-patrón a evitar

**MAL**: "Voy a construir los 8 envs conda, clonar las 22 repos, normalizar el YAML, y luego smoke-test todos a la vez." → Descubres los problemas después de invertir 2h y cientos de llamadas a tool.

**BIEN**: "Voy a gastar 15 min verificando una por una que las 22 repos tienen script de inferencia y pesos cargables. Solo construyo infra para las que pasen el filtro." → Descubres los problemas antes de invertir.

---

## Cuándo NO aplica

- Un solo artefacto externo bien conocido (ej: `pip install biopython`) — la verificación es trivial.
- Repos internos del equipo cuyo estado ya conoces.
- Tareas puramente locales sin dependencias externas.

---

## Estado actual de aplicación

- Tabla viva: `docs/pipeline_viability.md`.
- Tools viables tras auditoría inicial (2026-04-22 → 2026-04-25): toxinpred3, antibp3, hemopi2, hemodl, deepb3p, deepbp, eippred (7/26).
- Reclasificación 2026-04-26: candidatos adicionales FIXABLE bajo nueva frontera — apex, hypeptox_fuse, bert_ampep60 (alta confianza); perseucpp, aapl, if_aip, acp_dpe (necesitan inspección directa).
- Diferidos por bloqueo manual (esperando acción del usuario): antifungipept (`git lfs pull`), plm4alg (login KSU), avppred_bwr (Baidu Netdisk).
- Sin clonar (necesita verificación local): mfe_acvp.
- Genuinamente BLOCKED: multimodal_aop, afp_mvfl, antiaging_fl, aip_tranlac, deepforest_htp, stackthp, cpppred_en, macppred2.

---
[? Volver al �ndice](INDEX.md)
