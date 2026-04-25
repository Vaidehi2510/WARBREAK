from __future__ import annotations
import json
from game_state import GameState
from llm_client import call_llm

PROMPT = """You are generating a military Failure Autopsy for WARBREAK. Readers are national security practitioners.

Be specific. Reference actual moves and assumptions by ID and name. No fluff.

ORIGINAL PLAN:
{plan}

ASSUMPTIONS:
{assumptions}

GAME HISTORY:
{history}

FINAL METRICS:
Blue strength: {blue_strength}/100 | Intl opinion: {intl}/100
US domestic: {us_domestic}/100 | Allied confidence: {allied}/100
Red domestic: {red_domestic}/100 | Status: {status}

Write with exactly these 5 section headers (use == TITLE == format):

== ASSUMPTION INVENTORY ==
All 6 assumptions ranked by fragility. For each: ID, fragility, status, turn broken if applicable, what it caused.

== FAILURE CHAIN ==
Exact causal sequence from first stress to final state. Which broke first, what cascaded, trace the path.

== DECISION AUDIT ==
Which moves were sound. Which created new fragile assumptions. Which missed opportunities. Be direct.

== INFORMATION VERDICT ==
Did Blue win or lose the information war? What drove each metric? What should have been different?

== RESILIENT PLAN ==
Three specific changes to the original plan. Each must cite doctrine (JP 3-0, FM 6-0, FM 4-0, JP 3-12, JP 3-16) and explain why it addresses the fragility.

Write in direct military prose. No bullet points. No vague advice."""

def generate_autopsy(game: GameState) -> dict:
    assumptions_data = [
        {"id": a.id, "text": a.text, "fragility": a.fragility, "category": a.category,
         "basis": a.basis, "doctrine_ref": a.doctrine_ref, "status": a.status,
         "turn_broken": a.turn_broken, "cascade_effect": a.cascade_effect}
        for a in game.assumptions
    ]
    history_data = [
        {"turn": e.turn, "blue_move": e.blue_move, "red_move": e.red_move,
         "ghost_reasoning": e.ghost_reasoning, "broken_chain": e.broken_chain}
        for e in game.events
    ]
    report = call_llm(PROMPT.format(
        plan=game.plan,
        assumptions=json.dumps(assumptions_data, indent=2),
        history=json.dumps(history_data, indent=2),
        blue_strength=game.metrics.get("blue_strength", 0),
        intl=game.metrics.get("intl_opinion", 0),
        us_domestic=game.metrics.get("us_domestic", 0),
        allied=game.metrics.get("allied_confidence", 0),
        red_domestic=game.metrics.get("red_domestic", 0),
        status=game.status,
    ), temperature=0.4, max_tokens=2000)

    broken = [a for a in game.assumptions if a.status == "broken"]
    stressed = [a for a in game.assumptions if a.status == "stressed"]
    return {
        "game_id": game.id, "status": game.status, "turns": game.turn,
        "final_metrics": game.metrics, "report": report,
        "root_causes": [a.text for a in sorted(broken, key=lambda x: x.fragility, reverse=True)[:3]],
        "assumptions_broken": len(broken), "assumptions_stressed": len(stressed),
        "escalation_gates": {
            "nuclear_signaling": game.metrics.get("red_domestic", 0) > 75,
            "preemptive_strike_auth": game.metrics.get("us_domestic", 0) > 40,
            "japan_support": game.metrics.get("allied_confidence", 0) > 80,
            "allied_basing": game.metrics.get("intl_opinion", 0) > -30,
        },
        "lessons": [
            "Separate assumptions from objectives before execution.",
            "Treat high-fragility assumptions as decision gates requiring explicit mitigation.",
            "Design contingency branches for logistics, communications, and alliance failure modes.",
        ],
        "recommendation": "Before the next run, require one mitigation or trigger condition for every assumption with fragility above 70.",
    }
