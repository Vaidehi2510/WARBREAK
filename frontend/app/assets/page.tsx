"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { identifyOpponentAssets } from "../../lib/api";

const assets = [
  { id:"carrier",  name:"Carrier Strike Group",      type:"Naval",     cost:10, icon:"⚓",  desc:"Air wing, escorts, long-range presence." },
  { id:"sub",      name:"Virginia-class Submarine",  type:"Naval",     cost:6,  icon:"◆",  desc:"Covert sea denial and surveillance." },
  { id:"f35",      name:"F-35C Squadron",            type:"Air",       cost:7,  icon:"✈️", desc:"Stealth strike and air superiority." },
  { id:"patriot",  name:"Patriot PAC-3 Battery",     type:"Defense",   cost:4,  icon:"▲",  desc:"Missile defense for forward bases." },
  { id:"growler",  name:"EA-18G Growler Squadron",   type:"Air",       cost:4,  icon:"📡", desc:"Electronic warfare and air defense suppression." },
  { id:"p8",       name:"P-8 Poseidon Patrol",       type:"Air",       cost:3,  icon:"🔎", desc:"Anti-submarine search and tracking." },
  { id:"aegis",    name:"Aegis Destroyer",           type:"Naval",     cost:5,  icon:"⚔️", desc:"Air defense, escort, missile intercept." },
  { id:"stryker",  name:"Stryker Brigade",           type:"Ground",    cost:5,  icon:"▰",  desc:"Rapid ground presence and urban security." },
  { id:"cyber",    name:"Cyber Command Cell",        type:"Cyber",     cost:3,  icon:"⚡", desc:"Network defense and disruption." },
  { id:"mq9",      name:"MQ-9 Reaper Flight",        type:"Air",       cost:2,  icon:"◈",  desc:"Persistent surveillance and precision strike." },
  { id:"sof",      name:"Special Operations Team",   type:"Ground",    cost:4,  icon:"✦",  desc:"Reconnaissance, hostage rescue, direct action." },
  { id:"sealift",  name:"Sealift Logistics Package", type:"Logistics", cost:4,  icon:"▣",  desc:"Fuel, spares, sustainment, evacuation lift." },
];

const TYPE_COLOR: Record<string, string> = {
  Naval:"#4d9fff", Air:"#00e87a", Defense:"#ffaa00",
  Ground:"#ff8800", Cyber:"#a855f7", Logistics:"#888",
};

