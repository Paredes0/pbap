# AGENTS.md — PBAP

> **Operating manual for every AI agent working on this repository.**
> `CLAUDE.md`, `GEMINI.md` and `.github/copilot-instructions.md`
> automatically import this file. Compatible agents: Claude Code,
> Gemini CLI in Antigravity, Cursor, GitHub Copilot Workspace.
>
> This file is the **index** of operating rules. The actual project
> memory lives in `docs/`. The contract between code and docs lives
> in [`ONBOARDING.md`](ONBOARDING.md).

## Rule #1 — Read [`ONBOARDING.md`](ONBOARDING.md) and [`docs/INDEX.md`](docs/INDEX.md) before acting

Any non-trivial task on this repository starts with two reads:

1. [`ONBOARDING.md`](ONBOARDING.md) — explains what the docs system
   is for, what contract you must follow when changing things, and
   what the end-of-task checklist looks like. **Required reading**
   for the first task in any session.
2. [`docs/INDEX.md`](docs/INDEX.md) — navigation map of all canonical
   docs. From there, jump to the specific doc relevant to your task.

Area → doc mapping (quick lookup):

| Area you are working on | Doc(s) to consult |
|---|---|
| Design / architecture | `docs/architecture.md`, `docs/decisions.md` |
| Public APIs of `audit_lib/` | `docs/api.md` |
| Data models / schemas / I/O formats | `docs/data.md` |
| Orchestrator behavior (Phase 1) | `docs/orchestrator_design.md` |
| Per-tool viability and history | `docs/pipeline_viability.md` |
| CD-HIT-2D grading / Applicability Domain | `docs/leakage_analysis.md` |
| Taxonomic bias methodology | `docs/taxonomic_analysis.md` |
| Code patterns and idioms | `docs/conventions.md` |
| Domain terms | `docs/glossary.md` |
| Tool inventory / environments | `docs/deployment.md` |
| Third-party licensing | `docs/licenses_audit.md`, `THIRD_PARTY_LICENSES.md` |
| Known issues / tech debt | `docs/todo.md` |
| Recent project state | `docs/changelog.md` |
| Anything else | see the table in `docs/INDEX.md` |

`docs/changelog.md` is updated by the agent at task close (see
Rule #2). Do not edit it manually for past events; do append for the
current task.

## Rule #2 — After a task, run the end-of-task checklist

Before declaring a task complete, run the contract checks defined in
[`ONBOARDING.md`](ONBOARDING.md) §4 (contract table) and §5
(end-of-task checklist). Summary:

| If you touched | Then check |
|---|---|
| Public signature in `audit_lib/*.py` | `docs/api.md` |
| Runner dimensions in `audit_lib/tool_runner.py` | `docs/orchestrator_design.md` §3 |
| `scripts/run_audit.py` behavior or reports | `docs/orchestrator_design.md` + `docs/data.md` |
| Phase-2 scripts | `docs/INDEX_LOOKUP.md` + `docs/*_analysis.md` |
| `config/pipeline_config.yaml` (tool change) | `docs/deployment.md` + `docs/pipeline_viability.md` |
| `config/categories_config.yaml` | `docs/orchestrator_design.md` §9 |
| New external tool | `docs/pipeline_viability.md` + `THIRD_PARTY_LICENSES.md` + `docs/licenses_audit.md` |
| New statistical threshold / heuristic | `docs/decisions.md` (new ADR) |
| Architectural change | `docs/architecture.md` + `docs/decisions.md` |
| `demo/api/` (backend endpoints, queue, limits) | `demo/api/README.md` |
| `demo/frontend/` (Gradio UI, attribution, disclaimer) | `demo/frontend/README.md` |
| `patches/<tool>.patch` or `scripts/bootstrap_*.sh` | `patches/README.md` and `docs/SETUP_FROM_SCRATCH.md` |
| `envs/<env>.yaml` | `docs/deployment.md` §4 + `docs/SETUP_FROM_SCRATCH.md` |
| Any user-visible change | `docs/changelog.md` (one-line entry) |

The CI workflow `.github/workflows/docs-sync.yml` will additionally
warn on every PR/push that changes `audit_lib/`, `scripts/` or
`config/` without touching `docs/`. The warning is **non-blocking but
visible** — do not push code-only changes hoping it will go unnoticed.

If you used `/plan` to plan the task, the plan must include a docs
subtask. If you used `/log close-task`, the changelog entry is
generated automatically.

## Stack and commands (quick lookup)

- Language / framework: Python / Bash.
- Tests: (no automated suite — scientific project; manual verification
  by running the scripts. See `docs/INDEX_LOOKUP.md` to invoke
  individual components).
- Lint: (none).
- Build: (none).
- Dev: `python scripts/run_audit.py --input <name>.fasta` (Phase 1
  E2E orchestrator).
- Format: (none enforced).

Full detail in `docs/architecture.md` and `docs/conventions.md`.

## Conventions (top-level — fine detail in `docs/conventions.md`)

- Commit language: **Spanish** (project convention).
- Commit style: free, focused on impact of the change.
- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`,
  `docs/<topic>`.
- Indentation: 4 spaces (PEP 8).

## Do not touch without explicit permission

- `Dataset_Bioactividad/`, `Outputs/`, `DATABASES_FASTA/` (scientific
  data).
- `_external_refs/` (external notes, not project content).
- `CLAUDE.md.bak` (pre-swarm backup).
- `Inputs/*.fasta` (input datasets — editing them invalidates past
  runs).
- `reference_data/` (immutable reference).
- `config/pipeline_config.yaml` (~900 lines with 14 active tools —
  only edit the block of the specific tool, never refactor in bulk.
  The 12 BLOCKED / inactive tools live in
  `config/pipeline_config_blocked.yaml`).

## Routing (if part of a multi-agent swarm)

- Task categories: `code`, `code-hard`, `async`, `git`, `docs-google`,
  `review`.
- Hard delegation rules in the global skill `swarm-routing`.
- **Before delegating or executing**, every agent must have read
  `ONBOARDING.md` and `docs/INDEX.md`. Non-negotiable.

## Orchestrator failover

If Antigravity runs out of tokens:
`claude --mcp-config .swarm/mcp_failover.json`
State persisted to `.swarm/plan.md` and `.swarm/worklog.md`.

---

> If you are an AI agent reading this for the first time in this
> session, your immediate next action is to read
> [`ONBOARDING.md`](ONBOARDING.md), then `docs/INDEX.md`, then the
> specific doc(s) most relevant to the task at hand. Do not skip
> these reads even for "small" tasks.
