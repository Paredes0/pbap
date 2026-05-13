# Auditoría de Licencias — Tools del Pipeline

**Fecha**: 2026-04-27.
**Propósito**: identificar qué tools del pipeline son compatibles con (a) despliegue como SaaS comercial y (b) publicación científica.
**Cobertura**: 12 tools viables (los 11 OK + hypeptox_fuse en cuanto el usuario complete la descarga manual).

---

## Resumen ejecutivo

| Categoría | Count | Tools | Acción para SaaS |
|---|---|---|---|
| **Permisiva (Apache 2.0)** | 1 | hypeptox_fuse | ✅ Libre, atribución obligatoria |
| **Copyleft (GPL-3.0)** | 4 | toxinpred3, antibp3, hemopi2, eippred | ⚠️ OK vía subprocess (aggregation §5), atribución + GPL-3 notice en TOS |
| **Académica restrictiva (Penn custom)** | 1 | apex | ❌ Requiere licencia comercial de Penn |
| **Sin licencia explícita (= all rights reserved)** | 6 | hemodl, deepb3p, deepbp, perseucpp, acp_dpe, aip_tranlac | ❌ Requiere permiso explícito de cada autor |

**Tools 100% libres para SaaS comercial sin gestión adicional: 5/12** (4 GPL-3 + 1 Apache).
**Tools que requieren contacto con autores/instituciones: 7/12** (6 sin licencia + apex).

---

## Matriz detallada

| Tool | Licencia | Archivo | Categoría bioactividad | SaaS comercial | Publicación académica | Comentarios |
|---|---|---|---|---|---|---|
| **hypeptox_fuse** | Apache 2.0 | LICENSE | toxicity | ✅ Libre | ✅ Libre | Atribución obligatoria + NOTICE file. Ideal. |
| **toxinpred3** | GPL-3.0 | LICENSE | toxicity | ⚠️ OK como subprocess | ✅ | Lab raghavagps. Aggregation argument: subprocess no cuenta como linking. |
| **antibp3** | GPL-3.0 | LICENSE | antimicrobial | ⚠️ Igual | ✅ | Mismo lab. Mismo razonamiento. |
| **hemopi2** | GPL-3.0 | LICENSE.txt | hemolytic | ⚠️ Igual | ✅ | Mismo lab. |
| **eippred** | GPL-3.0 | LICENSE | ecoli_inhibitor | ⚠️ Igual | ✅ | Mismo lab. |
| **apex** | Penn Software APEX (custom) | LICENSE | antimicrobial (34 strains) | ❌ NO sin licencia comercial Penn | ✅ Cita | "Non-profit research only". Cláusulas explícitas que prohíben distribución a terceros comerciales sin permiso escrito de Penn. Contactar Penn Center for Innovation: 215-898-9591. |
| **hemodl** | NINGUNA | (ausente) | hemolytic | ❌ All rights reserved | ⚠️ Riesgo | GitHub user: `abcair`. README sin mención. Default copyright. |
| **deepb3p** | NINGUNA | (ausente) | bbb | ❌ Igual | ⚠️ | Lab `GreatChenLab`. README sin mención. |
| **deepbp** | NINGUNA | (ausente) | anticancer | ❌ Igual | ⚠️ | Autor Zhou-Jianren. README sin mención. |
| **perseucpp** | NINGUNA | (ausente) | cpp | ❌ Igual | ⚠️ | Autor goalmeida05. README sin mención. |
| **acp_dpe** | NINGUNA | (ausente) | anticancer | ❌ Igual | ⚠️ | Autor CYJ-sudo. README sin mención. |
| **aip_tranlac** | NINGUNA | (ausente) | anti-inflammatory | ❌ Igual | ⚠️ | Autor desconocido (buscar paper). README sin mención. |

---

## Análisis legal sintético (no es asesoramiento, consultar abogado)

### Apache 2.0 (hypeptox_fuse)
- Permite uso comercial, modificación, distribución, uso privado.
- Requiere: incluir copia de la licencia, atribución a los autores, marcar cambios si modificas el código.
- Compatible con SaaS sin restricciones.

