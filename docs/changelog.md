---
description: Chronological log of project changes. Append a new entry at the end of each significant task.
last_updated: 2026-05-13
---

# Changelog

> Entry format: `- YYYY-MM-DD — <title>. Files: <list>.`

## 2026-05

- 2026-05-13 — **Landing page redesign pass**: refreshed
  `site/index.html` (+478 lines of CSS/UX polish). Preserves the
  Applicability Domain framing in Section 07 (two-lens block,
  identity-band tier cards, takeaway paragraph). Components and Pages
  workflow unchanged.
- 2026-05-13 — **Docs-sync infrastructure** to keep `docs/` aligned
  with code. Three additions:
  (a) `ONBOARDING.md` at the root — single canonical entry point for any
  new human or AI contributor, with the **contract table** mapping code
  paths to docs to update;
  (b) `AGENTS.md` rewritten in English and reinforced with the explicit
  code→docs mapping under Rule #2;
  (c) `.github/workflows/docs-sync.yml` CI guard — non-blocking warning
  on every PR/push that touches `audit_lib/`, `scripts/` or `config/`
  without touching `docs/`. Also: `README.md` banner pointing to the
  live landing page; clone URL in the README fixed to the new repo
  name.
- 2026-05-13 — **GitHub Pages landing site** added under `site/` with auto-deploy workflow (`.github/workflows/pages.yml`). Standalone HTML5 + React via UMD + Babel (no build step). Two-lens framing of the CD-HIT-2D bands aligned with the AD reframing in `docs/leakage_analysis.md`. Files: `site/index.html`, `site/components/*.jsx`, `site/.nojekyll`, `site/DEPLOY.md`, `.github/workflows/pages.yml`. Target URL: `https://paredes0.github.io/pbap/`.
- 2026-05-13 — **Applicability-domain reframing of leakage grades**.
  Rewrote `docs/leakage_analysis.md` to introduce the Applicability
  Domain (AD) concept from QSAR (Tropsha & Golbraikh; OECD Principle 3)
  and present Gold / Silver / Bronze / Red as **identity bands** with
  **two reading lenses**: benchmarking the tool vs. trusting a specific
  prediction. The previous framing ("Gold = highest confidence") is
  correct only for benchmarking; for practical reliability of an
  individual prediction it is inverted (Gold = out-of-distribution).
  Names of the bands are preserved (already embedded in code, configs,
  filenames); only the docs interpretation changes. Files:
  `docs/leakage_analysis.md`, `docs/glossary.md`, `docs/data.md`,
  `docs/decisions.md` (new ADR), `docs/context_objective.md`,
  `docs/INDEX.md`.
- 2026-05-13 — **Docs audit and translation to English**. Removed
  `docs/contributors.md` (internal AI-swarm roster, not relevant for the
  public project). Fixed encoding on 12 files (cp1252 / latin-1 / BOM →
  UTF-8 no BOM). Normalized line endings to LF. Translated 17 Spanish
  documents to English. Files: all `docs/*.md`, `AGENTS.md`,
  `docs/INDEX.md`.
- 2026-05-13 — **Public release v0.1.0** under PolyForm Noncommercial
  1.0.0 at `https://github.com/Paredes0/pbap`. Contact for commercial
  licensing: noeparedesalf@gmail.com. Files: `LICENSE`, `README.md`,
  `CODE_OF_CONDUCT.md`, `THIRD_PARTY_LICENSES.md`.
- 2026-05-13 — **CI smoke workflow** + personal-data leak guard added.
  `requirements.txt` created for runtime dependencies of the
  orchestrator. Files: `.github/workflows/smoke.yml`, `requirements.txt`.
- 2026-05-13 — **Phase 1 / Phase 2 scope disclaimers** added across
  user-facing docs to clarify that Gold/Silver/Bronze/Red grading is
  Phase 2 (scientific audit, offline) and not part of the user-inference
  report. Files: `docs/INDEX.md`, `docs/context_objective.md`,
  `docs/leakage_analysis.md`, `docs/decisions.md`.
- 2026-05-13 — **Branch protection on main**: `enforce_admins` disabled
  to allow hotfix flow without removing protections permanently.
