// Hierarchical ranking visualisation: structural_score → holistic_score
const POLARITY_TABLE = [
  { polarity: 'good', pos: 3, split: 2, neg: 1, none: 0, examples: 'antimicrobial · anticancer · bbb · cpp · anti_inflammatory' },
  { polarity: 'bad',  pos: 1, split: 2, neg: 3, none: 0, examples: 'toxicity · hemolytic · allergenicity' },
  { polarity: 'neutral', pos: 0, split: 0, neg: 0, none: 0, examples: '(none currently)' },
];

const SAMPLE_PEPTIDES = [
  { id: 'peptide_007', struct: 16, max: 18, holistic: 0.78, badges: ['pathogen', 'very_potent'],
    profile: { antimicrobial: 'POS', anticancer: 'POS', bbb: 'POS', cpp: 'SPLIT', anti_inflammatory: 'POS', toxicity: 'NEG', hemolytic: 'NEG' } },
  { id: 'peptide_001', struct: 14, max: 18, holistic: 0.52, badges: ['pathogen'],
    profile: { antimicrobial: 'POS', anticancer: 'SPLIT', bbb: 'POS', cpp: 'NONE', anti_inflammatory: 'POS', toxicity: 'NEG', hemolytic: 'NEG' } },
  { id: 'peptide_012', struct: 12, max: 18, holistic: 0.41, badges: ['potent'],
    profile: { antimicrobial: 'POS', anticancer: 'NEG', bbb: 'NONE', cpp: 'POS', anti_inflammatory: 'SPLIT', toxicity: 'NEG', hemolytic: 'SPLIT' } },
  { id: 'peptide_004', struct: 10, max: 18, holistic: 0.18, badges: [],
    profile: { antimicrobial: 'POS', anticancer: 'NEG', bbb: 'NEG', cpp: 'NONE', anti_inflammatory: 'NEG', toxicity: 'NEG', hemolytic: 'SPLIT' } },
  { id: 'peptide_022', struct: 7, max: 18, holistic: -0.24, badges: [],
    profile: { antimicrobial: 'NEG', anticancer: 'NEG', bbb: 'NONE', cpp: 'NONE', anti_inflammatory: 'NEG', toxicity: 'POS', hemolytic: 'POS' } },
];

const CAT_COLS = [
  { id: 'antimicrobial', label: 'AMP', polarity: 'good' },
  { id: 'anticancer',    label: 'ACP', polarity: 'good' },
  { id: 'anti_inflammatory', label: 'AIP', polarity: 'good' },
  { id: 'bbb',           label: 'BBB', polarity: 'good' },
  { id: 'cpp',           label: 'CPP', polarity: 'good' },
  { id: 'toxicity',      label: 'TOX', polarity: 'bad' },
  { id: 'hemolytic',     label: 'HEM', polarity: 'bad' },
];

function consensusChip(c) {
  const cls = c === 'POS' ? 'pos' : c === 'NEG' ? 'neg' : c === 'SPLIT' ? 'split' : 'none';
  const label = c === 'NONE' ? '—' : c;
  return <span className={'cell-cons ' + cls}>{label}</span>;
}

