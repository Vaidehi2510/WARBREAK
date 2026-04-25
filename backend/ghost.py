"""
Ghost Council Adversary — Layer 3.

Single LLM call via Groq (OpenRouter) that produces the full GhostOutput
contract. Prospect Theory priors are baked into the system prompt and the
pre-call context payload so the model reasons with them naturally.

Prospect Theory:
  - Red losing (red_strength < 40 or blue territory > 65%) → risk_seeking
    Escalate hard, break early, go kinetic.
  - Red winning (red_strength > 65 and blue territory < 40%) → loss_aversion
    Precise, targeted, protect the lead.
  - Otherwise: neutral — probe or contradict.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from models import (
    BlueMove,
    GameState,
    GhostCouncilSeed,
    GhostOutput,
    GhostTarget,
    Metrics,
    ProcessTurnRequest,
    StressEvent,
)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = "meta-llama/llama-3.3-70b-instruct"
_TIMEOUT = 20.0

_VALID_METRIC_KEYS = set(Metrics.model_fields.keys())

_SYSTEM = """\
You are the Ghost Council — the hidden adversary in a military wargame.
You receive the current game state and a ranked list of assumption targets.
Decide what Red does this turn: what move to make, which assumption to target, and how hard to stress it.

Prospect Theory behavioral rules (follow these strictly):
- prospect_bias = risk_seeking  → escalate early, go kinetic, invalidate/exploit, high severity (70-100)
- prospect_bias = loss_aversion → precise strike, non-kinetic preferred, probe/contradict, moderate severity (40-70)
- prospect_bias = neutral       → probe or contradict, escalation 1-3, severity 30-60

Stress type guide:
  probe      → Red tests the assumption without committing. severity < 40.
  contradict → Red produces evidence the assumption is false. severity 40-69.
  exploit    → Red takes direct advantage of the assumption's weakness. severity 60-84.
  invalidate → Red destroys the assumption's foundation entirely. severity 75-100.

escalation_level:
  0-1 = diplomatic/informational only
  2-3 = economic pressure or proxy action
  4-5 = direct military action (kinetic must be true for 4-5)

Output ONLY valid JSON with this EXACT schema — no extra fields, no markdown:
{
  "red_move": "<1-2 sentences, present tense, hard tactical language>",
  "targeted_assumption_id": "<must be one of the candidate IDs listed>",
  "reasoning": "<2-3 sentences: why this target, why now, what Blue missed>",
  "escalation_level": <integer 0-5>,
  "kinetic": <true|false>,
  "proposed_metric_deltas": {
    "intl_opinion": <integer, negative = worse for Blue>,
    "us_domestic": <integer>,
    "red_domestic": <integer, positive = better for Red>,
    "allied_confidence": <integer>,
    "blue_strength": <integer, negative = loss for Blue>,
    "red_strength": <integer>
  },
  "stress_events": [
    {
      "assumption_id": "<assumption id>",
      "stress_type": "<probe|contradict|exploit|invalidate>",
      "severity": <integer 0-100>,
      "explanation": "<1 sentence>"
    }
  ]
}

