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
