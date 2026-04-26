"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAutopsy } from "../../lib/api";

function compactReport(raw:string, scenario:string, history:any[], redUsed:string[]) {
  const firstAction = history[0]?.action || "the opening move";
  const lastRed = history.at(-1)?.red || redUsed[0] || "opponent pressure";
  return {
    verdict: `The mission became fragile because ${firstAction.toLowerCase()} depended on conditions the opponent could pressure quickly.`,
    root: "Root cause: the plan treated key assumptions as facts instead of decision gates.",
    chain: [
      `Blue opened with ${firstAction}.`,
      `Red used ${lastRed} to pressure the weakest assumption.`,
      "The broken assumption reduced freedom of action and forced reactive choices.",
    ],
    historical: scenario.includes("Taiwan") ? "Real-world echo: wargames and public analyses often show Taiwan scenarios turning on basing access, missile pressure, submarine risk, and political timing." : scenario.includes("NATO") ? "Real-world echo: Cold War and Ukraine-era planning both show that alliance cohesion, logistics corridors, and escalation control can matter as much as tactical wins." : scenario.includes("Embassy") ? "Real-world echo: evacuation missions such as Kabul 2021 and earlier embassy crises show that airspace access, crowd control, and host-nation reliability can collapse quickly." : "Real-world echo: major cyber incidents show that recovery depends on backups, public confidence, attribution, and preventing spread into adjacent systems.",
    fixes: ["Name the top three assumptions before execution.", "Create a backup action for each fragile assumption.", "Protect logistics, access, and public legitimacy before committing high-risk moves."],
    technical: raw || "The game tracked assumption stress, opponent pressure, selected assets, force state, information metrics, and red assets used."
  };
}

export default function AutopsyPage(){
  const router = useRouter();
  const [loading,setLoading]=useState(true); const [report,setReport]=useState<any|null>(null);
  useEffect(()=>{ (async()=>{ const scenario=localStorage.getItem("warbreak_scenario")||"Taiwan Strait 2027"; let history:any[]=[]; let redUsed:string[]=[]; try{history=JSON.parse(localStorage.getItem("warbreak_history")||"[]"); redUsed=JSON.parse(localStorage.getItem("warbreak_red_used")||"[]");}catch{} let raw=""; try{ const gid=localStorage.getItem("warbreak_game_id")||""; const r= await getAutopsy(gid); raw = r.report || r.autopsy || ""; }catch{} setTimeout(()=>{ setReport(compactReport(raw,scenario,history,redUsed)); setLoading(false); }, 1100); })(); },[]);
  if(loading) return <main className="autopsy-loader"><div className="ring">AUTOPSY</div></main>;
  return <main className="report"><button className="btn ghost" onClick={()=>router.push('/game')}>← BACK TO MAP</button><section className="report-hero"><div className="kicker">WARBREAK AUTOPSY</div><h1>Mission Debrief</h1><p style={{fontSize:18,maxWidth:900}}>{report.verdict}</p><div className="scenarios" style={{gridTemplateColumns:"repeat(4,1fr)",maxWidth:"none"}}><div className="scenario-card"><h3>Root cause</h3><p>{report.root}</p></div><div className="scenario-card"><h3>Impact</h3><p>Freedom of action narrowed after the assumption was pressured.</p></div><div className="scenario-card"><h3>Red pressure</h3><p>Opponent attacked the plan's weak point, not only the visible force.</p></div><div className="scenario-card"><h3>Better posture</h3><p>Build backup actions before committing irreversible moves.</p></div></div></section><section className="report-grid"><div className="report-card"><h3>Failure chain</h3>{report.chain.map((c:string,i:number)=><div className="timeline-row" key={i}><b>Step {i+1}</b><span>{c}</span></div>)}<h3 style={{marginTop:20}}>Historical precedent</h3><p>{report.historical}</p></div><div className="report-card"><h3>What should change</h3>{report.fixes.map((f:string,i:number)=><p key={i}>✓ {f}</p>)}<h3 style={{marginTop:18}}>Technical note</h3><p className="small">{report.technical.slice(0,900)}{report.technical.length>900?"…":""}</p><button className="btn primary" onClick={()=>navigator.clipboard.writeText(JSON.stringify(report,null,2))}>COPY DEBRIEF →</button></div></section></main>;
}
