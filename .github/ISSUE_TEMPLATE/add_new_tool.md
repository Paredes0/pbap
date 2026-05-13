---
name: Add a new prediction tool
about: Propose integrating a new peptide-bioactivity prediction tool
title: "[ADD TOOL] <tool_name>"
labels: enhancement, new-tool
assignees: ''
---

## Tool identification
- **Name**:
- **Upstream URL**:
- **Paper / DOI**:
- **License**: <!-- Apache-2.0, GPL-3.0, MIT, custom, "no LICENSE file", … -->
- **Year**:

## Bioactivity category
<!-- Pick one: toxicity, hemolytic, antimicrobial, anticancer,
     anti_inflammatory, bbb, cpp, antifungal, antiviral, allergenicity,
     hypotensive, anti_aging, antioxidant, tumor_homing, anti_angiogenic,
     ecoli_inhibitor -->

## 5-point viability check
- [ ] Runnable **inference** script exists (not a training script)
- [ ] Model weights are accessible (in repo or with a downloadable URL)
- [ ] Accepts FASTA input (or a trivially adaptable format)
- [ ] Dependencies install cleanly in a conda env without conflicting
      with the existing ones
- [ ] Free of unavoidable external services or institutional login walls

## Proposed YAML block

```yaml
tools:
  <tool_id>:
    display_name: <Display Name>
    category: <category>
    conda_env: <env name; reuse an existing one if possible>
    script: <relative path inside Tool_Repos/<tool_id>/>
    arg_style: flagged   # or positional
    input_flag: -i
    output_flag: -o
    output_capture: file   # or hardcoded_file | stdout
    # hardcoded_output_name: <name>  # if output_capture=hardcoded_file
    output_parsing:
      format: csv
      prediction_column: <colname>
      positive_label: <value>
      score_column: <colname or null>
      score_threshold: 0.5
```

## Smoke-test results
<!--
After running `python scripts/run_audit.py --input Inputs/example.fasta
--tools <tool_id>`, paste here:
  - Runtime in seconds
  - Number of peptides predicted positive / negative
  - Any warnings or partial failures
-->

## Anything else
<!-- License notes, RAM requirements, GPU requirements, special steps. -->
