from __future__ import annotations

from collections import Counter
from typing import Any

from game_state import GameState

try:
    from llm_client import call_llm
except Exception:  # pragma: no cover - local/offline fallback.
    call_llm = None

PROMPT = """You are writing a WARBREAK mission debrief for a non-technical commander.
Use plain English. Avoid jargon. No long doctrine paragraphs.

Write exactly 5 short sections:
== BOTTOM LINE ==
One sentence.

== WHAT BROKE ==
Three bullets.

== WHY IT MATTERED ==
Three bullets.

== REAL-WORLD ECHO ==
Name a comparable historical pattern, but do not overclaim it is identical.

== BETTER NEXT PLAN ==
Three concrete changes.

Original plan: {plan}
History: {history}
Ranked assumptions: {assumptions}
Final metrics: {metrics}
"""


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _event_summary(event: Any) -> dict[str, Any]:
    return {
        "turn": _value(event, "turn", 0),
        "blue_move": _value(event, "blue_move", ""),
        "red_move": _value(event, "red_move", ""),
        "ghost_reasoning": _value(event, "ghost_reasoning", ""),
        "targeted_assumption_id": _value(event, "targeted_assumption_id", ""),
        "broken_chain": list(_value(event, "broken_chain", []) or []),
        "metric_deltas": dict(_value(event, "metric_deltas", {}) or {}),
    }


def _rank_score(assumption: Any, targeted_count: int, broken_count: int) -> int:
    fragility = float(_value(assumption, "fragility", 0) or 0)
    criticality = float(_value(assumption, "criticality", 0) or 0)
    dependency_count = len(_value(assumption, "dependencies", []) or [])
    status = str(_value(assumption, "status", "untested") or "untested")
    status_bonus = {"broken": 28, "stressed": 18, "validated": -8}.get(status, 8)
    dependency_bonus = min(14, dependency_count * 4)
    targeting_bonus = min(18, targeted_count * 9)
    broken_bonus = min(12, broken_count * 6)

    score = fragility * 0.58 + criticality * 100 * 0.24
    score += status_bonus + dependency_bonus + targeting_bonus + broken_bonus
    return max(0, min(100, int(round(score))))


def _rank_reason(assumption: Any, targeted_count: int, broken_count: int) -> str:
    pieces: list[str] = []
    status = str(_value(assumption, "status", "untested") or "untested")
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
    dependencies = _value(assumption, "dependencies", []) or []
    if dependencies:
        pieces.append(f"it can cascade into {len(dependencies)} linked assumption(s)")
    return "; ".join(pieces) + "."


def _validation_move(category: str) -> str:
    category = category.lower()
    if "logistics" in category or "resource" in category:
        return "Name the minimum sustainment threshold, owner, and backup route before the next move."
    if "alliance" in category or "partner" in category or "permission" in category:
        return "Convert partner support into an explicit go/no-go decision gate."
    if "communications" in category or "digital" in category or "cyber" in category:
        return "Prove the backup communications path and manual fallback before execution."
    if "intelligence" in category or "information" in category:
        return "Define the signal that would disprove the estimate and pause on stale data."
    if "timing" in category:
        return "Add a branch plan for delay, early closure, or missed handoff."
    if "civil" in category:
        return "Validate public movement and messaging through a trusted local channel."
    return "Assign an owner, a validation signal, and a branch plan before committing forces."


def _assumption_summary(
    assumption: Any,
    rank: int,
    targeted_counts: Counter[str],
    broken_counts: Counter[str],
) -> dict[str, Any]:
    assumption_id = str(_value(assumption, "id", f"A{rank}") or f"A{rank}")
    category = str(_value(assumption, "category", "operational") or "operational")
    targeted_count = targeted_counts[assumption_id]
    broken_count = broken_counts[assumption_id]

    return {
        "id": assumption_id,
        "rank": rank,
        "text": _value(assumption, "text", ""),
        "category": category,
        "confidence": _value(assumption, "confidence", 0.55),
        "criticality": _value(assumption, "criticality", 0.55),
        "fragility": _value(assumption, "fragility", 60),
        "basis": _value(assumption, "basis", ""),
        "doctrine_ref": _value(assumption, "doctrine_ref", ""),
        "dependencies": list(_value(assumption, "dependencies", []) or []),
        "cascade_effect": _value(assumption, "cascade_effect", ""),
        "status": _value(assumption, "status", "untested"),
        "turn_broken": _value(assumption, "turn_broken", None),
        "targeted_count": targeted_count,
        "broken_chain_count": broken_count,
        "rank_score": _rank_score(assumption, targeted_count, broken_count),
        "rank_reason": _rank_reason(assumption, targeted_count, broken_count),
        "validation_move": _validation_move(category),
    }


