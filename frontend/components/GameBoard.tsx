'use client';
import { useState } from 'react';
import { playTurn, GameState } from '../lib/api';

const QUICK_ACTIONS = [
  { id: 'airstrike',  label: 'F-35 airstrike',      desc: 'Strike missile battery. High kinetic, high info cost.' },
  { id: 'submarine',  label: 'Deploy submarines',    desc: 'Covert interdiction. Lower escalation.' },
  { id: 'sanctions',  label: 'Economic sanctions',   desc: 'Non-kinetic pressure. Boosts intl opinion.' },
  { id: 'isr',        label: 'Pause for ISR',        desc: 'Intelligence gathering. Rebuild initiative.' },
  { id: 'coalition',  label: 'Coalition messaging',  desc: 'Strengthen allied confidence.' },
  { id: 'cyber',      label: 'Cyber operation',      desc: 'Degrade C2. Moderate escalation.' },
];

export default function GameBoard({ game, onUpdate }: { game: GameState; onUpdate: (g: GameState) => void }) {
  const [action, setAction] = useState('');
  const [selected, setSelected] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  async function send(actionText: string) {
    if (!actionText.trim()) return;
    setBusy(true); setErr('');
    try {
      const updated = await playTurn(game.id, actionText);
      onUpdate(updated);
      setAction(''); setSelected('');
      if (updated.status !== 'active') {
        localStorage.setItem('warbreak_game_id', game.id);
        setTimeout(() => { window.location.href = '/autopsy'; }, 1500);
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Turn failed');
    } finally {
      setBusy(false);
    }
  }

  const last = game.events.at(-1);

  return (
    <div style={{ background: '#0d0d0d', border: '0.5px solid #1e1e1e', borderRadius: 12, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ fontSize: 11, letterSpacing: '0.1em', color: '#555' }}>
          TURN {game.turn + 1} OF {game.max_turns} — BLUE MOVE
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {Array.from({ length: game.max_turns }).map((_, i) => (
            <div key={i} style={{
              width: 20, height: 20, borderRadius: '50%', fontSize: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: i < game.turn ? '#222' : i === game.turn ? '#378ADD' : '#111',
              color: i < game.turn ? '#444' : '#fff',
              border: i === game.turn ? '0.5px solid #378ADD' : '0.5px solid #222',
            }}>{i + 1}</div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
        {QUICK_ACTIONS.map(({ id, label, desc }) => (
          <button key={id}
            onClick={() => { setSelected(id); setAction(label); }}
            style={{ padding: '10px 12px', background: selected === id ? '#0c2240' : '#111', border: `0.5px solid ${selected === id ? '#378ADD' : '#222'}`, borderRadius: 8, color: selected === id ? '#7ab8e8' : '#888', fontSize: 12, cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s' }}>
            <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>
            <div style={{ fontSize: 10, color: selected === id ? '#5a9acc' : '#444' }}>{desc}</div>
          </button>
        ))}
      </div>

      <div style={{ fontSize: 10, letterSpacing: '0.08em', color: '#444', marginBottom: 6 }}>OR WRITE A CUSTOM ACTION</div>
      <textarea
        value={action}
        onChange={e => { setAction(e.target.value); setSelected(''); }}
        placeholder="e.g. surge logistics to forward base, conduct cyber deception against radar..."
        rows={3}
        style={{ width: '100%', background: '#080808', border: '0.5px solid #222', borderRadius: 8, padding: '10px 12px', color: '#e8e6e0', fontSize: 13, fontFamily: 'monospace', resize: 'vertical', outline: 'none', boxSizing: 'border-box' }}
      />

      {err && <div style={{ fontSize: 12, color: '#cc4444', marginTop: 8 }}>{err}</div>}

      <button
        onClick={() => send(action)}
        disabled={busy || !action.trim()}
        style={{ marginTop: 10, width: '100%', padding: 12, background: busy ? '#111' : '#e8e6e0', color: busy ? '#555' : '#0a0a0a', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: busy ? 'not-allowed' : 'pointer', letterSpacing: '0.05em', transition: 'all 0.15s' }}>
        {busy ? 'Ghost Council analyzing...' : 'COMMIT MOVE →'}
      </button>

      {last && (
        <div style={{ marginTop: 12, padding: '10px 12px', background: '#080808', border: '0.5px solid #1a1a1a', borderRadius: 8 }}>
          <div style={{ fontSize: 10, color: '#333', marginBottom: 5 }}>LAST TURN</div>
          <div style={{ fontSize: 12, color: '#555' }}>Blue: {last.blue_move}</div>
          {last.broken_chain.length > 0 && (
            <div style={{ fontSize: 12, color: '#cc4444', marginTop: 4 }}>
              Assumptions broken: {last.broken_chain.join(', ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
