"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Map as LeafletMap } from "leaflet";
import "leaflet/dist/leaflet.css";
import { playTurn } from "../../lib/api";

type Action = { key:string; title:string; desc:string; icon:string; asset?:string; once?:boolean; kind:string };

const baseActions: Action[] = [
  { key:"isr",       title:"ISR sweep",         desc:"Reveal and verify before acting.",       icon:"🔎", kind:"sensor" },
  { key:"coalition", title:"Coalition message",  desc:"Strengthen public and allied support.",  icon:"🤝", kind:"info" },
  { key:"cyber",     title:"Cyber operation",    desc:"Disrupt command links.",                 icon:"⚡", kind:"cyber", once:true },
];

const assetActions: Record<string, Action> = {
  carrier:  { key:"carrier_strike",    title:"Carrier strike",    desc:"Launch long-range air package.",         icon:"⚓",  asset:"carrier",  kind:"strike",  once:true },
  f35:      { key:"f35_airstrike",     title:"F-35 strike",       desc:"Strike key enemy system.",               icon:"✈️", asset:"f35",      kind:"strike",  once:true },
  sub:      { key:"submarine_deploy",  title:"Submarine screen",  desc:"Contest sea lanes covertly.",            icon:"◆",  asset:"sub",      kind:"sub" },
  patriot:  { key:"missile_defense",   title:"Missile defense",   desc:"Protect forward base access.",           icon:"▲",  asset:"patriot",  kind:"defense" },
  growler:  { key:"electronic_attack", title:"EW suppression",    desc:"Blind radar and targeting.",             icon:"📡", asset:"growler",  kind:"cyber",   once:true },
  p8:       { key:"asw_patrol",        title:"ASW patrol",        desc:"Hunt underwater threats.",               icon:"🔎", asset:"p8",       kind:"sensor" },
  aegis:    { key:"aegis_intercept",   title:"Aegis intercept",   desc:"Defend against missile salvo.",          icon:"⚔️", asset:"aegis",    kind:"defense" },
  stryker:  { key:"ground_secure",     title:"Secure corridor",   desc:"Hold roads and evacuation routes.",      icon:"▰",  asset:"stryker",  kind:"ground" },
  mq9:      { key:"drone_watch",       title:"Drone overwatch",   desc:"Track targets continuously.",            icon:"◈",  asset:"mq9",      kind:"sensor" },
  sof:      { key:"sof_raid",          title:"SOF raid",          desc:"Hit a fragile node quietly.",            icon:"✦",  asset:"sof",      kind:"strike",  once:true },
  sealift:  { key:"logistics_surged",  title:"Surge logistics",   desc:"Repair sustainment gaps.",               icon:"▣",  asset:"sealift",  kind:"defense" },
  cyber:    { key:"cyber_op",          title:"Cyber operation",   desc:"Network defense and disruption.",        icon:"⚡", asset:"cyber",    kind:"cyber",   once:true },
};

const mapCfg: any = {
  "Taiwan Strait 2027": { center:[23.8,121.1], zoom:6, why:"Sea lanes, Okinawa access, PLA coastal systems, Luzon Strait.", label:"Taiwan Strait", red:[[24.2,118.2,"🚀"],[23.5,118.7,"✈️"],[22.5,119.2,"⚓"]], blue:[[25.2,122.1,"⚓"],[24.2,122.7,"◆"],[26.1,127.7,"✈️"]] },
  "NATO Eastern Flank": { center:[53.4,22.6],  zoom:6, why:"Suwalki Gap, Baltic access, NATO cohesion, Russian pressure.",  label:"Suwalki Gap",   red:[[54.6,25.3,"▰"],[53.9,27.5,"🚀"],[54.9,20.5,"⚓"]], blue:[[52.2,21.0,"▰"],[54.7,18.6,"✈️"],[53.1,23.1,"▲"]] },
  "Embassy Evacuation": { center:[33.33,44.38], zoom:7, why:"Air corridors, roads, embassy access, harbor reach.",          label:"Capital zone",  red:[[33.45,44.45,"▰"],[33.28,44.54,"🚀"],[33.36,44.25,"⚡"]], blue:[[33.31,44.36,"🚁"],[33.25,44.31,"✦"],[33.5,44.1,"▣"]] },
  "Cyber Infrastructure": { center:[40.75,-74.3], zoom:6, why:"Substations, command networks, cascading infrastructure.",   label:"Northeast grid",red:[[40.72,-74.0,"⚡"],[41.1,-73.7,"▣"],[40.2,-75.1,"⚠️"]], blue:[[40.76,-73.9,"🛡️"],[40.4,-74.6,"⚡"],[41.0,-74.2,"🔎"]] },
};

