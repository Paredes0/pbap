# Glossary — Términos del Proyecto

Este glosario define los términos científicos, técnicos y operativos utilizados en el Pipeline de Auditoría de Bioactividad.

## 🧬 Términos Científicos

- **Bioactividad**: Capacidad de un péptido para interactuar con un sistema biológico y producir un efecto (ej. matar una bacteria, inhibir una enzima).
- **MIC (Minimum Inhibitory Concentration)**: La concentración más baja de un péptido que previene el crecimiento visible de un microorganismo. Se mide típicamente en µM o µg/mL.
- **Leakage (Fuga de datos)**: Problema en el que secuencias utilizadas para evaluar un modelo ya estaban presentes en su conjunto de entrenamiento, inflando artificialmente los resultados de precisión.
- **Grados de Leakage**:
    - **Gold**: Novedad alta (<40% identidad con training).
    - **Silver**: Novedad media (40-60%).
    - **Bronze**: Novedad baja (60-80%).
    - **Red**: Leakage probable (>80% identidad).
- **Péptido**: Cadena corta de aminoácidos (típicamente <50-100 AA en este proyecto).

## 💻 Términos Técnicos (Arquitectura)

- **Orquestador (Orchestrator)**: Script maestro (`run_audit.py`) que gestiona la ejecución secuencial o paralela de múltiples herramientas.
- **SSH Dispatch**: Técnica para ejecutar tareas pesadas (como CD-HIT) en un servidor Linux remoto mediante SSH, permitiendo que el orquestador principal corra en Windows.
- **Capa 2 (Consenso)**: Lógica que compara los resultados de varias herramientas de la misma categoría para emitir un veredicto de acuerdo (`consensus_positive`) o desacuerdo (`split`).
- **Tool Health**: Estado operativo de una herramienta durante un run (`OK` o `PROBLEMATIC`).
- **Normalización**: Proceso de convertir los diversos formatos de salida de las herramientas a un esquema común (`class_norm`, `score`).

## 🤖 Términos Operativos (Swarm)

- **Swarm**: El ecosistema de agentes IA (Antigravity, Gemini, Claude, etc.) y humanos que colaboran en el desarrollo del proyecto.
- **Memoria del Proyecto**: El conjunto de documentos en `docs/` que sirven como "fuente de verdad" para todos los agentes.
- **Index-First**: Estrategia de los agentes de consultar primero los índices (`INDEX.md`, `INDEX_LOOKUP.md`) antes de leer código masivo.
- **ADR (Architecture Decision Record)**: Registro formal de por qué se tomó una decisión técnica (en `docs/decisions.md`).
- **Roster**: Lista de contribuyentes (humanos e IAs) en `docs/contributors.md`.

---
[? Volver al �ndice](INDEX.md)
