'use client';
import { useState } from 'react';
import { createGame } from '../lib/api';

const SAMPLE = `Deploy carrier strike group to western Pacific and establish air superiority over Taiwan Strait using F-35 sorties from Okinawa. Coordinate with Japanese Self-Defense Forces for logistics support. Conduct precision strikes on PLA missile batteries to degrade anti-ship capability. Maintain open supply lines through Luzon Strait. Assume 48-hour window before international pressure constrains options.`;

const MSGS = [
  'Parsing operational plan...',
  'Scanning for hidden assumptions...',
  'Cross-referencing CDB90 database...',
  'Calibrating fragility scores against doctrine...',
  'Building dependency graph...',
];

export default function PlanInput() {
  const [plan, setPlan] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');

  async function submit() {
    if (plan.trim().length < 20) { setErr('Write a more detailed plan — at least 2-3 sentences.'); return; }
    setBusy(true); setErr(''); setMsg(MSGS[0]);
    let i = 0;
    const t = setInterval(() => { i = (i + 1) % MSGS.length; setMsg(MSGS[i]); }, 1400);
    try {
      const g = await createGame(plan);
      clearInterval(t);
      localStorage.setItem('warbreak_game_id', g.id);
      window.location.href = '/game';
    } catch (e: unknown) {
      clearInterval(t);
      setErr(e instanceof Error ? e.message : 'Extraction failed');
      setBusy(false);
    }
  }

  return (
    <div>
      <textarea
        value={plan}
        onChange={e => setPlan(e.target.value)}
        placeholder="Write your operational plan in plain English. Be specific about objectives, forces, and approach..."
        rows={7}
        style={{ width: '100%', background: '#111', border: '0.5px solid #333', borderRadius: 10, padding: '14px 16px', color: '#e8e6e0', fontSize: 14, fontFamily: 'monospace', resize: 'vertical', outline: 'none', lineHeight: 1.7, boxSizing: 'border-box', marginBottom: 8 }}
      />
      <button
        onClick={() => setPlan(SAMPLE)}
        style={{ fontSize: 11, color: '#444', background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginBottom: 16 }}
      >
        load sample plan →
      </button>
      {err && <div style={{ fontSize: 12, color: '#cc4444', marginBottom: 12 }}>{err}</div>}
      <button
        onClick={submit}
        disabled={busy}
        style={{ width: '100%', padding: 14, background: busy ? '#1a1a1a' : '#e8e6e0', color: busy ? '#555' : '#0a0a0a', border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 700, cursor: busy ? 'not-allowed' : 'pointer', letterSpacing: '0.05em', transition: 'all 0.15s' }}
      >
        {busy ? msg : 'EXTRACT ASSUMPTIONS →'}
      </button>
    </div>
  );
}
