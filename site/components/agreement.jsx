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
  const consensusToChip = {
    'consensus_positive': 'POS',
    'consensus_negative': 'NEG',
    'split': 'SPLIT',
    'single_tool': '—',
  };
  const consensusToCls = {
    'consensus_positive': 'pos',
    'consensus_negative': 'neg',
    'split': 'split',
    'single_tool': 'none',
  };

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
              <span className={'cell-cons ' + consensusToCls[row.consensus]}>
                {consensusToChip[row.consensus]}
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