const metricNames = [
  ["intl_opinion","Intl opinion"],
  ["us_domestic","US support"],
  ["red_domestic","Red support"],
  ["allied_confidence","Allied confidence"],
  ["blue_strength","Blue force"],
  ["red_strength","Red force"],
];

export default function GamePage() {
  const router = useRouter();
  const mapRef  = useRef<HTMLDivElement>(null);
  const leaflet = useRef<LeafletMap | null>(null);
  const leafletLib = useRef<any>(null);

  const [scenario,  setScenario]  = useState("Taiwan Strait 2027");
  const [turn,      setTurn]      = useState(1);
  const [maxTurns,  setMaxTurns]  = useState(5);
  const [metrics,   setMetrics]   = useState<any>({ intl_opinion:50, us_domestic:72, red_domestic:61, allied_confidence:58, blue_strength:100, red_strength:100 });
  const [selected,  setSelected]  = useState<string>("");
  const [used,      setUsed]      = useState<string[]>([]);
  const [toast,     setToast]     = useState("");
  const [ghost,     setGhost]     = useState("Ghost Council is watching. Make your first move.");
  const [ghostHistory, setGhostHistory] = useState<{turn:number; response:string}[]>([]);
  const [redUsed,   setRedUsed]   = useState<string[]>([]);
  const [fx,        setFx]        = useState<any[]>([]);
  const [history,   setHistory]   = useState<any[]>([]);
  const [assetIds,  setAssetIds]  = useState<string[]>([]);
  const [busy,      setBusy]      = useState(false);

  // ── Load saved assets + scenario on mount ────────────────────────────────
  const actions = useMemo<Action[]>(() => {
    let ids: string[] = [];
    try { ids = JSON.parse(localStorage.getItem("warbreak_asset_ids") || "[]"); } catch {}
    if (!ids.length) ids = ["carrier", "sub", "f35", "patriot", "growler", "p8"];
    const fromAssets = ids.map(id => assetActions[id]).filter(Boolean);
    const all = [...fromAssets, ...baseActions];
    // deduplicate by key
    const seen = new Set<string>();
    return all.filter(a => { if (seen.has(a.key)) return false; seen.add(a.key); return true; });
  }, []);

  useEffect(() => {
    const sc  = localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027";
    const ids = (() => { try { return JSON.parse(localStorage.getItem("warbreak_asset_ids") || "[]"); } catch { return []; } })();
    const mt  = Number(localStorage.getItem("warbreak_max_turns") || ids.length || 5);
    setScenario(sc);
    setAssetIds(ids);
    setMaxTurns(Math.max(3, mt));
  }, []);

  // ── Map init ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || leaflet.current) return;
    let cancelled = false;

    async function initMap() {
      const L = await import("leaflet");
      if (cancelled || !mapRef.current || leaflet.current) return;

      leafletLib.current = L;
      const sc   = localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027";
      const cfg  = mapCfg[sc] || mapCfg["Taiwan Strait 2027"];
      const m    = L.map(mapRef.current, { center: cfg.center, zoom: cfg.zoom, zoomControl:false, attributionControl:false, dragging:true, scrollWheelZoom:true });
      leaflet.current = m;
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { subdomains:"abcd", maxZoom:19 }).addTo(m);
      const icon = (cls: string, emoji: string) => L.divIcon({ html:`<div class="marker ${cls}">${emoji}</div>`, className:"", iconSize:[34,34], iconAnchor:[17,17] });
      cfg.blue.forEach((p: any) => L.marker([p[0],p[1]], { icon:icon("blue",p[2]) }).addTo(m));
      cfg.red.forEach((p: any)  => L.marker([p[0],p[1]], { icon:icon("red",p[2]) }).addTo(m));
    }

    initMap();
    return () => { cancelled = true; };
  }, [scenario]);

  // ── Sound ─────────────────────────────────────────────────────────────────
  const sound = (type: string) => {
    try {
      const ctx = new AudioContext(); const o = ctx.createOscillator(); const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = type==="boom"?70:type==="sonar"?440:type==="cyber"?880:260;
      g.gain.value = 0.09; o.start();
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
      o.stop(ctx.currentTime + 0.5);
    } catch {}
  };

  // ── Animation ─────────────────────────────────────────────────────────────
  const animate = (kind: string) => {
    const id  = Date.now() + Math.random();
    const cls = kind==="sub"||kind==="sensor" ? "sonar" : kind==="cyber" ? "cyber" : "explosion";
    setFx(f => [...f, { id, cls }]);
    sound(cls==="explosion"?"boom":cls==="sonar"?"sonar":"cyber");
    setTimeout(() => setFx(f => f.filter(x => x.id !== id)), 1700);
    const cfg = mapCfg[scenario] || mapCfg["Taiwan Strait 2027"];
    const L = leafletLib.current;
    if (leaflet.current && L) {
      leaflet.current.flyTo([cfg.red[0][0], cfg.red[0][1]], cfg.zoom + 1, { duration:0.8 });
      if (kind === "strike") {
        const from = cfg.blue[0], to = cfg.red[0];
        const line = L.polyline([[from[0],from[1]], [to[0],to[1]]], { color:"#e5d28c", weight:3, className:"arc" }).addTo(leaflet.current);
        setTimeout(() => line.remove(), 1300);
      }
    }
  };

  // ── Execute turn ──────────────────────────────────────────────────────────
  const execute = async () => {
    if (busy) return;
    const act = actions.find(a => a.key === selected) || actions[0];
    if (!act) return;
    if (act.once && used.includes(act.key)) {
      setToast("That one-time action has already been used.");
      setTimeout(() => setToast(""), 2000);
      return;
    }
    if (act.once) setUsed(u => [...u, act.key]);
    animate(act.kind);
    setBusy(true);

    const redAsset = act.kind==="strike"          ? "mobile air defense + information response"
                   : act.kind==="sub"             ? "diesel-electric submarine screen"
                   : act.kind==="cyber"           ? "cyber / electronic disruption cell"
                   : act.kind==="defense"         ? "missile pressure and decoys"
                                                  : "media pressure + observation network";
    setRedUsed(r => Array.from(new Set([...r, redAsset])));

    let ghostReply = "";
    try {
      const gid = localStorage.getItem("warbreak_game_id") || "local-demo";
      const res  = await playTurn(gid, act.title);

      // Extract ghost reasoning from all possible fields
      ghostReply = res.ghost_reasoning
        || res.ghost_response
        || res.red_move
        || (res.events?.at(-1)?.ghost_reasoning)
        || "";

      // Update metrics from response
      const newMetrics = res.metrics || res.game_state || {};
      if (Object.keys(newMetrics).length > 0) {
        setMetrics((m: any) => ({ ...m, ...newMetrics }));
      }
    } catch {
      ghostReply = "Backend unavailable — visual simulation continues.";
    }

    if (!ghostReply) {
      ghostReply = `Turn ${turn}: Ghost Council responds to your ${act.title}. Red exploits the assumption behind your move — not just the unit you moved.`;
    }

    setGhost(ghostReply);
    setGhostHistory(h => [...h, { turn, response: ghostReply }]);
    setHistory(h => [...h, { turn, action: act.title, red: redAsset, ghost: ghostReply }]);
    setBusy(false);

    if (turn >= maxTurns) {
      localStorage.setItem("warbreak_history",  JSON.stringify([...history, { turn, action:act.title, red:redAsset, ghost:ghostReply }]));
      localStorage.setItem("warbreak_metrics",  JSON.stringify(metrics));
      localStorage.setItem("warbreak_red_used", JSON.stringify(Array.from(new Set([...redUsed, redAsset]))));
      router.push("/autopsy");
    } else {
      setTurn(t => t + 1);
    }
  };

  const cfg = mapCfg[scenario] || mapCfg["Taiwan Strait 2027"];

  return (
    <main className="game">
      {/* Top bar */}
      <div className="topbar">
        <div className="brand">
          <button className="btn ghost" onClick={() => router.push("/")}>← Exit</button>
          WARBREAK
          <span className="badge">{scenario}</span>
        </div>
        <div style={{ display:"flex", gap:8, alignItems:"center" }}>
          <span className="badge">Turn {turn}/{maxTurns}</span>
          <span className="badge" style={{ background:"rgba(0,232,122,0.15)", border:"1px solid rgba(0,232,122,0.3)", color:"#00e87a" }}>
            ACTIVE
          </span>
          {busy && <span className="badge" style={{ background:"rgba(255,170,0,0.15)", color:"#ffaa00" }}>PROCESSING...</span>}
        </div>
      </div>

      <div className="game-layout">
        {/* Map stage */}
        <section className="map-stage">
          <div ref={mapRef} className="map3d" />
          <div className="map-overlay" />
          <div className="scanline" />
          <div className="stage-hud">
            <div className="note">Drag to pan · scroll to zoom</div>
            <div className="note dark">Why this area? {cfg.why}</div>
          </div>
          {fx.map(x => <div key={x.id} className={`fx ${x.cls}`} style={{ left:"54%", top:"45%" }} />)}
          {toast && <div className="toast">{toast}</div>}

          {/* Actions dock */}
          <div className="execute-row">
            <button className="btn primary" onClick={execute} disabled={busy || !selected} style={{ opacity: busy||!selected ? 0.5 : 1 }}>
              {busy ? "EXECUTING…" : "EXECUTE SELECTED →"}
            </button>
          </div>
          <div className="actions-dock">
            {actions.map((a, i) => (
              <button
                key={a.key}
                onClick={() => setSelected(a.key)}
                className={`action-card ${selected===a.key?"selected":""} ${used.includes(a.key)?"used":""}`}
              >
                <h4 style={{ fontSize:12, margin:"0 0 3px" }}>{i+1}. {a.icon} {a.title}</h4>
                <p style={{ fontSize:10, margin:0, opacity:0.65 }}>{a.desc}</p>
                {used.includes(a.key) && <span className="small" style={{ fontSize:9, color:"#ff6644" }}>Used</span>}
              </button>
            ))}
          </div>
        </section>

        {/* Sidebar */}
        <aside className="sidebar">
          {/* Metrics */}
          <div className="side-card">
            <h3 style={{ fontSize:13, marginTop:0, marginBottom:10 }}>Information battlefield</h3>
            {metricNames.map(([k, n]) => (
              <div className="metric" key={k}>
                <div className="metric-head">
                  <span style={{ fontSize:11 }}>{n}</span>
                  <b style={{ fontSize:12 }}>{Math.round(metrics[k] ?? 50)}</b>
                </div>
                <div className="bar">
                  <span style={{ width:`${Math.max(0, Math.min(100, metrics[k] ?? 50))}%` }} />
                </div>
              </div>
            ))}
          </div>

          {/* Ghost Council */}
          <div className="side-card" style={{ border:"1px solid rgba(255,60,60,0.25)", background:"rgba(255,20,20,0.04)" }}>
            <h3 style={{ fontSize:13, marginTop:0, marginBottom:8, color:"#ff8888" }}>
              👁 Ghost Council
            </h3>
            <p style={{ fontSize:12, lineHeight:1.65, margin:0, color:"rgba(255,200,200,0.85)" }}>
              {ghost}
            </p>
            {ghostHistory.length > 1 && (
              <div style={{ marginTop:10, paddingTop:10, borderTop:"1px solid rgba(255,60,60,0.15)" }}>
                <div style={{ fontSize:10, opacity:0.4, marginBottom:6, letterSpacing:"0.08em" }}>PREVIOUS</div>
                {ghostHistory.slice(-3, -1).reverse().map((h, i) => (
                  <p key={i} style={{ fontSize:10, opacity:0.5, margin:"0 0 4px", lineHeight:1.5 }}>
                    T{h.turn}: {h.response.slice(0, 80)}…
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Red assets */}
          <div className="side-card">
            <h3 style={{ fontSize:13, marginTop:0, marginBottom:8 }}>Red assets committed</h3>
            {redUsed.length
              ? redUsed.map((r, i) => <p key={i} className="small" style={{ fontSize:11 }}>• {r}</p>)
              : <p className="small" style={{ fontSize:11, opacity:0.4 }}>No enemy asset committed yet.</p>
            }
          </div>

          {/* Mission log */}
          <div className="side-card">
            <h3 style={{ fontSize:13, marginTop:0, marginBottom:8 }}>Mission log</h3>
            {history.length === 0 && <p className="small" style={{ fontSize:11, opacity:0.4 }}>No moves yet.</p>}
            {history.map(h => (
              <p key={h.turn} className="small" style={{ fontSize:10, margin:"0 0 4px" }}>
                T{h.turn}: Blue → {h.action}. Red → {h.red}.
              </p>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}
