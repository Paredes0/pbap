# 📚 Índice de Documentación - Pipeline de Bioactividad

> 🚦 **Estado actual del proyecto (Mayo 2026)**
>
> **Fase 1 — Inferencia de usuario** (`scripts/run_audit.py`): operativa.
> 10 herramientas integradas, 7 categorías, schema dual, agreement,
> APEX selectivity, ranking jerárquico (structural + holistic),
> reportes en HTML/MD/CSV/JSON/XLSX. Es lo que se ejecuta cuando un
> usuario corre `python scripts/run_audit.py --input mi.fasta`.
>
> **Fase 2 — Auditoría científica** (`bin/audit_pipeline.sh`):
> herramientas de análisis implementadas (mineria de positivos,
> extracción de training, leakage analysis CD-HIT-2D con grados
> Gold/Silver/Bronze/Red, sesgo taxonómico, QC, reporte global).
> **No integrada en el output de Fase 1** — sus resultados son
> artefactos offline de validación, no etiquetas por péptido en
> el reporte del usuario. La integración en producción es trabajo
> futuro (ver `roadmap.md`).
>
> Si una herramienta o documento describe el sistema Gold/Silver/
> Bronze/Red, asume **Fase 2** salvo declaración explícita en
> contrario.

Este documento centraliza el acceso a toda la documentación técnica, metodológica y operativa del proyecto.

## 🏗️ Arquitectura y Fundamentos
- [Arquitectura del Sistema](architecture.md): Visión general de los componentes y su interacción.
- [Referencia de API](api.md): Detalles técnicos de los módulos, clases y funciones.
- [Estructura de Datos](data.md): Manejo de archivos FASTA, bases de datos y formatos de entrada/salida.
- [Convenciones y Estándares](conventions.md): Guías de estilo de código, nomenclatura y mejores prácticas.
- [Glosario de Términos](glossary.md): Definiciones de conceptos clave en bioinformática y el flujo de trabajo.

## 🧪 Metodología y Análisis
- [Objetivo y Contexto](context_objective.md): Justificación científica, objetivos y alcance del pipeline.
- [Análisis de Leakage](leakage_analysis.md) **[Fase 2]**: Investigación y mitigación de contaminación de datos entre conjuntos. Sistema de graduación Gold/Silver/Bronze/Red, aplicado solo en el flujo de auditoría científica.
- [Análisis Taxonómico](taxonomic_analysis.md): Evaluación de sesgos y diversidad en el origen de las secuencias.
- [Viabilidad del Pipeline](pipeline_viability.md): Análisis de factibilidad técnica, operativa y científica.
- [Diseño del Orquestador](orchestrator_design.md): Lógica de ejecución, gestión de procesos y flujo de herramientas.
- [Auditoría de Licencias](licenses_audit.md): Revisión legal de permisos y restricciones de uso de software y datos de terceros.
- [Verificación de Artefactos Externos](verify_external_artifacts.md): Protocolos de validación para pesos de modelos y recursos descargados.

## 📅 Estado y Planificación
- [Hoja de Ruta (Roadmap)](roadmap.md): Hitos principales y cronograma de desarrollo.
- [Lista de Tareas (TODO)](todo.md): Seguimiento de actividades pendientes y errores conocidos.
- [Registro de Cambios (Changelog)](changelog.md): Historial detallado de versiones y actualizaciones.
- [Registro de Decisiones (ADR)](decisions.md): Documentación de decisiones arquitectónicas significativas y su justificación.

## 🚀 Despliegue y Colaboración
- [Guía de Despliegue](deployment.md): Instrucciones para la instalación y puesta en marcha en diferentes entornos.
- [Guía de Contribución](contributors.md): Información sobre el equipo, roles y cómo colaborar en el proyecto.

## 📂 Archivo
Documentación de referencia histórica o versiones obsoletas:
- [Registro de Compilación de Entornos (2026-05)](_archive/2026-05/envs_build_log.md)
- [Índice Legado](_archive/2026-05/legacy_index.md)
- [Listado de Archivos Obsoletos](_archive/2026-05/obsolete_files.md)

---
*Última actualización: Mayo 2026*
