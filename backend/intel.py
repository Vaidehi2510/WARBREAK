from __future__ import annotations
import json, re
try:
    from llm_client import call_llm
except Exception:
    call_llm = None
from pathlib import Path

PROMPT = """You are helping identify likely opponent assets for a public, unclassified training wargame.
Do not call this OSINT. Call it Opponent Asset Identification.
Use plain English. Avoid jargon. Give concise, useful results.

Scenario: {scenario}
Adversary: {adversary}
Blue selected assets: {blue_assets}

Return JSON only:
{{
  "classification":"PUBLIC-SOURCE ESTIMATE",
  "scenario":"{scenario}",
  "adversary":"{adversary}",
  "threat_level":"HIGH",
  "confidence":75,
  "summary":"short plain English summary",
  "predicted_assets":[{{"name":"asset name","category":"category","quantity":"plain estimate","confidence":75,"threat_to_blue":"HIGH","capability":"why it matters in plain English","counter":"how Blue can reduce risk"}}],
  "key_warnings":["warning 1","warning 2","warning 3"],
  "recommended_blue_additions":["addition 1","addition 2","addition 3"],
  "historical_precedent":"brief real-world echo, not overclaiming exact match"
}}
"""

def fallback(scenario: str, adversary: str):
    s=(scenario or '').lower()
    if 'embassy' in s:
        return {"classification":"PUBLIC-SOURCE ESTIMATE","scenario":scenario,"adversary":adversary,"threat_level":"HIGH","confidence":72,"summary":"The likely opponent package is small but dangerous: mobile air threats, roadblocks, and rumor campaigns that slow civilian movement.","predicted_assets":[{"name":"Mobile air-defense teams","category":"air defense","quantity":"small teams near routes","confidence":76,"threat_to_blue":"HIGH","capability":"Can make air evacuation unsafe.","counter":"Use alternate pickup sites and suppress threats before flights."},{"name":"Roadblocks and militia patrols","category":"ground","quantity":"several checkpoints","confidence":82,"threat_to_blue":"MEDIUM","capability":"Can delay civilians reaching the embassy.","counter":"Use protected convoys and multiple muster points."},{"name":"Rumor/disinformation channels","category":"information","quantity":"local media and social channels","confidence":68,"threat_to_blue":"MEDIUM","capability":"Can cause crowds to move to the wrong place.","counter":"Use trusted public messaging."}],"key_warnings":["Air access may close suddenly.","Civilians may not reach muster points on time.","Rumors can break the plan before combat does."],"recommended_blue_additions":["Alternate pickup site","Route clearing team","Public communications cell"],"historical_precedent":"Comparable evacuation missions often struggle when air access, route control, or civilian accountability breaks before extraction begins."}
    if 'nato' in s:
        return {"classification":"PUBLIC-SOURCE ESTIMATE","scenario":scenario,"adversary":adversary,"threat_level":"HIGH","confidence":74,"summary":"The opponent is likely to use ambiguity first: cyber pressure, border incidents, and long-range fires designed to slow allied decisions.","predicted_assets":[{"name":"Long-range fires","category":"missile/artillery","quantity":"regional network","confidence":74,"threat_to_blue":"HIGH","capability":"Can threaten staging areas.","counter":"Disperse and use alternate logistics routes."},{"name":"Cyber disruption teams","category":"cyber","quantity":"state-backed groups","confidence":80,"threat_to_blue":"HIGH","capability":"Can delay mobilization.","counter":"Backup communications and manual procedures."},{"name":"Deniable border forces","category":"ground","quantity":"small units/proxies","confidence":69,"threat_to_blue":"MEDIUM","capability":"Can create confusion below the war threshold.","counter":"Define response triggers early."}],"key_warnings":["Alliance decision speed is a target.","Cyber effects may arrive first.","Ambiguity can delay response."],"recommended_blue_additions":["Redundant communications","Public attribution plan","Pre-approved reinforcement triggers"],"historical_precedent":"Gray-zone crises often exploit hesitation before open combat; slow political response can be as costly as weak military response."}
    return {"classification":"PUBLIC-SOURCE ESTIMATE","scenario":scenario,"adversary":adversary,"threat_level":"CRITICAL","confidence":78,"summary":"The likely opponent package combines missiles, submarines, air defense, cyber disruption, and public pressure.","predicted_assets":[{"name":"Anti-ship missiles","category":"missile","quantity":"multiple mobile units","confidence":85,"threat_to_blue":"CRITICAL","capability":"Forces ships to stay farther away.","counter":"Disperse, use deception, and strike only with reliable intelligence."},{"name":"Diesel-electric submarines","category":"naval","quantity":"several patrol groups","confidence":79,"threat_to_blue":"HIGH","capability":"Threatens sea lanes and supply routes.","counter":"Use ASW patrols and alternate routes."},{"name":"Integrated air defense","category":"air defense","quantity":"coastal network","confidence":83,"threat_to_blue":"HIGH","capability":"Makes air control slower and costlier.","counter":"Use electronic warfare and avoid assuming rapid air control."}],"key_warnings":["Political windows may close quickly.","Mobile targets are hard to confirm.","Allied basing access is fragile."],"recommended_blue_additions":["ASW patrol aircraft","Electronic warfare support","Allied messaging plan"],"historical_precedent":"Past crises show political windows can close faster than operational plans expect, and mobile target hunts are often harder than planners hope."}

def generate_intel_briefing(scenario: str, adversary: str, blue_assets: list) -> dict:
    if call_llm:
        try:
            raw=call_llm(PROMPT.format(scenario=scenario,adversary=adversary,blue_assets=json.dumps(blue_assets)),max_tokens=1400,temperature=0.25)
            raw=re.sub(r'^```json\s*|^```\s*|\s*```$','',raw.strip())
            return json.loads(re.search(r'\{.*\}', raw, re.S).group())
        except Exception:
            pass
    return fallback(scenario, adversary)
