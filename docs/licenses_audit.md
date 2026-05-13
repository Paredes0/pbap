# License Audit — Pipeline Tools

**Date**: 2026-04-27.
**Purpose**: identify which pipeline tools are compatible with (a)
deployment as a commercial SaaS and (b) scientific publication.
**Coverage**: 12 viable tools (the 11 OK ones + hypeptox_fuse once the
user completes the manual download).

---

## Executive summary

| Category | Count | Tools | Action for SaaS |
|---|---|---|---|
| **Permissive (Apache 2.0)** | 1 | hypeptox_fuse | ✅ Free, mandatory attribution |
| **Copyleft (GPL-3.0)** | 4 | toxinpred3, antibp3, hemopi2, eippred | ⚠️ OK via subprocess (aggregation §5), attribution + GPL-3 notice in TOS |
| **Restrictive academic (Penn custom)** | 1 | apex | ❌ Requires commercial license from Penn |
| **No explicit license (= all rights reserved)** | 6 | hemodl, deepb3p, deepbp, perseucpp, acp_dpe, aip_tranlac | ❌ Requires explicit permission from each author |

**Tools 100% free for commercial SaaS with no extra paperwork: 5/12**
(4 GPL-3 + 1 Apache).
**Tools that require contacting authors/institutions: 7/12** (6 with no
license + apex).

---

## Detailed matrix

| Tool | License | File | Bioactivity category | Commercial SaaS | Academic publication | Comments |
|---|---|---|---|---|---|---|
| **hypeptox_fuse** | Apache 2.0 | LICENSE | toxicity | ✅ Free | ✅ Free | Mandatory attribution + NOTICE file. Ideal. |
| **toxinpred3** | GPL-3.0 | LICENSE | toxicity | ⚠️ OK as subprocess | ✅ | raghavagps lab. Aggregation argument: subprocess does not count as linking. |
| **antibp3** | GPL-3.0 | LICENSE | antimicrobial | ⚠️ Same | ✅ | Same lab. Same reasoning. |
| **hemopi2** | GPL-3.0 | LICENSE.txt | hemolytic | ⚠️ Same | ✅ | Same lab. |
| **eippred** | GPL-3.0 | LICENSE | ecoli_inhibitor | ⚠️ Same | ✅ | Same lab. |
| **apex** | Penn Software APEX (custom) | LICENSE | antimicrobial (34 strains) | ❌ NO without Penn commercial license | ✅ Cite | "Non-profit research only". Explicit clauses prohibit distribution to commercial third parties without written permission from Penn. Contact: Penn Center for Innovation, 215-898-9591. |
| **hemodl** | NONE | (absent) | hemolytic | ❌ All rights reserved | ⚠️ Risk | GitHub user `abcair`. README does not mention license. Default copyright. |
| **deepb3p** | NONE | (absent) | bbb | ❌ Same | ⚠️ | `GreatChenLab` lab. README does not mention license. |
| **deepbp** | NONE | (absent) | anticancer | ❌ Same | ⚠️ | Author Zhou-Jianren. README does not mention license. |
| **perseucpp** | NONE | (absent) | cpp | ❌ Same | ⚠️ | Author goalmeida05. README does not mention license. |
| **acp_dpe** | NONE | (absent) | anticancer | ❌ Same | ⚠️ | Author CYJ-sudo. README does not mention license. |
| **aip_tranlac** | NONE | (absent) | anti-inflammatory | ❌ Same | ⚠️ | Author unknown (look up the paper). README does not mention license. |

---

## Brief legal analysis (not legal advice; consult a lawyer)

### Apache 2.0 (hypeptox_fuse)
- Allows commercial use, modification, distribution, private use.
- Requires: include a copy of the license, attribution to the authors,
  mark changes if you modify the code.
- Compatible with SaaS without restriction.

### GPL-3.0 (4 tools from raghavagps)
- **Strong copyleft**: if you "link" GPL-3 code with yours, your entire
  code must also be GPL-3.
- **"Aggregation" loophole §5**: if your program **launches the tool
  as a subprocess** and only communicates via files/stdin/stdout,
  that is aggregation (aggregate), NOT linking. Your code keeps its
  own license.
- Our `audit_lib/tool_runner.py` uses `micromamba run` + subprocess →
  falls under aggregation → safe for SaaS.
- **Obligations**:
  - Attribute the authors in docs and TOS.
  - If you redistribute GPL-3 binaries/repos to your users, you must
    also offer them the source code and the license.
  - If you modify a GPL-3 tool (as we did with patches to hemopi2,
    hemodl, deepb3p, etc.), the modifications are also GPL-3 — but
    that only matters if you redistribute.
- **GPL-3 §13 mentions AGPL**: AGPL closes the "SaaS loophole" by
  requiring source publication when the software is offered over a
  network. **GPL-3 has no such clause** — the SaaS loophole stays
  open for pure GPL-3.

### Penn academic license (apex)
- Verbatim from the LICENSE: *"non-profit research, non-commercial, or
  academic purposes only"*, *"shall not distribute Software or
  Modifications to any commercial third parties without the prior
  written approval of Penn"*.