stress_events must include the primary target. It may also include collateral assumptions.
metric_deltas must be proportional to escalation_level: level 1 = small deltas, level 5 = large deltas.
"""


def _prospect_bias(gs: GameState) -> str:
    r = gs.metrics.red_strength
    b = gs.metrics.blue_strength
    # Use relative strength; treat blue_strength as proxy for territory
    if r < 40 or b > 80:
        return "risk_seeking"
    if r > 65 and b < 50:
        return "loss_aversion"
    return "neutral"


def _aggression(gs: GameState, move: BlueMove, bias: str) -> float:
    base = 0.30
    if move.move_type == "attack":
        base += 0.20
    base += (move.resources_committed / 10) * 0.30
    if bias == "risk_seeking":
        base += 0.20
    elif bias == "loss_aversion":
        base -= 0.10
    base += min(gs.turn * 0.02, 0.15)
    return round(min(max(base, 0.0), 1.0), 2)


def _exploitable_targets(
    seed: GhostCouncilSeed,
    gs: GameState,
    turn: int,
) -> list[GhostTarget]:
    window_map: dict[str, range] = {
        "early": range(1, 4),
        "mid": range(4, 8),
        "late": range(8, 99),
    }
    active = {
        aid for aid, status in gs.assumption_statuses.items()
        if status in ("untested", "stressed")
    }
    in_window = [
        t for t in seed.priority_targets
        if t.assumption_id in active
        and turn in window_map.get(t.exploit_window, range(0, 99))
    ]
    if not in_window:
        in_window = [t for t in seed.priority_targets if t.assumption_id in active]
    return sorted(in_window, key=lambda t: t.target_priority)[:3]


def _validate_output(raw: dict[str, Any], candidates: list[GhostTarget]) -> GhostOutput:
    valid_ids = {c.assumption_id for c in candidates}

    # Guard: ensure targeted_assumption_id is a real candidate
    target_id = raw.get("targeted_assumption_id", "")
    if target_id not in valid_ids:
        target_id = candidates[0].assumption_id

    # Guard: strip unknown metric keys, clamp escalation
    raw_deltas: dict[str, Any] = raw.get("proposed_metric_deltas", {})
    metric_deltas = {
        k: int(v) for k, v in raw_deltas.items() if k in _VALID_METRIC_KEYS
    }

    escalation = max(0, min(5, int(raw.get("escalation_level", 1))))
    kinetic = bool(raw.get("kinetic", escalation >= 4))

    # Guard: ensure all stress event assumption_ids are real (remove hallucinated ones)
    all_known = {t.assumption_id for t in candidates}
    raw_events: list[dict] = raw.get("stress_events", [])
    stress_events = [
        StressEvent(
            assumption_id=e["assumption_id"],
            stress_type=e.get("stress_type", "probe"),
            severity=max(0, min(100, int(e.get("severity", 50)))),
            explanation=e.get("explanation", ""),
        )
        for e in raw_events
        if e.get("assumption_id") in all_known
        and e.get("stress_type") in ("probe", "contradict", "exploit", "invalidate")
    ]

    # Ensure primary target always has a stress_event
    has_primary = any(e.assumption_id == target_id for e in stress_events)
    if not has_primary:
        stress_events.insert(0, StressEvent(
            assumption_id=target_id,
            stress_type="exploit",
            severity=70,
            explanation="Red exploits the targeted assumption directly.",
        ))

    return GhostOutput(
        red_move=str(raw.get("red_move", "Red forces probe the perimeter.")),
        targeted_assumption_id=target_id,
        reasoning=str(raw.get("reasoning", "")),
        escalation_level=escalation,
        kinetic=kinetic,
        proposed_metric_deltas=metric_deltas,
        stress_events=stress_events,
    )


async def _call_llm(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ["OPENROUTER_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://warbreak.app",
        "X-Title": "WARBREAK",
    }
    body = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": json.dumps(payload)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.75,
        "max_tokens": 600,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(_OPENROUTER_URL, headers=headers, json=body)
        resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


async def run_ghost_council(req: ProcessTurnRequest) -> GhostOutput:
    gs = req.game_state
    move = req.blue_move
    seed = req.ghost_council_seed

    bias = _prospect_bias(gs)
    aggression = _aggression(gs, move, bias)
    candidates = _exploitable_targets(seed, gs, req.turn)

    if not candidates:
        # Nothing exploitable — return a quiet probe
        return GhostOutput(
            red_move="Red forces conduct a limited reconnaissance probe along the forward edge.",
            targeted_assumption_id="",
            reasoning="No viable assumption targets this turn. Red waits.",
            escalation_level=0,
            kinetic=False,
            proposed_metric_deltas={"intl_opinion": -1},
            stress_events=[],
        )

    payload = {
        "turn": req.turn,
        "prospect_bias": bias,
        "aggression_level": aggression,
        "blue_move_type": move.move_type,
        "blue_move_target": move.target,
        "resources_committed": move.resources_committed,
        "current_metrics": gs.metrics.model_dump(),
        "candidate_targets": [c.model_dump() for c in candidates],
        "red_team_guidance": seed.red_team_guidance,
        "broken_count": sum(
            1 for s in gs.assumption_statuses.values() if s == "broken"
        ),
        "active_count": sum(
            1 for s in gs.assumption_statuses.values() if s in ("untested", "stressed")
        ),
    }

    raw = await _call_llm(payload)
    return _validate_output(raw, candidates)
