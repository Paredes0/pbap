# AGENTS.md — pipeline_Work - copia

> **Operating manual para todos los agentes IA del swarm.**
> CLAUDE.md, GEMINI.md y .github/copilot-instructions.md importan este archivo automáticamente.
> Este archivo es solo el ÍNDICE rápido. La memoria real del proyecto vive en `docs/`.

## REGLA #1 — Antes de actuar, lee `docs/INDEX.md`

`docs/INDEX.md` es el entry point de la memoria del proyecto. CUALQUIER agente (humano o IA) que vaya a tocar este repo en cualquier subtarea no trivial DEBE empezar leyéndolo y, desde ahí, navegar a los docs específicos relevantes a lo que va a hacer.

Mapeo área → doc(s):
- **Diseño / arquitectura** → `docs/architecture.md`, `docs/decisions.md`
- **APIs públicas (firmas, contratos)** → `docs/api.md` (si existe)
- **Modelos de datos, esquemas, formatos** → `docs/data.md` (si existe)
- **Patrones e idioms del código** → `docs/conventions.md`
- **Términos del dominio** → `docs/glossary.md`
- **Issues conocidos / deuda técnica / TODOs** → `docs/todo.md` (si existe)
- **Cualquier otro doc opcional/custom** → ver tabla en `docs/INDEX.md`

`docs/changelog.md` se actualiza automáticamente al cerrar cada tarea (lo hace `/log`). No lo edites a mano salvo emergencia.

## REGLA #2 — Tras una tarea, actualiza la memoria si procede

Si una subtarea cambia arquitectura, decisiones, APIs públicas, modelos de datos, convenciones, glossary, etc., DEBE incluirse en el mismo plan una subtarea adicional para actualizar (o crear) el doc correspondiente. `/plan` lo hace automáticamente; si lo invocas manualmente, no lo olvides.

## Stack y comandos (lookup rápido)

- Lenguaje / framework: Python / Bash
- Tests: (ninguno automatizado — proyecto científico ad-hoc; verificación manual ejecutando los scripts. Ver `docs/INDEX_LOOKUP.md` para invocar componentes individuales)
- Lint: (ninguno)
- Build: (ninguno)
- Dev: `python scripts/run_audit.py --input <name>.fasta` (orquestador E2E Fase 1)
- Format: (ninguno)

Detalle pleno en `docs/architecture.md` y `docs/conventions.md`.

## Convenciones (top-level — el detalle fino en `docs/conventions.md`)

- Idioma de commits: español
- Estilo de commits: libre
- Nombres de ramas: `feat/<tema>`, `fix/<tema>`, `chore/<tema>`
- Indentación: 4 espacios

## No tocar sin permiso explícito

- `Dataset_Bioactividad/`, `Outputs/`, `DATABASES_FASTA/` (datos científicos)
- `_external_refs/` (notas externas Claude Code, no del proyecto)
- `CLAUDE.md.bak` (backup pre-swarm-init)
- `Inputs/*.fasta` (datasets de entrada — modificar invalidaría runs anteriores)
- `reference_data/` (referencia inmutable)
- `config/pipeline_config.yaml` (~900 líneas con 14 tools activas — solo editar el bloque del tool específico, nunca refactor masivo. Las 12 tools BLOCKED/inactivas viven en `config/pipeline_config_blocked.yaml`)

## Routing del swarm

- Categorías: `code`, `code-hard`, `async`, `git`, `docs-google`, `review`.
- Reglas duras y políticas de delegación en la skill global `swarm-routing` (`~/.gemini/antigravity/skills/swarm-routing/SKILL.md`).
- **Antes de delegar/ejecutar**, cada agente debe haber leído `docs/INDEX.md`. Esto es no negociable.

## Failover de orquestador

Si Antigravity se queda sin tokens:
`claude --mcp-config .swarm/mcp_failover.json`
Estado persistido en `.swarm/plan.md` y `.swarm/worklog.md`.
