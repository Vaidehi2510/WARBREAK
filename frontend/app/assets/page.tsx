"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { identifyOpponentAssets } from "../../lib/api";

const assets = [
  { id:"carrier", name:"Carrier Strike Group", type:"Naval", cost:10, icon:"⚓", desc:"Air wing, escorts, long-range presence." },
  { id:"sub", name:"Virginia-class Submarine", type:"Naval", cost:6, icon:"◆", desc:"Covert sea denial and surveillance." },
  { id:"f35", name:"F-35C Squadron", type:"Air", cost:7, icon:"✈️", desc:"Stealth strike and air superiority." },
  { id:"patriot", name:"Patriot PAC-3 Battery", type:"Defense", cost:4, icon:"▲", desc:"Missile defense for forward bases." },
  { id:"growler", name:"EA-18G Growler Squadron", type:"Air", cost:4, icon:"📡", desc:"Electronic warfare and air defense suppression." },
  { id:"p8", name:"P-8 Poseidon Patrol", type:"Air", cost:3, icon:"🔎", desc:"Anti-submarine search and tracking." },
  { id:"aegis", name:"Aegis Destroyer", type:"Naval", cost:5, icon:"⚔️", desc:"Air defense, escort, missile intercept." },
  { id:"stryker", name:"Stryker Brigade", type:"Ground", cost:5, icon:"▰", desc:"Rapid ground presence and urban security." },
  { id:"cyber", name:"Cyber Command Cell", type:"Cyber", cost:3, icon:"⚡", desc:"Network defense and disruption." },
  { id:"mq9", name:"MQ-9 Reaper Flight", type:"Air", cost:2, icon:"◈", desc:"Persistent surveillance and precision strike." },
  { id:"sof", name:"Special Operations Team", type:"Ground", cost:4, icon:"✦", desc:"Reconnaissance, hostage rescue, direct action." },
  { id:"sealift", name:"Sealift Logistics Package", type:"Logistics", cost:4, icon:"▣", desc:"Fuel, spares, sustainment, evacuation lift." },
];

const fallback = {
  summary:"Likely opponent package centers on mobile missiles, air defense, submarines, cyber disruption, and information pressure.",
  predicted_assets:[
    { name:"Mobile missile batteries", confidence:86, threat_to_blue:"High", capability:"Can threaten fixed bases or major naval units.", counter:"Disperse forces, suppress launchers, avoid predictable routes." },
    { name:"Diesel-electric submarines", confidence:74, threat_to_blue:"High", capability:"Can contest chokepoints and supply lanes.", counter:"Use ASW patrols, decoys, and submarine barriers." },
    { name:"Cyber / electronic disruption", confidence:79, threat_to_blue:"Medium", capability:"Can delay targeting, communications, and public messaging.", counter:"Use backup comms, manual procedures, and pre-cleared public messaging." },
  ],
  key_warnings:["The opponent will likely pressure assumptions before directly destroying forces.", "Chokepoints, basing rights, public confidence, and airspace access are likely attack surfaces."],
  recommended_blue_additions:["Add ISR redundancy.", "Add logistics reserve.", "Add public/coalition messaging capacity."],
};

export default function AssetsPage() {
  const router = useRouter();
  const scenario = typeof window !== "undefined" ? localStorage.getItem("warbreak_scenario") || "Taiwan Strait 2027" : "Taiwan Strait 2027";
  const [budget, setBudget] = useState(28);
  const [selected, setSelected] = useState<string[]>(["carrier", "sub", "f35"]);
  const [brief, setBrief] = useState<any>(fallback);
  const [loading, setLoading] = useState(false);
  const picked = useMemo(()=>assets.filter(a=>selected.includes(a.id)), [selected]);
  const spent = picked.reduce((s,a)=>s+a.cost,0);
  const toggle = (id:string) => {
    const next = selected.includes(id) ? selected.filter(x=>x!==id) : [...selected, id];
    const nextSpent = assets.filter(a=>next.includes(a.id)).reduce((s,a)=>s+a.cost,0);
    if (nextSpent <= budget) setSelected(next);
  };
  const identify = async () => {
    setLoading(true);
    const res = await identifyOpponentAssets(scenario, picked);
    setBrief(res || fallback);
    setLoading(false);
  };
  const enter = () => {
    localStorage.setItem("warbreak_assets", JSON.stringify(picked));
    localStorage.setItem("warbreak_opponent_assets", JSON.stringify(brief));
    router.push("/game");
  };
  return <main className="assets-page">
    <div className="topbar" style={{margin:"-24px -32px 24px"}}><div className="brand"><button className="btn ghost" onClick={()=>router.push('/')}>← BACK</button> WARBREAK <span className="badge">{scenario}</span></div><button className="btn primary" onClick={enter}>ENTER WARGAME →</button></div>
    <div className="budget-row"><div><div className="kicker">CHOOSE YOUR FORCE PACKAGE</div><p className="small">Set the mission budget. Higher budget means more readiness, lift, logistics, and political attention available before the mission starts.</p></div><div className="badge">BUDGET {budget} · SPENT {spent}</div><input type="range" min="12" max="60" value={budget} onChange={e=>setBudget(Number(e.target.value))}/></div>
    <div className="assets-grid">
      <section className="asset-list">{assets.map(a=><button key={a.id} className={`asset-card ${selected.includes(a.id)?"selected":""}`} onClick={()=>toggle(a.id)}><span className="cost">{a.cost}</span><div style={{fontSize:24}}>{a.icon}</div><h3>{a.name}</h3><p>{a.desc}</p><div className="small" style={{marginTop:10}}>{a.type}</div></button>)}</section>
      <aside>
        <div className="side-panel"><h2 style={{marginTop:0,fontSize:20}}>Your forces</h2>{picked.map(a=><span className="chip" key={a.id}>{a.icon} {a.name}</span>)}</div>
        <div className="side-panel" style={{marginTop:14}}><h2 style={{marginTop:0,fontSize:20}}>Opponent Asset Identification</h2><p className="small">Estimate what the opposing side is likely to use against your force package.</p><button className="btn primary" onClick={identify}>{loading?"IDENTIFYING…":"IDENTIFY OPPONENT ASSETS →"}</button></div>
        <div className="side-panel" style={{marginTop:14}}><h2 style={{marginTop:0,fontSize:20}}>Likely opponent package</h2><p>{brief.summary}</p>{(brief.predicted_assets||[]).map((x:any,i:number)=><div className="asset-card" style={{minHeight:0, marginTop:10}} key={i}><h3>{x.name}</h3><p>Confidence {x.confidence || "—"}% · Threat {x.threat_to_blue || "Medium"}</p><p>{x.capability}</p><p className="small">Counter: {x.counter}</p></div>)}<h3 style={{fontSize:15}}>Key warnings</h3>{(brief.key_warnings||[]).map((w:string,i:number)=><p key={i} className="small">• {w}</p>)}</div>
      </aside>
    </div>
  </main>;
}
