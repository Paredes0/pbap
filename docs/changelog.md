---
description: Chronological log of project changes. Append a new entry at the end of each significant task.
last_updated: 2026-05-13
---

# Changelog

> Entry format: `- YYYY-MM-DD — <title>. Files: <list>.`

## 2026-05

- 2026-05-13 — **SETUP_FROM_SCRATCH.md: añadido bloque "expected tree"**.
  Entre paso 2 (envs) y paso 3 (HemoPI2 manual download) se inserta
  un árbol ASCII que muestra la estructura exacta que un tercero debe
  ver tras los dos bootstrap scripts: el contenido del clone público,
  los 10 subdirectorios bajo `Dataset_Bioactividad/Tool_Repos/<tool>/`
  (con anotación de qué upstream se clonó y qué patch se aplicó), y
  los 6 envs en `~/micromamba/envs/`. Sirve como checkpoint visual:
  si tu árbol coincide, vas bien; si no, ya sabes qué paso revisar.
  Punto disparador: pregunta del usuario "¿el bootstrap crea toda
  la estructura ordenada en su sitio?". Sí, y ahora está
  explícitamente documentado.
- 2026-05-13 — **`wrappers/README.md` añadido**. La carpeta `wrappers/`
  contenía solo un archivo (`bert_ampep60_cli.py`) sin contexto, lo
  cual disparó la pregunta legítima "¿es código del autor upstream?".
  Auditado: 100% código del PBAP maintainer (lee `predict.py` upstream
  en runtime con `re.sub`, no copia/redistribuye ninguna línea
  literal). El nuevo README documenta: cuándo usar `wrappers/` vs
  `patches/`, los 4 modos del runner (`flagged|positional|script|wrapper`),
  el estado DEFERRED_USER de bert_ampep60, y la regla para añadir
  wrappers nuevos. Cierra la ambigüedad y explica por qué hay solo
  un wrapper.
- 2026-05-13 — **Postura legal explícita para los patches**. El
  `patches/README.md` añade una sección "Legal posture" que documenta
  por escrito (a) que los patches son adaptadores de interoperabilidad,
  no redistribución de las tools; (b) que aplican on top de `git clone`
  upstream y son inútiles solos; (c) para las 4 tools sin LICENSE
  explícito (hemodl, deepb3p, perseucpp, acp_dpe) la postura es
  fair-use / academic-interoperability con ~50 líneas de código
  original en I/O adapters, no en arquitectura/weights/training; (d)
  takedown email noeparedesalf@gmail.com con commit a 24h; (e) reglas
  para forks: preservar notice + paso de "clone upstream" + contacto
  takedown. Postura consistente con el ADR del 2026-05-13 sobre el
  demo público.
- 2026-05-13 — **README: pequeño fix de coherencia post-bootstrap**.
  La sección "Folders excluded from the repository" (a) añade
  `reference_data/` (estaba gitignored pero no documentado en este
  bloque), (b) actualiza la nota de `Dataset_Bioactividad/` para
  indicar que `scripts/bootstrap_tools.sh` ahora lo auto-clona en
  vez del antiguo "consulta `pipeline_viability.md` y clona manual",
  (c) matiza que `Inputs/example.fasta` sí está tracked aunque
  `Inputs/*` esté gitignored. Sin cambio de código.
- 2026-05-13 — **Repro gaps cerrados — la repo es ahora reproducible
  de cero para Phase 1**. Cinco piezas nuevas atan el setup desde
  `git clone` a un smoke test en verde:
  (a) `patches/<tool>.patch` × 5 (hemodl, deepb3p, apex, perseucpp,
      acp_dpe) — diffs reales extraídos del árbol interno con
      `git diff`, total ~100 líneas de adaptaciones mecánicas (CLI,
      argparse, FASTA→CSV adapters). Cada patch lleva su rationale
      en `patches/README.md`. HemoPI2 no es patch (su modelo se
      descarga externamente, documentado en SETUP).
  (b) `envs/<env>.yaml` × 6 — exports `micromamba env export
      --no-builds` con `prefix:` retirado, versiones exactas
      (ml/torch/qsar/pipeline_bertaip = Python 3.10, torch_legacy =
      3.9, deepb3p_legacy = 3.7). 100% portables, sin paths locales.
  (c) `scripts/bootstrap_tools.sh` — bash idempotente que lee
      `github_url` del `pipeline_config.yaml`, clona cada tool y le
      aplica su patch. Detección de "patch ya aplicado" con
      `git apply --check --reverse`.
  (d) `scripts/bootstrap_envs.sh` — bash idempotente que invoca
      `micromamba create -y -n <env> -f envs/<env>.yaml` por env.
      Skip si el env ya existe.
  (e) `docs/SETUP_FROM_SCRATCH.md` — walkthrough end-to-end en 5
      pasos con presupuesto de tiempo/disco real (~30-60 min /
      ~35-45 GB) y troubleshooting cheatsheet. Es la referencia
      canónica para cualquier operador nuevo.
  También: `test_data/AMPs_canonical.fasta` (10 péptidos
  históricos: magainin, melittin, LL37, etc.) y
  `test_data/BAPs_canonical.fasta` (12 péptidos bioactivos:
  ACE inhibitors, BPC-157, MSH, etc.) para smoke tests más
  significativos que `Inputs/example.fasta`. Reach out: phase 2 no
  está incluida (sus datos curados no son redistribuidos); el SETUP
  doc lo declara explícitamente.
