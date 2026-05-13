// Phase 1 interactive flow diagram (Sections 01–06 ground truth)
const FLOW_STEPS = [
  {
    id: 'input',
    short: 'INPUT',
    name: 'FASTA',
    label: 'Unlabeled peptides',
    tech: 'Inputs/*.fasta',
    title: 'Raw FASTA',
    desc: 'The user drops one or more FASTA files into the Inputs/ directory. Each peptide is a 5–100 amino-acid sequence. PBAP validates the format, normalises headers, and rejects sequences with ambiguous characters (X, B, Z) as required by the downstream tool.',
    kbits: '5–100 aa · 20 standard amino acids · no ambiguous characters',
    code: `>peptide_001
GIGAVLKVLTTGLPALISWIKRKRQQ
>peptide_002
GIGKFLHSAKKFGKAFVGEIMNS
>peptide_003
TRSSRAGLQFPVGRVHRLLRK`
  },
  {
    id: 'batch',
    short: '01',
    name: 'Batching',
    label: 'Chunks vs OOM',
    tech: 'batch_size: 100',
    title: 'Batched processing (anti-OOM)',
    desc: 'The orchestrator splits the FASTA into batches (default 100 peptides, per-tool override allowed). For every (tool × batch) it writes a temporary sub-FASTA and runs the tool. A failed batch does NOT abort the run — its peptides get class_norm=null, raw_class="error_batch_failed", and the rest of the run continues.',
    kbits: 'CLI: --batch-size N · YAML: batch_size_override per tool',
    code: `Outputs/<run>/per_tool/<tool>/
  └── _batches/
      ├── batch_001/
      │   ├── input_<tool>_batch_001.fasta
      │   ├── predictions_<tool>.csv  ← parsed individually
      │   └── completed.stdout
      ├── batch_002/  ...
      └── predictions_<tool>.csv      ← final concat`
  },
  {
    id: 'envs',
    short: '02',
    name: 'Tools',
    label: '10 tools, 9 envs',
    tech: 'micromamba run',
    title: 'Per-tool execution in isolated sub-processes',
    desc: 'Each tool runs inside its dedicated conda environment via micromamba run. The runner abstracts six generic dimensions (arg_style, output_capture, pre_command, cwd_subdir, extra_args, hardcoded_output_name) — adding a new tool is a YAML block, not Python code. The runner returns a ToolResult with runtime, exit_code and diagnosis.',
    kbits: 'audit_lib/tool_runner.py · 6 generic dimensions',
    code: `# What the runner executes after resolving the YAML:
micromamba run -n torch \\
  python predict.py \\
    -i input_apex_batch_001.fasta \\
    -o predictions_apex.csv \\
    --threshold 0.5

→ ToolResult(
    tool_id='apex',
    output_path='.../predictions_apex.csv',
    exit_code=0,
    runtime=9.4,
    diagnosis=None
  )`
  },
  {
    id: 'norm',
    short: '03',
    name: 'Normalize',
    label: 'Dual schema',
    tech: 'class_norm + extras',
    title: 'Normalisation to the dual schema',
    desc: 'Every heterogeneous tool output is translated into the common schema: a binary axis (class_norm, score) plus an extra_metrics axis (magnitudes with unit). The per-tool parser lives in pipeline_config.yaml — no custom code for new tools. The prefer_threshold_over_raw_class flag lets you re-evaluate against your own threshold when a tool ships with a hard-coded cutoff you disagree with.',
    kbits: '_derive_class_norm() · score ∈ [0,1] · extras: <tool>__<metric>__<unit>',
    code: `# Canonical prediction after normalisation:
{
  "tool": "apex",
  "peptide_id": "peptide_001",
  "class_norm": null,           # extra_only
  "score": null,
  "extra_metrics": {
    "MIC_E_coli__uM":  12.4,
    "MIC_S_aureus__uM": 8.1,
    "MIC_MRSA__uM":     6.7,
    ...
  }
}`
  },
  {
    id: 'agree',
    short: '04',
    name: 'Agreement',
    label: 'POS · SPLIT · NEG',
    tech: 'consensus_<cat>',
    title: 'Intra-category agreement detection',
    desc: 'When ≥2 tools cover the same category on the binary axis, PBAP computes a per-peptide consensus: consensus_positive (all POS), consensus_negative (all NEG), split (mixed) or single_tool. No voting, no ensemble — disagreements are surfaced for human review. Option E (reliability-weighted ensemble) is deferred until the tool pool is frozen.',
    kbits: 'Option B (honest fallback) · future: Option E (weighted)',
    code: `# hemolytic — 2 tools disagree:
hemopi2:  positive  (score 0.71)
hemodl:   negative  (score 0.32)

→ consensus_hemolytic = "split"
→ flagged in REPORT.md Disagreements section
→ row filled yellow #fff3cd in XLSX`
  },
  {
    id: 'rank',
    short: '05',
    name: 'Ranking',
    label: 'structural → holistic',
    tech: '2-level sort key',
    title: 'Hierarchical viability ranking',
    desc: 'Level 1 — structural_score (int): for every evaluated category, POS=3 / SPLIT=2 / NEG=1 / NONE=0 if the category has good polarity; inverted if bad. Level 2 — holistic_score (float): good_mean − bad_mean + apex_adjustment + potency_adjustment. Sort key = (structural desc, holistic desc).',
    kbits: 'Polarity per category · APEX adjustment ∈ {+0.15, +0.05, 0, −0.20}',
    code: `# Peptide profile:
#   antimicrobial=POS, anticancer=SPLIT, toxicity=NEG,
#   hemolytic=NEG, bbb=POS, cpp=NONE
#
structural_score = 3+2+3+3+3+0 = 14 / 18
holistic_score   = 0.67 (good_mean) − 0.23 (bad_mean)
                 + 0.15 (apex: pathogen_specific)
                 + 0.10 (potency: POTENTE_AMP)
                 = +0.69`
  },
  {
    id: 'report',
    short: 'OUT',
    name: 'Reports',
    label: '5 formats',
    tech: 'Outputs/<run>/',
    title: 'Consolidated reports',
    desc: 'REPORT.html is the primary artifact — standalone, no CDN, with inline JS for sort/filter on the matrix. consolidated.xlsx has 5 sheets with row-by-row conditional formatting. CSV/JSON for integration. REPORT.md as a plain-text backup. tool_health_report.json captures partial failures without aborting.',
    kbits: 'Outputs/<input_stem>_<ISO_ts>/ · auto-resolved',
    code: `Outputs/peptides_2026-05-08T1530/
  ├── REPORT.html              ← primary  (interactive matrix)
  ├── REPORT.md                ← backup   (plain Markdown)
  ├── consolidated.csv         ← wide     (sorted by structural,holistic)
  ├── consolidated.xlsx        ← 5 sheets (openpyxl, conditional fmt)
  ├── consolidated.json        ← nested   (per-peptide drill-down)
  ├── tool_health_report.json  ← runtime, status, diagnosis
  └── per_tool/                ← raw outputs preserved for debug`
  }
];

