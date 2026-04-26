"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createGame } from "../lib/api";

const scenarios = [
  { name:"Taiwan Strait 2027", tag:"Western Pacific", icon:"⚓", plan:"Deploy carrier strike group to the western Pacific. Establish air superiority over the Taiwan Strait using F-35 sorties from Okinawa. Coordinate with Japan for logistics support. Conduct precision strikes on PLA missile batteries. Maintain open supply lines through the Luzon Strait and preserve international support.", why:"Sea lanes, Okinawa access, PLA coastal systems, Luzon Strait." },
  { name:"NATO Eastern Flank", tag:"Poland / Baltics", icon:"🛡️", plan:"Reinforce NATO's eastern flank after Russian gray-zone pressure near the Suwalki Gap. Deploy airborne forces to Poland, establish Patriot coverage, coordinate with Baltic host nations, and preserve Article 5 consensus while avoiding uncontrolled escalation.", why:"Suwalki Gap, Baltic access, NATO cohesion, Russian pressure zones." },
  { name:"Embassy Evacuation", tag:"Capital evacuation", icon:"🚁", plan:"Evacuate embassy personnel and civilians after host government collapse. Secure the embassy compound, identify evacuation routes, use airlift to offshore ships, coordinate with State Department, and avoid civilian casualties while hostile militia forces converge.", why:"Embassy zone, air corridor, harbor access, roadblocks." },
  { name:"Cyber Infrastructure", tag:"US critical grid", icon:"⚡", plan:"Respond to a ransomware and sabotage campaign against the northeastern power grid. Deploy CISA response teams, activate National Guard cyber units, restore priority substations, attribute the attack, and prevent spread into water and gas infrastructure.", why:"Grid hubs, backup systems, public confidence, cascading infrastructure risk." },
];

export default function Page() {
  const router = useRouter();
  const [selected, setSelected] = useState(scenarios[0]);
  const [plan, setPlan] = useState(scenarios[0].plan);
  const [loading, setLoading] = useState(false);
  const choose = (s:any) => { setSelected(s); setPlan(s.plan); };
  const start = async () => {
    setLoading(true);
    localStorage.setItem("warbreak_scenario", selected.name);
    localStorage.setItem("warbreak_map_why", selected.why);
    localStorage.setItem("warbreak_plan", plan);
    try {
      const g = await createGame(plan);
      localStorage.setItem("warbreak_game_id", g.id || g.game_id || g.session_id || "local-demo");
      localStorage.setItem("warbreak_game", JSON.stringify(g));
    } catch {
      localStorage.setItem("warbreak_game_id", "local-demo");
      localStorage.setItem("warbreak_game", JSON.stringify({ assumptions: [] }));
    }
    router.push("/assets");
  };
  return <main className="landing">
    <section className="panel hero">
      <div className="kicker">WARBREAK · ASSUMPTION WARGAME</div>
      <h1>Find the weak point before contact.</h1>
      <p>Choose a crisis, shape the plan, pick forces, identify likely opponent assets, then fight through a command simulation where hidden assumptions can become mission risk.</p>
      <div className="scenarios">
        {scenarios.map(s => <button key={s.name} className={`scenario-card ${selected.name===s.name?"active":""}`} onClick={()=>choose(s)}>
          <div style={{fontSize:24}}>{s.icon}</div><h3>{s.name}</h3><p>{s.tag}</p>
        </button>)}
      </div>
      <div className="radar-disc" />
    </section>
    <section className="panel order">
      <div className="kicker">MISSION ORDER</div>
      <h2>Edit the plan</h2>
      <textarea value={plan} onChange={e=>setPlan(e.target.value)} />
      <div style={{display:"flex", gap:12, alignItems:"center", marginTop:18}}>
        <button className="btn primary" onClick={start} disabled={loading}>{loading ? "BUILDING MISSION…" : "START MISSION →"}</button>
        {loading && <div className="ring" style={{width:54,height:54,fontSize:8}}>SCAN</div>}
      </div>
      <div style={{marginTop:18}} className="small">The plan becomes a playable risk map: assumptions, opponent pressure, force movement, and final autopsy.</div>
    </section>
  </main>;
}
