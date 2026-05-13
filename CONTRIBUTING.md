# Contributing to PBAP

Thanks for being interested in this project. **Anyone is welcome to
contribute**, whether you write Python or have only ever worked with an
AI assistant — this repository is explicitly designed to be navigable by
AI agents (see `AGENTS.md`).

This guide explains how to set up, what kinds of contributions are most
valuable, and how to submit them.

---

## TL;DR for contributors

| If you want to … | Do this |
|---|---|
| **Report a bug** | Open an issue with the `bug` template. Include the FASTA you used (or a synthetic excerpt) and the relevant `Outputs/<run>/tool_health_report.json`. |
| **Suggest a feature** | Open a GitHub Discussion. If it grows traction, we promote it to an issue. |
| **Add a new prediction tool** | Open an issue with the `Add a new tool` template, then submit a PR with a YAML block in `config/pipeline_config.yaml`. See "Adding a tool" below. |
| **Fix a typo or doc** | Just open a PR. |
| **Discuss licensing or commercial use** | See `LICENSE` for the commercial-licensing contact. |

---

## Code of Conduct

Participation in this project is governed by the [Contributor Covenant
Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to
uphold it.

---

## Development setup

The pipeline is heterogeneous by design: every integrated prediction
tool ships its own conda environment. The orchestrator itself is plain
Python ≥ 3.10. Minimal setup:

```bash
# 1. Clone the repository
git clone https://github.com/Paredes0/pbap.git
cd pbap

# 2. Install micromamba (the per-tool environment manager)
# See https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html

# 3. Create the orchestrator environment (Python ≥ 3.10)
micromamba create -n pbap_orchestrator python=3.11 pip
micromamba activate pbap_orchestrator
pip install -r requirements.txt

# 4. Run the smoke test (uses Inputs/example.fasta)
python scripts/run_audit.py --input Inputs/example.fasta --dry-run
```

> ⚠️ **The 26 prediction tools are not bundled.** To run a real
> inference you need to clone each tool you want to use and place it
> under `Dataset_Bioactividad/Tool_Repos/<tool_name>/`. See
> `docs/pipeline_viability.md` for upstream URLs and per-tool setup
> notes.

For full setup see `docs/deployment.md`.

---

## Adding a new prediction tool

This is the most valuable contribution you can make: the pipeline is a
**platform**, and every new tool extends its coverage.

The architecture is intentionally designed so that **you do not need to
modify Python code** to add a tool. You only edit the YAML configuration.

### Steps

1. **Check viability first**. Read `docs/pipeline_viability.md` and apply
   the 5-criteria checklist:
   - Is there a runnable inference script (not a training script in
     disguise)?
   - Are the model weights publicly accessible?
   - Does it accept FASTA input (or can it be adapted trivially)?
   - Can its dependencies be installed in an isolated conda env without
     conflicting with the others?
   - Is it free of unavoidable external services or login walls?

2. **Open an issue** using the "Add a new tool" template. Wait for a
   maintainer to confirm the tool is in scope.

3. **Clone the tool upstream** into your local
   `Dataset_Bioactividad/Tool_Repos/<tool_name>/` (this folder is
   gitignored on purpose).

4. **Add or reuse a conda env** for the tool, declaring its
   dependencies. If an existing env (e.g. `torch`, `ml`) covers it,
   reuse it.

5. **Write a YAML block** in `config/pipeline_config.yaml`:

   ```yaml
   tools:
     your_tool_id:
       display_name: Your Tool
       category: <one of: toxicity, hemolytic, antimicrobial, anticancer,
                          anti_inflammatory, bbb, cpp, antifungal,
                          antiviral, allergenicity, ...>
       conda_env: <env_name>
       script: <relative path inside Tool_Repos/your_tool_id/>
       arg_style: flagged | positional
       input_flag: -i           # if arg_style=flagged
       output_flag: -o          # if arg_style=flagged
       output_capture: file | hardcoded_file | stdout
       hardcoded_output_name: predictions.csv   # if hardcoded_file
       output_parsing:
         format: csv | tsv | stdout
         prediction_column: <colname with class>
         positive_label: <value of positive class>
         score_column: <colname with probability or None>
         score_threshold: 0.5
   ```

   See existing tools in `config/pipeline_config.yaml` for full
   working examples.

6. **Add a row** to `THIRD_PARTY_LICENSES.md` with the tool's license
   and upstream URL.

7. **Smoke-test** by running `python scripts/run_audit.py --input Inputs/example.fasta --tools your_tool_id`.

8. **Submit the PR**. Reference the issue.

If the tool needs something the runner's existing dimensions can't
express (`arg_style`, `output_capture`, `pre_command`, `cwd_subdir`,
`extra_args`), discuss in the issue first — we may extend the runner
generically rather than special-casing your tool.

---

## Working with AI agents on this repository

This repository is structured to be **AI-agent friendly**. The entry
point for any non-trivial change is `docs/INDEX.md`, which links every
relevant doc. The `AGENTS.md` file at the repository root is loaded
automatically by Claude Code, Gemini CLI, Cursor and other compatible
agents.

If you use an AI assistant:

- Tell it to read `docs/INDEX.md` first.
- It will navigate to the docs relevant to your task (architecture,
  decisions, conventions, glossary, etc.).
- After completing a task, it should update the relevant doc — that
  is the project's convention (see Rule #2 in `AGENTS.md`).

This is not an experiment — it is how the project is designed to be
maintained. Contributions made via AI assistance are equally welcome,
provided they pass the same code-review bar as manual contributions.

---

## Commit messages and PRs

- Commit messages can be in Spanish or English.
- Keep messages descriptive: *what* changed and *why*.
- PRs should target the `develop_public` branch (or `master` if no
  active develop branch exists at the time).
- Small, focused PRs review faster than monoliths.

---

## License of contributions

By contributing to this repository, you agree that your contributions
will be licensed under the same **PolyForm Noncommercial License 1.0.0**
that covers the rest of the project (see `LICENSE`). If you require
different terms for your contribution, raise it in the issue **before**
opening the PR.

---

## Questions

- Use **GitHub Discussions** for design questions, vague ideas or
  "is this in scope?".
- Use **GitHub Issues** for bugs, well-defined feature requests and
  tool integrations.
- Use the commercial-licensing contact in `LICENSE` for anything
  related to commercial use.
