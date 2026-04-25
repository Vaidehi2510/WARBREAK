import { AutopsyReport } from '../lib/api';

export default function Autopsy({ report }: { report: AutopsyReport }) {
  const sections: { title: string; content: string }[] = [];
  const parts = report.report.split(/^== (.+) ==$/m);
  for (let i = 1; i < parts.length - 1; i += 2) {
    sections.push({ title: parts[i].trim(), content: parts[i + 1].trim() });
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 10, letterSpacing: '0.15em', color: '#444', marginBottom: 8 }}>WARBREAK — FAILURE AUTOPSY</div>
        <h1 style={{ fontSize: 32, fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
          {report.status === 'failed' ? 'Plan Collapsed' : 'Campaign Complete'}
        </h1>
        <p style={{ color: '#555', marginTop: 8, fontSize: 14 }}>
          {report.turns} turns · {report.assumptions_broken} assumptions broken · {report.assumptions_stressed} stressed
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 24 }}>
        {Object.entries(report.final_metrics).map(([k, v]) => (
          <div key={k} style={{ background: '#111', border: '0.5px solid #1e1e1e', borderRadius: 8, padding: '10px 12px' }}>
            <div style={{ fontSize: 10, color: '#444', marginBottom: 4 }}>{k.replace(/_/g, ' ').toUpperCase()}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: v < 30 ? '#cc4444' : v > 65 ? '#88cc44' : '#e8e6e0' }}>{Math.round(v)}</div>
          </div>
        ))}
      </div>

      {report.root_causes.length > 0 && (
        <div style={{ background: '#0e0404', border: '0.5px solid #3a1010', borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#cc2222', marginBottom: 10 }}>ROOT CAUSES</div>
          {report.root_causes.map((c, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#cc3333', marginTop: 5, flexShrink: 0 }} />
              <div style={{ fontSize: 13, color: '#ff9999' }}>{c}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 24 }}>
        {sections.length > 0 ? sections.map(({ title, content }) => (
          <div key={title} style={{ background: '#0d0d0d', border: '0.5px solid #1e1e1e', borderRadius: 10, padding: '14px 16px' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#444', marginBottom: 10 }}>{title}</div>
            <div style={{ fontSize: 13, color: '#999', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{content}</div>
          </div>
        )) : (
          <div style={{ background: '#0d0d0d', border: '0.5px solid #1e1e1e', borderRadius: 10, padding: '14px 16px' }}>
            <div style={{ fontSize: 13, color: '#999', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{report.report}</div>
          </div>
        )}
      </div>

      <div style={{ background: '#040e04', border: '0.5px solid #1a3a1a', borderRadius: 10, padding: '14px 16px', marginBottom: 20 }}>
        <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#2a7a2a', marginBottom: 8 }}>RECOMMENDATION</div>
        <div style={{ fontSize: 13, color: '#88cc88', lineHeight: 1.6 }}>{report.recommendation}</div>
      </div>

      <button
        onClick={() => window.location.href = '/'}
        style={{ width: '100%', padding: 12, background: '#e8e6e0', color: '#0a0a0a', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: 'pointer', letterSpacing: '0.05em' }}>
        RUN ANOTHER PLAN →
      </button>
    </div>
  );
}
