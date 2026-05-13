// APEX deep dive — 34 strains, pathogen vs commensal, selectivity tags
const STRAINS = [
  // pathogens (14)
  { name: 'S. aureus',       cls: 'path', mic: 4.2 },
  { name: 'MRSA',            cls: 'path', mic: 6.7 },
  { name: 'VRE',             cls: 'path', mic: 8.1 },
  { name: 'K. pneumoniae',   cls: 'path', mic: 12.4 },
  { name: 'P. aeruginosa',   cls: 'path', mic: 18.7 },
  { name: 'A. baumannii',    cls: 'path', mic: 22.3 },
  { name: 'E. faecium',      cls: 'path', mic: 9.4 },
  { name: 'S. typhimurium',  cls: 'path', mic: 28.1 },
  { name: 'L. monocytogenes',cls: 'path', mic: 14.8 },
  { name: 'S. pneumoniae',   cls: 'path', mic: 19.2 },
  { name: 'C. difficile',    cls: 'path', mic: 30.5 },
  { name: 'M. tuberculosis', cls: 'path', mic: 45.0 },
  { name: 'Shigella',        cls: 'path', mic: 16.1 },
  { name: 'N. gonorrhoeae',  cls: 'path', mic: 11.3 },
  // commensals (18)
  { name: 'A. muciniphila',  cls: 'comm', mic: 84.0 },
  { name: 'B. fragilis',     cls: 'comm', mic: 92.5 },
  { name: 'B. uniformis',    cls: 'comm', mic: 76.3 },
  { name: 'F. prausnitzii',  cls: 'comm', mic: 110.0 },
  { name: 'R. bromii',       cls: 'comm', mic: 95.4 },
  { name: 'E. rectale',      cls: 'comm', mic: 88.1 },
  { name: 'L. acidophilus',  cls: 'comm', mic: 70.2 },
  { name: 'L. plantarum',    cls: 'comm', mic: 65.8 },
  { name: 'B. longum',       cls: 'comm', mic: 102.3 },
  { name: 'B. bifidum',      cls: 'comm', mic: 98.7 },
  { name: 'E. coli Nissle',  cls: 'comm', mic: 80.1 },
  { name: 'P. distasonis',   cls: 'comm', mic: 71.4 },
  { name: 'Eubacterium',     cls: 'comm', mic: 86.9 },
  { name: 'Ruminococcus',    cls: 'comm', mic: 78.5 },
  { name: 'C. coccoides',    cls: 'comm', mic: 82.2 },
  { name: 'B. thetaiotaomicron', cls: 'comm', mic: 73.6 },
  { name: 'L. reuteri',      cls: 'comm', mic: 67.9 },
  { name: 'L. rhamnosus',    cls: 'comm', mic: 90.4 },
  // ambiguous (2)
  { name: 'E. coli K12',     cls: 'amb',  mic: 32.0 },
  { name: 'S. epidermidis',  cls: 'amb',  mic: 35.5 },
];

const THRESHOLD = 32; // µM

function strainStateClass(s) {
  const active = s.mic <= THRESHOLD;
  if (!active) return s.cls;
  if (s.cls === 'path') return 'path path-active';
  if (s.cls === 'comm') return 'comm comm-active';
  if (s.cls === 'amb') return 'amb amb-active';
}

