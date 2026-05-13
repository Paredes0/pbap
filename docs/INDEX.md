# 📚 Documentation Index — Peptide Bioactivity Pipeline

> 🚦 **Current project status (May 2026)**
>
> **Phase 1 — User inference** (`scripts/run_audit.py`): operational.
> 10 integrated tools, 7 categories, dual schema, agreement, APEX
> selectivity, hierarchical ranking (structural + holistic), reports in
> HTML/MD/CSV/JSON/XLSX. This is what runs when a user invokes
> `python scripts/run_audit.py --input my.fasta`.
>
> **Phase 2 — Scientific audit** (`bin/audit_pipeline.sh`): analysis
> tools implemented (positive-mining, training-set extraction, CD-HIT-2D
> leakage analysis with Gold/Silver/Bronze/Red grading, taxonomic bias,
> QC, global report). **Not integrated into Phase 1 output** — its
> results are offline validation artifacts, not per-peptide labels in
> the user report. Production integration is future work (see
> `roadmap.md`).
>
> If a tool or document describes the Gold/Silver/Bronze/Red system,
> assume **Phase 2** unless stated otherwise.

This document centralizes access to all technical, methodological and
operational documentation of the project.

## 🏗️ Architecture and foundations
- [System architecture](architecture.md): overview of components and their interaction.
- [API reference](api.md): module, class and function reference for `audit_lib`.
- [Data structures](data.md): FASTA handling, databases and I/O formats.
- [Conventions and standards](conventions.md): code style, naming, best practices.
- [Glossary](glossary.md): definitions of key bioinformatics and workflow terms.

## 🧪 Methodology and analysis
- [Context and objective](context_objective.md): scientific justification, goals, scope.
- [Leakage analysis](leakage_analysis.md) **[Phase 2]**: data leakage investigation and mitigation. Gold/Silver/Bronze/Red grading, applied only in the scientific audit flow.
- [Taxonomic bias analysis](taxonomic_analysis.md): biases and diversity in sequence origin.
- [Pipeline viability](pipeline_viability.md): technical, operational and scientific feasibility analysis (26-tool audit history).
- [Orchestrator design](orchestrator_design.md): execution logic, process management, tool flow.
- [License audit](licenses_audit.md): legal review of third-party software and data permissions.
- [External-artifact verification](verify_external_artifacts.md): mandatory pre-infra rule.

## 📅 Status and planning
- [Roadmap](roadmap.md): main milestones and development timeline.
- [TODO](todo.md): pending work and known issues.
- [Changelog](changelog.md): version history.
- [Decisions (ADR)](decisions.md): architectural decisions and their justification.

## 🚀 Deployment
- [Deployment guide](deployment.md): installation and bring-up across environments.

## 🧭 Quick navigation for code
- [Function/script lookup table](INDEX_LOOKUP.md): jump table to canonical functions in `audit_lib/` and scripts in `scripts/`.

---
*Last updated: May 2026*
