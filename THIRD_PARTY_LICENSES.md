# Third-Party Tools — Licenses and Attribution

This document lists every third-party prediction tool that the Peptide
Bioactivity Audit Pipeline (PBAP) is designed to orchestrate. **None of
these tools is bundled with this repository.** You must clone each tool
from its upstream source and comply with its license independently.

The pipeline interacts with every tool as an independent subprocess
(via `audit_lib/tool_runner.py` and `micromamba run`). Under most copyleft
licenses (notably GPL-3.0), this aggregation does not extend the upstream
license to the orchestrator itself. However, **redistributing the upstream
tools or their model weights** *is* governed by the upstream license, and
this repository does not redistribute them.

If you intend to use the pipeline commercially, you must additionally
obtain a commercial license for **this orchestrator** (see `LICENSE`).

---

## Status legend

| Symbol | Meaning |
|---|---|
| ✅ | Tool is integrated and runnable through the pipeline today |
| ⏸ | Tool is integrated configuration-wise but currently parked (RAM, login, etc.) |
| ❌ | Tool was evaluated and is blocked or removed (no integration available) |

---

## Active and integrated tools (10)

| Tool | Status | License | Upstream | Citation |
|---|---|---|---|---|
| **ToxinPred3** | ✅ | GPL-3.0 | <https://github.com/raghavagps/toxinpred3> | Rathore et al., *Comput. Biol. Med.* 2024. DOI: 10.1016/j.compbiomed.2024.108926 |
| **AntiBP3** | ✅ | GPL-3.0 | <https://github.com/raghavagps/antibp3> | Bajiya et al., *Antibiotics* 2024;13(2):168. DOI: 10.3390/antibiotics13020168 |
| **HemoPI2** | ✅ | GPL-3.0 | <https://github.com/raghavagps/hemopi2> | Rathore et al., *Commun. Biol.* 2025. DOI: 10.1038/s42003-025-07615-w |
| **HemoDL** | ✅ | *No explicit LICENSE* (all rights reserved by default) | <https://github.com/abcair/HemoDL> | Yang et al., *Anal. Biochem.* 2024. DOI: 10.1016/j.ab.2024.115523 |
| **DeepB3P** | ✅ | *No explicit LICENSE* | <https://github.com/GreatChenLab/DeepB3P> | Tang et al., *J. Adv. Res.* 2025. DOI: 10.1016/j.jare.2024.08.002 |
| **DeepBP** | ✅ | *No explicit LICENSE* | <https://github.com/Zhou-Jianren/bioactive-peptides> | Zhang et al., *BMC Bioinformatics* 2024. DOI: 10.1186/s12859-024-05974-5 |
| **APEX (Penn)** | ✅ | Penn Software APEX (custom, non-commercial only) | <https://gitlab.com/machine-biology-group-public/apex> | Wan et al., *Nat. Biomed. Eng.* 2024. DOI: 10.1038/s41551-024-01201-x |
| **PerseuCPP** | ✅ | *No explicit LICENSE* | <https://github.com/goalmeida05/PERSEUcpp> | Bernardes-Loch et al., *Bioinformatics Advances* 2025. DOI: 10.1093/bioadv/vbaf213 |
| **ACP-DPE** | ✅ | *No explicit LICENSE* | <https://github.com/CYJ-sudo/ACP-DPE> | Huang et al., *IET Syst. Biol.* 2025. DOI: 10.1049/syb2.70010 |
| **BertAIP** | ✅ | *No explicit LICENSE* | <https://github.com/ying-jc/BertAIP> | ying-jc, GitHub (under review) |

## Parked / deferred (5)

These are tools whose integration is implemented but blocked by external
factors (RAM, login walls, manual hydration of LFS pointers, etc.).