function ApexDeepDive() {
  const pathActive = STRAINS.filter(s => s.cls === 'path' && s.mic <= THRESHOLD).length;
  const commActive = STRAINS.filter(s => s.cls === 'comm' && s.mic <= THRESHOLD).length;

  const meanPath = STRAINS.filter(s => s.cls === 'path').reduce((a,s) => a + s.mic, 0) / 14;
  const meanComm = STRAINS.filter(s => s.cls === 'comm').reduce((a,s) => a + s.mic, 0) / 18;

  const minMic = Math.min(...STRAINS.filter(s => s.cls !== 'amb').map(s => s.mic));

  // selectivity tag
  let tag, tagColor;
  if (pathActive > 0 && commActive === 0) { tag = 'PATHOGEN_SPECIFIC'; tagColor = 'pathogen'; }
  else if (pathActive === 0 && commActive > 0) { tag = 'COMMENSAL_SPECIFIC'; tagColor = 'commensal'; }
  else if (pathActive > 0 && commActive > 0) { tag = 'BROAD_SPECTRUM'; tagColor = 'broad'; }
  else { tag = 'NON_ACTIVE'; tagColor = 'inactive'; }

  // potency
  let potency = null;
  if (minMic <= 5)  potency = { tag: 'MUY_POTENTE_AMP', icon: '🔥', adj: 0.20 };
  else if (minMic <= 10) potency = { tag: 'POTENTE_AMP', icon: '💪', adj: 0.10 };

  return (
    <div>
      {/* 4 selectivity tag cards */}
      <div className="four-col mb-24">
        <div style={{
          padding: '18px 18px 16px', borderRadius: 'var(--radius)',
          background: 'linear-gradient(135deg, oklch(0.94 0.1 85), oklch(0.9 0.13 70))',
          border: '1px solid oklch(0.75 0.13 75)', color: 'oklch(0.32 0.13 60)'
        }}>
          <div style={{fontSize: 22, fontWeight: 600, fontFamily: 'IBM Plex Mono'}}>🏆 path</div>
          <div className="mt-8" style={{fontSize: 12.5, lineHeight: 1.45}}>
            <b>PATHOGEN_SPECIFIC</b> — active against ≥1 pathogen, 0 commensals. Therapeutic bonus.
          </div>
          <div className="mono mt-8" style={{fontSize: 11, fontWeight: 600}}>holistic +0.15</div>
        </div>

        <div style={{
          padding: '18px 18px 16px', borderRadius: 'var(--radius)',
          background: 'oklch(0.95 0.06 250)', border: '1px solid oklch(0.78 0.08 250)',
          color: 'oklch(0.32 0.13 250)'
        }}>
          <div style={{fontSize: 22, fontWeight: 600, fontFamily: 'IBM Plex Mono'}}>broad</div>
          <div className="mt-8" style={{fontSize: 12.5, lineHeight: 1.45, color: 'var(--ink-2)'}}>
            <b style={{color: 'oklch(0.32 0.13 250)'}}>BROAD_SPECTRUM</b> — active against both groups. Still a useful AMP, no selectivity.
          </div>
          <div className="mono mt-8" style={{fontSize: 11, fontWeight: 600, color: 'oklch(0.32 0.13 250)'}}>holistic +0.05</div>
        </div>

        <div style={{
          padding: '18px 18px 16px', borderRadius: 'var(--radius)',
          background: 'var(--bg)', border: '1px solid var(--line)',
          color: 'var(--ink-2)'
        }}>
          <div style={{fontSize: 22, fontWeight: 600, fontFamily: 'IBM Plex Mono', color: 'var(--muted)'}}>⊘ none</div>
          <div className="mt-8" style={{fontSize: 12.5, lineHeight: 1.45}}>
            <b>NON_ACTIVE</b> — inactive against both groups. No contribution (positive or negative).
          </div>
          <div className="mono mt-8" style={{fontSize: 11, fontWeight: 600}}>holistic 0.00</div>
        </div>

        <div style={{
          padding: '18px 18px 16px', borderRadius: 'var(--radius)',
          background: 'oklch(0.95 0.06 28)', border: '1px solid oklch(0.75 0.12 28)',
          color: 'oklch(0.4 0.15 28)'
        }}>
          <div style={{fontSize: 22, fontWeight: 600, fontFamily: 'IBM Plex Mono'}}>⚠ comm</div>
          <div className="mt-8" style={{fontSize: 12.5, lineHeight: 1.45, color: 'var(--ink-2)'}}>
            <b style={{color: 'oklch(0.4 0.15 28)'}}>COMMENSAL_SPECIFIC</b> — harms the microbiome without killing pathogens. Penalised.
          </div>
          <div className="mono mt-8" style={{fontSize: 11, fontWeight: 600, color: 'oklch(0.4 0.15 28)'}}>holistic −0.20</div>
        </div>
      </div>

      {/* Live example */}
      <div className="card" style={{padding: '24px 26px'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6, flexWrap: 'wrap', gap: 12}}>
          <div>
            <div className="ml">EXAMPLE · one APEX run</div>
            <div style={{fontFamily: 'IBM Plex Serif', fontSize: 22, marginTop: 4}}>peptide_007 · <span className="mono" style={{fontSize: 14}}>GIGAVLKVLTTGLPALISWIKRKRQQ</span></div>
          </div>
          <div style={{display: 'flex', gap: 8, flexWrap: 'wrap'}}>
            <span className="badge badge-pathogen">🏆 {tag}</span>
            {potency && (
              <span className={'badge ' + (potency.tag === 'MUY_POTENTE_AMP' ? 'badge-very-potent' : 'badge-potent')}>
                {potency.icon} {potency.tag}
              </span>
            )}
          </div>
        </div>

        <p style={{fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.6, marginTop: 14, marginBottom: 20}}>
          APEX predicts MIC in µM against all 34 strains. Threshold T = 32 µM (configurable in{' '}
          <span className="mono">apex_strain_classification.yaml</span>) flags activity. PBAP counts hits per group and derives the selectivity_tag. The two ambiguous strains (E. coli K12, S. epidermidis) are exported but <b>do not count</b> toward the aggregate.
        </p>

        {/* counts row */}
        <div className="four-col mb-24">
          <div style={{
            padding: '14px 16px', borderRadius: 6,
            background: 'oklch(0.94 0.08 145)', border: '1px solid oklch(0.7 0.1 145)'
          }}>
            <div className="ml" style={{color: 'oklch(0.32 0.1 145)'}}>PATHOGEN HITS · MIC ≤ 32</div>
            <div style={{fontSize: 28, fontWeight: 600, marginTop: 4, color: 'oklch(0.32 0.1 145)', fontFamily: 'IBM Plex Serif'}}>{pathActive} <span style={{fontSize: 14, color: 'var(--muted)', fontFamily: 'IBM Plex Mono'}}>/ 14</span></div>
          </div>
          <div style={{
            padding: '14px 16px', borderRadius: 6,
            background: 'var(--bg)', border: '1px solid var(--line)'
          }}>
            <div className="ml">COMMENSAL HITS · MIC ≤ 32</div>
            <div style={{fontSize: 28, fontWeight: 600, marginTop: 4, fontFamily: 'IBM Plex Serif'}}>{commActive} <span style={{fontSize: 14, color: 'var(--muted)', fontFamily: 'IBM Plex Mono'}}>/ 18</span></div>
          </div>
          <div style={{
            padding: '14px 16px', borderRadius: 6,
            background: 'var(--bg)', border: '1px solid var(--line)'
          }}>
            <div className="ml">mean MIC pathogen</div>
            <div style={{fontSize: 22, fontWeight: 600, marginTop: 4, fontFamily: 'IBM Plex Serif'}}>{meanPath.toFixed(1)} <span style={{fontSize: 13, color: 'var(--muted)', fontFamily: 'IBM Plex Mono'}}>µM</span></div>
          </div>
          <div style={{
            padding: '14px 16px', borderRadius: 6,
            background: 'var(--bg)', border: '1px solid var(--line)'
          }}>
            <div className="ml">mean MIC commensal</div>
            <div style={{fontSize: 22, fontWeight: 600, marginTop: 4, fontFamily: 'IBM Plex Serif'}}>{meanComm.toFixed(1)} <span style={{fontSize: 13, color: 'var(--muted)', fontFamily: 'IBM Plex Mono'}}>µM</span></div>
          </div>
        </div>

        {/* legend */}
        <div className="row gap-20 mb-16" style={{flexWrap: 'wrap', fontFamily: 'IBM Plex Mono', fontSize: 11}}>
          <div className="row gap-12">
            <div style={{width: 12, height: 12, background: 'oklch(0.92 0.1 145)', border: '1px solid oklch(0.7 0.12 145)', borderRadius: 2}}/>
            <span>active pathogen (≤ 32 µM)</span>
          </div>
          <div className="row gap-12">
            <div style={{width: 12, height: 12, background: 'oklch(0.92 0.1 28)', border: '1px solid oklch(0.7 0.14 28)', borderRadius: 2}}/>
            <span>active commensal</span>
          </div>
          <div className="row gap-12">
            <div style={{width: 12, height: 12, background: 'oklch(0.95 0.13 85)', border: '1px solid oklch(0.78 0.14 85)', borderRadius: 2}}/>
            <span>active ambiguous</span>
          </div>
          <div className="row gap-12">
            <div style={{width: 12, height: 12, background: 'var(--paper)', border: '1px solid var(--line)', borderRadius: 2}}/>
            <span>inactive (&gt; 32 µM)</span>
          </div>
        </div>

        {/* 34-strain grid */}
        <div className="strain-grid">
          {STRAINS.map(s => (
            <div key={s.name} className={'strain ' + strainStateClass(s)} title={`${s.name} — MIC ${s.mic} µM`}>
              <div className="sname">{s.name}</div>
              <div className="smic num">{s.mic.toFixed(1)} <span style={{opacity: 0.6}}>µM</span></div>
            </div>
          ))}
        </div>

        <div className="ml mt-16" style={{fontSize: 11, lineHeight: 1.6}}>
          Post-processing result: selectivity_tag = <b style={{color: 'oklch(0.4 0.13 60)'}}>{tag}</b>{' '}
          → holistic_score += <b className="num">+0.15</b>
          {potency && <> · potency_tag = <b style={{color: potency.tag === 'MUY_POTENTE_AMP' ? 'oklch(0.4 0.16 40)' : 'oklch(0.35 0.13 250)'}}>{potency.tag}</b> (min MIC = <span className="num">{minMic} µM</span>) → += <b className="num">+{potency.adj.toFixed(2)}</b></>}
        </div>
      </div>
    </div>
  );
}

window.ApexDeepDive = ApexDeepDive;
