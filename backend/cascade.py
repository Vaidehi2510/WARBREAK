"""
Cascade Engine — Layer 3.

Deterministic — no LLM. Takes a GhostOutput and propagates the effects
through the assumption dependency graph using the FOGLINE cascade_seed.

Break determination from stress_events:
  severity >= 70  → assumption breaks
  severity >= 30  → assumption stressed
  severity <  30  → no status change

After direct breaks from stress_events, BFS propagation runs using
propagation_rules. Each rule's weight determines cascade severity:
  weight >= 0.70  → cascade_break
  weight >= 0.30  → stressed
  weight <  0.30  → no change (below cascade threshold)

Final metric_deltas = ghost.proposed_metric_deltas amplified by cascade depth:
  each cascade_break node adds +30% to all deltas (capped at 2×).
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from models import (
    AssumptionPatch,
    CascadeOutput,
    CascadeSeed,
    FailureFlags,
    GameState,
    GhostOutput,
)

_BREAK_SEVERITY = 70
_STRESS_SEVERITY = 30
_CASCADE_BREAK_WEIGHT = 0.70
_CASCADE_STRESS_WEIGHT = 0.30
_AMPLIFY_PER_CASCADE = 0.30
_MAX_AMPLIFY = 2.0

_MILITARY_TAGS = {"military", "air", "naval", "ground", "supply", "logistics"}
_POLITICAL_TAGS = {"political", "domestic", "us_domestic", "public", "legitimacy"}
_ALLIANCE_TAGS = {"alliance", "allied", "coalition", "partner", "nato"}


def _build_adjacency(seed: CascadeSeed) -> dict[str, list[tuple[str, float, int]]]:
    adj: dict[str, list[tuple[str, float, int]]] = defaultdict(list)
    for rule in seed.propagation_rules:
        adj[rule.from_id].append((rule.to_id, rule.weight, rule.delay_turns))
    return dict(adj)


def _lookup(assumption_id: str, assumptions: list[dict[str, Any]]) -> dict[str, Any]:
    for a in assumptions:
        if a.get("id") == assumption_id:
            return a
    return {}


def _tags_of(assumption_id: str, assumptions: list[dict[str, Any]]) -> set[str]:
    a = _lookup(assumption_id, assumptions)
    return {t.lower() for t in a.get("tags", [])}


def _compute_failure_flags(
    broken_chain: list[str],
    metric_deltas: dict[str, int],
    escalation_level: int,
    assumptions: list[dict[str, Any]],
) -> FailureFlags:
    all_tags: set[str] = set()
    for aid in broken_chain:
        all_tags |= _tags_of(aid, assumptions)

    military = (
        bool(all_tags & _MILITARY_TAGS)
        or metric_deltas.get("blue_strength", 0) <= -15
    )
    political = (
        bool(all_tags & _POLITICAL_TAGS)
        or metric_deltas.get("us_domestic", 0) <= -10
        or metric_deltas.get("intl_opinion", 0) <= -12
    )
    alliance = (
        bool(all_tags & _ALLIANCE_TAGS)
        or metric_deltas.get("allied_confidence", 0) <= -12
    )
    escalation_fail = escalation_level >= 4

    return FailureFlags(
        military_failure=military,
        political_failure=political,
        alliance_failure=alliance,
        escalation_failure=escalation_fail,
    )


def _build_narrative(
    broken_chain: list[str],
    stressed_ids: list[str],
    flags: FailureFlags,
    assumptions: list[dict[str, Any]],
) -> str:
    if not broken_chain:
        if stressed_ids:
            labels = [
                f"'{_lookup(aid, assumptions).get('statement', aid)}'"
                for aid in stressed_ids[:2]
            ]
            return (
                f"No assumptions collapsed this turn, but "
                f"{' and '.join(labels)} {'is' if len(labels) == 1 else 'are'} "
                f"under severe stress and may break soon."
            )
        return "The plan held this turn. No assumptions failed."

    primary = _lookup(broken_chain[0], assumptions)
    primary_label = primary.get("statement", broken_chain[0])
    parts = [f"Once '{primary_label}' collapsed"]

    if len(broken_chain) > 1:
        downstream = [
            f"'{_lookup(aid, assumptions).get('statement', aid)}'"
            for aid in broken_chain[1:]
        ]
        if len(downstream) == 1:
            parts.append(f", it pulled down {downstream[0]}")
        else:
            parts.append(
                f", it triggered the collapse of "
                f"{', '.join(downstream[:-1])} and {downstream[-1]}"
            )

    consequences: list[str] = []
    if flags.alliance_failure:
        consequences.append("allied support fractured")
    if flags.political_failure:
        consequences.append("political legitimacy eroded")
    if flags.military_failure:
        consequences.append("military effectiveness degraded")
    if flags.escalation_failure:
        consequences.append("escalation spiraled beyond control")

    if consequences:
        parts.append(f", {', '.join(consequences)}")

    parts.append(". Blue's operational assumptions proved fatally optimistic.")
    return "".join(parts)


def trigger(
    ghost_output: GhostOutput,
    game_state: GameState,
    cascade_seed: CascadeSeed,
    assumptions: list[dict[str, Any]],
    current_turn: int,
) -> CascadeOutput:
    adj = _build_adjacency(cascade_seed)

    # Working copy of statuses so we don't mutate the input
    statuses = dict(game_state.assumption_statuses)
    broken_chain: list[str] = []
    stressed_ids: list[str] = []
    patches: dict[str, AssumptionPatch] = {}

    # ── Step 1: apply stress_events from Ghost ───────────────────────────────
    for event in ghost_output.stress_events:
        aid = event.assumption_id
        current_status = statuses.get(aid)
        if current_status not in ("untested", "stressed"):
            continue                                     # already broken or not in play

        if event.severity >= _BREAK_SEVERITY:
            statuses[aid] = "broken"
            broken_chain.append(aid)
            patches[aid] = AssumptionPatch(id=aid, status="broken", turn_broken=current_turn)
        elif event.severity >= _STRESS_SEVERITY:
            statuses[aid] = "stressed"
            stressed_ids.append(aid)
            patches[aid] = AssumptionPatch(id=aid, status="stressed")

    # ── Step 2: BFS propagation from broken nodes ────────────────────────────
    queue: deque[str] = deque(broken_chain.copy())
    visited: set[str] = set(broken_chain)

    while queue:
        current = queue.popleft()
        for neighbor_id, weight, delay_turns in adj.get(current, []):
            if neighbor_id in visited:
                continue
            visited.add(neighbor_id)

            current_status = statuses.get(neighbor_id)
            if current_status not in ("untested", "stressed"):
                continue

            if delay_turns > 0:
                # Schedule deferred — mark stressed now
                statuses[neighbor_id] = "stressed"
                stressed_ids.append(neighbor_id)
                patches[neighbor_id] = AssumptionPatch(id=neighbor_id, status="stressed")
                continue

            if weight >= _CASCADE_BREAK_WEIGHT:
                statuses[neighbor_id] = "broken"
                broken_chain.append(neighbor_id)
                patches[neighbor_id] = AssumptionPatch(
                    id=neighbor_id, status="broken", turn_broken=current_turn
                )
                queue.append(neighbor_id)               # propagate further downstream

            elif weight >= _CASCADE_STRESS_WEIGHT:
                statuses[neighbor_id] = "stressed"
                stressed_ids.append(neighbor_id)
                patches[neighbor_id] = AssumptionPatch(id=neighbor_id, status="stressed")

    # ── Step 3: amplify metric deltas based on cascade depth ─────────────────
    # Exclude primary; clamp to 0 so no-cascade case keeps amplification = 1.0
    cascade_breaks = max(0, len(broken_chain) - 1)
    amplification = min(1.0 + cascade_breaks * _AMPLIFY_PER_CASCADE, _MAX_AMPLIFY)
    metric_deltas: dict[str, int] = {
        k: int(v * amplification)
        for k, v in ghost_output.proposed_metric_deltas.items()
    }

    # ── Step 4: failure flags ─────────────────────────────────────────────────
    failure_flags = _compute_failure_flags(
        broken_chain, metric_deltas, ghost_output.escalation_level, assumptions
    )

    # ── Step 5: status ────────────────────────────────────────────────────────
    active_after = [
        aid for aid, s in statuses.items() if s in ("untested", "stressed")
    ]
    projected_strength = (
        game_state.metrics.blue_strength + metric_deltas.get("blue_strength", 0)
    )
    if not active_after or projected_strength <= 0:
        status = "failed"
    else:
        status = "active"

    narrative = _build_narrative(broken_chain, stressed_ids, failure_flags, assumptions)

    return CascadeOutput(
        updated_assumptions=list(patches.values()),
        broken_chain=broken_chain,
        metric_deltas=metric_deltas,
        cascade_narrative=narrative,
        failure_flags=failure_flags,
        status=status,
    )


def apply_delta(game_state: GameState, cascade_output: CascadeOutput) -> GameState:
    """Returns a new GameState with cascade effects applied. Pure — no mutation."""
    gs = deepcopy(game_state)

    # Apply metric deltas
    for key, delta in cascade_output.metric_deltas.items():
        if hasattr(gs.metrics, key):
            setattr(gs.metrics, key, getattr(gs.metrics, key) + delta)

    # Apply assumption patches
    for patch in cascade_output.updated_assumptions:
        gs.assumption_statuses[patch.id] = patch.status

    # Fire deferred breaks whose turn has now arrived
    due = [aid for aid, fire_turn in gs.pending_breaks.items() if fire_turn <= gs.turn]
    for aid in due:
        gs.assumption_statuses[aid] = "broken"
        del gs.pending_breaks[aid]

    # Game-over check
    active = [
        aid for aid, s in gs.assumption_statuses.items() if s in ("untested", "stressed")
    ]
    gs.game_over = gs.metrics.blue_strength <= 0 or not active
    if gs.game_over:
        gs.winner = "red"

    return gs