- 2026-05-13 — **Fix de atribuciones erróneas en el frontend del demo**.
  El `demo/frontend/app.py` tenía dos clases de bugs heredados de la
  primera redacción:
  (a) Categoría incorrecta: DeepBP figuraba como "bitter peptides"
      cuando es **anticancer** (el config y `docs/deployment.md` ya
      decían anticancer; solo el demo estaba mal).
  (b) URLs upstream incorrectas en 6/10 tools (yo me inventé
      `plisson-lab/HemoDL`, `GreenStarTeam/DeepB3P3`, `Brian-fei/DeepBP`,
      `de-la-Fuente-Lab/APEX`, `plisson-lab/Perseus`, `Brian-fei/ACP-DPE`).
      Las URLs reales según `config/pipeline_config.yaml :: github_url`
      son: `abcair/HemoDL`, `GreatChenLab/deepB3P`,
      `Zhou-Jianren/bioactive-peptides`,
      `gitlab.com/machine-biology-group-public/apex`,
      `goalmeida05/PERSEU`, `CYJ-sudo/ACP-DPE`.
  Esto importa: el escudo de mitigación del demo (ver ADR del
  2026-05-13 "Public demo as a separate layer") se apoya
  explícitamente en atribución correcta por tool. Linkar al repo
  equivocado anulaba esa garantía.
  Aprovechado también para alinear el nombre BertAIP (config) en vez
  de BERT-AIP (display que solo aparecía en el demo).
- 2026-05-13 — **Contract gaps del demo cerrados**. Cuando se añadió
  el área `demo/` (commit `3985822`) el `ONBOARDING.md` §4 exigía
  tres updates secundarios que omití entonces. Ahora aplicados:
  (a) Nuevo ADR en `docs/decisions.md` "Public demo as a separate
  layer with mitigation shield" — justifica la separación de
  `demo/` del orquestador y la posición de lanzar sin permisos
  previos a los autores upstream con un escudo de mitigación
  explícito (atribución, takedown email, no-weights, no-tracking,
  ALLOWED_TOOLS allow-list).
  (b) `docs/deployment.md` §4 incorpora `pbap_demo_api` como env
  opcional (solo para operadores del demo, no requerido para CLI).
  (c) `docs/architecture.md` gana una sección §5 "Optional layer —
  public web demo (`demo/`)" con el diagrama del flujo backend +
  frontend + Cloudflare Tunnel y la mención del directorio en §1.
- 2026-05-13 — **CTA del demo en la landing page**. `site/index.html`
  gana un bloque "hero-cta" después de los stats: botón primario
  amarillo HF "Try the live demo" → `huggingface.co/spaces/Paredes-0/pbap-demo`,
  botón secundario "View source on GitHub", y un meta-text con la
  política ("Free · non-commercial · up to 50 peptides"). Sigue la
  paleta existente del site (oklch tokens + IBM Plex). El workflow
  `pages.yml` redeploya automáticamente al pushear `site/**`.
- 2026-05-13 — **Public demo live**. Banner del README enlaza directo
  al Space en `huggingface.co/spaces/Paredes-0/pbap-demo` (antes
  apuntaba solo al scaffold `demo/`). Añadido badge "Open in HF
  Space" arriba del bloque de shields. Backend
  (`pbap-api.service`) y túnel (`cloudflared.service`) corriendo
  bajo systemd en el host del operador.
- 2026-05-13 — **Public demo scaffold** under `demo/`. Two halves:
  (a) `demo/api/` — FastAPI backend (`server.py`, `jobs.py`,
  `limits.py`, `runner.py`) intended to run on the operator's Linux
  host. Single-worker FIFO queue, per-IP rate limit (3 jobs/h),
  global daily cap (200 jobs/day), 50-peptide submission cap,
  10-minute per-job timeout, in-memory state (no PII persists).
  Subprocess wrapper invokes `scripts/run_audit.py` unchanged.
  Templates included for `.env`, `cloudflared` config and a systemd
  unit. (b) `demo/frontend/` — Gradio Hugging Face Space app that
  proxies submissions to the backend, renders the inline
  `REPORT.html` and exposes the four downloadable artifacts. Ships
  with the mandatory "Tools and attribution" block plus the
  takedown-contact disclaimer (mitigation shield, documented in
  `demo/api/README.md`). The root `README.md` banner gains a "Try
  it online" pointer; `ONBOARDING.md` §3–§4 and `AGENTS.md` Rule #2
  contract tables learn about the new `demo/` paths.
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
