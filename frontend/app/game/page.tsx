'use client';
import { useEffect, useState } from 'react';
import { getGame, GameState } from '../../lib/api';
import InfoDashboard from '../../components/InfoDashboard';
import AssumptionMap from '../../components/AssumptionMap';
import GameBoard from '../../components/GameBoard';
import CascadeOverlay from '../../components/CascadeOverlay';

export default function GamePage() {
  const [game, setGame] = useState<GameState | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    const id = localStorage.getItem('warbreak_game_id');
    if (!id) { window.location.href = '/'; return; }
    getGame(id).then(setGame).catch(e => setErr(e.message));
  }, []);

  if (err) return (
    <main className="shell" style={{ color: '#cc4444', paddingTop: 60 }}>{err}</main>
  );
  if (!game) return (
    <main className="shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.1em', color: '#444', marginBottom: 8 }}>WARBREAK</div>
        <div style={{ fontSize: 14, color: '#333' }}>Loading session...</div>
      </div>
    </main>
  );

  return (
    <main className="shell">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: '#333', marginBottom: 4 }}>WARBREAK — ACTIVE SESSION</div>
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Taiwan Strait 2027</h1>
        </div>
        <div style={{ fontSize: 11, color: '#444', background: '#111', border: '0.5px solid #222', padding: '6px 12px', borderRadius: 8 }}>
          Turn {game.turn} / {game.max_turns}
        </div>
      </div>

      <InfoDashboard metrics={game.metrics} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 4 }}>
        <GameBoard game={game} onUpdate={setGame} />
        <CascadeOverlay events={game.events} assumptions={game.assumptions} />
      </div>

      <AssumptionMap assumptions={game.assumptions} />

      {game.status !== 'active' && (
        <div style={{ marginTop: 20, padding: 20, background: '#040e04', border: '0.5px solid #1a4a1a', borderRadius: 10, textAlign: 'center' }}>
          <div style={{ fontSize: 14, color: '#88cc88', marginBottom: 14 }}>
            Game {game.status}. Redirecting to failure autopsy...
          </div>
          <button
            onClick={() => window.location.href = '/autopsy'}
            style={{ padding: '10px 24px', background: '#e8e6e0', color: '#0a0a0a', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
            VIEW FAILURE AUTOPSY →
          </button>
        </div>
      )}
    </main>
  );
}
