# ONBOARDING — Read this first

> 🎯 **Purpose of this document**: be the single, canonical entry point
> for anyone — human or AI agent — touching this repository for the
> first time. It explains *what the docs system is for*, *what
> contract you must follow when you change things*, and *where to go
> next*. If you can only read one file, read this one.

---

## 1. What is this repository?

**PBAP** (Peptide Bioactivity Audit Pipeline) is a modular orchestrator
that runs published peptide-prediction tools under a unified output
schema. See [`README.md`](README.md) for the user-facing pitch and
[`docs/architecture.md`](docs/architecture.md) for how it is built.

The project is in a stable **Phase-1 operational** state with 10 active
prediction tools, a public landing page at
[paredes0.github.io/pbap](https://paredes0.github.io/pbap/), and a
**living documentation system in `docs/`** that mirrors the code state.

---

## 2. Why this onboarding doc exists

Multiple agents (Claude Code, Gemini CLI in Antigravity, Cursor,
GitHub Copilot Workspace, occasionally humans) edit this repository in
turns. Without a shared contract, the docs in `docs/` drift out of sync
with the code in `audit_lib/`, `scripts/`, `config/` until they stop
being useful.

This file is the **shared contract**. It is intentionally short and
opinionated. Every other doc system (AGENTS.md, CLAUDE.md, GEMINI.md,
docs/INDEX.md) imports or references it.

---

## 3. The docs system in 60 seconds

```
.
├── ONBOARDING.md          ← you are here
├── README.md              ← user-facing pitch (visible on GitHub home)
├── AGENTS.md              ← operating manual for AI agents (CLAUDE.md / GEMINI.md import this)
├── CLAUDE.md / GEMINI.md  ← agent-specific aliases of AGENTS.md
├── CONTRIBUTING.md        ← how to add a tool (humans)
├── docs/
│   ├── INDEX.md           ← navigation map of all canonical docs
│   ├── INDEX_LOOKUP.md    ← function/script jump table
│   ├── architecture.md    ← system architecture
│   ├── api.md             ← public API of audit_lib/
│   ├── data.md            ← I/O formats, schema
│   ├── conventions.md     ← naming, file org, dev discipline
│   ├── deployment.md      ← install, environments, tool inventory
│   ├── decisions.md       ← ADRs (why we chose X, not Y)
│   ├── orchestrator_design.md  ← deep dive into the orchestrator
│   ├── pipeline_viability.md   ← 26-tool audit history
│   ├── leakage_analysis.md     ← CD-HIT-2D + Applicability Domain
│   ├── taxonomic_analysis.md   ← bias methodology
│   ├── licenses_audit.md       ← third-party license matrix
│   ├── verify_external_artifacts.md  ← mandatory pre-infra rule
│   ├── glossary.md
│   ├── roadmap.md
│   ├── todo.md
│   └── changelog.md            ← append a line on every notable change
├── demo/                  ← reference scaffold for the public web demo
│   ├── api/                    ← FastAPI backend (operator's Linux host)
│   └── frontend/               ← Gradio app (Hugging Face Space)
└── site/                  ← GitHub Pages landing source
```

`docs/INDEX.md` is the **navigation root**. Open it when you need to
find a doc. This file (ONBOARDING.md) is the **contract root**. Open
it when you need to know what to do.

---

## 4. The contract: when code changes, docs change

This table is the heart of the contract. **If you touch the path on
the left, you must check (and probably update) the doc on the right
in the same task.** No exceptions for trivial changes; trivial changes
are often the ones that leave the worst paper trail.

| If you touch | Then check |
|---|---|
| `audit_lib/*.py` (public function signatures) | `docs/api.md` |
| `audit_lib/tool_runner.py` (runner dimensions: `arg_style`, `output_capture`, `pre_command`, `cwd_subdir`, …) | `docs/orchestrator_design.md` §3 |
| `scripts/run_audit.py` (orchestrator behavior, reports, ranking) | `docs/orchestrator_design.md` §5, §7, §8, §9 + `docs/data.md` |
| `scripts/*.py` (Phase-2 scripts: leakage, mining, audit) | `docs/INDEX_LOOKUP.md` §2 + the relevant `docs/*_analysis.md` |
| `config/pipeline_config.yaml` (tool added / removed / re-categorized) | `docs/deployment.md` §3 + `docs/pipeline_viability.md` (verdict) |
| `config/categories_config.yaml` (new category, polarity change) | `docs/orchestrator_design.md` §9 (polarity table) + `docs/data.md` |
| `config/apex_strain_classification.yaml` | `docs/orchestrator_design.md` §8 (strain classification) |
| New external tool integrated | `docs/pipeline_viability.md` (add row) + `THIRD_PARTY_LICENSES.md` + `docs/licenses_audit.md` |
| Statistical threshold / heuristic changed | `docs/decisions.md` (new ADR) |
| New environment / installation step | `docs/deployment.md` §4 |
| Significant behavior change (any of the above) | `docs/changelog.md` (one-line entry) |
| Architecture-level change (component added / replaced / removed) | `docs/architecture.md` + `docs/decisions.md` (new ADR) |
| Landing page (`site/`) | `site/DEPLOY.md` if the build flow changed |
| Public demo backend (`demo/api/`) | `demo/api/README.md` (endpoints, deployment, mitigation shield) |
| Public demo frontend (`demo/frontend/`) | `demo/frontend/README.md` (Space deployment) |
| `AGENTS.md` / this file / `docs/INDEX.md` | nothing else — these are the meta-layer |

If your task does not change anything in the left column, you do not
need to touch the right column.

If you are **not sure** whether your change qualifies, default to
updating `docs/changelog.md` with a one-line entry. A stale doc is
worse than a noisy changelog.

---

## 5. End-of-task checklist

Before declaring a task complete, run through this list:

- [ ] Code changes match the contract table above. Relevant docs
      updated in the **same task** (not "later, in a follow-up").
- [ ] `docs/changelog.md` has a new entry if anything user-visible
      changed.
- [ ] If statistical thresholds or design choices changed,
      `docs/decisions.md` has a new ADR.
- [ ] Cross-references between docs are still correct (no broken
      `[link](other.md)` references introduced).
- [ ] If you added a new external tool, dependency, environment, or
      data source, it is listed in the corresponding inventory
      (`docs/deployment.md`, `THIRD_PARTY_LICENSES.md`,
      `docs/pipeline_viability.md`).

The CI workflow `docs-sync.yml` will additionally warn on pushes/PRs
that change `audit_lib/`, `scripts/` or `config/` without touching
`docs/`. The warning is non-blocking but visible.

---

## 6. Quick start by role

**I want to *run* the pipeline (user)**
→ [`README.md`](README.md) §"Quick start" + [`docs/deployment.md`](docs/deployment.md).
Stop here unless you want to modify code.

**I want to *add a tool* (contributor)**
→ [`CONTRIBUTING.md`](CONTRIBUTING.md) §"Adding a prediction tool" +
[`docs/orchestrator_design.md`](docs/orchestrator_design.md) §3
(YAML dimensions). End-of-task checklist applies.

**I am an *AI agent* picking up a task**
→ [`AGENTS.md`](AGENTS.md) for the operating manual. Reference
[`docs/INDEX.md`](docs/INDEX.md) for navigation. End-of-task checklist
is **mandatory**, not optional.

**I am *reviewing* a PR**
→ Check the contract table (§4) against the diff. If the PR touches
the left column and not the right, ask the contributor to update or
to justify the omission.

---

## 7. Where to go next

- [`README.md`](README.md) — user-facing overview and quick start.
- [`AGENTS.md`](AGENTS.md) — full operating manual for AI agents.
- [`docs/INDEX.md`](docs/INDEX.md) — navigation map of all docs.
- [`docs/decisions.md`](docs/decisions.md) — why the system is built
  the way it is.
- [paredes0.github.io/pbap](https://paredes0.github.io/pbap/) —
  visual architecture overview (the landing page).

---

## 8. Meta: keeping this doc alive

This file (ONBOARDING.md) itself is part of the docs system. If the
contract in §4 stops matching reality — for example, because a new
top-level area of the codebase appears — update §4 in the same task
that introduces the change. The same end-of-task checklist applies to
this file.

> *Last reviewed: 2026-05-13. If the date is more than 6 months stale
> and the project is still active, audit the contract table against
> the current code layout.*