- 2026-05-03 — **Hierarchical ranking** (`structural_score` +
  `holistic_score`) implemented. Sort order:
  `(structural_score desc, holistic_score desc)`. APEX selectivity tag
  and potency badges (`MUY_POTENTE_AMP` ≤ 5 µM, `POTENTE_AMP` ≤ 10 µM)
  contribute to `holistic_score` as adjustments. HTML reports an
  interactive matrix with per-tool ranking dropdown. Files:
  `scripts/run_audit.py`, `config/categories_config.yaml`,
  `docs/orchestrator_design.md` §9–§10.
- 2026-05-03 — `prefer_threshold_over_raw_class` flag added to
  `output_parsing` to override the tool's own class when both class and
  score are emitted (applied to `bertaip`). Files: `audit_lib/`,
  `config/pipeline_config.yaml`, `docs/orchestrator_design.md` §11.
- 2026-05-01 — APEX reverts to `class_norm=None` (pure `extra_only`).
  Selectivity tag enters holistic adjustment instead of binary voting.
  `bertaip` threshold raised 0.5 → 0.8. Files: `scripts/run_audit.py`,
  `config/pipeline_config.yaml`, `docs/orchestrator_design.md` §8.
- 2026-05-01 — `bertaip` replaces `aip_tranlac` in the
  `anti_inflammatory` category (env `pipeline_bertaip`,
  `transformers==4.30.2` pinned to resolve simpletransformers conflict).
  `aip_tranlac` preserved as `_aip_tranlac_backup` (off pipeline).
  Files: `config/pipeline_config.yaml`, `scripts/run_audit.py`.

## 2026-04

- 2026-04-30 — `eippred` removed from the orchestrator at user request.
  Code preserved on disk; env marked obsolete. Active tools after the
  change: 10/26. Files: `config/pipeline_config.yaml`,
  `scripts/run_audit.py`, `docs/pipeline_viability.md`.
- 2026-04-30 — `hemopi2` switched from mode `-m 4` (Hybrid) to `-m 3`
  (ESM2-only) because the MERCI sentinel `−1.0` was collapsing the
  Hybrid score and misclassifying mellitin. Threshold 0.58 unchanged.
  Files: `config/pipeline_config.yaml`.
- 2026-04-28 — `consolidated.xlsx` added (5 sheets, openpyxl pure,
  conditional formatting row by row, autofilter, freeze pane).
  Convention `Inputs/<name>.fasta` and
  `Outputs/<input_stem>_<ISO_ts>/` auto-created by the run. Files:
  `scripts/run_audit.py`, `docs/orchestrator_design.md` §5.3.
- 2026-04-27 — `REPORT.html` standalone report added (initially
  CSS-only; JS inline allowed from 2026-05-01 for the interactive
  matrix; no CDN). Files: `scripts/run_audit.py`,
  `docs/orchestrator_design.md` §5.2.
- 2026-04-25 — **Dual schema** adopted: binary axis (`class_norm`,
  `score`) + `extra_metrics`. APEX outputs 34 MIC columns as
  `apex__MIC_<strain>__uM`. Files: `audit_lib/tool_runner.py`,
  `config/pipeline_config.yaml`, `docs/orchestrator_design.md`.
- 2026-04-25 — Layer-2 aggregation frozen as **Option B**
  (agreement/split, no voting). Option E (weighted ensemble by
  reliability) deferred until the tool pool is closed.
- 2026-04-22 — **Operational rule established**: verify external
  artifacts (inference script, weights, paths) **before** building
  infrastructure. Files: `docs/verify_external_artifacts.md`.
- 2026-04-17 — **Project pivot**: Phase 1 (end-to-end user inference)
  prioritized over Phase 2 (scientific audit). Phase 2 deferred.

## 2026-05-08 (documentation bootstrap)

- 2026-05-08 — **Documentation bootstrap**: consolidated project memory
  into canonical `docs/*.md`, renamed/merged legacy files, updated
  internal references. Files: `docs/*.md`, `README.md`, `CLAUDE.md`.

---
[← Back to Index](INDEX.md)
