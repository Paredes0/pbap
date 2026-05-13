# Rule — Verify external artifacts BEFORE building infrastructure

**Type**: mandatory planning rule.
**Established**: 2026-04-22.
**Last revised**: 2026-04-26 (clarification of the patch/wrapper boundary).
**Applies to**: any task that depends on N external artifacts (third-party
repositories, published models, downloadable datasets, APIs).

---

## Rule

**Before building infrastructure that depends on external artifacts,
verify one by one that each artifact exists, is usable in inference
mode, and has loadable weights / data.**

Do not assume that just because a repo has a `README`, an
`environment.yml` or a published paper, the code is plug-and-play. In
open-source bioinformatics that is the exception, not the norm.

---

## Why (reference incident 2026-04-22)

After building 8 conda environments (~2 h of work), cloning 22 repos
and editing 24 YAML entries, the bulk smoke test revealed that **11 of
22 tools (50%) had no usable inference script**: only training code,
notebooks, hardcoded paths, or weights not included. This wasted work
and tokens was avoidable with a 15–30 min viability audit upfront.

After a second iteration (BLOCK B–D of the later plan) the initial
figure settled at 6/26 tools E2E-viable. The 2026-04-26 review extended
the criterion to 11–13/26 by clarifying the patch/wrapper boundary (see
§"Adaptation / engineering boundary").

---

## How to apply

### Before touching envs, clones or YAML

For each planned external repo, verify:

1. Is there an inference script (`predict.py`, `infer.py`, `main.py`
   with `--predict`) **OR a class with a prediction method that accepts
   FASTA/sequences and returns results**?
2. Does the `__main__` or the method accept peptide input (FASTA / CSV
   / TSV) and produce parseable output?
3. Are the weights/models included in the repo, or documented for
   download? Does the URL still work?
4. Are there hardcoded paths (`./Model/`, `/home/<author>/...`) that
   break outside the original context?
5. Does the license / access permit use?

### Recording

Record the result in a table `docs/<task>_viability.md` with columns:

```
tool | has_inference | weights_available | hardcoded_paths | verdict (OK / FIXABLE / BLOCKED) | reason
```

### Decision

- Only then design the infrastructure (envs, runner, config) for the
  `OK + FIXABLE` subset.
- `BLOCKED` items go into an exclusion list with a documented reason.
- If the pre-viability audit reveals >30% of tools as `BLOCKED`,
  **stop and discuss with the user** before continuing — the strategy
  probably needs adjustment (standby, replacement, renegotiate scope).

---

## 🔧 Boundary: lightweight adaptation (ALLOWED) vs. inference engineering (FORBIDDEN)

**This is the key section to correctly classify FIXABLE vs. BLOCKED.**
It was added 2026-04-26 after we detected that the "no wrappers" rule
had been applied inconsistently — patches were accepted for `hemodl`,
`deepb3p`, `deepbp` while equivalent adaptations were rejected on
`apex`, `hypeptox_fuse`, `bert_ampep60`.

### Principle

**The author's inference logic must exist in the repo, complete and
executable. We only wire it into the pipeline. If we would have to
rewrite the inference, it is out of scope.**

### ✅ ALLOWED adaptations (count as FIXABLE)

Any of the following modifications are valid if the author's prediction
logic is already complete:

1. **Patches to existing scripts**: fix paths (script-relative instead
   of cwd-relative), API migration (e.g.
   `tokenizer.batch_encode_plus()` → `tokenizer()`), change hardcoded
   GPU index (`cuda:2 → cuda:0`), add `map_location` to `torch.load`,
   normalize case sensitivity (`Model → model`).
2. **I/O format adaptation**: convert FASTA → the format expected by
   the tool (txt with one sequence per line, CSV with a specific
   column, etc.) and map the output back.
3. **Add argparse to `__main__`**: when the `predict()` function is
   already parametrized but `__main__` hardcodes paths.
4. **Class wiring**: when the full inference logic is in a class with
   a method like `predict_fasta_file()`. Instantiate + call =
   ~20–30 lines of glue.
5. **Replace interactive input**: `input()` → argparse when the
   underlying logic is complete.
6. **Add `__main__` to a module**: if all inference functions exist
   but the module is not directly executable.
7. **Set `cwd` for cwd-bound scripts**: run the script from its own
   directory when it hardcodes `./relative_path`.