export default function AssetsPage() {
  const router   = useRouter();
  const scenario = typeof window !== "undefined"
    ? localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027"
    : "Taiwan Strait 2027";

  const [budget,   setBudget]   = useState(28);
  const [selected, setSelected] = useState<string[]>(["carrier", "sub", "f35"]);
  const [brief,    setBrief]    = useState<any>(null);   // ← null until fetched
  const [loading,  setLoading]  = useState(false);
  const [intelErr, setIntelErr] = useState("");

  const picked = useMemo(() => assets.filter(a => selected.includes(a.id)), [selected]);
  const spent  = picked.reduce((s, a) => s + a.cost, 0);

  const toggle = (id: string) => {
    const next      = selected.includes(id) ? selected.filter(x => x !== id) : [...selected, id];
    const nextSpent = assets.filter(a => next.includes(a.id)).reduce((s, a) => s + a.cost, 0);
    if (nextSpent <= budget) setSelected(next);
  };

  const identify = async () => {
    setLoading(true);
    setIntelErr("");
    setBrief(null);
    try {
      const res = await identifyOpponentAssets(scenario, picked);
      if (res) {
        setBrief(res);
      } else {
        setIntelErr("No response from intel API. Check backend is running.");
      }
    } catch (e: unknown) {
      setIntelErr(e instanceof Error ? e.message : "Intel request failed.");
    } finally {
      setLoading(false);
    }
  };

  const enter = () => {
    localStorage.setItem("warbreak_assets",          JSON.stringify(picked));
    localStorage.setItem("warbreak_asset_ids",       JSON.stringify(selected));
    localStorage.setItem("warbreak_max_turns",       String(picked.length));
    localStorage.setItem("warbreak_opponent_assets", JSON.stringify(brief || {}));
    router.push("/game");
  };

  return (
    <main className="assets-page">
      {/* Top bar */}
      <div className="topbar" style={{ margin:"-24px -32px 20px" }}>
        <div className="brand">
          <button className="btn ghost" onClick={() => router.push("/")}>← BACK</button>
          WARBREAK
          <span className="badge">{scenario}</span>
        </div>
        <button className="btn primary" onClick={enter}>ENTER WARGAME →</button>
      </div>

      {/* Budget row */}
      <div className="budget-row" style={{ marginBottom:16 }}>
        <div>
          <div className="kicker" style={{ fontSize:10, marginBottom:4 }}>CHOOSE YOUR FORCE PACKAGE</div>
          <p className="small" style={{ margin:0, opacity:0.6, fontSize:11 }}>
            Higher budget = more assets. Turns equal your selected assets.
          </p>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <span className="badge" style={{ fontSize:11 }}>BUDGET {budget} · SPENT {spent}</span>
          <span className="badge" style={{ fontSize:11, background:"rgba(0,232,122,0.15)", border:"1px solid rgba(0,232,122,0.3)" }}>
            {picked.length} TURNS
          </span>
        </div>
        <input type="range" min="12" max="60" value={budget} onChange={e => setBudget(Number(e.target.value))} />
      </div>

      <div className="assets-grid">
        {/* Asset grid */}
        <section className="asset-list">
          {assets.map(a => {
            const isSel  = selected.includes(a.id);
            const tColor = TYPE_COLOR[a.type] || "#888";
            return (
              <button
                key={a.id}
                onClick={() => toggle(a.id)}
                style={{
                  position:"relative", padding:"12px 14px", textAlign:"left",
                  borderRadius:10,
                  border:`1.5px solid ${isSel ? tColor+"80" : "rgba(255,255,255,0.12)"}`,
                  background: isSel ? `${tColor}18` : "rgba(255,255,255,0.05)",
                  cursor:"pointer", transition:"all 0.18s ease", color:"inherit",
                  display:"flex", flexDirection:"column", gap:4,
                }}
              >
                <span style={{ position:"absolute", top:8, right:10, fontSize:10, fontWeight:700, color:isSel?tColor:"rgba(255,255,255,0.4)" }}>{a.cost}</span>
                <span style={{ fontSize:20, lineHeight:1, marginBottom:2 }}>{a.icon}</span>
                <span style={{ fontSize:12, fontWeight:700, lineHeight:1.25, color:isSel?tColor:"rgba(255,255,255,0.85)" }}>{a.name}</span>
                <span style={{ fontSize:11, opacity:0.55, lineHeight:1.4 }}>{a.desc}</span>
                <span style={{ marginTop:4, display:"inline-block", fontSize:9, padding:"2px 7px", borderRadius:3, background:`${tColor}20`, color:tColor, border:`1px solid ${tColor}30` }}>
                  {a.type.toUpperCase()}
                </span>
              </button>
            );
          })}
        </section>

        {/* Sidebar */}
        <aside>
          {/* Your forces */}
          <div className="side-panel">
            <h2 style={{ marginTop:0, fontSize:15, marginBottom:10 }}>Your forces</h2>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {picked.map(a => (
                <span key={a.id} className="chip" style={{ fontSize:11 }}>{a.icon} {a.name}</span>
              ))}
              {picked.length === 0 && <span style={{ fontSize:11, opacity:0.4 }}>No assets selected</span>}
            </div>
            <div style={{ marginTop:12, padding:"8px 10px", background:"rgba(0,232,122,0.08)", border:"1px solid rgba(0,232,122,0.2)", borderRadius:7 }}>
              <span style={{ fontSize:11, color:"#00e87a" }}>
                {picked.length} assets selected = {picked.length} turns in the wargame
              </span>
            </div>
          </div>

          {/* Opponent identification */}
          <div className="side-panel" style={{ marginTop:12 }}>
            <h2 style={{ marginTop:0, fontSize:15, marginBottom:6 }}>Opponent Asset Identification</h2>
            <p className="small" style={{ fontSize:11, opacity:0.6, marginBottom:10 }}>
              AI-powered OSINT analysis — predicts what the opposing side will use based on your force package and scenario.
            </p>
            <button
              className="btn primary"
              onClick={identify}
              disabled={loading}
              style={{ fontSize:11, padding:"9px 14px", width:"100%", opacity:loading?0.6:1 }}
            >
              {loading ? "ANALYZING OSINT…" : "IDENTIFY OPPONENT ASSETS →"}
            </button>
            {intelErr && (
              <div style={{ marginTop:8, fontSize:11, color:"#ff6644", padding:"6px 10px", background:"rgba(255,60,60,0.08)", border:"1px solid rgba(255,60,60,0.2)", borderRadius:6 }}>
                ⚠ {intelErr}
              </div>
            )}
          </div>

          {/* Opponent package — only shows after fetch */}
          {loading && (
            <div className="side-panel" style={{ marginTop:12 }}>
              <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
                {["Scanning Jane's Defence Weekly…","Cross-referencing IISS Military Balance…","Querying Correlates of War DB…","Analyzing OSINT sources…"].map((m, i) => (
                  <div key={i} style={{ fontSize:11, opacity:0.5, animation:`pulse 1.5s ease ${i*0.25}s infinite` }}>{m}</div>
                ))}
              </div>
            </div>
          )}

          {!loading && brief && (
            <div className="side-panel" style={{ marginTop:12 }}>
              {/* Classification banner */}
              {brief.classification && (
                <div style={{ marginBottom:10, padding:"5px 10px", background:"rgba(255,60,60,0.1)", border:"1px solid rgba(255,60,60,0.25)", borderRadius:5, textAlign:"center" }}>
                  <span style={{ fontSize:10, color:"#ff8888", letterSpacing:"0.1em" }}>{brief.classification}</span>
                </div>
              )}

              {/* Threat + confidence */}
              {(brief.threat_level || brief.confidence) && (
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:12 }}>
                  {brief.threat_level && (
                    <div style={{ padding:"8px 10px", background:"rgba(255,60,60,0.08)", border:"1px solid rgba(255,60,60,0.2)", borderRadius:7 }}>
                      <div style={{ fontSize:9, opacity:0.5, marginBottom:3 }}>THREAT LEVEL</div>
                      <div style={{ fontSize:16, fontWeight:700, color:"#ff8888" }}>{brief.threat_level}</div>
                    </div>
                  )}
                  {brief.confidence && (
                    <div style={{ padding:"8px 10px", background:"rgba(255,170,0,0.08)", border:"1px solid rgba(255,170,0,0.2)", borderRadius:7 }}>
                      <div style={{ fontSize:9, opacity:0.5, marginBottom:3 }}>CONFIDENCE</div>
                      <div style={{ fontSize:16, fontWeight:700, color:"#ffaa00" }}>{brief.confidence}%</div>
                    </div>
                  )}
                </div>
              )}

              <h2 style={{ marginTop:0, fontSize:14, marginBottom:8 }}>Likely opponent package</h2>

              {brief.summary && (
                <p style={{ fontSize:12, opacity:0.75, lineHeight:1.6, marginBottom:12 }}>{brief.summary}</p>
              )}

              {(brief.predicted_assets || []).map((x: any, i: number) => (
                <div key={i} style={{ marginBottom:8, padding:"9px 11px", background:"rgba(255,60,60,0.06)", border:"1px solid rgba(255,60,60,0.15)", borderRadius:7 }}>
                  <div style={{ fontSize:12, fontWeight:700, marginBottom:3, color:"#ffaaaa" }}>{x.name}</div>
                  <div style={{ fontSize:10, opacity:0.6, marginBottom:3 }}>
                    Confidence {x.confidence || "—"}% · Threat {x.threat_to_blue || "Medium"}
                  </div>
                  <div style={{ fontSize:11, opacity:0.7, marginBottom:3 }}>{x.capability}</div>
                  <div style={{ fontSize:10, opacity:0.5 }}>Counter: {x.counter}</div>
                </div>
              ))}

              {(brief.key_warnings || []).length > 0 && (
                <div style={{ marginTop:10, padding:"8px 10px", background:"rgba(255,170,0,0.06)", border:"1px solid rgba(255,170,0,0.2)", borderRadius:7 }}>
                  <div style={{ fontSize:9, fontWeight:700, color:"#ffaa00", marginBottom:6, letterSpacing:"0.08em" }}>KEY WARNINGS</div>
                  {(brief.key_warnings || []).map((w: string, i: number) => (
                    <p key={i} style={{ fontSize:11, opacity:0.7, margin:"0 0 4px", lineHeight:1.5 }}>• {w}</p>
                  ))}
                </div>
              )}

              {(brief.historical_precedent) && (
                <div style={{ marginTop:10, padding:"8px 10px", background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.08)", borderRadius:7 }}>
                  <div style={{ fontSize:9, opacity:0.4, marginBottom:4, letterSpacing:"0.08em" }}>HISTORICAL PRECEDENT</div>
                  <p style={{ fontSize:11, opacity:0.6, margin:0, lineHeight:1.6, fontStyle:"italic" }}>{brief.historical_precedent}</p>
                </div>
              )}
            </div>
          )}

          {/* Placeholder when nothing fetched yet */}
          {!loading && !brief && (
            <div className="side-panel" style={{ marginTop:12, opacity:0.4, textAlign:"center", padding:"24px 16px" }}>
              <div style={{ fontSize:24, marginBottom:8 }}>🔍</div>
              <div style={{ fontSize:12 }}>Run OSINT analysis to see predicted opponent assets</div>
            </div>
          )}

        </aside>
      </div>
    </main>
  );
}