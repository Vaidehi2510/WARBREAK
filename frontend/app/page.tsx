"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createGame } from "../lib/api";

const scenarios = [
  { name:"Taiwan Strait 2027",   tag:"Western Pacific",    icon:"⚓",  plan:"Deploy carrier strike group to the western Pacific. Establish air superiority over the Taiwan Strait using F-35 sorties from Okinawa. Coordinate with Japan for logistics support. Conduct precision strikes on PLA missile batteries. Maintain open supply lines through the Luzon Strait and preserve international support.", why:"Sea lanes, Okinawa access, PLA coastal systems, Luzon Strait." },
  { name:"NATO Eastern Flank",   tag:"Poland / Baltics",   icon:"🛡️", plan:"Reinforce NATO's eastern flank after Russian gray-zone pressure near the Suwalki Gap. Deploy airborne forces to Poland, establish Patriot coverage, coordinate with Baltic host nations, and preserve Article 5 consensus while avoiding uncontrolled escalation.", why:"Suwalki Gap, Baltic access, NATO cohesion, Russian pressure zones." },
  { name:"Embassy Evacuation",   tag:"Capital evacuation", icon:"🚁",  plan:"Evacuate embassy personnel and civilians after host government collapse. Secure the embassy compound, identify evacuation routes, use airlift to offshore ships, coordinate with State Department, and avoid civilian casualties while hostile militia forces converge.", why:"Embassy zone, air corridor, harbor access, roadblocks." },
  { name:"Cyber Infrastructure", tag:"US critical grid",   icon:"⚡",  plan:"Respond to a ransomware and sabotage campaign against the northeastern power grid. Deploy CISA response teams, activate National Guard cyber units, restore priority substations, attribute the attack, and prevent spread into water and gas infrastructure.", why:"Grid hubs, backup systems, public confidence, cascading infrastructure risk." },
];

export default function Page() {
  const router = useRouter();
  const [selected, setSelected] = useState(scenarios[0]);
  const [plan,     setPlan]     = useState(scenarios[0].plan);
  const [loading,  setLoading]  = useState(false);

  const choose = (s: typeof scenarios[0]) => { setSelected(s); setPlan(s.plan); };

  const start = async () => {
    setLoading(true);
    localStorage.setItem("warbreak_scenario", selected.name);
    localStorage.setItem("warbreak_map_why",  selected.why);
    localStorage.setItem("warbreak_plan",     plan);
    try {
      const g = await createGame(plan);
      localStorage.setItem("warbreak_game_id", g.id || g.game_id || g.session_id || "local-demo");
      localStorage.setItem("warbreak_game",    JSON.stringify(g));
    } catch {
      localStorage.setItem("warbreak_game_id", "local-demo");
      localStorage.setItem("warbreak_game",    JSON.stringify({ assumptions: [] }));
    }
    router.push("/assets");
  };

  return (
    <main style={{
      height: "100vh",
      width: "100vw",
      overflow: "hidden",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      position: "relative",
    }}>

      {/* Radar top-right */}
      <div style={{
        position: "fixed", top: -50, right: -50,
        width: 240, height: 240,
        opacity: 0.15, pointerEvents: "none", zIndex: 0,
      }}>
        <div className="radar-disc" style={{ width: "100%", height: "100%" }} />
      </div>

      {/* ── LEFT ── */}
      <div style={{
        padding: "0 40px 0 56px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 22,
        position: "relative",
        zIndex: 1,
        borderRight: "1px solid rgba(255,255,255,0.07)",
      }}>
        {/* Title */}
        <div>
          <div className="kicker" style={{ marginBottom: 8, fontSize: 10 }}>WARBREAK · ASSUMPTION WARGAME</div>
          <h1 style={{ margin: "0 0 10px", fontSize: "clamp(24px, 2.8vw, 38px)", lineHeight: 1.15 }}>
            Find the weak point<br />before contact.
          </h1>
          <p style={{ margin: 0, lineHeight: 1.65, opacity: 0.65, fontSize: 13 }}>
            Choose a crisis, shape the plan, pick forces, identify likely opponent assets, then fight through a command simulation where hidden assumptions can become mission risk.
          </p>
        </div>

        {/* Scenario cards */}
        <div>
          <div className="kicker" style={{ marginBottom: 10, fontSize: 10 }}>SELECT SCENARIO</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {scenarios.map(s => (
              <button
                key={s.name}
                onClick={() => choose(s)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  textAlign: "left",
                  padding: "13px 14px",
                  borderRadius: 10,
                  border: `1.5px solid ${selected.name === s.name ? "rgba(120,180,80,0.7)" : "rgba(255,255,255,0.13)"}`,
                  background: selected.name === s.name
                    ? "rgba(90,140,50,0.22)"
                    : "rgba(255,255,255,0.07)",
                  cursor: "pointer",
                  transition: "all 0.18s ease",
                  color: "inherit",
                }}
              >
                <div style={{ fontSize: 22, flexShrink: 0, lineHeight: 1 }}>{s.icon}</div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13, lineHeight: 1.25, color: selected.name === s.name ? "#c8e8a0" : "#d8d8c8" }}>
                    {s.name}
                  </div>
                  <div style={{ fontSize: 11, opacity: 0.6, marginTop: 2, color: "#aaa" }}>{s.tag}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── RIGHT ── */}
      <div style={{
        padding: "0 56px 0 40px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 18,
        position: "relative",
        zIndex: 1,
      }}>
        <div>
          <div className="kicker" style={{ marginBottom: 6, fontSize: 10 }}>MISSION ORDER</div>
          <div style={{ fontSize: "clamp(18px, 2vw, 26px)", fontWeight: 700, lineHeight: 1.2, marginBottom: 14 }}>
            Edit the plan
          </div>
          <textarea
            value={plan}
            onChange={e => setPlan(e.target.value)}
            rows={8}
            style={{
              width: "100%",
              boxSizing: "border-box",
              fontSize: 13,
              lineHeight: 1.7,
              resize: "none",
            }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button
            className="btn primary"
            onClick={start}
            disabled={loading}
            style={{ flex: 1, fontSize: 13, padding: "13px 20px" }}
          >
            {loading ? "BUILDING MISSION…" : "START MISSION →"}
          </button>
          {loading && (
            <div className="ring" style={{ width: 44, height: 44, fontSize: 7, flexShrink: 0 }}>SCAN</div>
          )}
        </div>

        <div className="small" style={{ opacity: 0.4, fontSize: 12, lineHeight: 1.55 }}>
          The plan becomes a playable risk map: assumptions, opponent pressure, force movement, and final autopsy.
        </div>
      </div>

    </main>
  );
}