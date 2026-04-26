"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Map as LeafletMap } from "leaflet";
import "leaflet/dist/leaflet.css";
import { createGame, playTurn } from "../../lib/api";

type Action = { key:string; title:string; desc:string; icon:string; asset?:string; once?:boolean; kind:string };
type LatLng = [number, number];

const assetActions: Record<string, Action> = {
  carrier:  { key:"carrier_strike",    title:"Carrier Strike Group",      desc:"Launch long-range air package.",         icon:"⚓",  asset:"carrier",  kind:"strike",  once:true },
  f35:      { key:"f35_airstrike",     title:"F-35C Squadron",            desc:"Strike key enemy system.",               icon:"✈️", asset:"f35",      kind:"strike",  once:true },
  sub:      { key:"submarine_deploy",  title:"Virginia-class Submarine",  desc:"Contest sea lanes covertly.",            icon:"◆",  asset:"sub",      kind:"sub" },
  patriot:  { key:"missile_defense",   title:"Patriot PAC-3 Battery",     desc:"Protect forward base access.",           icon:"▲",  asset:"patriot",  kind:"defense" },
  growler:  { key:"electronic_attack", title:"EA-18G Growler Squadron",   desc:"Blind radar and targeting.",             icon:"📡", asset:"growler",  kind:"cyber",   once:true },
  p8:       { key:"asw_patrol",        title:"P-8 Poseidon Patrol",       desc:"Hunt underwater threats.",               icon:"🔎", asset:"p8",       kind:"sensor" },
  aegis:    { key:"aegis_intercept",   title:"Aegis Destroyer",           desc:"Defend against missile salvo.",          icon:"⚔️", asset:"aegis",    kind:"defense" },
  stryker:  { key:"ground_secure",     title:"Stryker Brigade",           desc:"Hold roads and evacuation routes.",      icon:"▰",  asset:"stryker",  kind:"ground" },
  mq9:      { key:"drone_watch",       title:"MQ-9 Reaper Flight",        desc:"Track targets continuously.",            icon:"◈",  asset:"mq9",      kind:"sensor" },
  sof:      { key:"sof_raid",          title:"Special Operations Team",   desc:"Hit a fragile node quietly.",            icon:"✦",  asset:"sof",      kind:"strike",  once:true },
  sealift:  { key:"logistics_surged",  title:"Sealift Logistics Package", desc:"Repair sustainment gaps.",               icon:"▣",  asset:"sealift",  kind:"defense" },
  cyber:    { key:"cyber_op",          title:"Cyber Command Cell",        desc:"Network defense and disruption.",        icon:"⚡", asset:"cyber",    kind:"cyber",   once:true },
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

const fallbackPlans: Record<string, string> = {
  "Taiwan Strait 2027": "Deploy the selected force package to the Taiwan Strait. Preserve sea lanes through the Luzon Strait, coordinate regional basing and logistics, identify PLA coastal threats, and maintain allied support while avoiding uncontrolled escalation.",
  "NATO Eastern Flank": "Deploy the selected force package to reinforce NATO's eastern flank. Secure logistics routes, protect forward air and missile defense access, coordinate with host nations, and preserve alliance cohesion under gray-zone pressure.",
  "Embassy Evacuation": "Deploy the selected force package to evacuate embassy personnel and civilians. Secure the compound, protect air and road corridors, coordinate evacuation lift, and avoid civilian casualties while hostile forces converge.",
  "Cyber Infrastructure": "Deploy the selected response package to stabilize critical infrastructure. Restore priority systems, protect command networks, attribute the attack, and prevent cascading public confidence and service failures.",
};

const assetPositions: Record<string, Record<string, LatLng>> = {
  "Taiwan Strait 2027": {
    carrier:[25.2,122.1], sub:[23.9,122.6], f35:[26.1,127.7], patriot:[24.1,121.2],
    growler:[25.7,124.2], p8:[24.7,123.5], aegis:[24.7,122.0], stryker:[23.5,120.7],
    cyber:[25.0,121.5], mq9:[24.4,121.8], sof:[23.9,121.0], sealift:[22.8,120.2],
  },
  "NATO Eastern Flank": {
    carrier:[55.1,18.8], sub:[55.3,19.9], f35:[54.8,20.8], patriot:[52.7,23.0],
    growler:[54.3,21.6], p8:[56.2,20.8], aegis:[54.9,19.2], stryker:[53.1,21.0],
    cyber:[52.25,21.0], mq9:[53.8,22.6], sof:[54.0,24.0], sealift:[54.5,18.6],
  },
  "Embassy Evacuation": {
    carrier:[33.5,44.1], sub:[33.48,44.05], f35:[33.58,44.28], patriot:[33.42,44.33],
    growler:[33.55,44.22], p8:[33.52,44.18], aegis:[33.46,44.12], stryker:[33.31,44.36],
    cyber:[33.37,44.31], mq9:[33.43,44.26], sof:[33.25,44.31], sealift:[33.28,44.18],
  },
  "Cyber Infrastructure": {
    carrier:[40.66,-74.05], sub:[40.55,-73.9], f35:[40.95,-73.9], patriot:[40.75,-74.18],
    growler:[40.88,-74.08], p8:[41.0,-74.2], aegis:[40.62,-74.12], stryker:[40.68,-74.45],
    cyber:[40.76,-73.9], mq9:[40.82,-74.25], sof:[40.7,-74.32], sealift:[40.5,-74.1],
  },
};

function localGhostCouncil(act: Action, redAsset: string, scenario: string) {
  const pressure: Record<string, string> = {
    strike: "Red disperses the visible target set and turns your kinetic move into a contest over proof, timing, and escalation control.",
    sub: "Red floods the operating area with ambiguous contacts, forcing Blue to spend time separating decoys from real threats.",
    cyber: "Red shifts to backup command paths and uses the disruption attempt as evidence of escalation.",
    defense: "Red probes for saturation points with decoys, cheap salvos, and information pressure around collateral risk.",
    ground: "Red avoids a direct fight and pressures the roads, ports, and local political assumptions behind the corridor.",
    sensor: "Red changes signatures, uses civilian clutter, and tries to make Blue act on stale intelligence.",
    info: "Red counters the narrative with selective evidence and pressure on allied hesitation.",
  };

  return `Ghost Council: ${act.title} is credible, but not decisive. ${pressure[act.kind] || pressure.info} Expected red response: ${redAsset}. In ${scenario}, protect the assumption behind the move before committing the next package.`;
}

function localMetricPatch(kind: string) {
  if (kind === "strike") return { red_strength:-6, intl_opinion:-3, allied_confidence:2 };
  if (kind === "sub") return { red_strength:-3, allied_confidence:2 };
  if (kind === "cyber") return { red_strength:-4, intl_opinion:-2 };
  if (kind === "defense") return { blue_strength:2, us_domestic:2 };
  if (kind === "ground") return { allied_confidence:2, us_domestic:1 };
  if (kind === "sensor") return { allied_confidence:3, intl_opinion:1 };
  return { intl_opinion:2, allied_confidence:2 };
}

function assetPoint(scenario: string, action: Action, index: number): LatLng {
  const configured = action.asset ? assetPositions[scenario]?.[action.asset] : undefined;
  if (configured) return configured;

  const cfg = mapCfg[scenario] || mapCfg["Taiwan Strait 2027"];
  const base = cfg.blue?.[index % Math.max(1, cfg.blue.length)] || cfg.center;
  const ring = Math.floor(index / Math.max(1, cfg.blue.length)) + 1;
  return [
    base[0] + Math.sin(index + 1) * 0.18 * ring,
    base[1] + Math.cos(index + 1) * 0.24 * ring,
  ];
}

function redTargetPoint(scenario: string, action: Action): LatLng {
  const cfg = mapCfg[scenario] || mapCfg["Taiwan Strait 2027"];
  const red = cfg.red || [];
  const maritimeAssets = new Set(["sub", "p8"]);
  const missileDefenseAssets = new Set(["patriot", "aegis"]);
  const index =
    action.asset && maritimeAssets.has(action.asset) ? 2 :
    action.asset && missileDefenseAssets.has(action.asset) ? 1 :
    action.kind === "sub" ? 2 :
    action.kind === "cyber" ? 1 :
    action.kind === "defense" ? 1 :
    action.kind === "ground" ? 0 :
    action.kind === "sensor" ? 0 :
    1;
  const point = red[Math.min(index, Math.max(0, red.length - 1))] || red[0] || cfg.center;
  return [point[0], point[1]];
}

function effectRadius(scenario: string, meters: number) {
  const scale =
    scenario === "Embassy Evacuation" ? 0.055 :
    scenario === "Cyber Infrastructure" ? 0.075 :
    scenario === "Taiwan Strait 2027" ? 0.82 :
    1;
  return Math.round(meters * scale);
}

export default function GamePage() {
  const router = useRouter();
  const mapRef  = useRef<HTMLDivElement>(null);
  const leaflet = useRef<LeafletMap | null>(null);
  const leafletLib = useRef<any>(null);
  const blueLayer = useRef<any>(null);
  const redLayer = useRef<any>(null);
  const fxLayer = useRef<any>(null);

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
  const [history,   setHistory]   = useState<any[]>([]);
  const [assetIds,  setAssetIds]  = useState<string[]>([]);
  const [mapReady,  setMapReady]  = useState(false);
  const [busy,      setBusy]      = useState(false);

  // ── Load saved assets + scenario on mount ────────────────────────────────
  const actions = useMemo<Action[]>(() => {
    const seen = new Set<string>();
    return assetIds
      .map(id => assetActions[id])
      .filter(Boolean)
      .filter(a => { if (seen.has(a.key)) return false; seen.add(a.key); return true; });
  }, [assetIds]);

  useEffect(() => {
    const sc  = localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027";
    let ids = (() => { try { return JSON.parse(localStorage.getItem("warbreak_asset_ids") || "[]"); } catch { return []; } })();
    if (!Array.isArray(ids) || !ids.length) {
      try {
        const savedAssets = JSON.parse(localStorage.getItem("warbreak_assets") || "[]");
        ids = Array.isArray(savedAssets) ? savedAssets.map((asset: any) => asset?.id).filter(Boolean) : [];
      } catch {
        ids = [];
      }
    }

    if (!ids.length) {
      router.replace("/assets");
      return;
    }

    const mt  = Number(localStorage.getItem("warbreak_max_turns") || ids.length || 5);
    setScenario(sc);
    setAssetIds(ids);
    setMaxTurns(Math.max(1, mt));
    setSelected(assetActions[ids[0]]?.key || "");
  }, [router]);

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
      L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", { subdomains:"abcd", maxZoom:19 }).addTo(m);
      blueLayer.current = L.layerGroup().addTo(m);
      redLayer.current = L.layerGroup().addTo(m);
      fxLayer.current = L.layerGroup().addTo(m);
      setMapReady(true);
    }

    initMap();
    return () => { cancelled = true; };
  }, [scenario]);

  useEffect(() => {
    if (!mapReady || !leaflet.current || !leafletLib.current) return;
    const L = leafletLib.current;
    const cfg = mapCfg[scenario] || mapCfg["Taiwan Strait 2027"];
    const map = leaflet.current;

    blueLayer.current?.clearLayers();
    redLayer.current?.clearLayers();

    const icon = (cls: string, emoji: string, index?: number) => L.divIcon({
      html:`<div class="marker ${cls}">${emoji}${index ? `<span class="marker-index">${index}</span>` : ""}</div>`,
      className:"",
      iconSize:[40,40],
      iconAnchor:[20,20],
    });

    cfg.red.forEach((p: any) => {
      L.marker([p[0],p[1]], { icon:icon("red", p[2]), zIndexOffset:200 }).addTo(redLayer.current);
    });

    actions.forEach((action, index) => {
      const point = assetPoint(scenario, action, index);
      const marker = L.marker(point, {
        icon:icon(`blue asset kind-${action.kind} ${selected === action.key ? "active" : ""}`, action.icon, index + 1),
        zIndexOffset: selected === action.key ? 700 : 500,
      }).addTo(blueLayer.current);
      marker.bindTooltip(`${index + 1}. ${action.title}`, { direction:"top", offset:[0,-18], opacity:0.92 });
      marker.on("click", () => setSelected(action.key));
    });

    if (actions.length) {
      const points = actions.map((action, index) => assetPoint(scenario, action, index));
      const redPoints = (cfg.red || []).map((p: any) => [p[0], p[1]]);
      try {
        map.fitBounds(L.latLngBounds([...points, ...redPoints]).pad(0.22), { animate:false, maxZoom:cfg.zoom + 1 });
      } catch {}
    }
  }, [mapReady, scenario, actions, selected]);

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
  const animate = (action: Action) => {
    const cfg = mapCfg[scenario] || mapCfg["Taiwan Strait 2027"];
    const L = leafletLib.current;
    const map = leaflet.current;
    if (!map || !L) return;

    const index = Math.max(0, actions.findIndex(item => item.key === action.key));
    const from = assetPoint(scenario, action, index);
    const to = redTargetPoint(scenario, action);
    const layers: any[] = [];
    const add = (layer: any) => {
      layer.addTo(fxLayer.current || map);
      layers.push(layer);
      return layer;
    };

    try {
      map.flyToBounds(L.latLngBounds([from, to]).pad(0.55), { duration:0.55, maxZoom:cfg.zoom + 1 });
    } catch {}

    if (action.kind === "strike") {
      sound("boom");
      add(L.polyline([from, to], { color:"#e5d28c", weight:4, opacity:0.95, className:"arc strike-arc" }));
      add(L.circleMarker(to, { radius:15, color:"#fff2ac", fillColor:"#d55348", fillOpacity:0.82, weight:3, className:"map-impact strike-impact" }));
    } else if (action.kind === "sub") {
      sound("sonar");
      add(L.circle(from, { radius:effectRadius(scenario, 170000), color:"#48a8d8", fill:false, weight:3, className:"map-ring sonar-ring" }));
      add(L.polyline([from, to], { color:"#48a8d8", weight:3, opacity:0.82, className:"arc patrol-arc" }));
      add(L.circleMarker(to, { radius:9, color:"#48a8d8", fillColor:"#176b8d", fillOpacity:0.7, weight:2, className:"map-impact sonar-contact" }));
    } else if (action.kind === "cyber") {
      sound("cyber");
      add(L.polyline([from, to], { color:"#a855f7", weight:3, opacity:0.9, className:"arc cyber-arc" }));
      add(L.circleMarker(to, { radius:18, color:"#c084fc", fillColor:"#6d28d9", fillOpacity:0.42, weight:3, className:"map-impact cyber-node" }));
    } else if (action.kind === "defense") {
      sound("sonar");
      add(L.circle(from, { radius:effectRadius(scenario, 140000), color:"#ffaa00", fillColor:"#ffaa00", fillOpacity:0.06, weight:3, className:"map-ring defense-ring" }));
      add(L.polyline([to, from], { color:"#ffaa00", weight:3, opacity:0.9, className:"arc intercept-arc" }));
    } else if (action.kind === "sensor") {
      sound("sonar");
      add(L.circle(from, { radius:effectRadius(scenario, 230000), color:"#00e87a", fill:false, weight:3, className:"map-ring sensor-ring" }));
      add(L.polyline([from, to], { color:"#00e87a", weight:2, opacity:0.7, className:"arc sensor-arc" }));
      add(L.circleMarker(to, { radius:10, color:"#00e87a", fillColor:"#00e87a", fillOpacity:0.28, weight:2, className:"map-impact sensor-contact" }));
    } else if (action.kind === "ground") {
      sound("move");
      add(L.polyline([from, to], { color:"#ff8800", weight:4, opacity:0.86, className:"arc ground-arc" }));
      add(L.circle(from, { radius:effectRadius(scenario, 90000), color:"#ff8800", fillColor:"#ff8800", fillOpacity:0.08, weight:3, className:"map-ring ground-zone" }));
    } else {
      sound("sonar");
      add(L.circle(from, { radius:effectRadius(scenario, 160000), color:"#e0d494", fill:false, weight:3, className:"map-ring sensor-ring" }));
    }

    setTimeout(() => {
      layers.forEach(layer => {
        try { layer.remove(); } catch {}
      });
    }, 1900);
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
    animate(act);
    setBusy(true);

    const redAsset = act.kind==="strike"          ? "mobile air defense + information response"
                   : act.kind==="sub"             ? "diesel-electric submarine screen"
                   : act.kind==="cyber"           ? "cyber / electronic disruption cell"
                   : act.kind==="defense"         ? "missile pressure and decoys"
                                                  : "media pressure + observation network";
    setRedUsed(r => Array.from(new Set([...r, redAsset])));

    let ghostReply = "";
    try {
      let gid = localStorage.getItem("warbreak_game_id") || "";
      if (!gid || gid === "local-demo") {
        gid = await createPlayableGame(act);
      }

      let res;
      try {
        res = await playTurn(gid, act.title);
      } catch (turnError) {
        const message = turnError instanceof Error ? turnError.message : "";
        if (!message.toLowerCase().includes("game not found")) throw turnError;
        gid = await createPlayableGame(act);
        res = await playTurn(gid, act.title);
      }

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
      localStorage.setItem("warbreak_game", JSON.stringify(res));
    } catch {
      const patch = localMetricPatch(act.kind);
      setMetrics((m: any) => {
        const next = { ...m };
        Object.entries(patch).forEach(([key, delta]) => {
          next[key] = Math.max(0, Math.min(100, Math.round((next[key] ?? 50) + delta)));
        });
        return next;
      });
      ghostReply = localGhostCouncil(act, redAsset, scenario);
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

  const buildFallbackPlan = (act?: Action) => {
    const forceNames = actions.map(a => a.title).join(", ") || "the selected force package";
    return localStorage.getItem("warbreak_plan")
      || `${fallbackPlans[scenario] || fallbackPlans["Taiwan Strait 2027"]} Current move: ${act?.title || "initial force action"}. Selected forces: ${forceNames}.`;
  };

  const createPlayableGame = async (act?: Action) => {
    const game = await createGame(buildFallbackPlan(act));
    const gameId = game.id || game.game_id || game.session_id;
    if (!gameId) throw new Error("Backend did not return a game id.");
    localStorage.setItem("warbreak_game_id", gameId);
    localStorage.setItem("warbreak_game", JSON.stringify(game));
    return gameId;
  };

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