| Tool | Status | License | Upstream | Blocker |
|---|---|---|---|---|
| **AntiFungiPept** | ⏸ | *No explicit LICENSE* | upstream private/LFS | Git-LFS pointers not hydrated |
| **HyPepTox-Fuse** | ⏸ | Apache-2.0 | <https://github.com/duongttr/HyPepToxFuse> | RAM ≥ 32 GB to load 3 PLMs concurrently |
| **BERT-AmPEP60** | ⏸ | *No explicit LICENSE* | upstream behind SharePoint MPU | Institutional login wall |
| **pLM4Alg** | ⏸ | *No explicit LICENSE* | upstream behind KSU SharePoint | Institutional login wall |
| **AVPpred-BWR** | ⏸ | *No explicit LICENSE* | upstream + Baidu Netdisk | Baidu Netdisk for cached features |

## Blocked / not integrated (10)

These tools were evaluated but cannot be wired into the pipeline as-is
(training-script-as-inference patterns, missing weights, missing FASTA
input adapters, dependency conflicts).

| Tool | License | Reason |
|---|---|---|
| **mACPpred2** | *No explicit LICENSE* | `bio_embeddings==0.2.2` dependency incompatible with current PyTorch |
| **AAPL** | *No explicit LICENSE* | Pre-computed 4335-D feature vector required; no FASTA→features extractor |
| **IF-AIP** | *No explicit LICENSE* | Training scripts only (train_test_split + CV); no inference function |
| **MFE-ACVP** | *No explicit LICENSE* | Requires ESMAtlas + NetSurfP-3.0 web services |
| **Multimodal-AOP** | *No explicit LICENSE* | Training script only, no published checkpoint |
| **AFP-MVFL** | *No explicit LICENSE* | Trains on pre-extracted feature CSVs, no FASTA input |
| **AntiAging-FL** | *No explicit LICENSE* | `predict.py` performs training + RFE/RFECV |
| **DeepForest-HTP** | *No explicit LICENSE* | Empty `Features/` and `Model Training/` directories |
| **StackTHP** | *No explicit LICENSE* | Colab notebook only, hardcoded `/content/drive/...` paths |
| **CPPpred-En** | *No explicit LICENSE* | Six PLMs (~30 GB) + multi-step feature pipeline; no orchestrator |

## Removed (1)

| Tool | Reason for removal |
|---|---|
| **EIPpred** | scikit-learn version conflict irresolvable inside shared `ml` env. Code kept on disk locally for traceability but disconnected from the orchestrator. |

---

## License notes

### Apache-2.0
- Permissive. Attribution required (see NOTICE).
- Compatible with both academic and commercial use.

### GPL-3.0
- Strong copyleft applies to **derivative works** (linked code).
- The pipeline invokes each tool as a subprocess; under the GPL "mere
  aggregation" clause (§5), this does not extend the GPL to the
  orchestrator.
- If you **modify and redistribute** any GPL-3 tool, your modifications
  remain under GPL-3. This repository does not redistribute upstream
  tools, so the obligation only arises if you do.
- GPL-3.0 does **not** carry an Affero (AGPL) network clause; a SaaS
  deployment of an unmodified GPL-3 tool does not trigger a source-
  publication obligation. The orchestrator's PolyForm Noncommercial
  License does, however, prohibit any commercial SaaS deployment without
  a separate commercial license from the orchestrator's author.

### Penn Software APEX (custom)
- The APEX license explicitly limits use to "non-profit research,
  non-commercial, or academic purposes". Commercial deployment requires
  a separate license from the Penn Center for Innovation.

### Tools without an explicit LICENSE file
- A repository on GitHub *without* an explicit LICENSE file does **not**
  grant any open-source rights. Default copyright applies; you may
  *view* and *fork* per GitHub's Terms of Service, but execution and
  redistribution require the author's permission.
- This repository does not redistribute any of these tools. If you
  intend to use them, you need to contact the upstream authors for
  permission. See `docs/licenses_audit.md` for a template email.

---

## How to update this file

- When a new tool is integrated, add a row with its license, upstream
  URL and citation.
- When an upstream tool changes its license, update the row and note
  the date in `docs/changelog.md`.
- When a tool is unblocked from the parked list, move its row to the
  active section.

---
[← Back to README](README.md)
