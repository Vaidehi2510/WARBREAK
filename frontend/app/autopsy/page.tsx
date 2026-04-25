'use client';
import { useEffect, useState } from 'react';
import { getAutopsy, AutopsyReport } from '../../lib/api';
import Autopsy from '../../components/Autopsy';

export default function AutopsyPage() {
  const [report, setReport] = useState<AutopsyReport | null>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = localStorage.getItem('warbreak_game_id');
    if (!id) { window.location.href = '/'; return; }
    getAutopsy(id).then(setReport).catch(e => setErr(e.message)).finally(() => setLoading(false));
  }, []);

  if (err) return <main className="shell" style={{ color: '#cc4444', paddingTop: 60 }}>{err}</main>;
  if (loading) return (
    <main className="shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 11, letterSpacing: '0.1em', color: '#444', marginBottom: 8 }}>WARBREAK</div>
        <div style={{ fontSize: 14, color: '#333' }}>Generating failure autopsy...</div>
      </div>
    </main>
  );
  if (!report) return null;

  return <main className="shell"><Autopsy report={report} /></main>;
}
