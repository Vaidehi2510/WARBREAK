import PlanInput from '../components/PlanInput';

export default function Home() {
  return (
    <main className="shell" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ maxWidth: 680, margin: '0 auto', width: '100%' }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: '#444', marginBottom: 10 }}>
            SCSP AI+ EXPO HACKATHON 2026 — WARGAMING TRACK
          </div>
          <h1 style={{ fontSize: 42, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 12 }}>
            WARBREAK
          </h1>
          <p style={{ fontSize: 15, color: '#666', lineHeight: 1.7 }}>
            Every wargame shows you what happens.<br />
            WARBREAK shows you <em>why it was always going to happen.</em>
          </p>
        </div>
        <PlanInput />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 28 }}>
          {[
            { t: 'FOGLINE extraction', d: 'Live AI scans your plan for hidden assumptions with fragility scores grounded in CDB90 and doctrine' },
            { t: 'Ghost Council', d: 'Psychologically realistic PLA adversary — targets your most fragile assumption every turn' },
            { t: 'Failure autopsy', d: 'Ranked post-mortem with doctrine citations generated after every session' },
          ].map(({ t, d }) => (
            <div key={t} style={{ padding: '12px 14px', background: '#111', border: '0.5px solid #1e1e1e', borderRadius: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 5 }}>{t}</div>
              <div style={{ fontSize: 11, color: '#444', lineHeight: 1.5 }}>{d}</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