8. **`git lfs pull`**: hydrate LFS files if the user authorizes.
9. **Auto-download of weights**: if the script already implements the
   download (URLs in code), trust it.

**Typical cost**: 10–50 lines per tool. Same level as the patches
already applied to `hemodl` / `deepb3p` / `deepbp`.

### ❌ FORBIDDEN work (classify as BLOCKED)

Any of the following situations = the repo is not viable under our
rules:

1. **Implementing inference from scratch**: only `train.py` exists,
   no reusable prediction flow. The model is there but the logic to
   load it + extract features + predict is not written.
2. **Re-engineering of multi-step feature pipelines**: the tool
   requires 6+ precomputed embeddings (ProtT5, ESM-1b/2/1v, etc.)
   with no orchestrator, and there is no `extract_all_features.py`
   or equivalent.
3. **Training new models**: pretrained weights do not exist and
   cannot be downloaded.
4. **Replicating notebook logic line by line**: code lives only in
   `.ipynb` with Colab paths (`/content/drive/...`).
5. **External services unavailable**: requires ESMAtlas, NetSurfP,
   BLAST against private databases, with no local alternative.
6. **Destructive incompatible dependencies**: installing the required
   library breaks other tools in the same env and no isolated env is
   viable.
7. **Weights behind institutional login with no access**: SharePoint
   with login, Baidu Netdisk, private FTPs.

**Typical cost**: hours to days of engineering. Out of scope for an
audit pipeline.

### Quick decision heuristic

> "If after the change the code that predicts is still the author's and
> only the way I call it or the I/O changed → FIXABLE.
> If I would have to write the logic that loads the model and produces
> predictions → BLOCKED."

### Edge cases

- **Repo has only a notebook but the logic is linear and trivial to
  extract**: case by case. If converting the notebook to a script is
  <30 lines AND the Colab paths replace trivially, FIXABLE. If the
  notebook depends on magic commands or Colab state, BLOCKED.
- **Weights downloadable but the URL is unstable** (Google Drive with
  captcha, temporary Dropbox): document in YAML as
  `manual_download_required` with the URL and instructions; classify
  as FIXABLE only if the user confirms they will download.

---

## Red flags that trigger this rule

Any of these signals in an external repo = do NOT assume it works:

- The repo only has notebooks (`.ipynb`) with no executable `.py`.
- The `README` only describes training, not inference.
- Models referenced as `model.pkl` / `checkpoint.pt` but the file is
  not in the repo and there is no download link.
- Absolute paths like `/home/<author>/...` or relative paths like
  `./Model/` (case-sensitive on Linux).
- Dependencies pinned to old versions without a reproducible
  `environment.yml`.
- Last commit >3 years old with no maintenance.
- Imports from private, internal, or non-PyPI packages.
- Paper cited but no tag/release matches the paper's version.

---

## Anti-pattern to avoid

**BAD**: "I'll build the 8 conda envs, clone the 22 repos, normalize
the YAML, and then smoke-test them all at once." → You discover the
problems after 2 h of investment and hundreds of tool calls.

**GOOD**: "I'll spend 15 min verifying one by one that the 22 repos
have an inference script and loadable weights. I only build infra for
the ones that pass the filter." → You discover the problems before
investing.

---

## When this rule does NOT apply

- A single well-known external artifact (e.g. `pip install biopython`)
  — verification is trivial.
- Internal team repos whose state you already know.
- Purely local tasks with no external dependencies.

---

## Current application status

- Live table: `docs/pipeline_viability.md`.
- Tools viable after the initial audit (2026-04-22 → 2026-04-25):
  toxinpred3, antibp3, hemopi2, hemodl, deepb3p, deepbp, eippred
  (7/26).
- 2026-04-26 reclassification: additional FIXABLE candidates under the
  new boundary — apex, hypeptox_fuse, bert_ampep60 (high confidence);
  perseucpp, aapl, if_aip, acp_dpe (need direct inspection).
- Deferred by manual blocking (waiting on user action):
  antifungipept (`git lfs pull`), plm4alg (KSU login), avppred_bwr
  (Baidu Netdisk).
- Not yet cloned (needs local verification): mfe_acvp.
- Genuinely BLOCKED: multimodal_aop, afp_mvfl, antiaging_fl,
  aip_tranlac, deepforest_htp, stackthp, cpppred_en, macppred2.

---
[← Back to Index](INDEX.md)
