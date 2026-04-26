from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

try:
    from game_state import GameState
except Exception:  # pragma: no cover - package import path fallback.
    from .game_state import GameState

try:
    from llm_client import call_llm
except Exception:
    try:
        from .llm_client import call_llm
    except Exception:
        call_llm = None


METRIC_LABELS = {
    "intl_opinion": "international opinion",
    "us_domestic": "US support",
    "red_domestic": "red support",
    "allied_confidence": "allied confidence",
    "blue_strength": "blue force",
    "red_strength": "red force",
}

PROMPT = """You are writing a WARBREAK mission debrief for a non-technical commander.
Use plain English. Stay abstract and training-safe. Do not give real-world tactical targeting instructions.

Write exactly 5 short sections:
== BOTTOM LINE ==
One sentence.
== WHAT BROKE ==
Three concise bullets based only on the assumptions and events.
== WHY IT MATTERED ==
Three concise cause-and-effect bullets based on the final metrics.
== REAL-WORLD ECHO ==
Name a comparable historical planning pattern without claiming it is identical.
== BETTER NEXT PLAN ==
Three concrete planning changes.

Original plan: {plan}
Event history: {history}
Ranked assumptions: {assumptions}
Final metrics: {metrics}
"""


def _dump(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return dict(value)
    return {}


def _assumptions(state: GameState) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, item in enumerate(getattr(state, "assumptions", []) or [], start=1):
        data = _dump(item)
        rows.append(
            {
                "id": str(data.get("id") or f"a{index}"),
                "text": str(data.get("text") or "").strip(),
                "category": str(data.get("category") or "operational"),
                "confidence": data.get("confidence", 0),
                "criticality": data.get("criticality", 0),
                "fragility": data.get("fragility", 0),
                "basis": str(data.get("basis") or ""),
                "doctrine_ref": str(data.get("doctrine_ref") or ""),
                "dependencies": list(data.get("dependencies") or []),
                "cascade_effect": str(data.get("cascade_effect") or ""),
                "status": str(data.get("status") or "untested"),
                "turn_broken": data.get("turn_broken"),
            }
        )
    return rows


def _events(state: GameState) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in getattr(state, "events", []) or []:
        data = _dump(item)
        rows.append(
            {
                "turn": data.get("turn", len(rows) + 1),
                "title": str(data.get("title") or ""),
                "description": str(data.get("description") or ""),
                "blue_move": str(data.get("blue_move") or ""),
                "red_move": str(data.get("red_move") or ""),
                "ghost_reasoning": str(data.get("ghost_reasoning") or ""),
                "ghost_state_text": str(data.get("ghost_state_text") or ""),
                "targeted_assumption_id": str(data.get("targeted_assumption_id") or ""),
                "broken_chain": list(data.get("broken_chain") or []),
                "metric_deltas": dict(data.get("metric_deltas") or {}),
                "options": list(data.get("options") or []),
            }
        )
    return rows


def _status_counts(assumptions: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "broken": sum(1 for item in assumptions if item.get("status") == "broken"),
        "stressed": sum(1 for item in assumptions if item.get("status") == "stressed"),
    }


def _safe_float(value: Any, fallback: float = 0) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _validation_move(category: str) -> str:
    value = category.lower()
    if "logistics" in value or "resource" in value or "supply" in value:
        return "Name the minimum sustainment threshold, owner, and backup route before the next move."
    if "alliance" in value or "partner" in value or "permission" in value or "access" in value:
        return "Convert external support into an explicit go/no-go decision gate."
    if "communications" in value or "digital" in value or "cyber" in value:
        return "Prove the backup communications path and manual fallback before execution."
    if "intelligence" in value or "information" in value:
        return "Define the signal that would disprove the estimate and pause on stale data."
    if "timing" in value or "tempo" in value:
        return "Add a branch plan for delay, early closure, or missed handoff."
    if "civil" in value or "public" in value:
        return "Validate public movement and messaging through a trusted local channel."
    return "Assign an owner, a validation signal, and a branch plan before committing forces."


def _rank_reason(item: Dict[str, Any], targeted_count: int, broken_count: int) -> str:
    pieces: List[str] = []
    status = str(item.get("status") or "untested")
    if status == "broken":
        pieces.append("it broke during execution")
    elif status == "stressed":
        pieces.append("the adversary pressured it without fully breaking it")
    else:
        pieces.append("it stayed unvalidated while the plan depended on it")
    if targeted_count:
        pieces.append(f"Ghost Council targeted it {targeted_count} time(s)")
    if broken_count:
        pieces.append(f"it appeared in {broken_count} broken chain event(s)")
    dependencies = item.get("dependencies") or []
    if dependencies:
        pieces.append(f"it can cascade into {len(dependencies)} linked assumption(s)")
    return "; ".join(pieces) + "."


def _rank_score(item: Dict[str, Any], targeted_count: int, broken_count: int) -> int:
    fragility = _safe_float(item.get("fragility"), 0)
    criticality = _safe_float(item.get("criticality"), 0)
    criticality_score = criticality if criticality > 1 else criticality * 100
    dependency_count = len(item.get("dependencies") or [])
    status = str(item.get("status") or "untested")
    status_bonus = {"broken": 28, "stressed": 18, "validated": -8}.get(status, 8)
    score = fragility * 0.58 + criticality_score * 0.24
    score += status_bonus
    score += min(14, dependency_count * 4)
    score += min(18, targeted_count * 9)
    score += min(12, broken_count * 6)
    return max(0, min(100, int(round(score))))


def _first_broken_turn(assumption_id: str, events: List[Dict[str, Any]]) -> Any:
    for event in events:
        if assumption_id in (event.get("broken_chain") or []):
            return event.get("turn")
    return None


def _rank_assumptions(
    assumptions: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    targeted_counts: Counter[str] = Counter(
        str(event.get("targeted_assumption_id") or "")
        for event in events
        if event.get("targeted_assumption_id")
    )
    broken_counts: Counter[str] = Counter(
        str(assumption_id)
        for event in events
        for assumption_id in (event.get("broken_chain") or [])
    )
    ranked: List[Dict[str, Any]] = []

    for index, item in enumerate(assumptions, start=1):
        row = dict(item)
        assumption_id = str(row.get("id") or f"a{index}")
        targeted_count = targeted_counts[assumption_id]
        broken_count = broken_counts[assumption_id]
        status = str(row.get("status") or "untested")

        if broken_count and status != "broken":
            status = "broken"
            row["turn_broken"] = row.get("turn_broken") or _first_broken_turn(assumption_id, events)
        elif targeted_count and status == "untested":
            status = "stressed"

        row["id"] = assumption_id
        row["status"] = status
        row["targeted_count"] = targeted_count
        row["broken_chain_count"] = broken_count
        row["rank_score"] = _rank_score(row, targeted_count, broken_count)
        row["rank_reason"] = _rank_reason(row, targeted_count, broken_count)
        row["validation_move"] = _validation_move(str(row.get("category") or "operational"))
        ranked.append(row)

    ranked.sort(
        key=lambda item: (
            -int(item.get("rank_score") or 0),
            -int(item.get("fragility") or 0),
            str(item.get("id") or ""),
        )
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def _weak_metrics(metrics: Dict[str, Any]) -> List[str]:
    weak: List[str] = []
    for key, label in METRIC_LABELS.items():
        try:
            value = int(metrics.get(key, 50))
        except Exception:
            value = 50
        if value < 50:
            weak.append(f"{label} at {value}")
    return weak


def _root_causes(
    assumptions: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> List[str]:
    causes: List[str] = []
    by_id = {item.get("id"): item for item in assumptions}

    for item in assumptions:
        status = item.get("status")
        if status in {"broken", "stressed"} and item.get("text"):
            prefix = "Broke" if status == "broken" else "Stressed"
            turn = item.get("turn_broken")
            when = f" on turn {turn}" if turn else ""
            causes.append(f"{prefix}{when}: {item['text']}")

    for event in events:
        target = by_id.get(event.get("targeted_assumption_id"))
        if target and target.get("text"):
            causes.append(f"Turn {event.get('turn')}: Red pressure targeted the assumption that {target['text']}")
        elif event.get("red_move"):
            causes.append(f"Turn {event.get('turn')}: Red response shifted pressure to {event['red_move']}")

    for weak in _weak_metrics(metrics):
        causes.append(f"End-state pressure: {weak}")

    deduped: List[str] = []
    for cause in causes:
        if cause and cause not in deduped:
            deduped.append(cause)
    return deduped[:5]


def _lessons(
    assumptions: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> List[str]:
    lessons: List[str] = []

    fragile = sorted(
        [item for item in assumptions if item.get("text")],
        key=lambda item: (int(item.get("rank_score") or 0), int(item.get("fragility") or 0)),
        reverse=True,
    )
    for item in fragile[:2]:
        move = item.get("validation_move") or "validate or branch this assumption"
        lessons.append(f"Validate this before escalation: {item['text']} ({move})")

    for event in events[-2:]:
        if event.get("red_move"):
            lessons.append(f"Build a branch plan for this response pattern: {event['red_move']}")

    for weak in _weak_metrics(metrics)[:2]:
        lessons.append(f"Recover the weak information metric before the next high-risk move: {weak}")

    if not lessons and events:
        latest = events[-1]
        move = latest.get("blue_move") or latest.get("title") or "the last move"
        lessons.append(f"Review the assumptions behind {move} before repeating the sequence.")

    deduped: List[str] = []
    for lesson in lessons:
        if lesson and lesson not in deduped:
            deduped.append(lesson)
    return deduped[:5]


def _recommendation(lessons: List[str], assumptions: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> str:
    if lessons:
        return lessons[0]
    if assumptions:
        highest = max(assumptions, key=lambda item: (int(item.get("rank_score") or 0), int(item.get("fragility") or 0)))
        move = highest.get("validation_move") or "assign an owner and branch plan"
        return f"Start the next run by validating the top-ranked assumption: {highest.get('text', '').strip()} ({move})"
    if events:
        latest = events[-1]
        return f"Start the next run by testing the assumption behind {latest.get('blue_move') or latest.get('title')}."
    return "Run a mission with a concrete plan and at least one executed turn to generate a live autopsy."


def _fallback_report(
    plan: str,
    assumptions: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    root_causes: List[str],
    lessons: List[str],
) -> str:
    bottom = (
        root_causes[0]
        if root_causes
        else "The run did not record enough pressure data to identify a failure chain."
    )
    broken = root_causes[:3] or ["No broken or stressed assumption was recorded in the completed state."]
    mattered = _weak_metrics(metrics)[:3] or ["Final metrics did not record a weak end-state below 50."]
    better = lessons[:3] or [_recommendation(lessons, assumptions, events)]

    def bullets(rows: List[str]) -> str:
        return "\n".join(f"- {row}" for row in rows)

    return "\n".join(
        [
            "== BOTTOM LINE ==",
            bottom,
            "== WHAT BROKE ==",
            bullets(broken),
            "== WHY IT MATTERED ==",
            bullets(mattered),
            "== REAL-WORLD ECHO ==",
            "The pattern resembles planning failures where access, timing, coordination, or public support proved weaker than the plan assumed.",
            "== BETTER NEXT PLAN ==",
            bullets(better),
        ]
    )


def generate_autopsy(state: GameState) -> Dict[str, Any]:
    events = _events(state)
    assumptions = _rank_assumptions(_assumptions(state), events)
    metrics = dict(getattr(state, "metrics", {}) or {})
    counts = _status_counts(assumptions)
    root_causes = _root_causes(assumptions, events, metrics)
    lessons = _lessons(assumptions, events, metrics)
    recommendation = _recommendation(lessons, assumptions, events)

    report_text = ""
    if call_llm:
        try:
            report_text = call_llm(
                PROMPT.format(
                    plan=getattr(state, "plan", ""),
                    history=events,
                    assumptions=assumptions,
                    metrics=metrics,
                ),
                max_tokens=900,
                temperature=0.25,
            )
        except Exception:
            report_text = ""

    if not report_text.strip():
        report_text = _fallback_report(
            getattr(state, "plan", ""),
            assumptions,
            events,
            metrics,
            root_causes,
            lessons,
        )

    turn_count = int(getattr(state, "turn", 0) or len(events))
    status = getattr(state, "status", "active")
    if status == "active" and getattr(state, "max_turns", 0) and turn_count >= int(getattr(state, "max_turns", 0)):
        status = "completed"

    return {
        "status": status,
        "turns": turn_count,
        "assumptions_broken": counts["broken"],
        "assumptions_stressed": counts["stressed"],
        "final_metrics": metrics,
        "assumptions": assumptions,
        "events": events,
        "root_causes": root_causes,
        "recommendation": recommendation,
        "report": report_text,
        "lessons": lessons,
    }
