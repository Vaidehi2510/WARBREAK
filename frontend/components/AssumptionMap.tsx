import { Assumption } from '../lib/api';

const STATUS_BG:   Record<string, string> = { untested:'#111', stressed:'#1a1000', broken:'#1a0000', validated:'#001a08' };
const STATUS_BORDER: Record<string, string> = { untested:'#2a2a2a', stressed:'#cc8800', broken:'#cc3333', validated:'#33cc77' };
const STATUS_TEXT: Record<string, string> = { untested:'#555', stressed:'#cc8800', broken:'#cc3333', validated:'#33cc77' };

export default function AssumptionMap({ assumptions }: { assumptions: Assumption[] }) {
  return (
    <div style={{ background: '#0d0d0d', border: '0.5px solid #1e1e1e', borderRadius: 12, padding: 16, marginTop: 16 }}>
      <div style={{ fontSize: 11, letterSpacing: '0.1em', color: '#444', marginBottom: 14 }}>ASSUMPTION MAP — {assumptions.length} EXTRACTED</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {assumptions.map(a => (
          <div key={a.id} style={{ background: STATUS_BG[a.status] || '#111', border: `0.5px solid ${STATUS_BORDER[a.status] || '#2a2a2a'}`, borderRadius: 8, padding: '10px 14px', transition: 'all 0.4s ease', animation: 'fadeIn 0.3s ease' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#666' }}>{a.id}</span>
                <span style={{ fontSize: 10, background: '#1a1a1a', border: '0.5px solid #333', borderRadius: 4, padding: '1px 6px', color: '#555' }}>{a.category}</span>
                <span style={{ fontSize: 10, color: STATUS_TEXT[a.status] || '#555', fontWeight: 600 }}>
                  {a.status.toUpperCase()}{a.turn_broken ? ` (turn ${a.turn_broken})` : ''}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 12, flexShrink: 0 }}>
                <span style={{ fontSize: 10, color: '#555' }}>fragility <b style={{ color: a.fragility > 75 ? '#cc4444' : a.fragility > 55 ? '#cc8800' : '#88cc44' }}>{a.fragility}</b></span>
                <span style={{ fontSize: 10, color: '#555' }}>crit <b>{Math.round(a.criticality * 100)}%</b></span>
              </div>
            </div>
            <div style={{ fontSize: 13, color: a.status === 'broken' ? '#ff9999' : a.status === 'stressed' ? '#ffcc88' : '#ccc', lineHeight: 1.5 }}>{a.text}</div>
            {a.basis && <div style={{ fontSize: 11, color: '#444', marginTop: 5 }}>Basis: {a.basis}</div>}
            {a.cascade_effect && a.status !== 'untested' && (
              <div style={{ fontSize: 11, color: '#cc8800', marginTop: 4 }}>→ {a.cascade_effect}</div>
            )}
            {a.dependencies.length > 0 && (
              <div style={{ fontSize: 10, color: '#333', marginTop: 3 }}>cascades to: {a.dependencies.join(', ')}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