- **Directly blocks commercial SaaS**. For commercial use: contact
  Penn Center for Innovation (215-898-9591).
- If the SaaS is only for academic clients without charging
  commercially, it is still grey — the license restricts distribution
  to "commercial third parties" even when the use is academic. Better
  to seek clarification from Penn.

### No license (6 tools)
- In the absence of a LICENSE, the code is **under default copyright**
  (Berne Convention, national laws).
- Being on public GitHub does NOT imply an open license. The GitHub
  TOS lets others **view** and **fork**, but NOT execute commercially
  without the rights holder's permission.
- For SaaS: **you need an email from the author granting permission**
  (better: a formal license like MIT / Apache / GPL).
- For academic publication: risk is low if you only CITE and do not
  redistribute the code, but requesting permission is still
  advisable.

---

## Three SaaS deployment scenarios

### Scenario A — Conservative (only Apache + GPL-3 subprocess)
- **Tools**: hypeptox_fuse, toxinpred3, antibp3, hemopi2, eippred
  (5 tools).
- **Categories**: toxicity (×2), antimicrobial, hemolytic,
  ecoli_inhibitor → 4 unique categories.
- **Required actions**: add attribution + GPL-3 text to TOS and
  documentation. Zero external follow-up.
- **Production-ready**: now.

### Scenario B — Restricted academic (A + apex with limited TOS)
- **Tools**: A + apex (6 tools).
- **Categories**: + antimicrobial multi-strain (34 strains).
- **Required actions**: TOS that restricts use to non-commercial
  research. Optionally notify Penn.
- **Risk**: if a commercial user accesses without restriction, you
  infringe the Penn license.

### Scenario C — Full (all tools, requires follow-up)
- **Tools**: 12.
- **Categories**: 8 (toxicity, antimicrobial, hemolytic,
  ecoli_inhibitor, anticancer, bbb, cpp, anti_inflammatory).
- **Required actions**:
  - Email to 6 authors of license-less tools (template below).
  - Contact Penn Center for Innovation for apex.
  - Wait for responses (~2–6 weeks).
  - Document each response as evidence.
- **Availability**: uncertain (depends on responses).

**Recommendation**: start with Scenario A for launch; in parallel
manage emails to escalate to B and C as responses arrive.

---

## Email template for license-less authors

Customize `<toolname>`, `<github_url>` and final details:

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
<your name>
<your institution / project>
```

### Contact addresses

| Tool | GitHub user / author | Strategy to find email |
|---|---|---|
| hemodl | `abcair` | Search the paper on Google Scholar; GitHub profile may have an email |
| deepb3p | `GreatChenLab` | Lab account; find the lab leader and an institutional email |
| deepbp | `Zhou-Jianren` | Repo `bioactive-peptides`. Look up the paper. |
| perseucpp | `goalmeida05` | PERSEU thesis/paper. |
| acp_dpe | `CYJ-sudo` | Look up the paper "ACP-DPE". |
| aip_tranlac | (author unclear in repo) | Look up the paper "AIP-TranLAC" |
| apex | Fangping Wan / Penn | Penn Center for Innovation: 215-898-9591. Author email: Nature Biomed Eng 2024 article. |

---

## For scientific publication

- **Citation**: cite each tool's original paper in the manuscript.
  Standard practice and does not require a license.
- **Redistribution of weights/binaries**: do NOT redistribute weights
  or binaries of license-less tools without explicit permission.
- **Reproducibility**: the manuscript can describe how to invoke each
  tool in its original repo; readers download them themselves.
- **Pipeline code**: you can release the orchestrator
  (`scripts/run_audit.py`, `audit_lib/`) under whichever license you
  choose (MIT / Apache / GPL). It is your code + subprocess aggregation
  — it does not incorporate code from others.
- **Patches to GPL-3 tools**: your patches are GPL-3 derivatives → if
  you redistribute them (e.g. in supplementary material), they are
  GPL-3.

---

## Immediate actions

1. **Add LICENSE to your pipeline**: decide MIT / Apache 2.0 / GPL-3 /
   PolyForm Noncommercial and create `LICENSE` at the repo root. As of
   v0.1.0 the public release uses PolyForm Noncommercial 1.0.0.
2. **Create `NOTICE` and `THIRD_PARTY_LICENSES.md`**: list each
   integrated tool with its license and attribution.
3. **SaaS TOS draft** with a "Software components and licenses"
   section listing the 5 tools of Scenario A.
4. **Emails** to the 6 license-less authors (Scenario C). If responses
   are fast, escalate to full SaaS.
5. **Penn contact** for apex if you want that category in commercial
   SaaS.
6. **Legal review**: once you have a TOS draft, one hour with a lawyer
   specialized in open source / SaaS will confirm whether the
   aggregation argument is solid in your jurisdiction.

---

## When to update this document

- When a response arrives from any author (record date, terms, full
  email saved separately as evidence).
- When a new tool is integrated into the pipeline (audit its license
  before adding to the matrix).
- If a tool updates its LICENSE in the repo (re-check on
  `git pull`).

---
[← Back to Index](INDEX.md)
