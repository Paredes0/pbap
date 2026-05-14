---
description: Chronological log of project changes. Append a new entry at the end of each significant task.
last_updated: 2026-05-13
---

# Changelog

> Entry format: `- YYYY-MM-DD — <title>. Files: <list>.`

## 2026-05

- 2026-05-14 — **docs: cleanup post-aip_tranlac→bertaip y
  post-reclasificación APEX**. Auditoría docs-vs-código identificó
  drifts heredados de las decisiones de 2026-04-30 / 2026-05-01 que
  nunca se propagaron a las páginas de referencia. Fixes aplicados:
  (a) `docs/api.md`: firma real de `ToolResult` (status,
  predictions_path, stderr_tail, runtime_seconds) y default
  `classify_habitat(fallback="desconocido")`. (b) `docs/deployment.md`
  §3: `bert_ampep60` y `antifungipept` movidas de Active a Standby
  (DEFERRED_USER) — ambas bloqueadas por descarga de pesos (MPU
  SharePoint login wall / git-lfs pointers no hidratados); el conteo
  de Active queda en 10, coherente con `DEFAULT_TOOLS` de
  `run_audit.py` y con §4.1. (c) `docs/orchestrator_design.md` §8:
  conteo APEX `pathogenic`/`commensal`/`ambiguous` 14/18/2 → 15/19/0
  (reclasificación de C. spiroforme y E. coli ATCC11775 del
  2026-04-30 ya estaba en `apex_strain_classification.yaml`, no en
  la doc). (d) `docs/orchestrator_design.md` §3, §4: refs muertas a
  `aip_tranlac` reemplazadas por `bertaip` (§4) o por un ejemplo
  vigente — `toxinpred3` `["-m", "2"]` (§3). (e) `wrappers/README.md`:
  tabla de `arg_style` corregida — sólo `flagged`/`positional` en
  Phase 1; `wrapper` documentado como Phase-2-only (Phase 1 lo
  rechaza con `NotImplementedError` en `tool_runner.py:193-194`);
  `output_capture` y `pre_command` reconocidas como dimensiones
  independientes en lugar de arg_styles. No hay cambios de código
  ni de runtime — sólo alineación de docs con el estado actual.
  Files: `docs/api.md`, `docs/deployment.md`,
  `docs/orchestrator_design.md`, `wrappers/README.md`,
  `docs/changelog.md`.