### GPL-3.0 (4 tools de raghavagps)
- Es **copyleft fuerte**: si "linkeas" código GPL-3 con el tuyo, tu código entero también debe ser GPL-3.
- **Loophole "agregación" §5**: si tu programa **lanza el tool como subprocess** y solo se comunica vía archivos/stdin/stdout, eso es agregación (aggregate), NO linking. Tu código mantiene su propia licencia.
- Nuestro `audit_lib/tool_runner.py` usa `micromamba run` + subprocess → cae en aggregation → safe para SaaS.
- **Obligaciones**:
  - Atribuir a los autores en docs y TOS.
  - Si redistribuyes los binarios/repos GPL-3 a tus usuarios, debes ofrecerles también el código fuente y la licencia.
  - Si modificas un tool GPL-3 (como hicimos con patches a hemopi2/hemodl/deepb3p/etc.), las modificaciones también son GPL-3 — pero esto solo importa si redistribuyes.
- **GPL-3 §13 menciona AGPL**: AGPL cierra el "SaaS loophole" obligando a publicar fuente cuando ofreces el software por red. **GPL-3 NO tiene esta cláusula** — el SaaS-loophole sigue abierto para GPL-3 puro.

### Licencia académica Penn (apex)
- Cita textual del LICENSE: *"non-profit research, non-commercial, or academic purposes only"*, *"shall not distribute Software or Modifications to any commercial third parties without the prior written approval of Penn"*.
- **Bloquea SaaS comercial directamente**. Para uso comercial: contactar Penn Center for Innovation (215-898-9591).
- Si el SaaS es solo para clientes académicos sin cobrar comercialmente, sigue siendo gris — la licencia restringe distribución a "comerciales" aunque el uso sea académico. Mejor pedir clarificación a Penn.

### Sin licencia (6 tools)
- En ausencia de LICENSE, el código está **bajo copyright por defecto** (Berne Convention, leyes nacionales).
- Que esté en GitHub público NO implica licencia abierta. GitHub TOS permite a otros **ver** y **forkear**, pero NO ejecutar comercialmente sin permiso del titular.
- Para SaaS: **necesitas un email del autor concediendo permiso** (mejor licencia formal tipo MIT/Apache/GPL).
- Para publicación académica: el riesgo es bajo si solo CITAS y no redistribuyes su código, pero sigue siendo recomendable solicitar permiso.

---

## Tres escenarios de despliegue SaaS

### Escenario A — Conservador (solo Apache + GPL-3 subprocess)
- **Tools**: hypeptox_fuse, toxinpred3, antibp3, hemopi2, eippred (5 tools).
- **Categorías**: toxicity (×2), antimicrobial, hemolytic, ecoli_inhibitor → 4 categorías únicas.
- **Acciones requeridas**: añadir atribución + texto GPL-3 a TOS y documentación. Cero gestión externa.
- **Listo para producción**: ahora.

### Escenario B — Académico restringido (A + apex con TOS limitado)
- **Tools**: A + apex (6 tools).
- **Categorías**: + antimicrobial multi-strain (34 cepas).
- **Acciones requeridas**: TOS que restrinja uso a investigación no comercial. Notificar a Penn opcionalmente.
- **Riesgo**: si un usuario comercial accede sin restricción, infringes la licencia Penn.

### Escenario C — Pleno (todas las tools, requiere gestión)
- **Tools**: 12.
- **Categorías**: 8 (toxicity, antimicrobial, hemolytic, ecoli_inhibitor, anticancer, bbb, cpp, anti_inflammatory).
- **Acciones requeridas**:
  - Email a 6 autores de tools sin licencia (template abajo).
  - Contacto con Penn Center for Innovation para apex.
  - Esperar respuestas (~2-6 semanas).
  - Documentar cada respuesta como evidencia.
- **Disponibilidad**: incierta (depende de respuestas).

**Recomendación**: empezar con Escenario A para lanzamiento; en paralelo gestionar emails para escalar a B y C cuando lleguen respuestas.

---

## Plantilla email para autores sin licencia

Personalizar `<toolname>`, `<github_url>` y datos finales:

```
Subject: License clarification request for <toolname> (commercial / SaaS use)

Dear Dr. <last_name>,

I am developing a peptide bioactivity audit pipeline that integrates several
open-source predictors, including <toolname> from your repository at
<github_url>. I plan to deploy the pipeline as a SaaS for both academic and
commercial users, and to publish the methodology in a peer-reviewed venue.

Your tool is published as open-source on GitHub but I could not find an explicit
LICENSE file. I would like to clarify whether you could grant permission for
commercial use of <toolname> as part of an aggregated pipeline (the tool runs
as a subprocess; its source code is not modified or redistributed). Of course
your work would be cited prominently, and I would be happy to share the
manuscript with you before submission.

Could you confirm under which terms I may use <toolname> in:
  (a) academic/research deployments
  (b) commercial SaaS deployments

If a formal license (e.g., MIT, Apache 2.0, GPL-3.0) would be acceptable to you,
I'd be happy to discuss. Adding a LICENSE file to the repository would also
clarify usage for the broader community.

Thank you for your time and for sharing <toolname> with the field.

Best regards,
<tu nombre>
<tu institución / proyecto>
```

### Direcciones de contacto

| Tool | GitHub user / autor | Estrategia para encontrar email |
|---|---|---|
| hemodl | `abcair` | Buscar paper en Google Scholar; perfil GitHub puede tener email |
| deepb3p | `GreatChenLab` | Lab account; buscar líder del lab y email institucional |
| deepbp | `Zhou-Jianren` | Repo `bioactive-peptides`. Buscar paper. |
| perseucpp | `goalmeida05` | Tesis/paper PERSEU. |
| acp_dpe | `CYJ-sudo` | Buscar paper "ACP-DPE". |
| aip_tranlac | (autor en repo no obvio) | Buscar paper "AIP-TranLAC" |
| apex | Fangping Wan / Penn | Penn Center for Innovation: 215-898-9591. Email del autor: artículo Nature Biomed Eng 2024. |

---

## Para la publicación científica

- **Citación**: cita el paper original de cada tool en el manuscrito. Esto es estándar y no requiere licencia.
- **Redistribución de pesos/binarios**: NO redistribuyas pesos ni binarios de los tools sin licencia explícita.
- **Reproducibilidad**: el manuscrito puede describir cómo invocar cada tool en su repo original; los lectores los descargan ellos mismos.
- **Código del pipeline propio**: puedes liberar el orchestrator (`scripts/run_audit.py`, `audit_lib/`) bajo la licencia que elijas (MIT/Apache/GPL). Es código tuyo + agregación de subprocess calls — no incorpora código de otros.
- **Patches a tools GPL-3**: tus patches son derivados de GPL-3 → si los redistribuyes (p. ej. en supplementary material), van bajo GPL-3.

---

## Acciones inmediatas

1. **Añadir LICENSE a tu pipeline**: decide MIT / Apache 2.0 / GPL-3 y crea `LICENSE` en raíz del repo. Recomendado: Apache 2.0 (compatible con todo lo que uses).
2. **Crear `NOTICE` y `THIRD_PARTY_LICENSES.md`**: lista cada tool integrado con su licencia y atribución.
3. **Borrador TOS** del SaaS con sección "Software components and licenses" listando los 5 del Escenario A.
4. **Emails** a los 6 autores sin licencia (escenario C). Si respuestas son rápidas, escalar a SaaS pleno.
5. **Contacto Penn** para apex si quieres incluir esa categoría en SaaS comercial.
6. **Revisión legal**: cuando tengas el TOS borrador, una hora con un abogado especializado en open source / SaaS confirma que los argumentos de aggregation son sólidos en tu jurisdicción.

---

## Cuándo actualizar este doc

- Cuando llegue respuesta de algún autor (registrar fecha, términos, email completo guardado aparte como evidencia).
- Cuando un tool nuevo se integre al pipeline (auditar su licencia antes de añadirlo a la matriz).
- Si un tool actualiza su LICENSE en el repo (revisar al hacer `git pull`).

---
[? Volver al �ndice](INDEX.md)
