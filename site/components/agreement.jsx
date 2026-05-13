// Intra-category agreement examples
const AGREEMENT_EXAMPLES = [
  {
    cat: 'antimicrobial', polarity: 'good',
    tools: [
      { id: 'antibp3', class: 'positive', score: 0.84 },
    ],
    consensus: 'single_tool',
    note: 'antibp3 is the only binary provider · apex contributes MICs on the extras axis'
  },
  {
    cat: 'hemolytic', polarity: 'bad',
    tools: [
      { id: 'hemopi2', class: 'positive', score: 0.71 },
      { id: 'hemodl',  class: 'negative', score: 0.32 },
    ],
    consensus: 'split',
    note: 'flagged in Disagreements section · yellow fill in XLSX'
  },
  {
    cat: 'anticancer', polarity: 'good',
    tools: [
      { id: 'deepbp',  class: 'positive', score: 0.91 },
      { id: 'acp_dpe', class: 'positive', score: 0.78 },
    ],
    consensus: 'consensus_positive',
    note: 'both POS · counted as POS for structural_score'
  },
  {
    cat: 'toxicity', polarity: 'bad',
    tools: [
      { id: 'toxinpred3', class: 'negative', score: 0.18 },
    ],
    consensus: 'single_tool',
    note: 'NEG on bad polarity → +3 to structural_score'
  },
];

function AgreementDemo() {
  // For multi-tool consensus states the chip/colour comes from the
  // consensus map. For `single_tool` rows there is no consensus to
  // report (only one tool produced a non-null prediction in this
  // category), but a real POS/NEG value still exists — derive the chip
  // from the single tool's own class. The `single_tool` label below
  // the chip clarifies that this is not a multi-tool consensus.
  const consensusToChip = {
    'consensus_positive': 'POS',
    'consensus_negative': 'NEG',
    'split': 'SPLIT',
  };
  const consensusToCls = {
    'consensus_positive': 'pos',
    'consensus_negative': 'neg',
    'split': 'split',
  };
  const chipFor = (row) => (
    row.consensus === 'single_tool'
      ? (row.tools[0].class === 'positive' ? 'POS' : 'NEG')
      : consensusToChip[row.consensus]
  );
  const clsFor = (row) => (
    row.consensus === 'single_tool'
      ? (row.tools[0].class === 'positive' ? 'pos' : 'neg')
      : consensusToCls[row.consensus]
  );

  return (
    <table className="matrix">
      <thead>
        <tr>
          <th style={{width: '20%'}}>Category</th>
          <th style={{width: '8%'}}>Polarity</th>
          <th>Tools that voted</th>
          <th style={{width: '14%'}}>Consensus</th>
          <th style={{width: '32%'}}>Note</th>
        </tr>
      </thead>
      <tbody>
        {AGREEMENT_EXAMPLES.map((row, i) => (
          <tr key={i}>
            <td><b style={{fontFamily: 'IBM Plex Sans', fontWeight: 600, fontSize: 13}}>{row.cat}</b></td>
            <td><span className={'chip ' + row.polarity}>{row.polarity.toUpperCase()}</span></td>
            <td>
              <div style={{display: 'flex', flexWrap: 'wrap', gap: 8}}>
                {row.tools.map(t => (
                  <span key={t.id} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '2px 8px', borderRadius: 3,
                    background: t.class === 'positive' ? 'oklch(0.94 0.06 145)' : 'oklch(0.94 0.01 0)',
                    color: t.class === 'positive' ? 'oklch(0.32 0.1 145)' : 'oklch(0.4 0 0)',
                    fontSize: 11.5
                  }}>
                    {t.id}
                    <span style={{opacity: 0.65}}>
                      {t.class === 'positive' ? 'POS' : 'NEG'} ·&nbsp;{t.score.toFixed(2)}
                    </span>
                  </span>
                ))}
              </div>
            </td>
            <td>
              <span className={'cell-cons ' + clsFor(row)}>
                {chipFor(row)}
              </span>
              <div className="ml" style={{marginTop: 4, fontSize: 9.5}}>{row.consensus}</div>
            </td>
            <td><span style={{fontSize: 12, color: 'var(--ink-2)'}}>{row.note}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

window.AgreementDemo = AgreementDemo;
