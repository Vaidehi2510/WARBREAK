'use client';
import { useEffect, useState } from 'react';
import { GameEvent, Assumption } from '../lib/api';

export default function CascadeOverlay({ events, assumptions }: { events: GameEvent[]; assumptions: Assumption[] }) {
  const [showCascade, setShowCascade] = useState(false);
  const last = events.at(-1);

  useEffect(() => {
    if (last?.broken_chain?.length) {
      setShowCascade(true);
      const t = setTimeout(() => setShowCascade(false), 10000);
      return () => clearTimeout(t);
    }
  }, [events.length]);

  if (!last) return null;

  const broken = assumptions.filter(a => last.broken_chain.includes(a.id));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {last.red_move && (
        <div style={{ background: '#0e0606', border: '0.5px solid #3a1010', borderRadius: 10, padding: '14px 16px' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#661a1a', marginBottom: 8 }}>GHOST COUNCIL RESPONSE</div>
          <div style={{ fontSize: 13, color: '#ffaaaa', marginBottom: 8, fontWeight: 600 }}>{last.red_move}</div>
          <div style={{ fontSize: 12, color: '#cc8888', lineHeight: 1.6, fontStyle: 'italic' }}>"{last.ghost_reasoning}"</div>
          {last.ghost_state_text && (
            <div style={{ fontSize: 11, color: '#664444', marginTop: 10, paddingTop: 10, borderTop: '0.5px solid #2a1010' }}>
              Commander state: {last.ghost_state_text}
            </div>
          )}
        </div>
      )}

      {showCascade && broken.length > 0 && (
        <div style={{ background: '#120404', border: '0.5px solid #cc2222', borderRadius: 10, padding: '14px 16px', animation: 'pulse 1.5s ease-in-out 2' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#cc2222', marginBottom: 12 }}>
            ASSUMPTION BREAK — CASCADE INITIATED
          </div>
          {broken.map((a, i) => (
            <div key={a.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 10, opacity: Math.max(0.4, 1 - i * 0.2) }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#cc3333', marginTop: 4, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 12, color: '#ff9999', fontWeight: 600 }}>{a.id} — {a.text}</div>
                {a.cascade_effect && <div style={{ fontSize: 11, color: '#aa5555', marginTop: 3 }}>→ {a.cascade_effect}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {last.options.length > 0 && (
        <div style={{ background: '#0d0d0d', border: '0.5px solid #1e1e1e', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#444', marginBottom: 8 }}>SUGGESTED RESPONSES</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {last.options.map((opt, i) => (
              <div key={i} style={{ fontSize: 12, color: '#666', padding: '6px 10px', background: '#111', borderRadius: 6, border: '0.5px solid #222' }}>
                {opt}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
