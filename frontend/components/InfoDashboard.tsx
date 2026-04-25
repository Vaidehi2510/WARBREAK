export default function InfoDashboard({ metrics }: { metrics: Record<string, number> }) {
  const items = [
    { key: 'intl_opinion',      label: "Int'l opinion",      color: '#378ADD' },
    { key: 'us_domestic',       label: 'US domestic support', color: '#378ADD' },
    { key: 'red_domestic',      label: 'Red domestic support',color: '#E24B4A' },
    { key: 'allied_confidence', label: 'Allied confidence',   color: '#639922' },
    { key: 'blue_strength',     label: 'Blue force strength', color: '#185FA5' },
    { key: 'red_strength',      label: 'Red force strength',  color: '#A32D2D' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
      {items.map(({ key, label, color }) => {
        const val = Math.round(metrics[key] ?? 0);
        return (
          <div key={key} style={{ background: '#111', border: '0.5px solid #2a2a2a', borderRadius: 10, padding: '12px 14px' }}>
            <div style={{ fontSize: 10, color: '#555', letterSpacing: '0.06em', marginBottom: 6 }}>{label.toUpperCase()}</div>
            <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 6, color: val < 30 ? '#cc4444' : val > 70 ? '#88cc44' : '#e8e6e0' }}>{val}</div>
            <div style={{ height: 4, background: '#222', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, val))}%`, background: color, borderRadius: 2, transition: 'width 0.6s ease' }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