function HierarchicalRanking() {
  return (
    <div>
      <div className="two-col">
        <div>
          <h3>Level 01 — structural_score</h3>
          <p style={{fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.6, marginTop: 0}}>
            Integer that captures the POS/NEG/SPLIT profile across categories. SPLIT lands exactly between POS and NEG. Categories with no score contribute 0 — partial coverage is penalised.
          </p>
          <table className="matrix mt-16">
            <thead>
              <tr>
                <th>Polarity</th>
                <th style={{textAlign: 'center'}}>POS</th>
                <th style={{textAlign: 'center'}}>SPLIT</th>
                <th style={{textAlign: 'center'}}>NEG</th>
                <th style={{textAlign: 'center'}}>NONE</th>
              </tr>
            </thead>
            <tbody>
              {POLARITY_TABLE.map(p => (
                <tr key={p.polarity}>
                  <td>
                    <span className={'chip ' + p.polarity}>{p.polarity.toUpperCase()}</span>
                    <div className="ml" style={{marginTop: 6, fontSize: 10}}>{p.examples}</div>
                  </td>
                  <td style={{textAlign: 'center', fontWeight: 600}}>{p.pos}</td>
                  <td style={{textAlign: 'center', fontWeight: 600}}>{p.split}</td>
                  <td style={{textAlign: 'center', fontWeight: 600}}>{p.neg}</td>
                  <td style={{textAlign: 'center', fontWeight: 600}}>{p.none}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <h3>Level 02 — holistic_score</h3>
          <p style={{fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.6, marginTop: 0}}>
            Float that breaks ties within a structural_score tier. Mean of good-polarity scores minus mean of bad ones, plus two APEX adjustments. Categories without a score are excluded from the mean (not counted as 0).
          </p>

          <div className="formula mt-16">
            <span className="lhs">holistic_score</span><span className="op">=</span><span className="var-good">good_mean</span><span className="op">−</span><span className="var-bad">bad_mean</span><span className="op">+</span><span className="var-adj">apex_adj</span><span className="op">+</span><span className="var-adj">potency_adj</span>
          </div>

          <div className="four-col mt-16">
            <div className="card card-tight">
              <div className="ml">PATHOGEN_SPECIFIC</div>
              <div style={{fontSize: 18, fontWeight: 600, color: 'oklch(0.4 0.15 250)', marginTop: 4}}>+0.15</div>
            </div>
            <div className="card card-tight">
              <div className="ml">BROAD_SPECTRUM</div>
              <div style={{fontSize: 18, fontWeight: 600, color: 'oklch(0.4 0.15 250)', marginTop: 4}}>+0.05</div>
            </div>
            <div className="card card-tight">
              <div className="ml">NON_ACTIVE</div>
              <div style={{fontSize: 18, fontWeight: 600, color: 'var(--muted)', marginTop: 4}}>0.00</div>
            </div>
            <div className="card card-tight">
              <div className="ml">COMMENSAL_SPECIFIC</div>
              <div style={{fontSize: 18, fontWeight: 600, color: 'var(--bad)', marginTop: 4}}>−0.20</div>
            </div>
          </div>

          <div className="ml mt-16" style={{fontSize: 11, lineHeight: 1.5}}>
            potency_adj: <b style={{color: 'oklch(0.4 0.16 40)'}}>MUY_POTENTE_AMP</b> +0.20 when min(MIC) ≤ 5 µM ·{' '}
            <b style={{color: 'oklch(0.35 0.13 250)'}}>POTENTE_AMP</b> +0.10 when min(MIC) ≤ 10 µM. Mutually exclusive.
          </div>
        </div>
      </div>

      <h3 className="mt-40 mb-16">One run — peptides sorted by (structural desc, holistic desc)</h3>

      <table className="matrix">
        <thead>
          <tr>
            <th style={{width: '4%', textAlign: 'right'}}>#</th>
            <th style={{width: '17%'}}>peptide_id</th>
            <th style={{width: '11%'}}>structural</th>
            <th style={{width: '11%'}}>holistic</th>
            {CAT_COLS.map(c => (
              <th key={c.id} style={{textAlign: 'center', width: '6%'}}>
                <div style={{fontSize: 10}}>{c.label}</div>
                <div style={{fontSize: 9, color: c.polarity === 'good' ? 'oklch(0.4 0.15 145)' : 'oklch(0.4 0.17 28)', marginTop: 2, textTransform: 'none', letterSpacing: 0}}>{c.polarity}</div>
              </th>
            ))}
            <th style={{width: '14%'}}>badges</th>
          </tr>
        </thead>
        <tbody>
          {SAMPLE_PEPTIDES.map((p, i) => (
            <tr key={p.id}>
              <td style={{textAlign: 'right', color: 'var(--muted)'}}>{i + 1}</td>
              <td><b style={{fontWeight: 600}}>{p.id}</b></td>
              <td>
                <div style={{display: 'flex', alignItems: 'center', gap: 8}}>
                  <span className="num" style={{fontSize: 14, fontWeight: 600}}>{p.struct}</span>
                  <span className="muted num" style={{fontSize: 11}}>/ {p.max}</span>
                  <div style={{
                    flex: 1, height: 4, background: 'var(--bg)',
                    borderRadius: 2, overflow: 'hidden', maxWidth: 60
                  }}>
                    <div style={{
                      width: (p.struct / p.max * 100) + '%', height: '100%',
                      background: p.struct / p.max > 0.6 ? 'var(--good)' : p.struct / p.max > 0.4 ? 'var(--warn)' : 'var(--bad)'
                    }}/>
                  </div>
                </div>
              </td>
              <td className="num" style={{
                fontWeight: 600,
                color: p.holistic > 0.3 ? 'oklch(0.4 0.15 145)' : p.holistic > 0 ? 'var(--ink-2)' : 'var(--bad)'
              }}>{p.holistic >= 0 ? '+' : ''}{p.holistic.toFixed(2)}</td>
              {CAT_COLS.map(c => (
                <td key={c.id} style={{textAlign: 'center'}}>
                  {consensusChip(p.profile[c.id])}
                </td>
              ))}
              <td>
                <div style={{display: 'flex', gap: 4, flexWrap: 'wrap'}}>
                  {p.badges.includes('pathogen') && <span className="badge badge-pathogen">🏆 PATH</span>}
                  {p.badges.includes('very_potent') && <span className="badge badge-very-potent">🔥 VERY</span>}
                  {p.badges.includes('potent') && <span className="badge badge-potent">💪 POT</span>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="muted mono mt-16" style={{fontSize: 11, lineHeight: 1.6}}>
        Ordering follows the CSV/XLSX/HTML sort key. peptide_007 beats peptide_001 because its structural is 16/18 vs 14/18; the holistic isn't even consulted. peptide_012 vs peptide_004 is also decided at level 1.
      </p>
    </div>
  );
}

window.HierarchicalRanking = HierarchicalRanking;
