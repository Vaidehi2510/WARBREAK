from __future__ import annotations
import json, re
from game_state import GameState
from llm_client import call_llm_json

PROMPT = """You are the Ghost Council — a PLA Senior Theater Commander in a wargame.

You do NOT play doctrine-optimal. You play psychologically realistic human decisions.

PSYCHOLOGICAL PROFILE:
- Loss aversion: {loss_aversion}/1.0 — weight losses 2x more than gains. Protect assets over gaining new ones.
- Escalation threshold: {escalation_threshold}/1.0 — below 0.5 avoid direct kinetic retaliation.
- Red domestic support: {red_domestic}/100 — above 70 escalation options unlock.

BEHAVIORAL ANCHORS:
1. EP-3 2001: chose detention over military retaliation — patience over reaction
2. Taiwan Strait 1995: missiles as signaling only, halted when USS Nimitz arrived
3. Galwan 2020: absorbed casualties without escalating to air/naval

GAME STATE:
Blue strength: {blue_strength}/100 | Red strength: {red_strength}/100
Turn: {turn}/{max_turns}
Intl opinion: {intl} | Red domestic: {red_domestic} | US domestic: {us_domestic}

BLUE ACTION: {blue_move}

BLUE ASSUMPTION MAP (exploit these):
{assumption_map}

TASK: Target the highest-fragility unbroken assumption. Match your psychological profile. Never expend DF-21D reactively if loss_aversion > 0.7.

Return ONLY this JSON:
{{"red_move":"concrete action","targeted_assumption_id":"A1","reasoning":"first-person 2-3 sentences","kinetic":false,"escalation_level":1,"ghost_state":"one sentence on psychological state"}}"""

def _parse(raw: str) -> dict:
    raw = re.sub(r'^```json\s*|^```\s*|\s*```$', '', raw.strip()).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise

def ghost_response(game: GameState, blue_move: str) -> dict:
    assumption_map = [
        {"id": a.id, "text": a.text, "fragility": a.fragility,
         "cascade_effect": a.cascade_effect, "category": a.category}
        for a in game.assumptions if a.status != "broken"
    ]
    raw = call_llm_json(PROMPT.format(
        loss_aversion=game.ghost_loss_aversion,
        escalation_threshold=game.ghost_escalation_threshold,
        blue_strength=game.metrics.get("blue_strength", 100),
        red_strength=game.metrics.get("red_strength", 100),
        turn=game.turn + 1, max_turns=game.max_turns,
        intl=game.metrics.get("intl_opinion", 50),
        red_domestic=game.metrics.get("red_domestic", 61),
        us_domestic=game.metrics.get("us_domestic", 72),
        blue_move=blue_move,
        assumption_map=json.dumps(assumption_map, indent=2),
    ))
    return _parse(raw)
