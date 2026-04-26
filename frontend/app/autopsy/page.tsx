"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAutopsy } from "../../lib/api";

const OPTIMAL: Record<string, { moves: string[]; outcome: string }> = {
  "Taiwan Strait 2027": {
    moves: [
      "T1: Pause for ISR — verify PLA positions before committing forces",
      "T2: Economic sanctions — build coalition before kinetic action",
      "T3: Deploy submarines covertly — degrade PLA sea control without escalation",
    ],
    outcome: "Allied confidence held. International legitimacy preserved. PLA deterred without direct engagement.",
  },
  "NATO Eastern Flank": {
    moves: [
      "T1: Coalition messaging — lock in Article 5 consensus first",
      "T2: Pause for ISR — confirm Russian intent and force disposition",
      "T3: Economic sanctions — signal resolve without kinetic trigger",
    ],
    outcome: "NATO unity maintained. Russian escalation deterred. Suwalki Gap secured without direct contact.",
  },
  "Embassy Evacuation": {
    moves: [
      "T1: Pause for ISR — locate all civilians before insertion",
      "T2: Coalition messaging — secure host nation neutrality formally",
      "T3: SOF raid — quiet extraction of high-value personnel first",
    ],
    outcome: "All personnel extracted. No civilian casualties. Airspace maintained.",
  },
  "Cyber Infrastructure": {
    moves: [
      "T1: Pause for ISR — attribute attack before public response",
      "T2: Coalition messaging — coordinate with allied CERTs",
      "T3: Cyber operation — counter without kinetic escalation",
    ],
    outcome: "Attack attributed. Grid restored within 48 hours. Follow-on action deterred.",
  },
};

const METRICS = [
  { key:"intl_opinion",      label:"Int'l Opinion",  color:"#4d9fff" },
  { key:"us_domestic",       label:"US Support",     color:"#4d9fff" },
  { key:"red_domestic",      label:"Red Support",    color:"#ff3c3c" },
  { key:"allied_confidence", label:"Allied Conf.",   color:"#00e87a" },
  { key:"blue_strength",     label:"Blue Force",     color:"#4d9fff" },
  { key:"red_strength",      label:"Red Force",      color:"#ff3c3c" },
];

const TABS = [
  { label:"Assumption Rank", summary:"Priority order, validation moves, and cascade exposure" },
  { label:"Decision Log", summary:"Blue moves and opponent responses by turn" },
  { label:"Ghost Council", summary:"Adversary pressure, intent, and psychological pattern" },
  { label:"Info Battlefield", summary:"Political, allied, domestic, and force metrics" },
  { label:"Failure Chain", summary:"Root cause and cascade sequence" },
  { label:"What If", summary:"Your path compared with a resilient timeline" },
  { label:"Recommendations", summary:"Changes to make the next plan harder to break" },
];

const FALLBACK_ASSUMPTIONS: Record<string, any[]> = {
  "Taiwan Strait 2027": [
    { text:"Okinawa and regional basing remain politically available when combat risk rises.", category:"alliance_access", fragility:86, criticality:0.9, cascade_effect:"Air sortie tempo and resupply options compress." },
    { text:"PLA mobile missile batteries can be found and struck before they relocate.", category:"intelligence", fragility:84, criticality:0.88, cascade_effect:"Carrier and logistics forces must operate farther from the fight." },
    { text:"Supply lines through the Luzon Strait stay open long enough to sustain the package.", category:"logistics", fragility:80, criticality:0.86, cascade_effect:"Forward forces lose endurance before tactical gains matter." },
    { text:"International support survives precision strikes and escalation pressure.", category:"information", fragility:73, criticality:0.78, cascade_effect:"Allied confidence and legitimacy diverge." },
    { text:"Carrier survivability is not the limiting condition for the operation.", category:"force_protection", fragility:70, criticality:0.82, cascade_effect:"Blue must trade operational reach for protection." },
  ],
  "NATO Eastern Flank": [
    { text:"Article 5 consensus holds under gray-zone ambiguity.", category:"alliance_cohesion", fragility:88, criticality:0.92, cascade_effect:"Reinforcement authority slows while the opponent controls tempo." },
    { text:"The Suwalki logistics corridor remains usable under pressure.", category:"logistics", fragility:83, criticality:0.88, cascade_effect:"Forward units consume readiness faster than they can be reinforced." },
    { text:"Host nation permissions arrive before the operational window closes.", category:"permission", fragility:78, criticality:0.8, cascade_effect:"Air and missile defense coverage arrives late." },
    { text:"Russian escalation stays below the threshold that fractures allied response.", category:"escalation", fragility:75, criticality:0.86, cascade_effect:"Political risk begins driving military timing." },
    { text:"Forward air defense can cover the right assets at the right time.", category:"timing", fragility:69, criticality:0.76, cascade_effect:"Protected nodes become single points of failure." },
  ],
  "Embassy Evacuation": [
    { text:"Civilians can reach the evacuation control point before routes close.", category:"civilian_movement", fragility:90, criticality:0.94, cascade_effect:"The mission shifts from extraction to crowd control under threat." },
    { text:"The air corridor remains usable long enough for lift cycles.", category:"access", fragility:85, criticality:0.9, cascade_effect:"Offshore lift becomes irrelevant if aircraft cannot cycle." },
    { text:"Roadblocks and militia patrols can be bypassed or cleared on schedule.", category:"ground_access", fragility:79, criticality:0.84, cascade_effect:"Security forces are fixed protecting routes instead of moving people." },
    { text:"Host nation remnants stay neutral or at least predictable.", category:"partner_alignment", fragility:74, criticality:0.76, cascade_effect:"Permissions and local information become unreliable." },
    { text:"Public messaging prevents civilians from moving to the wrong place.", category:"information", fragility:72, criticality:0.74, cascade_effect:"The evacuation plan fragments into multiple unmanaged crowds." },
  ],
  "Cyber Infrastructure": [
    { text:"Attribution can be established before public retaliation pressure peaks.", category:"intelligence", fragility:84, criticality:0.84, cascade_effect:"Decision-makers may act before they know what system actually failed." },
    { text:"Priority substations can be restored without triggering adjacent failures.", category:"infrastructure", fragility:82, criticality:0.9, cascade_effect:"Recovery work creates new outage paths." },
    { text:"Manual procedures and backup communications are ready when networks degrade.", category:"digital_resilience", fragility:80, criticality:0.86, cascade_effect:"Command coordination slows exactly when tempo matters." },
    { text:"The incident stays contained inside power systems rather than water and gas.", category:"cascade_risk", fragility:77, criticality:0.88, cascade_effect:"A cyber incident becomes a multi-sector public safety crisis." },
    { text:"Public confidence holds while restoration timelines remain uncertain.", category:"information", fragility:68, criticality:0.72, cascade_effect:"Political pressure compresses technical recovery choices." },
  ],
};

