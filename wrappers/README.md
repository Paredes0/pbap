# `wrappers/`

This folder holds **CLI adapters** for upstream tools whose own entry
point cannot be invoked directly by the generic runner in
[`audit_lib/tool_runner.py`](../audit_lib/tool_runner.py).

A wrapper is invoked exactly like a tool — `python <wrapper>.py --input
foo.fasta --output bar.csv` — but internally takes care of whatever
the upstream tool needs (writing FASTAs to hardcoded paths, patching
config variables in-place, reformatting hardcoded output files,
etc.). The orchestrator sees a clean CLI; the upstream tool sees its
expected environment.

## When to add a wrapper instead of a patch

The runner supports four generic ways of invoking a tool, declared in
`config/pipeline_config.yaml`:

| `arg_style:` | Use when… | Example |
|---|---|---|
| `flagged` (default) | The tool has `--input FILE --output FILE` flags | `toxinpred3`, `hemodl` |
| `positional` | The tool takes the FASTA as a positional arg | `deepb3p` |
| `script` + `pre_command` + `output_capture` | Tool writes to a hardcoded filename; runner handles I/O | `apex` (writes `Predicted_MICs.csv`), `hemopi2` |
| **`wrapper`** | Tool has **no usable CLI at all** — hardcoded paths inside the script, requires runtime patching, multiple output files to merge, etc. | `bert_ampep60` |

Rule of thumb: if a small text **patch** to the upstream script
makes its CLI tractable, ship a `patches/<tool>.patch` instead and
use `arg_style: positional` / `flagged`. Only fall back to a
`wrappers/` script when the upstream's I/O surface is fundamentally
incompatible with the runner's three other modes.

A wrapper is **our own code** (the PBAP maintainer's, under
PolyForm Noncommercial 1.0.0). It must **never** redistribute the
upstream tool's source code — it should read the upstream files at
runtime, manipulate paths, and call them via subprocess. If you
find yourself copy-pasting upstream logic into a wrapper, write a
`patches/<tool>.patch` instead.

## Current wrappers (1)

### `bert_ampep60_cli.py` — BERT-AmPEP60 (currently inactive)

Wraps the `AMP_regression_EC_SA` repository (a.k.a. BERT-AmPEP60),
which predicts E. coli and S. aureus MIC values from peptide
sequences. The upstream `predict/predict.py` uses literal lines like
`fasta_path = "train_po.fasta"` and `csv_path = "train_po.csv"` —
there is no way to override them without modifying the file.

What this wrapper does:

1. Accepts the standard `--input <fasta> --output <csv>` interface.
2. Reads `predict/predict.py` into memory and uses `re.sub` to
   rewrite the two hardcoded path lines with absolute paths to the
   orchestrator's I/O. The original file on disk is **not modified**;
   a temporary `_predict_patched.py` is written next to it, executed,
   and removed.
3. Runs the patched script with the user's Python (lets the upstream
   auto-download model weights into its cache on first use).
4. Reads the hardcoded raw output CSV and reformats it into the
   standard pipeline schema (`ID`, `Sequence`,
   `ec_predicted_MIC_uM`, `sa_predicted_MIC_uM`,
   `mean_predicted_MIC_uM`, `Prediction`).
5. Computes the binary `Prediction` field from the mean MIC against
   a configurable threshold (default 1 µM).

**Why "currently inactive":** BERT-AmPEP60 is in state
`DEFERRED_USER` (see [`docs/pipeline_viability.md`](../docs/pipeline_viability.md)):
the upstream hosts the model on an institutional SharePoint behind an
MPU login. `onedrivedownloader` receives an HTML login page rather
than the `.pkl` weights, and the automated download fails. Until the
upstream publishes the weights at a programmatically reachable URL,
the tool cannot be activated.

The wrapper is preserved in the repo because:

- It is independent of the access problem — if a future operator
  obtains the weights via any other means (manual download, fork that
  rehosts), they can drop them into the repo and activate the tool
  just by flipping `stage` to `1-Bioactividad` in
  `config/pipeline_config.yaml`. No code rewrite needed.
- It is a working reference example of the `arg_style: wrapper`
  pattern, useful for future tools that need similar runtime
  rewriting. The pattern itself is documented in
  [`docs/orchestrator_design.md`](../docs/orchestrator_design.md) §3.

If you want to disable BERT-AmPEP60 entirely (instead of just letting
it stay deferred), set its `stage` to `BLOCKED` in the config or move
its block to `config/pipeline_config_blocked.yaml`. The wrapper file
can stay in this folder — it is inert until its tool is activated.

## Adding a new wrapper

1. Confirm a patch is not enough (see "When to add a wrapper instead
   of a patch" above).
2. Create `wrappers/<tool_id>_cli.py` with the same `--input/--output`
   interface as the example above.
3. Set the tool's `arg_style: wrapper` in
   `config/pipeline_config.yaml` and point `script:` at the wrapper
   file under `wrappers/`.
4. Document the wrapper in this README and add an entry to
   [`docs/orchestrator_design.md`](../docs/orchestrator_design.md) §3
   if you introduced any new runner dimension.
