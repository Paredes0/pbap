---
description: Project-specific patterns and idioms — finer-grained than AGENTS.md.
related: [/AGENTS.md]
last_updated: 2026-05-13
---

# Conventions

This document captures the naming, file organization and development
discipline followed in this project.

## 1. Naming

### Tools
- **Identifiers**: always lowercase, no hyphens (e.g. `toxinpred3`,
  `hemopi2`, `hemodl`).
- **Repository directories**: located in
  `Dataset_Bioactividad/Tool_Repos/<tool_id>/`.

### Data columns (Matrix)
- **Binary axis**: normalized to `class_norm` (0 or 1) and `score`
  (0.0 to 1.0).
- **Extra axis**: additional metrics follow the pattern
  `<tool_id>__<metric>__<unit>` (e.g. `apex__mic_staph_aureus__uM`).
- **Differentiation**: same magnitude + target + unit → same column;
  any difference → separate column.

## 2. File organization

### Inputs and outputs
- **Inputs**: input FASTA files are placed in `Inputs/`.
- **Outputs**: the orchestrator creates a subfolder per run:
  `Outputs/<input_stem>_<YYYY-MM-DDTHHMM>/`.
- **Name collisions**: a numeric suffix (`_2`, `_3`) is added if the
  timestamp collides.

### Documentation
- **Location**: all canonical documentation lives in `docs/`.
- **Archive**: obsolete documents are moved to `docs/_archive/YYYY-MM/`.
- **Index**: `docs/INDEX_LOOKUP.md` serves as the jump table for quick
  location of functions and files.

## 3. Development discipline

### Updating documentation (formerly "memory")
When finishing a task that changes the stable state of the project, the
corresponding document must be updated:

| Type of change | Document to update |
|---|---|
| New statistical threshold or heuristic | `docs/decisions.md` |
| Bug fixed (lessons learned) | `docs/decisions.md` |
| New SSH/infrastructure workaround | `docs/deployment.md` |
| Architectural change | `docs/architecture.md` |
| New planned improvement | `docs/roadmap.md` |

### 3.3 Efficient code reading
Given the length of some scripts (>500 lines), follow these rules to
save context:
- **Grep** → search for literals, function names or simple regex.
- **ast-grep (sg)** → search syntactic structure. Useful patterns:
  - Fisher calls: `sg --lang python -p 'fisher_exact($$$)'`
  - SSH dispatch: `sg --lang python -p 'ssh_dispatch($$$)'`
  - Logged functions: `sg --lang python -p 'def $F($$$): $$$ log.debug($$$) $$$'`
- **Read** → always use `offset` and `limit` (40-50 lines) after
  locating the point of interest.
- Avoid reading entire files except for major refactors.

## 4. Code standards

### 4.1 Python
- **Version**: minimum compatibility with Python 3.8.
- **Indentation**: 4 spaces (PEP 8).
- **Docstrings**: Google style. Every public module and function must
  document its parameters and return value.
- **Error handling**: `try/except` with detailed logging. Avoid
  `print()` for debugging; use `log.debug()`.
- **Logging**: standard setup per script:
  `logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")`.

### 4.2 Shell scripts (Bash)
- **Safety**: every script must start with `set -euo pipefail`.
- **Robustness**: locate base paths via
  `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.
- **Windows compatibility**: include path-conversion helpers (e.g.
  `to_win_path`) if the script interacts with Windows binaries from a
  Bash environment.

### 4.3 Git and commits
- **Language**: commit messages in **Spanish** (project convention).
- **Style**: free-form but focused on the impact of the change.
- **Branches**: standard prefixes — `feat/`, `fix/`, `chore/`, `docs/`.
- **Permissions**: never `git commit` or `git push` without explicit
  user permission.

### 4.4 File headers
All core scripts must include a structured header:
```python
"""
script_name.py
==============
Short description of the functionality.
Usage context and key dependencies.
"""
```

## 5. Auditing external tools

Do not assume that a third-party repository works out of the box.
Before integrating a new tool:

1. **Viability pass (15-30 min)**: verify the existence of an inference
   script, presence of model weights, absence of hardcoded absolute
   paths, and ease of installation.
2. **Recording**: document the verdict in `docs/decisions.md` (or a
   temporary task file).
3. **Stop condition**: pause and consult if >30% of candidate tools
   end up `BLOCKED`.

---
[← Back to Index](INDEX.md)