function readStoredJson(key: string, fallback: any) {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function validationMove(category: string) {
  const c = String(category || "").toLowerCase();
  if (c.includes("logistics") || c.includes("supply")) return "Set a sustainment go/no-go threshold and name the backup route.";
  if (c.includes("alliance") || c.includes("partner") || c.includes("permission") || c.includes("access")) return "Turn external support into an explicit decision gate with an owner.";
  if (c.includes("intelligence") || c.includes("information")) return "Define the signal that disproves the estimate before the next move.";
  if (c.includes("digital") || c.includes("cyber") || c.includes("communication")) return "Rehearse the manual fallback and backup comms path.";
  if (c.includes("civil")) return "Validate movement and messaging through a trusted local channel.";
  if (c.includes("timing")) return "Add a branch for delay, early closure, and missed handoff.";
  return "Assign an owner, a validation signal, and a branch plan.";
}

function fallbackAssumptions(scenario: string, plan: string) {
  const seeds = FALLBACK_ASSUMPTIONS[scenario] || FALLBACK_ASSUMPTIONS["Taiwan Strait 2027"];
  return seeds.map((item, index) => ({
    id: `D${index + 1}`,
    confidence: 0.55,
    status: "untested",
    basis: plan ? "Derived from the mission order and WARBREAK architecture fallback." : "Derived from the selected scenario.",
    doctrine_ref: "FOGLINE-derived",
    dependencies: index < seeds.length - 1 ? [`D${index + 2}`] : [],
    source: "derived",
    ...item,
  }));
}

function rankAssumptions(raw: any[], events: any[], scenario: string, plan: string) {
  const source = Array.isArray(raw) && raw.length ? raw : fallbackAssumptions(scenario, plan);
  const targeted = new Map<string, number>();
  const broken = new Map<string, number>();

  events.forEach((event: any) => {
    const target = event?.targeted_assumption_id;
    if (target) targeted.set(target, (targeted.get(target) || 0) + 1);
    if (Array.isArray(event?.broken_chain)) {
      event.broken_chain.forEach((id: string) => broken.set(id, (broken.get(id) || 0) + 1));
    }
  });

  return source.map((a: any, index: number) => {
    const id = String(a.id || `A${index + 1}`);
    const status = broken.has(id) ? "broken" : targeted.has(id) && a.status === "untested" ? "stressed" : (a.status || "untested");
    const dependencyCount = Array.isArray(a.dependencies) ? a.dependencies.length : 0;
    const statusBonus = status === "broken" ? 28 : status === "stressed" ? 18 : status === "validated" ? -8 : 8;
    const targetBonus = Math.min(18, (targeted.get(id) || a.targeted_count || 0) * 9);
    const brokenBonus = Math.min(12, (broken.get(id) || a.broken_chain_count || 0) * 6);
    const rankScore = typeof a.rank_score === "number"
      ? a.rank_score
      : Math.max(0, Math.min(100, Math.round((Number(a.fragility) || 60) * 0.58 + (Number(a.criticality) || 0.55) * 24 + statusBonus + Math.min(14, dependencyCount * 4) + targetBonus + brokenBonus)));

    return {
      ...a,
      id,
      status,
      rank_score: rankScore,
      targeted_count: targeted.get(id) || a.targeted_count || 0,
      broken_chain_count: broken.get(id) || a.broken_chain_count || 0,
      validation_move: a.validation_move || validationMove(a.category),
      rank_reason: a.rank_reason || `${status === "broken" ? "Broke during play" : status === "stressed" ? "Stressed by adversary pressure" : "Still unvalidated"}; fragility ${a.fragility ?? 60}; ${dependencyCount} linked assumption(s).`,
    };
  }).sort((a: any, b: any) => (b.rank_score || 0) - (a.rank_score || 0)).map((a: any, index: number) => ({ ...a, rank: index + 1 }));
}

function buildAutopsyReport(apiReport: any, scenario: string, history: any[], redUsed: string[], storedMet: any) {
  const storedGame = readStoredJson("warbreak_game", {});
  const plan = typeof window !== "undefined" ? localStorage.getItem("warbreak_plan") || "" : "";
  const incoming = apiReport && typeof apiReport === "object" ? apiReport : { report: typeof apiReport === "string" ? apiReport : "" };
  const events = Array.isArray(incoming.events) && incoming.events.length ? incoming.events : (Array.isArray(storedGame.events) ? storedGame.events : []);
  const assumptions = rankAssumptions(
    Array.isArray(incoming.assumptions) && incoming.assumptions.length ? incoming.assumptions : storedGame.assumptions,
    events,
    scenario,
    plan,
  );
  const brokenCount = assumptions.filter((a: any) => a.status === "broken").length;
  const stressedCount = assumptions.filter((a: any) => a.status === "stressed").length;
  const rootCauses = Array.isArray(incoming.root_causes) && incoming.root_causes.length
    ? incoming.root_causes
    : assumptions.slice(0, 3).map((a: any) => `${a.id}: ${a.text}`);

  return {
    status: incoming.status || storedGame.status || "completed",
    turns: incoming.turns ?? storedGame.turn ?? history.length ?? 0,
    final_metrics: incoming.final_metrics || storedGame.metrics || storedMet,
    assumptions,
    events,
    root_causes: rootCauses,
    assumptions_broken: incoming.assumptions_broken ?? brokenCount,
    assumptions_stressed: incoming.assumptions_stressed ?? stressedCount,
    report: incoming.report || "",
    lessons: incoming.lessons || [
      "Rank assumptions by collapse risk before execution.",
      "Treat the highest-ranked assumptions as turn-by-turn decision gates.",
      "Build branches for the first cascade, not only the final failure.",
    ],
    recommendation: incoming.recommendation || `Validate or branch ${assumptions[0]?.id || "the top assumption"} before the next force commitment.`,
    red_used: redUsed,
  };
}

function AssumptionRankPanel({ assumptions, report }: { assumptions: any[]; report: any }) {
  const [selectedId, setSelectedId] = useState<string | null>(assumptions[0]?.id || null);
  const selected = assumptions.find((a: any) => a.id === selectedId) || assumptions[0];
  const selectedScore = Number(selected?.rank_score ?? selected?.fragility ?? 0);
  const selectedColor = selectedScore>=82?"#ff3c3c":selectedScore>=65?"#ffaa00":"#00e87a";
  const selectedStatusColor = selected?.status==="broken"?"#ff3c3c":selected?.status==="stressed"?"#ffaa00":selected?.status==="validated"?"#00e87a":"rgba(255,255,255,0.45)";

  const scoreColor = (score: number) => score>=82 ? "#ff3c3c" : score>=65 ? "#ffaa00" : "#00e87a";
  const statusColor = (status: string) => status==="broken" ? "#ff3c3c" : status==="stressed" ? "#ffaa00" : status==="validated" ? "#00e87a" : "rgba(255,255,255,0.45)";

  return (
    <div className="assumption-rank-shell">
      <div className="assumption-rank-summary">
        {[
          ["TOP RISK", assumptions[0]?.id || "N/A", assumptions[0]?.rank_score ?? "--", "#ff6644"],
          ["BROKEN", report.assumptions_broken ?? 0, "assumptions", "#ff3c3c"],
          ["STRESSED", report.assumptions_stressed ?? 0, "under pressure", "#ffaa00"],
          ["SOURCE", assumptions[0]?.source === "derived" ? "DERIVED" : "FOGLINE", "rank model", "#4d9fff"],
        ].map(([label,value,sub,color]: any, i) => (
          <div key={i} className="assumption-rank-stat">
            <div style={{fontSize:9,opacity:0.38,letterSpacing:"0.08em",marginBottom:5}}>{label}</div>
            <div style={{fontSize:22,fontWeight:800,color,lineHeight:1}}>{value}</div>
            <div style={{fontSize:10,opacity:0.42,marginTop:5}}>{sub}</div>
          </div>
        ))}
      </div>

      <div className="assumption-rank-grid">
        <section className="assumption-risk-list">
          <div className="assumption-section-head">
            <span>RISK QUEUE</span>
            <b>{assumptions.length} assumptions</b>
          </div>
          {assumptions.map((a:any,i:number)=>{
            const score = Number(a.rank_score ?? a.fragility ?? 0);
            const c = scoreColor(score);
            const sColor = statusColor(a.status || "untested");
            const isSelected = selected?.id === a.id;
            const deps = Array.isArray(a.dependencies) ? a.dependencies.length : 0;
            const meta = [
              (a.status || "untested").toUpperCase(),
              deps ? `${deps} links` : "",
              (a.targeted_count || 0) > 0 ? `target x${a.targeted_count}` : "",
            ].filter(Boolean).join(" / ");

            return (
              <button
                key={a.id || i}
                className={`assumption-risk-row ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedId(a.id)}
                style={{borderColor:isSelected ? `${c}80` : "rgba(255,255,255,0.08)", background:isSelected ? `${c}12` : undefined}}
              >
                <span className="assumption-row-rank" style={{color:c}}>
                  {a.rank || i+1}
                  <small>{a.id}</small>
                </span>
                <span className="assumption-row-main">
                  <span className="assumption-row-title">{a.text}</span>
                  <span className="assumption-row-meta">
                    <i style={{background:`${sColor}18`,borderColor:`${sColor}35`,color:sColor}}>{meta}</i>
                    <em>{String(a.category || "operational").replaceAll("_"," ")}</em>
                  </span>
                  <span className="assumption-row-meter">
                    <span style={{width:`${Math.max(0,Math.min(100,score))}%`,background:c}} />
                  </span>
                </span>
                <span className="assumption-row-score" style={{color:c}}>{score}</span>
              </button>
            );
          })}
        </section>

        {selected && (
          <aside className="assumption-detail">
            <div className="assumption-detail-top">
              <div>
                <div className="assumption-section-head" style={{marginBottom:8}}>
                  <span>SELECTED ASSUMPTION</span>
                  <b>{selected.id}</b>
                </div>
                <h3>{selected.text}</h3>
              </div>
              <div className="assumption-collapse-score" style={{color:selectedColor}}>
                <span>Collapse</span>
                <b>{selectedScore}</b>
              </div>
            </div>

            <div className="assumption-pill-row">
              <span style={{background:`${selectedStatusColor}18`,borderColor:`${selectedStatusColor}35`,color:selectedStatusColor}}>
                {(selected.status || "untested").toUpperCase()}{selected.turn_broken ? ` T${selected.turn_broken}` : ""}
              </span>
              <span>{String(selected.category || "operational").replaceAll("_"," ").toUpperCase()}</span>
              {(selected.targeted_count || 0) > 0 && <span style={{color:"#ffaaa3",borderColor:"rgba(255,120,110,.22)",background:"rgba(255,60,60,.05)"}}>GHOST TARGET x{selected.targeted_count}</span>}
            </div>

            <div className="assumption-score-grid">
              {[
                ["Fragility", Number(selected.fragility ?? selectedScore), selectedColor],
                ["Consequence", Math.round(Number(selected.criticality ?? 0.55) * 100), Math.round(Number(selected.criticality ?? 0.55) * 100)>=80?"#ff3c3c":"#ffaa00"],
                ["Confidence", Math.round(Number(selected.confidence ?? 0.55) * 100), "#4d9fff"],
              ].map(([label,val,color]: any) => (
                <div key={label} className="assumption-score-card">
                  <div><span>{label}</span><b style={{color}}>{val}</b></div>
                  <i><em style={{width:`${Math.max(0,Math.min(100,Number(val)))}%`,background:color}} /></i>
                </div>
              ))}
            </div>

            <div className="assumption-detail-block">
              <span>WHY IT RANKED HERE</span>
              <p>{selected.rank_reason || selected.basis || "High planning dependency with limited validation."}</p>
            </div>

            <div className="assumption-detail-block green">
              <span>NEXT VALIDATION MOVE</span>
              <p>{selected.validation_move}</p>
            </div>

            {selected.cascade_effect && (
              <div className="assumption-detail-block red">
                <span>CASCADE IF WRONG</span>
                <p>{selected.cascade_effect}</p>
              </div>
            )}

            {Array.isArray(selected.dependencies) && selected.dependencies.length > 0 && (
              <div className="assumption-dependency-row">
                <span>LINKED ASSUMPTIONS</span>
                <div>{selected.dependencies.map((dep: string) => <b key={dep}>{dep}</b>)}</div>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

export default function AutopsyPage() {
  const router = useRouter();
  const [report,   setReport]  = useState<any>(null);
  const [loading,  setLoading] = useState(true);
  const [err,      setErr]     = useState("");
  const [tab,      setTab]     = useState(0);
  const [copied,   setCopied]  = useState(false);

  const scenario = typeof window !== "undefined"
    ? localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027"
    : "Taiwan Strait 2027";

  const history   = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("warbreak_history")  || "[]") : [];
  const redUsed   = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("warbreak_red_used") || "[]") : [];
  const storedMet = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("warbreak_metrics")  || "{}") : {};

  useEffect(() => {
    const id = localStorage.getItem("warbreak_game_id");
    if (!id || id === "local-demo") {
      setReport(buildAutopsyReport(null, scenario, history, redUsed, storedMet));
      setLoading(false);
      return;
    }
    getAutopsy(id)
      .then((data) => setReport(buildAutopsyReport(data, scenario, history, redUsed, storedMet)))
      .catch((e) => {
        const storedGame = readStoredJson("warbreak_game", {});
        if (Array.isArray(storedGame.assumptions) && storedGame.assumptions.length) {
          setReport(buildAutopsyReport(null, scenario, history, redUsed, storedMet));
        } else {
          setErr(e.message);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const copy = () => {
    const lines = [
      `WARBREAK FAILURE AUTOPSY — ${scenario}`,
      `Status: ${report?.status} | Turns: ${report?.turns}`,
      `Assumptions broken: ${report?.assumptions_broken}`,
      "",
      "DECISION LOG:",
      ...history.map((h:any) => `T${h.turn}: Blue → ${h.action} | Red → ${h.red}`),
      "",
      "ROOT CAUSES:",
      ...(report?.root_causes||[]).map((c:string) => `• ${c}`),
      "",
      "RECOMMENDATION:",
      report?.recommendation || "",
      "",
      report?.report || "",
    ].join("\n");
    navigator.clipboard?.writeText(lines).then(() => { setCopied(true); setTimeout(()=>setCopied(false),2000); });
  };

  if (err) return (
    <main style={{minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",flexDirection:"column",gap:16}}>
      <div style={{fontSize:14,color:"#ff3c3c"}}>{err}</div>
      <button className="btn primary" onClick={()=>router.push("/")}>Return</button>
    </main>
  );

  if (loading) return (
    <main style={{minHeight:"100vh",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:20}}>
      <div style={{width:80,height:80}}><div className="radar-disc" style={{width:"100%",height:"100%",opacity:0.5}}/></div>
      <div className="kicker">GENERATING AUTOPSY</div>
      {["Tracing failure chain…","Comparing timelines…","Consulting doctrine…"].map((m,i)=>(
        <div key={i} style={{fontSize:11,opacity:0.35,marginTop:-8}}>{m}</div>
      ))}
    </main>
  );

  if (!report) return null;

  const failed  = report.status === "failed";
  const metrics = report.final_metrics || storedMet;
  const optimal = OPTIMAL[scenario] || OPTIMAL["Taiwan Strait 2027"];
  const assumptions: any[] = report.assumptions || [];

  // Parse LLM report into sections
  const parsed: Record<string,string> = {};
  if (report.report) {
    const parts = report.report.split(/^== (.+) ==$/m).filter(Boolean);
    for (let i=0;i<parts.length-1;i+=2) parsed[parts[i].trim()] = parts[i+1].trim();
  }

  const tabContent = [
    // 0 ASSUMPTIONS
    <div key="assumptions">
      {assumptions.length === 0 ? (
        <div style={{opacity:0.4,fontSize:13}}>No assumptions extracted — start a game from the landing page to generate FOGLINE analysis.</div>
      ) : (
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          {assumptions.map((a:any,i:number)=>{
            const fragColor = a.fragility>75?"#ff3c3c":a.fragility>55?"#ffaa00":"#00e87a";
            const statusColor = a.status==="broken"?"#ff3c3c":a.status==="stressed"?"#ffaa00":"rgba(255,255,255,0.3)";
            return (
              <div key={i} style={{padding:"12px 14px",background:a.status==="broken"?"rgba(255,60,60,0.06)":a.status==="stressed"?"rgba(255,170,0,0.04)":"rgba(255,255,255,0.03)",border:`1px solid ${a.status==="broken"?"rgba(255,60,60,0.25)":a.status==="stressed"?"rgba(255,170,0,0.2)":"rgba(255,255,255,0.08)"}`,borderRadius:9}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:6}}>
                  <div style={{display:"flex",gap:8,alignItems:"center"}}>
                    <span style={{fontSize:11,fontWeight:700,opacity:0.5}}>{a.id}</span>
                    <span style={{fontSize:10,padding:"2px 7px",borderRadius:3,background:`${statusColor}18`,border:`1px solid ${statusColor}35`,color:statusColor}}>{(a.status||"untested").toUpperCase()}{a.turn_broken?` · T${a.turn_broken}`:""}</span>
                    <span style={{fontSize:10,opacity:0.35}}>{a.category}</span>
                  </div>
                  <div style={{textAlign:"right",flexShrink:0}}>
                    <div style={{fontSize:10,opacity:0.35,marginBottom:2}}>FRAGILITY</div>
                    <div style={{fontSize:18,fontWeight:800,color:fragColor,lineHeight:1}}>{a.fragility}</div>
                  </div>
                </div>
                <div style={{fontSize:13,lineHeight:1.6,marginBottom:a.basis?6:0}}>{a.text}</div>
                {a.basis&&<div style={{fontSize:11,opacity:0.4}}>📜 {a.basis}</div>}
                {a.cascade_effect&&a.status!=="untested"&&<div style={{fontSize:11,color:fragColor,marginTop:4}}>→ {a.cascade_effect}</div>}
              </div>
            );
          })}
        </div>
      )}
    </div>,

    // 1 DECISION LOG
    <div key="log">
      {history.length===0?(
        <div style={{opacity:0.4,fontSize:13}}>No moves recorded in this session.</div>
      ):(
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          {history.map((h:any,i:number)=>(
            <div key={i} style={{padding:"12px 14px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9}}>
              <div style={{display:"flex",gap:12,marginBottom:6}}>
                <div style={{width:28,height:28,borderRadius:"50%",background:"rgba(77,159,255,0.12)",border:"1px solid rgba(77,159,255,0.25)",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                  <span style={{fontSize:10,color:"#4d9fff",fontWeight:700}}>T{h.turn}</span>
                </div>
                <div style={{flex:1}}>
                  <div style={{fontSize:13,fontWeight:600,marginBottom:3}}>Blue: {h.action}</div>
                  <div style={{fontSize:12,opacity:0.5}}>Red responded with: {h.red}</div>
                  {h.ghost&&<div style={{fontSize:11,color:"rgba(255,150,150,0.7)",marginTop:6,fontStyle:"italic",borderLeft:"2px solid rgba(255,60,60,0.2)",paddingLeft:8}}>"{h.ghost.slice(0,120)}{h.ghost.length>120?"…":""}"</div>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>,

    // 2 GHOST COUNCIL
    <div key="ghost">
      <div style={{padding:"12px 14px",background:"rgba(255,60,60,0.05)",border:"1px solid rgba(255,60,60,0.15)",borderRadius:9,marginBottom:14}}>
        <div style={{fontSize:11,color:"#ff8888",marginBottom:8,letterSpacing:"0.08em"}}>ADVERSARY PROFILE — PLA THEATER COMMANDER</div>
        <div style={{fontSize:13,opacity:0.75,lineHeight:1.7}}>
          The Ghost Council does not play doctrine-optimal strategy. It plays psychologically realistic human decisions — loss-averse, domestically constrained, and focused on exploiting your plan's hidden weaknesses rather than your visible forces.
        </div>
      </div>
      {history.length===0?(
        <div style={{opacity:0.4,fontSize:13}}>No Ghost Council responses recorded.</div>
      ):(
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          {history.filter((h:any)=>h.ghost).map((h:any,i:number)=>(
            <div key={i} style={{padding:"12px 14px",background:"rgba(255,60,60,0.04)",border:"1px solid rgba(255,60,60,0.12)",borderRadius:9}}>
              <div style={{fontSize:10,color:"#ff8888",marginBottom:6}}>TURN {h.turn} RESPONSE</div>
              <div style={{fontSize:13,color:"rgba(255,200,200,0.85)",lineHeight:1.7,fontStyle:"italic"}}>"{h.ghost}"</div>
            </div>
          ))}
        </div>
      )}
      {parsed["FAILURE CHAIN"]&&(
        <div style={{marginTop:14,padding:"12px 14px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9}}>
          <div style={{fontSize:10,opacity:0.4,marginBottom:8,letterSpacing:"0.08em"}}>PSYCHOLOGICAL PATTERN</div>
          <div style={{fontSize:12,opacity:0.7,lineHeight:1.8,whiteSpace:"pre-wrap"}}>{parsed["FAILURE CHAIN"]}</div>
        </div>
      )}
    </div>,

    // 3 INFO BATTLEFIELD
    <div key="info">
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,marginBottom:16}}>
        {METRICS.map(({key,label,color})=>{
          const val = Math.round(metrics[key]??50);
          const c = val<30?"#ff3c3c":val>70?"#00e87a":color;
          return (
            <div key={key} style={{padding:"12px 14px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9}}>
              <div style={{fontSize:10,opacity:0.4,marginBottom:6}}>{label.toUpperCase()}</div>
              <div style={{fontSize:28,fontWeight:800,color:c,lineHeight:1,marginBottom:8}}>{val}</div>
              <div style={{height:3,background:"rgba(255,255,255,0.06)",borderRadius:2,overflow:"hidden"}}>
                <div style={{height:"100%",width:`${Math.max(0,Math.min(100,val))}%`,background:c,borderRadius:2}}/>
              </div>
              <div style={{fontSize:10,marginTop:6,opacity:0.4,color:val<30?"#ff3c3c":val>70?"#00e87a":"inherit"}}>
                {val<30?"Critical":val>70?"Strong":"Moderate"}
              </div>
            </div>
          );
        })}
      </div>
      {parsed["INFORMATION VERDICT"]?(
        <div style={{padding:"14px 16px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9}}>
          <div style={{fontSize:10,opacity:0.4,marginBottom:8,letterSpacing:"0.08em"}}>INFORMATION VERDICT</div>
          <div style={{fontSize:13,opacity:0.75,lineHeight:1.8,whiteSpace:"pre-wrap"}}>{parsed["INFORMATION VERDICT"]}</div>
        </div>
      ):(
        <div style={{padding:"14px 16px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9}}>
          <div style={{fontSize:10,opacity:0.4,marginBottom:8,letterSpacing:"0.08em"}}>INFORMATION VERDICT</div>
          <div style={{fontSize:13,opacity:0.65,lineHeight:1.8}}>
            {metrics.intl_opinion<40?"International opinion turned against Blue forces — the kinetic approach cost diplomatic standing."
            :metrics.allied_confidence<50?"Allied confidence degraded significantly — partners questioned Blue's commitment and judgment."
            :"Information metrics held within acceptable range. Force posture preserved political options."}
          </div>
        </div>
      )}
    </div>,

    // 4 FAILURE CHAIN
    <div key="chain">
      {report.root_causes?.length>0&&(
        <div style={{padding:"14px 16px",background:"rgba(255,60,60,0.06)",border:"1px solid rgba(255,60,60,0.2)",borderRadius:9,marginBottom:16}}>
          <div style={{fontSize:10,color:"#ff3c3c",letterSpacing:"0.1em",marginBottom:8}}>PRIMARY ROOT CAUSE</div>
          <div style={{fontSize:14,lineHeight:1.7}}>{report.root_causes[0]}</div>
        </div>
      )}
      {parsed["FAILURE CHAIN"]?(
        <div style={{padding:"14px 16px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9,marginBottom:14}}>
          <div style={{fontSize:10,opacity:0.4,marginBottom:8,letterSpacing:"0.08em"}}>CASCADE SEQUENCE</div>
          <div style={{fontSize:13,opacity:0.75,lineHeight:1.9,whiteSpace:"pre-wrap"}}>{parsed["FAILURE CHAIN"]}</div>
        </div>
      ):(
        <div style={{display:"flex",flexDirection:"column",gap:8}}>
          {(report.root_causes||[]).map((c:string,i:number)=>(
            <div key={i} style={{display:"flex",gap:12,alignItems:"flex-start",padding:"10px 12px",background:"rgba(255,60,60,0.04)",border:"1px solid rgba(255,60,60,0.12)",borderRadius:8}}>
              <div style={{width:6,height:6,borderRadius:"50%",background:"#ff3c3c",marginTop:5,flexShrink:0}}/>
              <div style={{fontSize:13,opacity:0.8,lineHeight:1.6}}>{c}</div>
            </div>
          ))}
          {report.root_causes?.length===0&&<div style={{opacity:0.4,fontSize:13}}>No failure chain data available.</div>}
        </div>
      )}
      {parsed["DECISION AUDIT"]&&(
        <div style={{marginTop:14,padding:"14px 16px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9}}>
          <div style={{fontSize:10,opacity:0.4,marginBottom:8,letterSpacing:"0.08em"}}>DECISION AUDIT</div>
          <div style={{fontSize:13,opacity:0.75,lineHeight:1.8,whiteSpace:"pre-wrap"}}>{parsed["DECISION AUDIT"]}</div>
        </div>
      )}
    </div>,

    // 5 WHAT IF
    <div key="whatif">
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
        <div style={{background:failed?"rgba(255,60,60,0.05)":"rgba(0,232,122,0.05)",border:`1px solid ${failed?"rgba(255,60,60,0.2)":"rgba(0,232,122,0.2)"}`,borderRadius:12,overflow:"hidden"}}>
          <div style={{padding:"11px 14px",background:failed?"rgba(255,60,60,0.1)":"rgba(0,232,122,0.1)",borderBottom:`1px solid ${failed?"rgba(255,60,60,0.15)":"rgba(0,232,122,0.15)"}`,display:"flex",alignItems:"center",gap:8}}>
            <div style={{width:7,height:7,borderRadius:"50%",background:failed?"#ff3c3c":"#00e87a"}}/>
            <div style={{fontSize:11,fontWeight:700,color:failed?"#ff3c3c":"#00e87a",letterSpacing:"0.08em"}}>TIMELINE A — YOUR PATH</div>
          </div>
          <div style={{padding:14,display:"flex",flexDirection:"column",gap:8}}>
            {history.length>0?history.map((h:any,i:number)=>(
              <div key={i} style={{display:"flex",gap:8}}>
                <div style={{fontSize:10,color:"#ff8888",flexShrink:0,fontWeight:700,paddingTop:1}}>T{h.turn}</div>
                <div style={{fontSize:12,opacity:0.75}}>{h.action}</div>
              </div>
            )):<div style={{fontSize:12,opacity:0.4}}>No moves recorded.</div>}
          </div>
        </div>
        <div style={{background:"rgba(77,159,255,0.05)",border:"1px solid rgba(77,159,255,0.2)",borderRadius:12,overflow:"hidden"}}>
          <div style={{padding:"11px 14px",background:"rgba(77,159,255,0.1)",borderBottom:"1px solid rgba(77,159,255,0.15)",display:"flex",alignItems:"center",gap:8}}>
            <div style={{width:7,height:7,borderRadius:"50%",background:"#4d9fff"}}/>
            <div style={{fontSize:11,fontWeight:700,color:"#4d9fff",letterSpacing:"0.08em"}}>TIMELINE B — OPTIMAL PATH</div>
          </div>
          <div style={{padding:14}}>
            <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:12}}>
              {optimal.moves.map((m,i)=>(
                <div key={i} style={{display:"flex",gap:8}}>
                  <div style={{fontSize:10,color:"#4d9fff",flexShrink:0,fontWeight:700,paddingTop:1}}>T{i+1}</div>
                  <div style={{fontSize:12,opacity:0.75}}>{m.replace(/^T\d+: /,"")}</div>
                </div>
              ))}
            </div>
            <div style={{padding:"8px 10px",background:"rgba(0,232,122,0.06)",border:"1px solid rgba(0,232,122,0.2)",borderRadius:7}}>
              <div style={{fontSize:10,color:"#00e87a",marginBottom:3}}>PROJECTED OUTCOME</div>
              <div style={{fontSize:11,opacity:0.65}}>{optimal.outcome}</div>
            </div>
          </div>
        </div>
      </div>
    </div>,

    // 6 RECOMMENDATIONS
    <div key="recs">
      {parsed["RESILIENT PLAN"]?(
        <div style={{padding:"14px 16px",background:"rgba(0,232,122,0.05)",border:"1px solid rgba(0,232,122,0.15)",borderRadius:9,marginBottom:14}}>
          <div style={{fontSize:10,color:"#00e87a",letterSpacing:"0.1em",marginBottom:8}}>DOCTRINE-GROUNDED CHANGES</div>
          <div style={{fontSize:13,color:"rgba(180,255,210,0.8)",lineHeight:1.9,whiteSpace:"pre-wrap"}}>{parsed["RESILIENT PLAN"]}</div>
        </div>
      ):(
        <div style={{display:"flex",flexDirection:"column",gap:10,marginBottom:14}}>
          {(report.lessons||[]).map((l:string,i:number)=>(
            <div key={i} style={{display:"flex",gap:12,padding:"12px 14px",background:"rgba(0,232,122,0.04)",border:"1px solid rgba(0,232,122,0.12)",borderRadius:9}}>
              <div style={{width:22,height:22,borderRadius:"50%",background:"rgba(0,232,122,0.12)",border:"1px solid rgba(0,232,122,0.2)",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                <span style={{fontSize:10,color:"#00e87a",fontWeight:700}}>{i+1}</span>
              </div>
              <div style={{fontSize:13,opacity:0.75,lineHeight:1.6}}>{l}</div>
            </div>
          ))}
        </div>
      )}
      {report.recommendation&&(
        <div style={{padding:"14px 16px",background:"rgba(77,159,255,0.05)",border:"1px solid rgba(77,159,255,0.2)",borderRadius:9}}>
          <div style={{fontSize:10,color:"#4d9fff",letterSpacing:"0.1em",marginBottom:7}}>KEY TAKEAWAY</div>
          <div style={{fontSize:14,lineHeight:1.75,color:"rgba(180,210,255,0.85)"}}>{report.recommendation}</div>
        </div>
      )}
    </div>,
  ];

  return (
    <main style={{minHeight:"100vh",display:"flex",flexDirection:"column"}}>

      {/* Top bar */}
      <div className="topbar" style={{position:"sticky",top:0,zIndex:100,backdropFilter:"blur(12px)"}}>
        <div className="brand">
          <button className="btn ghost" onClick={()=>router.push("/")}>← NEW MISSION</button>
          WARBREAK
          <span className="badge">{scenario}</span>
        </div>
        <button className="btn ghost" onClick={copy} style={{fontSize:11,opacity:copied?1:0.6}}>
          {copied?"✓ COPIED":"COPY REPORT"}
        </button>
      </div>

      <div style={{flex:1,padding:"28px 36px",maxWidth:1060,margin:"0 auto",width:"100%",boxSizing:"border-box"}}>

        {/* Verdict */}
        <div style={{textAlign:"center",marginBottom:32}}>
          <div className="kicker" style={{marginBottom:10,fontSize:10}}>FAILURE AUTOPSY — {scenario.toUpperCase()}</div>
          <h1 style={{fontSize:"clamp(36px,5.5vw,64px)",margin:"0 0 8px",color:failed?"#ff3c3c":"#00e87a",textShadow:`0 0 40px ${failed?"rgba(255,60,60,0.3)":"rgba(0,232,122,0.3)"}`}}>
            {failed?"▼ PLAN COLLAPSED":"▲ MISSION COMPLETE"}
          </h1>
          <div style={{fontSize:13,opacity:0.4}}>
            {report.turns} turns · {report.assumptions_broken} assumptions broken · {report.assumptions_stressed} stressed
          </div>
        </div>

        {/* 6 metrics — compact */}
        <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:8,marginBottom:28}}>
          {METRICS.map(({key,label,color})=>{
            const val = Math.round(metrics[key]??50);
            const c = val<30?"#ff3c3c":val>70?"#00e87a":color;
            return (
              <div key={key} style={{padding:"11px 10px",background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:9,textAlign:"center"}}>
                <div style={{fontSize:9,opacity:0.4,marginBottom:5,letterSpacing:"0.06em"}}>{label.toUpperCase()}</div>
                <div style={{fontSize:28,fontWeight:800,color:c,lineHeight:1,marginBottom:6}}>{val}</div>
                <div style={{height:2,background:"rgba(255,255,255,0.06)",borderRadius:1,overflow:"hidden"}}>
                  <div style={{height:"100%",width:`${Math.max(0,Math.min(100,val))}%`,background:c,borderRadius:1}}/>
                </div>
              </div>
            );
          })}
        </div>

        {/* Root cause — single line if available */}
        {report.root_causes?.length>0&&(
          <div style={{padding:"13px 16px",background:"rgba(255,60,60,0.06)",border:"1px solid rgba(255,60,60,0.2)",borderRadius:9,marginBottom:22,display:"flex",gap:12,alignItems:"flex-start"}}>
            <div style={{fontSize:18,flexShrink:0,marginTop:1}}>⚠</div>
            <div>
              <div style={{fontSize:10,color:"#ff3c3c",letterSpacing:"0.1em",marginBottom:5}}>ROOT CAUSE</div>
              <div style={{fontSize:14,lineHeight:1.6}}>{report.root_causes[0]}</div>
            </div>
          </div>
        )}

        {/* Tab bar */}
        <nav className="autopsy-tab-shell" aria-label="Autopsy sections">
          <div className="autopsy-tabs" role="tablist">
            {TABS.map((t,i)=>(
              <button
                key={t.label}
                className={`autopsy-tab ${tab===i ? "active" : ""}`}
                onClick={()=>setTab(i)}
                role="tab"
                aria-selected={tab===i}
                type="button"
              >
                <span className="autopsy-tab-index">{String(i + 1).padStart(2, "0")}</span>
                <span className="autopsy-tab-label">{t.label}</span>
              </button>
            ))}
          </div>
          <div className="autopsy-tab-context">
            <span>{TABS[tab].label}</span>
            <b>{TABS[tab].summary}</b>
          </div>
        </nav>

        {/* Tab content */}
        <div style={{padding:"18px 20px",background:"rgba(255,255,255,0.02)",border:"1px solid rgba(255,255,255,0.07)",borderRadius:10,marginBottom:24,minHeight:200}}>
          {tab === 0 ? <AssumptionRankPanel assumptions={assumptions} report={report} /> : tabContent[tab]}
        </div>

        {/* CTAs */}
        <div style={{display:"flex",gap:10,justifyContent:"center"}}>
          <button className="btn primary" onClick={()=>router.push("/")} style={{fontSize:13,padding:"11px 28px"}}>
            RUN NEW MISSION →
          </button>
          <button className="btn ghost" onClick={copy} style={{fontSize:13,padding:"11px 28px"}}>
            {copied?"✓ COPIED":"COPY REPORT"}
          </button>
        </div>

      </div>
    </main>
  );
}
