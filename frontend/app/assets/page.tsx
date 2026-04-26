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
  const remaining = Math.max(0, budget - spent);
  const spentPct = budget > 0 ? Math.min(100, Math.round((spent / budget) * 100)) : 0;
  const budgetFloor = Math.max(12, spent);
  const opponentAssets = Array.isArray(brief?.predicted_assets) ? brief.predicted_assets : [];
  const warnings = Array.isArray(brief?.key_warnings) ? brief.key_warnings : [];

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
        localStorage.setItem("warbreak_opponent_assets", JSON.stringify(res));
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
      <div className="topbar assets-topbar">
        <div className="brand">
          <button className="btn ghost" onClick={() => router.push("/")}>← BACK</button>
          WARBREAK
          <span className="badge">{scenario}</span>
        </div>
        <button className="btn primary" onClick={enter}>ENTER WARGAME →</button>
      </div>

      {/* Budget row */}
      <div className="budget-row">
        <div>
          <div className="kicker" style={{ fontSize:10, marginBottom:4 }}>CHOOSE YOUR FORCE PACKAGE</div>
          <p className="small" style={{ margin:0, opacity:0.6, fontSize:11 }}>
            Higher budget = more assets. Turns equal your selected assets.
          </p>
        </div>
        <div className="budget-console" aria-label="Force package budget">
          <div className="budget-stats">
            <span className="budget-stat">
              <small>BUDGET</small>
              <b>{budget}</b>
            </span>
            <span className="budget-stat spent">
              <small>SPENT</small>
              <b>{spent}</b>
            </span>
            <span className={`budget-stat ${remaining <= 2 ? "tight" : "left"}`}>
              <small>LEFT</small>
              <b>{remaining}</b>
            </span>
            <span className="budget-stat turns">
              <small>TURNS</small>
              <b>{picked.length}</b>
            </span>
          </div>
          <div className="budget-meter" aria-hidden="true">
            <span style={{ width:`${spentPct}%` }} />
          </div>
        </div>
        <label className="budget-slider-wrap">
          <span>ADJUST BUDGET</span>
          <input
            type="range"
            min={budgetFloor}
            max="60"
            value={budget}
            aria-label="Adjust mission budget"
            onChange={e => setBudget(Math.max(Number(e.target.value), budgetFloor))}
          />
        </label>
      </div>

      {!brief ? (
        <div className="assets-grid">
          {/* Asset grid */}
          <section className="asset-list">
            {assets.map(a => {
              const isSel  = selected.includes(a.id);
              const tColor = TYPE_COLOR[a.type] || "#888";
              const wouldExceed = !isSel && a.cost > remaining;
              const overBy = Math.max(0, a.cost - remaining);
              return (
                <button
                  key={a.id}
                  onClick={() => toggle(a.id)}
                  disabled={wouldExceed}
                  aria-pressed={isSel}
                  aria-label={`${a.name}. Cost ${a.cost}. ${isSel ? "Selected." : wouldExceed ? `Needs ${overBy} more budget.` : "Available."}`}
                  className={`asset-pick-card ${isSel ? "selected" : ""} ${wouldExceed ? "unavailable" : ""}`}
                  style={{
                    border:`1.5px solid ${isSel ? tColor+"80" : "rgba(255,255,255,0.12)"}`,
                    background: isSel ? `${tColor}18` : "rgba(255,255,255,0.05)",
                  }}
                >
                  <span className={`cost-pill ${isSel ? "selected" : ""}`} style={{ borderColor:`${tColor}42`, color:isSel?tColor:"rgba(241,234,210,0.74)" }}>
                    <small>COST</small>
                    <b>{a.cost}</b>
                  </span>
                  <span style={{ fontSize:20, lineHeight:1, marginBottom:2 }}>{a.icon}</span>
                  <span style={{ fontSize:12, fontWeight:700, lineHeight:1.25, color:isSel?tColor:"rgba(255,255,255,0.85)" }}>{a.name}</span>
                  <span style={{ fontSize:11, opacity:0.55, lineHeight:1.4 }}>{a.desc}</span>
                  <div className="asset-card-foot">
                    <span style={{ display:"inline-block", fontSize:9, padding:"2px 7px", borderRadius:3, background:`${tColor}20`, color:tColor, border:`1px solid ${tColor}30` }}>
                      {a.type.toUpperCase()}
                    </span>
                    {wouldExceed && <span className="asset-unavailable">NEED +{overBy}</span>}
                  </div>
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
                <span key={a.id} className="chip force-chip" style={{ fontSize:11 }}>
                  <span>{a.icon} {a.name}</span>
                  <b>{a.cost}</b>
                </span>
              ))}
              {picked.length === 0 && <span style={{ fontSize:11, opacity:0.4 }}>No assets selected</span>}
            </div>
            <div className="force-summary">
              <span><b>{spent}</b> / {budget} used</span>
              <span><b>{remaining}</b> left</span>
              <span><b>{picked.length}</b> turns</span>
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

          {/* Placeholder when nothing fetched yet */}
          {!loading && !brief && (
            <div className="side-panel" style={{ marginTop:12, opacity:0.4, textAlign:"center", padding:"24px 16px" }}>
              <div style={{ fontSize:24, marginBottom:8 }}>🔍</div>
              <div style={{ fontSize:12 }}>Run OSINT analysis to see predicted opponent assets</div>
            </div>
          )}

          </aside>
        </div>
      ) : (
        <section className="matchup-view">
          <div className="matchup-hero">
            <div>
              <div className="kicker" style={{ fontSize:10, marginBottom:8 }}>
                {brief.classification || "PUBLIC-SOURCE ESTIMATE"}
              </div>
              <h1>Force Package Matchup</h1>
              {brief.summary && <p>{brief.summary}</p>}
            </div>
            <div className="matchup-meta">
              {brief.threat_level && (
                <div className="matchup-stat red">
                  <span>Threat Level</span>
                  <b>{brief.threat_level}</b>
                </div>
              )}
              {brief.confidence && (
                <div className="matchup-stat amber">
                  <span>Confidence</span>
                  <b>{brief.confidence}%</b>
                </div>
              )}
              <button className="btn ghost" onClick={() => setBrief(null)}>REVISE PACKAGE</button>
              <button className="btn primary" onClick={identify} disabled={loading}>
                {loading ? "REFRESHING..." : "REFRESH ESTIMATE"}
              </button>
            </div>
          </div>

          <div className="matchup-columns">
            <div className="matchup-column blue">
              <div className="matchup-title">
                <span>BLUE SELECTED PACKAGE</span>
                <b>{picked.length} assets · {spent} points</b>
              </div>
              <div className={`matchup-card-grid blue-package-grid ${picked.length % 2 === 1 ? "odd" : ""}`}>
                {picked.map(a => {
                  const tColor = TYPE_COLOR[a.type] || "#888";
                  return (
                    <article className="force-card blue-card" key={a.id} style={{ borderColor:`${tColor}75` }}>
                      <div className="force-card-top">
                        <span className="force-icon">{a.icon}</span>
                        <span className="force-cost">{a.cost}</span>
                      </div>
                      <h3 style={{ color:tColor }}>{a.name}</h3>
                      <p>{a.desc}</p>
                      <span className="force-tag" style={{ color:tColor, borderColor:`${tColor}45`, background:`${tColor}18` }}>
                        {a.type.toUpperCase()}
                      </span>
                    </article>
                  );
                })}
              </div>
            </div>

            <div className="matchup-column red">
              <div className="matchup-title">
                <span>ESTIMATED OPPONENT PACKAGE</span>
                <b>{opponentAssets.length} likely assets</b>
              </div>
              <div className="matchup-card-grid">
                {opponentAssets.map((x: any, i: number) => (
                  <article className="force-card red-card" key={`${x.name || "asset"}-${i}`}>
                    <div className="force-card-top">
                      <span className="force-icon">◆</span>
                      <span className="force-cost">{x.confidence || "—"}%</span>
                    </div>
                    <h3>{x.name || "Unidentified asset"}</h3>
                    <p>{x.capability || x.quantity || "Likely asset based on the selected force package."}</p>
                    <div className="force-card-detail">
                      <span>{x.category || "asset"}</span>
                      <span>Threat {x.threat_to_blue || "MEDIUM"}</span>
                    </div>
                    {x.counter && <p className="counter-text">Counter: {x.counter}</p>}
                  </article>
                ))}
              </div>
            </div>
          </div>

          {(warnings.length > 0 || brief.historical_precedent) && (
            <div className="matchup-notes">
              {warnings.length > 0 && (
                <div>
                  <h3>Key Warnings</h3>
                  {warnings.map((w: string, i: number) => <p key={i}>{w}</p>)}
                </div>
              )}
              {brief.historical_precedent && (
                <div>
                  <h3>Historical Precedent</h3>
                  <p>{brief.historical_precedent}</p>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