function PhaseFlow() {
  const [active, setActive] = React.useState('input');
  const step = FLOW_STEPS.find(s => s.id === active);

  const hl = (txt) => {
    const lines = txt.split('\n');
    return lines.map((ln, i) => {
      if (/^\s*#/.test(ln)) {
        return <div key={i} className="cm">{ln || '\u00A0'}</div>;
      }
      const tokens = [];
      const re = /("[^"]*")|(>[\w_]+)/g;
      let lastIdx = 0, m;
      while ((m = re.exec(ln)) !== null) {
        if (m.index > lastIdx) tokens.push({ t: 'plain', v: ln.slice(lastIdx, m.index) });
        if (m[1]) tokens.push({ t: 'st', v: m[1] });
        else if (m[2]) tokens.push({ t: 'kw', v: m[2] });
        lastIdx = m.index + m[0].length;
      }
      if (lastIdx < ln.length) tokens.push({ t: 'plain', v: ln.slice(lastIdx) });
      return (
        <div key={i}>
          {tokens.length === 0 ? '\u00A0' : tokens.map((tk, j) =>
            tk.t === 'plain'
              ? <React.Fragment key={j}>{tk.v}</React.Fragment>
              : <span key={j} className={tk.t}>{tk.v}</span>
          )}
        </div>
      );
    });
  };

  return (
    <div>
      <div className="flow">
        <div className="flow-row">
          {FLOW_STEPS.map(s => (
            <div
              key={s.id}
              className={'step' + (s.id === active ? ' active' : '')}
              onClick={() => setActive(s.id)}
              onMouseEnter={() => setActive(s.id)}
            >
              <div className="step-num">{s.short}</div>
              <div className="step-name">{s.name}</div>
              <div className="step-label">{s.label}</div>
              <div className="step-tech mono">{s.tech}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="step-detail">
        <div>
          <h4>{step.title}</h4>
          <p className="desc">{step.desc}</p>
          <div className="kbits mono">{step.kbits}</div>
        </div>
        <div className="panel">{hl(step.code)}</div>
      </div>
    </div>
  );
}

window.PhaseFlow = PhaseFlow;