def _fallback_report(ranked: list[dict[str, Any]], status: str) -> str:
    top = ranked[0] if ranked else {}
    top_text = top.get("text") or "the highest-fragility planning assumption"
    verb = "collapsed" if status == "failed" else "remained the main risk"
    return (
        "== BOTTOM LINE ==\n"
        f"The mission outcome was driven by whether Blue protected this assumption: {top_text}.\n\n"
        "== WHAT BROKE ==\n"
        f"- The top-ranked assumption {verb} under adversary pressure.\n"
        "- Blue actions moved forces faster than the validation loop moved evidence.\n"
        "- Linked assumptions inherited risk once the first weak point was stressed.\n\n"
        "== WHY IT MATTERED ==\n"
        "- Fragile assumptions became decision points, not background conditions.\n"
        "- The adversary exploited uncertainty instead of only trading force-on-force.\n"
        "- Recovery became more expensive than early validation.\n\n"
        "== REAL-WORLD ECHO ==\n"
        "- Many planning failures show this pattern: access, timing, logistics, or partner support fails before the visible fight is decisive.\n\n"
        "== BETTER NEXT PLAN ==\n"
        "- Turn the top three assumptions into explicit go/no-go checks.\n"
        "- Give each critical assumption an owner and a disconfirming signal.\n"
        "- Build branches for the first assumption likely to break, not the last one you hope to fix."
    )


def generate_autopsy(state: GameState) -> dict[str, Any]:
    events = [_event_summary(event) for event in getattr(state, "events", [])]
    targeted_counts: Counter[str] = Counter(
        event["targeted_assumption_id"] for event in events if event["targeted_assumption_id"]
    )
    broken_counts: Counter[str] = Counter(
        assumption_id for event in events for assumption_id in event["broken_chain"]
    )

    ranked = [
        _assumption_summary(assumption, index, targeted_counts, broken_counts)
        for index, assumption in enumerate(getattr(state, "assumptions", []) or [], start=1)
    ]
    ranked.sort(key=lambda item: (-item["rank_score"], -int(item.get("fragility") or 0), item["id"]))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    broken = [item for item in ranked if item.get("status") == "broken"]
    stressed = [item for item in ranked if item.get("status") == "stressed"]
    root_pool = broken or stressed or ranked[:3]
    root_causes = [
        f"{item['id']}: {item['text']} ({item['rank_reason']})"
        for item in root_pool[:3]
    ]

    metrics = dict(getattr(state, "metrics", {}) or {})
    status = str(getattr(state, "status", "completed") or "completed")
    report_text = _fallback_report(ranked, status)
    if call_llm and ranked:
        try:
            report_text = call_llm(
                PROMPT.format(
                    plan=getattr(state, "plan", ""),
                    history=events,
                    assumptions=ranked[:6],
                    metrics=metrics,
                ),
                max_tokens=900,
                temperature=0.25,
            )
        except Exception:
            pass

    return {
        "status": status,
        "turns": getattr(state, "turn", 0),
        "assumptions_broken": len(broken),
        "assumptions_stressed": len(stressed),
        "final_metrics": metrics,
        "assumptions": ranked,
        "events": events,
        "root_causes": root_causes,
        "lessons": [
            "Rank assumptions by collapse risk, not by how confidently the plan states them.",
            "Treat high-fragility assumptions as decision gates before each turn.",
            "Use the Ghost Council target list as the adversary's implied attack surface.",
        ],
        "recommendation": (
            "Before the next run, validate or branch the top three assumptions by rank score, "
            "then rehearse the first cascade they can trigger."
        ),
        "report": report_text,
    }