- 2026-05-13 — **Memorias académicas: auditoría post-compact y
  corrección de datos del case study Octopus vulgaris**. Tras la
  auditoría sistemática (PubMed para 9 refs clave, cruce contra
  `consolidated.csv` real, code-concordance vs `run_audit.py` y
  `tool_runner.py`) se aplicaron correcciones a `docs/Memoria_*.docx`
  y `docs/PBAP_paper_EN.docx`. Cambios principales: (a) datos del run
  final actualizados al output canónico de fecha 2026-05-03 (AMP
  T1448 y BAP T1511 — antes referenciaba el pre-final T2257/T2005);
  AMP 442.92 s sobre 10 herramientas (con BertAIP, sin
  eippred/aip_tranlac), BAP 1314.67 s (antes 706.96 s), agregado
  29.3 min. (b) Worked example Ov_AMP_001 re-derivado del CSV real:
  selectivity_tag = non_active (antes "pathogen_specific"), min MIC
  40.27 µM en A. muciniphila (antes "2.7 µM en patógeno"), ACP-DPE
  NEG (antes POS), DeepB3P POS (antes NEG), BertAIP NEG score 0.662
  (antes 0.46), agreement_anticancer = split (antes
  consensus_positive). Mantienen structural_score=18 y
  holistic_score=0.5237 (sí coinciden con el CSV real). (c) ES:
  reordenada la bibliografía para alinear numeración con EN (Mayfield
  [1], Rubio-Herrera [2], Hölscher [3], Prypoten [4], …, Tropsha
  [22], OECD [23], Bioconda [24]); refs [22], [23], [24] añadidas en
  cuerpo §2.2 y §2.12 (antes huérfanas); cita "Mayfield et al. [4]"
  corregida a "[1]". (d) EN Table 2: runtimes actualizados con
  valores AMP/BAP reales por herramienta extraídos de
  `tool_health_report.json`; columna `arg_style` renombrada a
  "Invocation profile" para reflejar que `tool_runner.py:193-194`
  solo admite 2 arg_styles (flagged/positional) y que las entradas
  hardcoded_file/stdout/pre_command son dimensiones de
  `output_capture` / `pre_command` colapsadas. (e) EN Discussion: la
  afirmación "Ov_AMP_001 cae en Silver/Bronze AD" se sustituyó por
  una nota explicando que la integración Phase-2 AD en el reporte
  Phase-1 es deuda técnica documentada. Backups
  `docs/*.v3_preaudit.{docx,pdf}` conservados para trazabilidad de
  la evolución. Files: the rebuilt `Memoria_Pipeline_Bioactividad_Peptidos
  .{docx,pdf}` and `PBAP_paper_EN.{docx,pdf}` artefacts on the maintainer's
  local working tree, plus their corresponding python-docx builder scripts
  (kept outside this repo, under the maintainer's local build directory).
- 2026-05-13 — **site/components/agreement.jsx: fix bug del chip de
  consenso para `single_tool`**. La columna "Consensus" de la tabla
  "Intra-category agreement" mostraba "—" cuando el estado era
  `single_tool` (caso de las filas antimicrobial y toxicity en el
  ejemplo). En realidad, el orquestador (`run_audit.py:_compute_agreements`,
  líneas 305-324) asigna `single_tool` cuando exactamente una de las
  tools de la categoría produjo un valor binario no-null — pero ese
  valor binario sí existe (POS o NEG). El "—" era engañoso: sugería
  ausencia de predicción cuando lo que hay es ausencia de **consenso**
  por falta de una segunda tool. Fix: cuando `consensus === 'single_tool'`,
  el chip se deriva ahora de `tools[0].class` (POS si positive, NEG si
  negative), con el color verde/gris correspondiente; el subtítulo
  inferior sigue mostrando `single_tool` para indicar que NO es un
  consenso entre dos tools. Disparará redeploy de Pages.
- 2026-05-13 — **site/index.html: actualizar "9 envs" → "6 envs"**.
  Dos lugares quedaban con la cifra histórica (9, contando los 3
  legacy ml_deepforest/ml_legacy_py38/ml_pycaret que no se
  redistribuyen): el stat box del hero (línea 1232) y la lista de pasos
  de Phase 1 (línea 1262). Ambos actualizados a 6, consistente con el
  badge del README (`conda_envs-6_active`) y con lo que crea
  bootstrap_envs.sh. Etiqueta del paso de Phase 1 ahora dice "6
  isolated tool envs" para distinguir explícitamente que son los envs
  de las 10 tools activas, no incluidos los auxiliares
  (pbap_orchestrator, pbap_demo_api). Disparará redeploy de Pages
  (.github/workflows/pages.yml).
- 2026-05-13 — **Corrección de apellido del autor y declaración de uso
  de IA**. (a) En CITATION.cff, LICENSE, NOTICE y docs/decisions.md el
  apellido del autor se corrige de "Paredes Alfaro" a la forma correcta
  "Paredes Alfonso". El nombre completo legal es Noé Paredes Alfonso;
  el email noeparedesalf@gmail.com era correcto y no cambia. (b)
  README.md gana una sección "Use of generative AI in the development
  of this project" que documenta explícitamente el uso de Claude Opus
  4.7 (Anthropic) y Gemini 3 Pro (Google) como herramientas
  colaborativas, en cuatro ámbitos (code drafting, literatura,
  documentación, discusión metodológica) con curación humana en todos
  los outputs. La concepción del proyecto y todas las decisiones
  científicas se atribuyen explícitamente al autor humano, conforme a
  las guidelines de disclosure de IA de Nature, Elsevier y ICMJE
  (2023-2024). La IA no se lista como coautora.
- 2026-05-13 — **Auditoría total del repo: Tier D (depth)**. Tres
  mejoras de fondo derivadas del audit:
  (a) `docs/glossary.md` overhaul (Tier D + M3): ~16 términos nuevos
  o reescritos (Applicability Domain, APEX strain classification,
  arg_style, dual schema, holistic/structural score, patch
  reproducible, wrapper, bootstrap scripts, Cloudflare Quick Tunnel,
  mitigation shield, allow-list/kill switch, takedown, repro gaps,
  Phase 1/2, project memory, end-of-task checklist, contract,
  index-first, ADR…). Cada entrada enlaza al doc canónico.
  (b) `docs/roadmap.md` sincronizado con realidad: items "Public demo
  (Gradio)", "Bootstrap scripts", "Leakage analysis CD-HIT-2D" y
  "Taxonomic bias analysis" marcados como `done` con enlaces. Nuevo
  item "Phase-2 integration into Phase-1 reports" capturando deuda
  real. "Richer HTML report" pasa a `partially done`.
  (c) `.github/workflows/smoke.yml` gana 3 steps CI nuevos: validate
  bash syntax de los 2 bootstrap scripts (`bash -n`), validate que
  los 5 `.patch` son unified diffs bien formados (--- /+++ /@@), y
  validate que los 6 YAML manifests de envs/ parsean y cubren los 6
  envs core. Sin esto, un commit que rompiera un patch o un manifest
  pasaba el CI silenciosamente.
- 2026-05-13 — **Auditoría total del repo: Tier C (seguridad)**.
  Tres hallazgos del audit cerrados:
  (S1, X-Forwarded-For) — el backend del demo ya no toma ciegamente
  la primera IP del header XFF. Nueva env var `TRUSTED_PROXY_HOSTS`
  (default `127.0.0.1,::1`, que coincide con Cloudflare Tunnel local)
  determina desde qué hosts se confía el header. Si el immediate hop
  no es de un proxy de confianza, XFF se ignora y rate-limit usa la
  IP de la conexión directa. Si sí es de confianza, se walka el chain
  de derecha a izquierda quedándose con la primera IP no trusted —
  esa es la real, no spoofable más allá del primer proxy.
  (S2, CORS) — `ALLOWED_ORIGINS` ya no defaultea a `*`. Default
  ahora es lista vacía → el middleware CORS NO se instala y el
  backend rechaza requests cross-origin de browsers. El operador
  DEBE setear `ALLOWED_ORIGINS=https://<space>.hf.space` (o `*` si
  acepta el trade-off explícitamente) antes de exponer el demo.
  Logged como warning al arranque del servidor.
  (S3, iframe sandbox) — el iframe que embebe el REPORT.html en el
  frontend ahora lleva `sandbox="allow-scripts allow-same-origin"`
  + `referrerpolicy="no-referrer"`. Permite los scripts internos del
  reporte (sortable tables, filters) pero deniega top-navigation,
  form submission, popups y origen distinto. Blast radius mínimo.
- 2026-05-13 — **Auditoría total del repo: Tier A+B (coherencia)**.
  Seis hallazgos cerrados:
  (C1) `CITATION.cff:18` + `CONTRIBUTING.md:41` — URLs
  `pipeline_Work---copia` (nombre interno antiguo del repo) → `pbap`.
  (M1) README badge `conda_envs-9` → `conda_envs-6_active` (refleja
  lo que `bootstrap_envs.sh` realmente crea, sin contar los 3 envs
  históricos de tools standby).
  (M2) `docs/deployment.md` §4 reestructurado en 3 subsecciones:
  "4.1 Core envs (recreatable from this repo)" — los 6 con YAML;
  "4.2 Historical envs for parked/blocked tools (not redistributed)"
  — los 3 históricos sin YAML, ahora marcados explícitamente como
  no reproducibles; "4.3 Auxiliary envs (on demand)" —
  `pbap_orchestrator` (requerido para CLI) y `pbap_demo_api`
  (opcional, demo).
  (M4) `THIRD_PARTY_LICENSES.md:41` — URL upstream de PerseuCPP era
  `goalmeida05/PERSEUcpp` (404 verificado vía curl). Corregido a
  `goalmeida05/PERSEU` (200). Era el único upstream URL realmente
  roto del documento.
  (M5) `NOTICE` — "the 26 third-party prediction tools" → "the
  third-party prediction tools (roughly two dozen evaluated; ten
  currently active — see THIRD_PARTY_LICENSES.md and
  pipeline_viability.md for the authoritative inventory)". Evita
  cifra exacta ambigua entre 25 y 26.
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
