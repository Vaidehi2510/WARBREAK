from __future__ import annotations
import json, re
from game_state import Assumption
from llm_client import call_llm_json

PROMPT = """You are FOGLINE, a military assumption extraction engine for a serious wargame.

A planner wrote an operational plan. Extract every hidden assumption — things assumed true but never stated.

HISTORICAL CALIBRATION (use for fragility scores):
- CDB90: logistics assumptions fail in 67% of contested ops across 625 battles
- Correlates of War MID: escalation assumed controllable in 71% of crises that later escalated
- Tet Offensive 1968: assumed VC would not violate ceasefire — fragility 94, broke turn 1
- Maginot Line 1940: assumed enemy attacks through defended corridor — fragility 99
- Operation Market Garden 1944: assumed supply lines hold — broke day 3, full collapse
- FM 6-0: commanders average 3-5 unstated assumptions per COA
- JP 3-0: air superiority requires 72hrs minimum against peer air defense

RULES:
1. Extract exactly 6 assumptions
2. Each must be SPECIFIC to this plan — not generic military wisdom
3. Fragility 0-100 calibrated against historical data above
4. confidence = 1 - (fragility/100) approximately
5. criticality 0-1 = how much plan collapses if this breaks
6. basis = specific historical case with year
7. dependencies = list of assumption IDs that cascade if this breaks
8. cascade_effect = one concrete sentence on what breaks downstream
9. category: intel | logistics | alliance | adversary | civilian | cyber | operational

PLAN:
{plan}

Return ONLY this JSON — no other text:
{{
  "assumptions": [
    {{"id":"A1","text":"specific assumption","category":"logistics","fragility":78,"confidence":0.22,"criticality":0.85,"basis":"Operation Market Garden 1944 — supply lines broke day 3","doctrine_ref":"FM 4-0 Sustainment","dependencies":[],"cascade_effect":"what breaks downstream"}},
    {{"id":"A2","text":"specific assumption","category":"adversary","fragility":72,"confidence":0.28,"criticality":0.80,"basis":"historical case","doctrine_ref":"JP 3-0","dependencies":["A1"],"cascade_effect":"downstream effect"}},
    {{"id":"A3","text":"specific assumption","category":"intel","fragility":65,"confidence":0.35,"criticality":0.75,"basis":"historical case","doctrine_ref":"JP 2-0","dependencies":[],"cascade_effect":"downstream effect"}},
    {{"id":"A4","text":"specific assumption","category":"alliance","fragility":58,"confidence":0.42,"criticality":0.70,"basis":"historical case","doctrine_ref":"JP 3-16","dependencies":["A2"],"cascade_effect":"downstream effect"}},
    {{"id":"A5","text":"specific assumption","category":"cyber","fragility":52,"confidence":0.48,"criticality":0.65,"basis":"historical case","doctrine_ref":"JP 3-12","dependencies":[],"cascade_effect":"downstream effect"}},
    {{"id":"A6","text":"specific assumption","category":"civilian","fragility":44,"confidence":0.56,"criticality":0.60,"basis":"historical case","doctrine_ref":"JP 3-57","dependencies":["A3"],"cascade_effect":"downstream effect"}}
  ]
}}"""

def _parse(raw: str) -> dict:
    raw = re.sub(r'^```json\s*|^```\s*|\s*```$', '', raw.strip()).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise

def extract_assumptions(plan: str) -> list[Assumption]:
    raw = call_llm_json(PROMPT.format(plan=plan))
    data = _parse(raw)
    assumptions = [
        Assumption(
            id=a["id"], text=a["text"], category=a.get("category","operational"),
            fragility=int(a.get("fragility",60)), confidence=float(a.get("confidence",0.5)),
            criticality=float(a.get("criticality",0.6)), basis=a.get("basis",""),
            doctrine_ref=a.get("doctrine_ref",""), dependencies=a.get("dependencies",[]),
            cascade_effect=a.get("cascade_effect",""),
        )
        for a in data["assumptions"]
    ]
    assumptions.sort(key=lambda x: x.fragility, reverse=True)
    return assumptions
