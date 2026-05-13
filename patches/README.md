# Patches applied to upstream tools

These patches make a handful of integrated tools usable in batch /
non-interactive mode. They are applied on top of a fresh `git clone`
of each tool's upstream — none of them is a fork; the upstream
repository is the source of truth.

`scripts/bootstrap_tools.sh` (one level up) clones each tool and then
applies the matching patch automatically. If you prefer to do it
manually, the recipe is the same for every tool:

```bash
cd Dataset_Bioactividad/Tool_Repos/<tool>/
git apply ../../../patches/<tool>.patch
```

## What each patch fixes

| Tool | File touched | Lines | Why |
|---|---|---|---|
| `hemodl` | `source/predict.py` | +8 / −5 | Argparse + I/O normalization so the orchestrator can pass a FASTA path and read predictions back from a known location. |
| `deepb3p` | `model/deepb3p.py`, `utils/config.py` | +2 / −2 | Config path fix for the model checkpoints when running outside the upstream's working directory. |
| `apex` | `predict.py`, `test_seqs.txt` | +7 / −6 | `torch.load(..., map_location='cpu', weights_only=False)` (PyTorch ≥ 2.x compatibility) + `.cuda()` → CPU on lines 96 and 107 (so the CPU-basic Linux host can run it without a GPU). |
| `perseucpp` | `PERSEUcpp.py` | +37 / −32 | New `__main__` block with argparse before the legacy interactive `input()` prompt + extension allow-list relaxed from `.fasta` only to `('fasta','fa','faa','fna')`. |
| `acp_dpe` | `Test.py` | +42 / −33 | FASTA → CSV adapter (`_fasta_to_csv()`), new `__main__` with argparse, `drop_last=False` (the upstream's `drop_last=True` with `batch=128` silently discarded everything if you passed < 128 peptides), and a dump of the per-peptide probability. |

All changes are mechanical adapters (CLI surface, path resolution,
device mapping). None of them alters model architecture or
prediction logic.

## What is *not* a patch

`hemopi2` is not patched — the orchestrator needs a `Model.zip`
checkpoint that the authors host externally (not in their git repo).
The file is publicly downloadable but cannot be expressed as a
text patch. `docs/SETUP_FROM_SCRATCH.md` lists the download URL.

`toxinpred3`, `antibp3`, `deepbp`, `bertaip` work as-shipped after
their respective `git clone` — no patch is needed.

## Authorship

Patches authored by the PBAP maintainer to integrate each upstream
tool into the unified orchestrator. They do **not** affect each
tool's published behavior: same model weights, same predictions,
same outputs. They affect only the I/O surface so a single
orchestrator can drive ten heterogeneous tools.

If you re-publish any of these patches, please keep this attribution
together with the patch text.

## Reverting

`git -C Dataset_Bioactividad/Tool_Repos/<tool> apply -R ../../../patches/<tool>.patch`
restores the tool to its pristine upstream state.

---

## Legal posture (please read if you redistribute or fork)

These patch files contain small portions of each upstream tool's
source code (the diff context lines and the lines marked `-`),
together with the changes introduced by the PBAP maintainer (the
lines marked `+`). The size is intentionally minimal: across the five
patches, roughly **50 lines** of original third-party code appear,
all of them in I/O / CLI-adapter contexts — none of them in model
architecture, weights, training, or anything substantive.

### Our position

1. **These patches are interoperability adapters, not redistribution
   of the original tools.** A patch is useless without first running
   `git clone <upstream-url>` to obtain the full original code. The
   patch only describes *how to modify* an already-cloned tool so
   that a third-party orchestrator (PBAP) can drive it. The original
   tool's source remains the property of its respective author and
   under their respective license (see the table above and the per-
   tool entries in [`../THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md)
   and [`../docs/licenses_audit.md`](../docs/licenses_audit.md)).
2. **For tools without an explicit license** (currently 4 of the 5
   patched tools: `hemodl`, `deepb3p`, `perseucpp`, `acp_dpe`), we
   publish these patches under a fair-use / academic-interoperability
   rationale: the amount of original code reproduced is minimal, the
   purpose is non-commercial research interoperability, the function
   of the upstream tool is unchanged, and there is no market effect
   on the upstream author (if anything, this is free promotion of
   their work). This is the same posture under which dozens of
   academic adapter repositories operate on GitHub.
3. **For tools with an explicit license** (currently `apex` — Penn
   custom non-commercial), the patches are well within the license
   terms (non-commercial academic adaptation).
4. **No model weights, training data, or substantive algorithmic
   code is included in any patch.** Patches touch only argparse,
   `__main__` blocks, file-path handling, and similar mechanical
   adapters.

### Takedown

If you are an author of an upstream tool patched here and you would
like the corresponding patch (or all of them) removed:

- Email: **noeparedesalf@gmail.com**
- Subject: anything containing the tool name is fine.
- We commit to acting on the request **within 24 hours**: removing
  the offending `<tool>.patch` from this repository and disabling
  the tool in the public demo via the `ALLOWED_TOOLS` env var (see
  [`../demo/api/README.md`](../demo/api/README.md) §"Mitigation shield").

No legal justification is required from the requester.

### Reuse

If you fork PBAP or redistribute these patches, please:

- Preserve this notice in the redistributed `patches/README.md`.
- Preserve the "must clone upstream first" step in your setup
  documentation (do **not** bundle the upstream tools themselves
  inside your fork).
- Keep the takedown contact responsive, or replace it with your own
  contact and the same 24-hour commitment.

This posture is consistent with the architectural decision recorded
in [`../docs/decisions.md`](../docs/decisions.md) §"2026-05-13 —
Public demo as a separate layer with mitigation shield".
