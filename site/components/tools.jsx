// 10 active tools grouped by 7 bioactivity categories
const CATEGORIES = [
  { id: 'toxicity', name: 'Toxicity', polarity: 'bad', stage: 'Safety' },
  { id: 'hemolytic', name: 'Hemolytic', polarity: 'bad', stage: 'Safety' },
  { id: 'antimicrobial', name: 'Antimicrobial', polarity: 'good', stage: 'Bioactivity' },
  { id: 'anticancer', name: 'Anticancer', polarity: 'good', stage: 'Bioactivity' },
  { id: 'anti_inflammatory', name: 'Anti-inflammatory', polarity: 'good', stage: 'Bioactivity' },
  { id: 'bbb', name: 'BBB penetration', polarity: 'good', stage: 'Pharmacokinetics' },
  { id: 'cpp', name: 'Cell-penetrating', polarity: 'good', stage: 'Pharmacokinetics' },
];

const TOOLS = [
  { id: 'toxinpred3', cat: 'toxicity', polarity: 'bad', tech: 'SVM + molecular features', env: 'ml', emits: 'binary', threshold: 0.5 },
  { id: 'hemopi2',    cat: 'hemolytic', polarity: 'bad', tech: 'ESM-2 fine-tuned (-m 3)', env: 'torch', emits: 'binary', threshold: 0.58 },
  { id: 'hemodl',     cat: 'hemolytic', polarity: 'bad', tech: 'ESM-2 + ProtT5 ensemble', env: 'ml', emits: 'binary', threshold: 0.5 },
  { id: 'antibp3',    cat: 'antimicrobial', polarity: 'good', tech: 'sklearn + blastp', env: 'ml', emits: 'binary', threshold: 0.5 },
  { id: 'apex',       cat: 'antimicrobial', polarity: 'good', tech: '20-model ensemble · 34 strains', env: 'qsar', emits: 'extra_only', threshold: null, special: 'MIC µM × 34' },
  { id: 'deepbp',     cat: 'anticancer', polarity: 'good', tech: 'ESM-2 deep ensemble', env: 'torch_legacy', emits: 'binary', threshold: 0.5 },
  { id: 'acp_dpe',    cat: 'anticancer', polarity: 'good', tech: 'CNN + GRU dual-path', env: 'torch_legacy', emits: 'binary', threshold: 0.5 },
  { id: 'bertaip',    cat: 'anti_inflammatory', polarity: 'good', tech: 'BERT-based · HF yingjc/BertAIP', env: 'pipeline_bertaip', emits: 'binary', threshold: 0.8, note: 'threshold raised 0.5 → 0.8' },
  { id: 'deepb3p',    cat: 'bbb', polarity: 'good', tech: 'Transformer-based', env: 'deepb3p_legacy', emits: 'binary', threshold: 0.5 },
  { id: 'perseucpp',  cat: 'cpp', polarity: 'good', tech: 'Two-stage · CPP + efficiency', env: 'perseucpp', emits: 'binary', threshold: 0.5 },
];

function ToolGrid() {
  return (
    <div>
      {CATEGORIES.map(cat => {
        const tools = TOOLS.filter(t => t.cat === cat.id);
        return (
          <div key={cat.id} style={{marginBottom: 22}}>
            <div style={{
              display: 'flex', alignItems: 'baseline', gap: 12,
              padding: '12px 0 10px', borderBottom: '1px solid var(--hairline)',
              marginBottom: 12
            }}>
              <div style={{
                fontFamily: 'IBM Plex Serif', fontSize: 20, fontWeight: 500,
                letterSpacing: '-0.01em'
              }}>{cat.name}</div>
              <span className={'chip ' + cat.polarity}>{cat.polarity.toUpperCase()}</span>
              <span className="ml">stage · {cat.stage}</span>
              <span className="ml" style={{marginLeft: 'auto'}}>
                {tools.length} tool{tools.length > 1 ? 's' : ''}
                {tools.length > 1 && ' · agreement active'}
              </span>
            </div>

            <div className="tool-grid">
              {tools.map(t => (
                <div key={t.id} className={'tool ' + t.polarity}>
                  <div className="tool-name">{t.id}</div>
                  <div className="tool-cat mono">
                    {t.emits === 'extra_only' ? (
                      <span style={{color: 'oklch(0.4 0.15 250)'}}>extra_only · {t.special}</span>
                    ) : (
                      <span>binary · threshold {t.threshold}</span>
                    )}
                  </div>
                  <div className="tool-tech">{t.tech}</div>
                  <div className="tool-env mono">env: {t.env}{t.note ? ' · ' + t.note : ''}</div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <div style={{
        marginTop: 28, padding: '18px 22px',
        background: 'var(--paper)', border: '1px solid var(--line)',
        borderRadius: 'var(--radius)', display: 'flex', gap: 28, flexWrap: 'wrap',
        alignItems: 'baseline'
      }}>
        <div>
          <div className="ml">VERDICT ACROSS THE 26 EVALUATED TOOLS</div>
          <div style={{display: 'flex', gap: 18, marginTop: 8, fontSize: 13, flexWrap: 'wrap'}}>
            <div><b className="num">10</b> <span className="muted">OK / FIXED — operational</span></div>
            <div><b className="num">5</b> <span className="muted">DEFERRED_USER — pending manual download / login</span></div>
            <div><b className="num">10</b> <span className="muted">BLOCKED — missing weights or irreproducible pipeline</span></div>
            <div><b className="num">1</b> <span className="muted">REMOVED — eippred (user decision)</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.ToolGrid = ToolGrid;
