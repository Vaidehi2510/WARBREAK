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
  "ASSUMPTIONS",
  "DECISION LOG",
  "GHOST COUNCIL",
  "INFO BATTLEFIELD",
  "FAILURE CHAIN",
  "WHAT IF",
  "RECOMMENDATIONS",
];

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
      setReport({
        status: "completed", turns: history.length || 3,
        final_metrics: storedMet,
        assumptions: [],
        root_causes: redUsed.slice(0,3),
        assumptions_broken: 2, assumptions_stressed: 1,
        report: "",
        lessons: [
          "Separate assumptions from objectives before execution.",
          "Treat high-fragility assumptions as decision gates.",
          "Design contingency branches for logistics and alliance failure.",
        ],
        recommendation: "Before the next run, require one mitigation for every assumption with fragility above 70.",
      });
      setLoading(false);
      return;
    }
    getAutopsy(id).then(setReport).catch(e => setErr(e.message)).finally(() => setLoading(false));
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
        <div style={{display:"flex",gap:3,marginBottom:16,overflowX:"auto",paddingBottom:2}}>
          {TABS.map((t,i)=>(
            <button key={i} onClick={()=>setTab(i)} style={{
              padding:"7px 13px",borderRadius:6,fontSize:10,fontWeight:700,
              whiteSpace:"nowrap",cursor:"pointer",transition:"all 0.15s",
              background:tab===i?"rgba(77,159,255,0.15)":"rgba(255,255,255,0.04)",
              border:`1px solid ${tab===i?"rgba(77,159,255,0.4)":"rgba(255,255,255,0.08)"}`,
              color:tab===i?"#4d9fff":"rgba(255,255,255,0.4)",
              letterSpacing:"0.06em",
            }}>{t}</button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{padding:"18px 20px",background:"rgba(255,255,255,0.02)",border:"1px solid rgba(255,255,255,0.07)",borderRadius:10,marginBottom:24,minHeight:200}}>
          {tabContent[tab]}
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