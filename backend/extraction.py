from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


AssumptionType = Literal["explicit", "hidden", "derived"]
FragilityBand = Literal["low", "medium", "high", "critical"]
AssumptionStatus = Literal["intact"]
CascadeRelationship = Literal["depends_on", "weakens", "blocks_recovery"]
PropagationEffect = Literal["stress", "weaken", "break"]

MAX_ASSUMPTIONS = 12

WEIGHTS = {
    "base_pattern_risk": 0.20,
    "observability_gap": 0.15,
    "mitigation_gap": 0.15,
    "dependency_centrality": 0.15,
    "recovery_difficulty": 0.15,
    "consequence_severity": 0.15,
    "volatility": 0.05,
}

MITIGATION_TERMS = {
    "backup",
    "contingency",
    "fallback",
    "reserve",
    "alternate",
    "alternative",
    "redundant",
    "reroute",
    "reduce scope",
    "workaround",
}

OBSERVABILITY_TERMS = {
    "confirm",
    "indicator",
    "measure",
    "monitor",
    "observe",
    "report",
    "signal",
    "track",
    "validate",
    "verify",
}

CERTAINTY_TERMS = {"will", "must", "always", "guaranteed", "seamless", "rapid", "immediate"}
SINGLE_PATH_TERMS = {"only", "single", "sole", "primary", "all", "entire"}
TIME_TERMS = {"timeline", "schedule", "window", "before", "after", "by", "hour", "day", "phase"}
UNSAFE_REAL_WORLD_TERMS = {
    "actual",
    "civilian facility",
    "evade authorities",
    "real facility",
    "real people",
    "real target",
    "real-world",
    "specific target",
}
UNSAFE_ACTION_TERMS = {
    "ambush",
    "attack",
    "breach",
    "disable",
    "destroy",
    "exploit",
    "harm",
    "kill",
    "sabotage",
    "strike",
    "target",
    "weapon",
}
EDGE_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "before",
    "but",
    "can",
    "for",
    "from",
    "has",
    "have",
    "into",
    "its",
    "mission",
    "not",
    "our",
    "plan",
    "should",
    "that",
    "the",
    "their",
    "them",
    "then",
    "this",
    "through",
    "to",
    "when",
    "while",
    "will",
    "with",
}

SAFE_REPLACEMENTS = (
    (r"\battacks?\b", "stress event"),
    (r"\bassaults?\b", "pressure event"),
    (r"\bstrikes?\b", "disruption"),
    (r"\bdestroys?\b", "degrades"),
    (r"\bkill(?:s|ed|ing)?\b", "stop"),
    (r"\btargets?\b", "focus area"),
    (r"\bweapons?\b", "capabilities"),
    (r"\bexplosives?\b", "hazards"),
    (r"\bambush(?:es)?\b", "disruption"),
    (r"\bbreach(?:es|ed|ing)?\b", "access stress"),
)

CATEGORY_DEPENDENCIES = {
    "access": {"coordination", "permissions", "information", "timing"},
    "actor_cooperation": {"coordination", "communications", "permissions"},
    "communications": {"access", "logistics", "information", "cyber_system", "infrastructure", "resource"},
    "coordination": {"communications", "information", "actor_cooperation"},
    "decision": {"information", "communications", "coordination"},
    "fallback": {"logistics", "coordination", "communications", "access"},
    "information": {"communications", "coordination", "observability"},
    "logistics": {"access", "coordination", "timing", "communications", "infrastructure", "resource", "cyber_system", "partner_support"},
    "observability": {"communications", "information", "coordination"},
    "permissions": {"actor_cooperation", "coordination", "information"},
    "security": {"observability", "coordination", "communications"},
    "timing": {"logistics", "coordination", "communications", "weather_environment", "infrastructure", "partner_support"},
    "weather_environment": {"observability", "timing"},
    "partner_support": {"command_coordination", "communications", "authority_permissions"},
    "intelligence": {"communications", "information_environment", "command_coordination"},
    "civilian_behavior": {"communications", "logistics", "authority_permissions", "escalation", "information_environment", "partner_support"},
    "infrastructure": {"logistics", "authority_permissions", "timing", "resource", "weather_environment"},
    "cyber_system": {"communications", "intelligence", "command_coordination"},
    "escalation": {"information_environment", "command_coordination", "partner_support", "civilian_behavior"},
    "authority_permissions": {"partner_support", "command_coordination", "intelligence"},
    "resource": {"logistics", "timing", "command_coordination", "partner_support"},
    "command_coordination": {"communications", "intelligence", "authority_permissions", "partner_support"},
    "information_environment": {"communications", "cyber_system", "civilian_behavior", "partner_support"},
}

CATEGORY_ALIASES = {
    "access": "infrastructure",
    "actor_cooperation": "partner_support",
    "authority": "authority_permissions",
    "authority_legal": "authority_permissions",
    "coordination": "command_coordination",
    "coalition": "partner_support",
    "coalition_political": "partner_support",
    "command": "command_coordination",
    "communications_assumptions": "communications",
    "civilian": "civilian_behavior",
    "civilian_public": "civilian_behavior",
    "cyber": "cyber_system",
    "decision": "command_coordination",
    "environment": "weather_environment",
    "fallback": "resource",
    "information": "intelligence",
    "legal": "authority_permissions",
    "observability": "information_environment",
    "permissions": "authority_permissions",
    "political": "partner_support",
    "public": "civilian_behavior",
    "security": "escalation",
    "system": "cyber_system",
    "systems": "cyber_system",
    "supplies": "logistics",
    "weather": "weather_environment",
}

ALLOWED_AFFECTED_METRICS = {
    "logistics",
    "tempo",
    "coordination",
    "communications",
    "public_confidence",
    "intelligence_confidence",
    "infrastructure",
    "cyber_availability",
    "escalation_risk",
    "resource_margin",
    "authority_clarity",
    "mission_resilience",
}

GAME_EFFECT_PROFILES = {
    "communications": {
        "title": "Communications Reliability Degraded",
        "sitrep": "A key coordination channel is producing delayed or inconsistent updates. Confidence in shared situational awareness is reduced.",
        "effects": [
            "Coordination tempo decreases",
            "Decision confidence drops",
            "Dependent assumptions become stressed",
        ],
        "prompt": "Do you pause for validation, shift to backup channels, reduce scope, or continue under uncertainty?",
        "metrics": ["communications", "coordination", "tempo", "mission_resilience"],
    },
    "logistics": {
        "title": "Logistics Continuity Stressed",
        "sitrep": "A sustainment or movement dependency is delayed or harder to confirm. Resource timing and mission resilience are reduced.",
        "effects": [
            "Resource margin decreases",
            "Tempo slows around dependent tasks",
            "Fallback demand increases",
        ],
        "prompt": "Do you reroute support, reduce resource demand, wait for validation, or continue under uncertainty?",
        "metrics": ["logistics", "resource_margin", "tempo", "mission_resilience"],
    },
    "infrastructure": {
        "title": "Infrastructure Availability Uncertain",
        "sitrep": "A route, facility, or access point is not as available as planned. Dependent movement and staging assumptions are stressed.",
        "effects": [
            "Infrastructure confidence drops",
            "Logistics tempo decreases",
            "Dependent assumptions become stressed",
        ],
        "prompt": "Do you validate access, reroute, stage only critical tasks, or reduce scope?",
        "metrics": ["infrastructure", "logistics", "tempo", "mission_resilience"],
    },
    "timing": {
        "title": "Timing Synchronization Slips",
        "sitrep": "A planned window or phase gate is delayed. The team has less slack to validate dependent assumptions.",
        "effects": [
            "Tempo decreases",
            "Decision debt rises",
            "Coordination pressure increases",
        ],
        "prompt": "Do you pause for validation, resequence tasks, reduce scope, or continue under time pressure?",
        "metrics": ["tempo", "coordination", "mission_resilience"],
    },
    "command_coordination": {
        "title": "Command Coordination Stressed",
        "sitrep": "Ownership, handoff timing, or decision alignment is less clear than planned. Coordination quality and tempo are reduced.",
        "effects": [
            "Coordination clarity drops",
            "Decision confidence decreases",
            "Dependent handoffs become stressed",
        ],
        "prompt": "Do you name an owner, pause for validation, simplify handoffs, or continue under uncertainty?",
        "metrics": ["coordination", "tempo", "mission_resilience"],
    },
    "intelligence": {
        "title": "Intelligence Confidence Degraded",
        "sitrep": "A key estimate or status picture is stale, incomplete, or harder to verify. Decision confidence is reduced.",
        "effects": [
            "Intelligence confidence drops",
            "Decision debt rises",
            "Conservative branches become more attractive",
        ],
        "prompt": "Do you wait for validation, choose a conservative branch, reduce scope, or continue under uncertainty?",
        "metrics": ["intelligence_confidence", "coordination", "mission_resilience"],
    },
    "partner_support": {
        "title": "Partner Support Delayed",
        "sitrep": "External support or alignment is delayed or less certain. Dependent timing, authority, and resource assumptions are stressed.",
        "effects": [
            "Coordination tempo decreases",
            "Resource margin tightens",
            "Authority clarity may decrease",
        ],
        "prompt": "Do you coordinate a reduced-scope branch, wait for confirmation, reroute support, or continue under uncertainty?",
        "metrics": ["coordination", "resource_margin", "authority_clarity", "mission_resilience"],
    },
    "authority_permissions": {
        "title": "Authority And Permissions Unclear",
        "sitrep": "Approval or permission confidence is lower than planned. Dependent tasks may need to pause or shift to an approved branch.",
        "effects": [
            "Authority clarity drops",
            "Decision debt rises",
            "Dependent tasks may be delayed",
        ],
        "prompt": "Do you pause for validation, use an approved branch, reduce scope, or coordinate clarification?",
        "metrics": ["authority_clarity", "coordination", "tempo", "mission_resilience"],
    },
    "resource": {
        "title": "Resource Sufficiency Stressed",
        "sitrep": "Personnel, equipment, time, or reserve capacity is tighter than planned. Resource margin and resilience are reduced.",
        "effects": [
            "Resource margin decreases",
            "Mission resilience drops",
            "Prioritization pressure increases",
        ],
        "prompt": "Do you prioritize critical tasks, reduce scope, release reserves, or wait for validation?",
        "metrics": ["resource_margin", "logistics", "mission_resilience"],
    },
    "cyber_system": {
        "title": "Cyber System Availability Degraded",
        "sitrep": "A digital system or data service is delayed, stale, or less trustworthy. Manual validation may be needed.",
        "effects": [
            "Cyber availability decreases",
            "Communications confidence drops",
            "Decision tempo slows",
        ],
        "prompt": "Do you shift to manual validation, use a reduced-digital workflow, pause dependent tasks, or continue under uncertainty?",
        "metrics": ["cyber_availability", "communications", "tempo", "mission_resilience"],
    },
    "civilian_behavior": {
        "title": "Civilian/Public Behavior Less Predictable",
        "sitrep": "Public demand, access behavior, or civil coordination signals are less predictable than planned. Public confidence is stressed.",
        "effects": [
            "Public confidence decreases",
            "Coordination demand increases",
            "Access assumptions become stressed",
        ],
        "prompt": "Do you coordinate with civil partners, monitor indicators, reduce access scope, or continue under uncertainty?",
        "metrics": ["public_confidence", "coordination", "tempo", "mission_resilience"],
    },
    "weather_environment": {
        "title": "Weather/Environment Stability Degraded",
        "sitrep": "Environmental conditions are moving outside the assumed planning range. Timing, movement, and observation confidence decrease.",
        "effects": [
            "Tempo decreases",
            "Logistics confidence drops",
            "Dependent assumptions become stressed",
        ],
        "prompt": "Do you validate conditions, delay movement, reroute, reduce exposed tasks, or continue under uncertainty?",
        "metrics": ["tempo", "logistics", "mission_resilience"],
    },
    "escalation": {
        "title": "Escalation Containment Stressed",
        "sitrep": "A local disruption or misunderstanding is creating broader uncertainty. Coordination burden and escalation risk increase.",
        "effects": [
            "Escalation risk increases",
            "Coordination demand rises",
            "Decision confidence drops",
        ],
        "prompt": "Do you clarify constraints, reduce scope, coordinate review, wait for validation, or continue under uncertainty?",
        "metrics": ["escalation_risk", "coordination", "mission_resilience"],
    },
    "information_environment": {
        "title": "Information Environment Stability Degraded",
        "sitrep": "Public messaging, perception, or rumor signals are less stable than planned. Confidence and coordination quality are reduced.",
        "effects": [
            "Public confidence decreases",
            "Decision confidence drops",
            "Coordination demand increases",
        ],
        "prompt": "Do you validate information indicators, coordinate messaging, reduce scope, or continue under uncertainty?",
        "metrics": ["public_confidence", "intelligence_confidence", "coordination", "mission_resilience"],
    },
}


class FoglineAnalyzeRequest(BaseModel):
    plan_text: str = Field(..., min_length=1)
    scenario_name: Optional[str] = None
    domain: Optional[str] = None
    actors: Optional[List[str]] = None
    timeline: Optional[str] = None
    mission_objective: Optional[str] = None


class ScoreBreakdown(BaseModel):
    base_pattern_risk: float
    observability_gap: float
    mitigation_gap: float
    dependency_centrality: float
    recovery_difficulty: float
    consequence_severity: float
    volatility: float


class BreakEventTemplate(BaseModel):
    title: str
    sitrep: str
    immediate_effects: List[str]
    player_decision_prompt: str


class GameEffects(BaseModel):
    resilience_delta: int
    decision_debt_delta: int
    affected_metrics: List[str]


class FoglineAssumption(BaseModel):
    id: str
    text: str
    type: AssumptionType
    category: str
    fragility_score: float
    fragility_band: FragilityBand
    score_breakdown: ScoreBreakdown
    evidence_span: str
    why_it_matters: str
    pattern_id: str
    why_this_pattern_matches: str
    risk_factors_detected: List[str]
    missing_mitigations: List[str]
    monitoring_indicators: List[str]
    resilience_patches: List[str]
    validation_questions: List[str]
    fallback_options: List[str]
    rewrite_suggestion: str
    dependency_hints: List[str]
    status: AssumptionStatus = "intact"
    confidence: float
    break_event_template: BreakEventTemplate
    game_effects: GameEffects
    autopsy_tags: List[str]


class FoglineSummary(BaseModel):
    total_assumptions: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    average_fragility_score: float
    top_fragility_ids: List[str]
    dominant_categories: List[str]
    compiler_mode: str
    catalog_version: str


class FoglineGraphNode(BaseModel):
    id: str
    label: str
    category: str
    fragility_score: float
    fragility_band: FragilityBand
    status: AssumptionStatus = "intact"


class FoglineGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: CascadeRelationship
    strength: float
    reason: str
    rationale: Optional[str] = None


class FoglineGraph(BaseModel):
    nodes: List[FoglineGraphNode]
    edges: List[FoglineGraphEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FoglineEvidenceCard(BaseModel):
    id: str
    category: str
    description: str
    risk_factors: List[str]
    observable_indicators: List[str]
    mitigation_patterns: List[str]
    base_fragility: float
    safe_historical_analog_summary: str
    doctrine_note: str
    matched_keywords: List[str] = Field(default_factory=list)


class GhostCouncilCandidate(BaseModel):
    assumption_id: str
    text: str
    fragility_score: float
    fragility_band: FragilityBand
    why_it_matters: str
    validation_questions: List[str]
    resilience_patches: List[str]


class GhostCouncilPriorityTarget(BaseModel):
    assumption_id: str
    reason_to_target: str
    fragility_score: float
    expected_cascade: List[str]
    prospect_theory_trigger: str
    safe_pressure_frame: str


class GhostCouncilSeed(BaseModel):
    priority_targets: List[GhostCouncilPriorityTarget]
    red_team_guidance: List[str]
    focus_assumption_ids: List[str]
    candidates: List[GhostCouncilCandidate]
    briefing: str


class CascadeEdgeSeed(BaseModel):
    source: str
    target: str
    strength: float
    rationale: str


class CascadeCriticalPath(BaseModel):
    root_assumption_id: str
    cascade_path: List[str]
    risk_explanation: str


class CascadePropagationRule(BaseModel):
    source: str
    target: str
    effect: PropagationEffect
    threshold: float
    delay_ms: int = 400
    reason: str


class CascadeSeed(BaseModel):
    break_order: List[str]
    critical_paths: List[CascadeCriticalPath]
    propagation_rules: List[CascadePropagationRule]
    root_assumption_ids: List[str]
    edge_strengths: List[CascadeEdgeSeed]
    dependency_graph: FoglineGraph


class AutopsyRankItem(BaseModel):
    rank: int
    assumption_id: str
    fragility_score: float
    fragility_band: FragilityBand
    autopsy_tags: List[str]
    failure_chain_metadata: Dict[str, str]


class AutopsyRankedAssumption(BaseModel):
    assumption_id: str
    rank: int
    reason: str
    fragility_score: float
    category: str


class AutopsyPatchCandidate(BaseModel):
    assumption_id: str
    rewrite_suggestion: str
    monitoring_indicators: List[str]
    fallback_options: List[str]
    validation_questions: List[str]


class AutopsySeed(BaseModel):
    ranked_assumptions: List[AutopsyRankedAssumption]
    audit_fields: List[str]
    resilience_patch_candidates: List[AutopsyPatchCandidate]
    better_plan_principles: List[str]
    assumption_rank: List[AutopsyRankItem]
    decision_audit_fields: List[str]
    legacy_resilience_patch_candidates: List[str] = Field(default_factory=list)


class FoglineAnalyzeResponse(BaseModel):
    scenario_name: str
    mission_objective: str
    evidence_cards: List[FoglineEvidenceCard]
    assumptions: List[FoglineAssumption]
    summary: FoglineSummary
    graph_seed: FoglineGraph
    ghost_council_seed: GhostCouncilSeed
    cascade_seed: CascadeSeed
    autopsy_seed: AutopsySeed
    warnings: List[str]


def analyze_plan(request: FoglineAnalyzeRequest) -> FoglineAnalyzeResponse:
    """Compile a free-text plan into transparent FOGLINE assumptions and seeds."""
    catalog = load_evidence_catalog()
    warnings: List[str] = []
    compiler_mode = "fallback"

    if _is_unsafe_real_world_request(request.plan_text):
        return _safe_scope_refusal_response(request, catalog)

    candidates: List[Dict[str, Any]] = []
    if not _truthy_env("FOGLINE_DISABLE_LLM"):
        llm_candidates, llm_warning = _extract_with_anthropic(request, catalog)
        if llm_warning:
            warnings.append(llm_warning)
        if llm_candidates:
            compiler_mode = "anthropic"
            candidates = llm_candidates
    else:
        warnings.append("Anthropic extraction skipped because FOGLINE_DISABLE_LLM is set.")

    fallback_candidates = _extract_with_heuristics(request, catalog)
    if not candidates:
        candidates = fallback_candidates
    else:
        before = len(candidates)
        candidates = _dedupe_candidates(candidates + _derived_candidates(request, catalog), MAX_ASSUMPTIONS)
        if len(candidates) > before:
            compiler_mode = "hybrid"

    if not candidates:
        candidates = _derived_candidates(request, catalog)
        warnings.append("No direct assumptions were detected; generated derived assumptions from plan metadata.")

    evidence_cards = [
        FoglineEvidenceCard(**card)
        for card in build_rag_context(request.plan_text, catalog)
    ]
    assumptions, graph = _score_and_build(candidates[:MAX_ASSUMPTIONS], request, catalog)
    assumptions = sorted(assumptions, key=lambda item: (-item.fragility_score, item.id))
    assumptions = _renumber_assumptions(assumptions, graph)

    summary = _build_summary(assumptions, compiler_mode, catalog.get("catalog_version", "unknown"))
    graph = _build_graph(assumptions, _build_edges_from_assumptions(assumptions))
    ghost_seed = _build_ghost_seed(assumptions, graph)
    cascade_seed = _build_cascade_seed(assumptions, graph)
    autopsy_seed = _build_autopsy_seed(assumptions)

    if compiler_mode == "fallback" and not any("Anthropic" in warning for warning in warnings):
        warnings.append("Anthropic extraction unavailable; used deterministic fallback heuristics.")
    warnings.append("Scores are rubric-based and do not claim exact historical statistics.")

    return FoglineAnalyzeResponse(
        scenario_name=_safe_text(request.scenario_name or "Unnamed Scenario"),
        mission_objective=_infer_objective(request),
        evidence_cards=evidence_cards,
        assumptions=assumptions,
        summary=summary,
        graph_seed=graph,
        ghost_council_seed=ghost_seed,
        cascade_seed=cascade_seed,
        autopsy_seed=autopsy_seed,
        warnings=_dedupe_strings(warnings),
    )


def _is_unsafe_real_world_request(plan_text: str) -> bool:
    lowered = plan_text.lower()
    has_real_world_scope = any(term in lowered for term in UNSAFE_REAL_WORLD_TERMS)
    has_unsafe_action = any(re.search(rf"\b{re.escape(term)}(?:s|ed|ing)?\b", lowered) for term in UNSAFE_ACTION_TERMS)
    has_targeting_phrase = bool(
        re.search(
            r"\b(?:plan|help|how)\b.*\b(?:target|attack|disable|destroy|harm|evade)\b",
            lowered,
            flags=re.DOTALL,
        )
    )
    return has_unsafe_action and (has_real_world_scope or has_targeting_phrase)


def _safe_scope_refusal_response(
    request: FoglineAnalyzeRequest, catalog: Dict[str, Any]
) -> FoglineAnalyzeResponse:
    summary = FoglineSummary(
        total_assumptions=0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        average_fragility_score=0,
        top_fragility_ids=[],
        dominant_categories=[],
        compiler_mode="safe_scope_refusal",
        catalog_version=catalog.get("catalog_version", "unknown"),
    )
    graph = FoglineGraph(
        nodes=[],
        edges=[],
        metadata={
            "node_count": 0,
            "edge_count": 0,
            "edge_strength_scale": "0.0-1.0 rubric",
            "scope_gate": "unsafe_real_world_targeting_request",
        },
    )
    ghost = GhostCouncilSeed(
        priority_targets=[],
        red_team_guidance=[
            "Scope gate refused real-world targeting content.",
            "Use fictional, unclassified training scenarios with abstract pressure and validation language.",
        ],
        focus_assumption_ids=[],
        candidates=[],
        briefing="No Ghost Council seed generated because the request was outside the safe training scope.",
    )
    cascade = CascadeSeed(
        break_order=[],
        critical_paths=[],
        propagation_rules=[],
        root_assumption_ids=[],
        edge_strengths=[],
        dependency_graph=graph,
    )
    autopsy = AutopsySeed(
        ranked_assumptions=[],
        audit_fields=[
            "assumption_id",
            "original_status",
            "break_turn",
            "player_response",
            "new_assumptions_created",
            "resilience_delta",
            "decision_debt_delta",
            "final_status",
        ],
        resilience_patch_candidates=[],
        better_plan_principles=[
            "Use fictional training scenarios.",
            "Keep pressure frames abstract and non-operational.",
            "Validate assumptions before phase transitions.",
            "Define thresholds for delaying or reducing scope.",
        ],
        assumption_rank=[],
        decision_audit_fields=[
            "assumption_id",
            "original_status",
            "break_turn",
            "player_response",
            "new_assumptions_created",
            "resilience_delta",
            "decision_debt_delta",
            "final_status",
        ],
        legacy_resilience_patch_candidates=[],
    )
    return FoglineAnalyzeResponse(
        scenario_name=_safe_text(request.scenario_name or "Out Of Scope Request"),
        mission_objective="Request refused: FOGLINE only analyzes fictional, unclassified training scenarios.",
        evidence_cards=[],
        assumptions=[],
        summary=summary,
        graph_seed=graph,
        ghost_council_seed=ghost,
        cascade_seed=cascade,
        autopsy_seed=autopsy,
        warnings=[
            "Safe scope gate: refused unsafe real-world targeting request.",
            "Provide a fictional, unclassified training plan using abstract pressure, validation, fallback, and coordination language.",
        ],
    )


def load_evidence_catalog() -> Dict[str, Any]:
    catalog_path = Path(__file__).with_name("evidence_catalog.json")
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        catalog = _embedded_evidence_catalog()
    return _normalize_catalog(catalog)


def _load_evidence_catalog() -> Dict[str, Any]:
    return load_evidence_catalog()


def match_assumption_to_pattern(
    assumption_text: str, category: str, catalog: Dict[str, Any]
) -> Dict[str, Any]:
    normalized = _normalize_catalog(catalog)
    pattern, matched_keywords = _match_pattern(assumption_text, normalized, category)
    result = dict(pattern)
    result["matched_keywords"] = matched_keywords
    result["why_this_pattern_matches"] = _match_reason_for_pattern(
        assumption_text, category, pattern, matched_keywords
    )
    return result


def build_rag_context(plan_text: str, catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    normalized = _normalize_catalog(catalog)
    cards = normalized.get("pattern_cards", [])
    scored_cards = [
        (_card_match_score(plan_text, card), card)
        for card in cards
        if isinstance(card, dict)
    ]
    scored_cards.sort(key=lambda item: (-item[0], str(item[1].get("id", ""))))

    selected = [card for score, card in scored_cards if score > 0][:8]
    if len(selected) < 5:
        for _score, card in scored_cards:
            if card not in selected:
                selected.append(card)
            if len(selected) >= 5:
                break

    compact_cards = [_compact_evidence_card(card, plan_text) for card in selected]
    payload = json.dumps(compact_cards, separators=(",", ":"))
    while len(payload) > 4200 and len(compact_cards) > 3:
        compact_cards.pop()
        payload = json.dumps(compact_cards, separators=(",", ":"))
    return compact_cards


def _embedded_evidence_catalog() -> Dict[str, Any]:
    return {
        "catalog_version": "embedded-evidence-card-v1",
        "description": "Embedded fallback evidence card. Qualitative only; no precise statistical failure rates.",
        "pattern_cards": [
            {
                "id": "command_coordination",
                "category": "command_coordination",
                "description": "Assumptions that command relationships, responsibilities, and decision ownership remain clear.",
                "risk_factors": ["decision ownership may be unclear", "handoffs can fail without confirmation"],
                "observable_indicators": ["missed handoff", "unassigned task owner", "late decision request"],
                "mitigation_patterns": ["name owners for critical assumptions", "add decision review checkpoints"],
                "base_fragility": 68,
                "safe_historical_analog_summary": "Command and coordination assumptions can fail when roles and decision paths are unclear.",
                "doctrine_note": "Assumptions require validation by named owners.",
                "rag_keywords": ["command", "coordinate", "decision", "owner", "handoff", "team"],
            }
        ],
    }


def _normalize_catalog(catalog: Dict[str, Any]) -> Dict[str, Any]:
    if catalog.get("_normalized_for_fogline"):
        return catalog

    cards = [card for card in catalog.get("pattern_cards", []) if isinstance(card, dict)]
    if not cards and catalog.get("patterns"):
        cards = [_legacy_pattern_to_card(pattern) for pattern in catalog.get("patterns", []) if isinstance(pattern, dict)]
    if not cards:
        cards = _embedded_evidence_catalog()["pattern_cards"]

    normalized_cards = [_normalize_card(card) for card in cards]
    normalized = dict(catalog)
    normalized["pattern_cards"] = normalized_cards
    normalized["patterns"] = [_card_to_pattern(card) for card in normalized_cards]
    normalized["_normalized_for_fogline"] = True
    return normalized


def _normalize_card(card: Dict[str, Any]) -> Dict[str, Any]:
    card_id = _safe_identifier(str(card.get("id") or card.get("pattern_id") or "command_coordination"))
    category = _canonical_category(str(card.get("category") or "command_coordination"))
    base_fragility = _clamp_float(card.get("base_fragility", card.get("base_pattern_risk", 60)), 0, 100)
    return {
        "id": card_id,
        "category": category,
        "description": _safe_text(card.get("description") or card.get("why_it_matters") or "Planning assumption requires validation."),
        "risk_factors": _safe_plain_list(card.get("risk_factors", []), 6),
        "observable_indicators": _safe_plain_list(
            card.get("observable_indicators", card.get("monitoring_indicators", [])), 6
        ),
        "mitigation_patterns": _safe_plain_list(
            card.get("mitigation_patterns", card.get("resilience_patches", [])), 6
        ),
        "base_fragility": round(base_fragility, 1),
        "safe_historical_analog_summary": _safe_text(
            card.get("safe_historical_analog_summary")
            or "Planning assumptions can fail when validation, timing, or coordination are weak."
        ),
        "doctrine_note": _safe_text(
            card.get("doctrine_note")
            or "Assumptions require validation, and uncertainty must be actively monitored."
        ),
        "rag_keywords": _safe_plain_list(card.get("rag_keywords", card.get("keywords", [])), 16),
    }


def _card_to_pattern(card: Dict[str, Any]) -> Dict[str, Any]:
    base = _clamp_float(card.get("base_fragility", 60), 0, 100)
    category = _canonical_category(str(card.get("category", "command_coordination")))
    recovery_adjustment = 8 if category in {"logistics", "infrastructure", "authority_permissions"} else 0
    severity_adjustment = 7 if category in {"communications", "command_coordination", "intelligence"} else 0
    volatility_adjustment = 12 if category in {"weather_environment", "information_environment", "partner_support"} else 0
    return {
        **card,
        "pattern_id": card["id"],
        "base_pattern_risk": base,
        "recovery_difficulty": _clamp_float(base + recovery_adjustment, 0, 100),
        "consequence_severity": _clamp_float(base + severity_adjustment, 0, 100),
        "volatility": _clamp_float(base - 8 + volatility_adjustment, 0, 100),
        "keywords": card.get("rag_keywords", []),
        "dependency_hints": sorted(CATEGORY_DEPENDENCIES.get(category, set())),
        "missing_mitigations": card.get("mitigation_patterns", []),
        "monitoring_indicators": card.get("observable_indicators", []),
        "resilience_patches": card.get("mitigation_patterns", []),
        "validation_questions": _validation_questions_for_card(card),
        "fallback_options": _fallback_options_for_category(category),
        "why_it_matters": card.get("description", ""),
        "why_this_pattern_matches": (
            f"{card.get('description', 'This evidence card matches the assumption')} "
            f"Analog: {card.get('safe_historical_analog_summary', '')}"
        ).strip(),
    }


def _legacy_pattern_to_card(pattern: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _safe_identifier(str(pattern.get("pattern_id") or "command_coordination")),
        "category": pattern.get("category", "command_coordination"),
        "description": pattern.get("why_it_matters", "Planning assumption requires validation."),
        "risk_factors": pattern.get("risk_factors", []),
        "observable_indicators": pattern.get("monitoring_indicators", []),
        "mitigation_patterns": pattern.get("resilience_patches", pattern.get("missing_mitigations", [])),
        "base_fragility": pattern.get("base_pattern_risk", 60),
        "safe_historical_analog_summary": "Planning assumptions can fail when validation, timing, or coordination are weak.",
        "doctrine_note": "Assumptions require validation, and uncertainty must be actively monitored.",
        "rag_keywords": pattern.get("keywords", []),
    }


def _extract_with_anthropic(
    request: FoglineAnalyzeRequest, catalog: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        return [], "Anthropic API key missing; used deterministic fallback heuristics."

    try:
        import anthropic
    except ImportError:
        return [], "Anthropic package missing; used deterministic fallback heuristics."

    evidence_cards = build_rag_context(request.plan_text, catalog)

    system_prompt = (
        "You are FOGLINE's planning-assumption analyst for fictional, unclassified training scenarios. "
        "Extract assumptions embedded in the user's plan and find what the plan requires to be true "
        "but does not verify. Separate explicit assumptions stated in the plan, hidden assumptions the "
        "plan depends on, and derived assumptions implied by dependencies or missing checks. Return "
        "strict JSON only with no markdown, no prose wrapper, and no comments. Keep all outputs "
        "training-safe and abstract. Do not produce real-world tactical recommendations. Do not mention "
        "classified material, real-world operational details, exact historical failure rates, or precise "
        "statistics. Use safe language such as stress, degrade, delay, disrupt, validate, fallback, "
        "monitor, coordinate, reroute, and reduce scope."
    )
    user_prompt = {
        "task": "Extract planning assumptions for FOGLINE. Aim for 10-14 assumptions when the plan is detailed enough.",
        "scenario_name": request.scenario_name,
        "domain": request.domain,
        "actors": request.actors or [],
        "timeline": request.timeline,
        "mission_objective": request.mission_objective,
        "plan_text": request.plan_text,
        "evidence_cards": evidence_cards,
        "assumption_categories_to_check": [
            "logistics",
            "communications",
            "coalition_political",
            "intelligence",
            "infrastructure",
            "civilian_public",
            "weather_environment",
            "cyber_system",
            "timing",
            "escalation",
            "authority_legal",
            "resource",
            "command_coordination",
        ],
        "scoring_instruction": (
            "Suggest score components only as analyst hints. The application will ignore direct LLM "
            "scores for final scoring and recompute deterministic rubric scores in Python."
        ),
        "safety_constraints": [
            "No real-world tactical recommendations.",
            "No classified or real-world operational details.",
            "No precise statistical failure rates.",
            "Training-safe and abstract language only.",
        ],
        "return_shape": {
            "assumptions": [
                {
                    "text": "assumption text",
                    "type": "explicit | hidden | derived",
                    "category": "logistics | communications | coalition_political | intelligence | infrastructure | civilian_public | weather_environment | cyber_system | timing | escalation | authority_legal | resource | command_coordination",
                    "evidence_span": "short source span",
                    "why_it_matters": "short training-safe consequence statement",
                    "candidate_pattern_id": "one evidence card id",
                    "risk_factors_detected": ["short safe phrases"],
                    "missing_mitigations": ["short safe phrases"],
                    "dependency_hints": ["category names this depends on"],
                    "suggested_score_components": {
                        "base_pattern_risk": 0,
                        "observability_gap": 0,
                        "mitigation_gap": 0,
                        "dependency_centrality": 0,
                        "recovery_difficulty": 0,
                        "consequence_severity": 0,
                        "volatility": 0,
                    },
                    "confidence": 0.0,
                }
            ],
            "mission_objective_detected": "short objective or empty string",
            "warnings": ["short parser warning strings"],
        },
    }

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=20.0)
        message = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            max_tokens=2400,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_prompt)}],
        )
        text = _anthropic_text(message)
        payload, repair_warning = _parse_llm_json_with_repair(text)
        if repair_warning:
            return [], repair_warning
        raw_items = payload.get("assumptions", []) if isinstance(payload, dict) else []
        candidates = [_coerce_candidate(item, request, catalog, "anthropic") for item in raw_items]
        model_warnings = [
            _safe_text(str(warning))
            for warning in payload.get("warnings", [])
            if isinstance(warning, (str, int, float))
        ]
        warning_text = "; ".join(model_warnings[:3]) if model_warnings else None
        return _dedupe_candidates([item for item in candidates if item], MAX_ASSUMPTIONS), warning_text
    except Exception as exc:  # noqa: BLE001 - LLM failure must not break fallback.
        return [], f"Anthropic extraction failed; used deterministic fallback heuristics. Reason: {type(exc).__name__}."


def _anthropic_text(message: Any) -> str:
    chunks: List[str] = []
    for part in getattr(message, "content", []) or []:
        value = getattr(part, "text", None)
        if value:
            chunks.append(value)
        elif isinstance(part, dict) and part.get("text"):
            chunks.append(str(part["text"]))
    return "\n".join(chunks)


def _parse_json_object(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    if "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.index("{") : cleaned.rindex("}") + 1]
    payload = json.loads(cleaned)
    return payload if isinstance(payload, dict) else {}


def _parse_llm_json_with_repair(text: str) -> Tuple[Dict[str, Any], Optional[str]]:
    for candidate in (text.strip(), _strip_markdown_fences(text)):
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload, None
        return {}, "Anthropic returned JSON that was not an object; used deterministic fallback heuristics."
    return {}, "Anthropic returned invalid JSON; used deterministic fallback heuristics."


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return cleaned


def _extract_with_heuristics(request: FoglineAnalyzeRequest, catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for sentence in _sentence_split(request.plan_text):
        if not sentence:
            continue
        pattern, matched_keywords = _match_pattern(sentence, catalog)
        cue_strength = _cue_strength(sentence)
        if cue_strength == 0 and not matched_keywords:
            continue
        assumption_type: AssumptionType = "explicit" if cue_strength >= 2 else "hidden"
        text = _normalize_assumption_text(sentence)
        candidates.append(
            _candidate_from_parts(
                text=text,
                assumption_type=assumption_type,
                evidence_span=sentence,
                pattern=pattern,
                matched_keywords=matched_keywords,
                source="heuristic",
                confidence=0.62 + min(cue_strength, 3) * 0.07,
            )
        )

    candidates.extend(_derived_candidates(request, catalog))
    return _dedupe_candidates(candidates, MAX_ASSUMPTIONS)


def _derived_candidates(request: FoglineAnalyzeRequest, catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan = request.plan_text.lower()
    actors = request.actors or []
    derived: List[Tuple[str, str, str]] = []

    if not _contains_any(plan, OBSERVABILITY_TERMS):
        derived.append(
            (
                "Key plan dependencies can be observed early enough to validate, monitor, and adjust.",
                "observability",
                "Derived because the plan does not name monitoring or validation signals.",
            )
        )
    if not _contains_any(plan, MITIGATION_TERMS):
        derived.append(
            (
                "Fallback paths are available if the preferred approach is delayed or degraded.",
                "fallback",
                "Derived because the plan does not name fallback or reduced-scope options.",
            )
        )
    if len(actors) > 1 or re.search(r"\b(coordinate|handoff|partner|team|unit|agency|support)\b", plan):
        derived.append(
            (
                "Actors can coordinate timing, responsibilities, and updates without major delay.",
                "coordination",
                "Derived from multiple actors or coordination language in the plan.",
            )
        )
    if request.timeline or _contains_any(plan, TIME_TERMS):
        derived.append(
            (
                "The timeline has enough slack to absorb delay without reducing the mission objective.",
                "timing",
                "Derived from timeline or sequencing language in the plan.",
            )
        )
    if re.search(r"\b(supply|supplies|fuel|transport|maintenance|equipment|staging|route|port|harbor)\b", plan):
        derived.append(
            (
                "Required resources and movement capacity remain available when the plan needs them.",
                "logistics",
                "Derived from resource, movement, staging, or port language in the plan.",
            )
        )
    if re.search(r"\b(approval|permission|clearance|authority|host|civil|partner)\b", plan):
        derived.append(
            (
                "External approvals and partner permissions remain aligned with the plan timeline.",
                "permissions",
                "Derived from approval, authority, or partner-dependency language in the plan.",
            )
        )

    candidates = []
    for text, category, evidence in derived:
        pattern = _pattern_for_category(catalog, category)
        candidates.append(
            _candidate_from_parts(
                text=text,
                assumption_type="derived",
                evidence_span=evidence,
                pattern=pattern,
                matched_keywords=[category],
                source="derived",
                confidence=0.58,
            )
        )
    return candidates


def _coerce_candidate(
    item: Any, request: FoglineAnalyzeRequest, catalog: Dict[str, Any], source: str
) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    raw_text = str(item.get("text") or "").strip()
    if not raw_text:
        return None
    candidate_pattern_id = str(item.get("candidate_pattern_id") or item.get("pattern_id") or "")
    pattern = _pattern_by_id(catalog, candidate_pattern_id)
    inferred_matches: List[str] = []
    if not pattern:
        pattern, inferred_matches = _match_pattern(raw_text, catalog, str(item.get("category") or ""))
    assumption_type = item.get("type") if item.get("type") in {"explicit", "hidden", "derived"} else "hidden"
    evidence_span = str(item.get("evidence_span") or raw_text)
    candidate = _candidate_from_parts(
        text=raw_text,
        assumption_type=assumption_type,
        evidence_span=evidence_span,
        pattern=pattern,
        matched_keywords=inferred_matches + [str(value) for value in item.get("dependency_hints", []) if value],
        source=source,
        confidence=_clamp_float(item.get("confidence", 0.67), 0.35, 0.92),
    )
    candidate["why_it_matters"] = _safe_text(str(item.get("why_it_matters") or ""))
    candidate["suggested_score_components"] = _coerce_suggested_score_components(
        item.get("suggested_score_components", {})
    )
    candidate["risk_factors_detected"] = _dedupe_strings(
        [str(value) for value in item.get("risk_factors_detected", []) if value]
        + candidate["risk_factors_detected"]
    )[:5]
    candidate["missing_mitigations"] = _dedupe_strings(
        [str(value) for value in item.get("missing_mitigations", []) if value]
        + candidate["missing_mitigations"]
    )[:5]
    candidate["dependency_hints"] = _dedupe_strings(
        [str(value) for value in item.get("dependency_hints", []) if value]
        + candidate["dependency_hints"]
    )[:5]
    return candidate


def _coerce_suggested_score_components(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {
        key: round(_clamp_float(value.get(key), 0, 100), 1)
        for key in WEIGHTS
        if key in value
    }


def _candidate_from_parts(
    *,
    text: str,
    assumption_type: AssumptionType,
    evidence_span: str,
    pattern: Dict[str, Any],
    matched_keywords: List[str],
    source: str,
    confidence: float,
) -> Dict[str, Any]:
    safe_text = _safe_text(text)
    safe_evidence = _safe_text(evidence_span)
    category = str(pattern.get("category") or "coordination")
    return {
        "text": _ensure_sentence(safe_text),
        "type": assumption_type,
        "category": category,
        "evidence_span": _trim(safe_evidence, 220),
        "pattern_id": str(pattern.get("pattern_id") or pattern.get("id") or "command_coordination"),
        "matched_keywords": matched_keywords,
        "risk_factors_detected": _risk_factors(safe_text, pattern),
        "missing_mitigations": _missing_mitigations(safe_text, pattern),
        "dependency_hints": _dependency_hints(safe_text, pattern),
        "source": source,
        "confidence": _clamp_float(confidence, 0.35, 0.92),
    }


def _score_and_build(
    candidates: List[Dict[str, Any]], request: FoglineAnalyzeRequest, catalog: Dict[str, Any]
) -> Tuple[List[FoglineAssumption], FoglineGraph]:
    for index, candidate in enumerate(candidates, start=1):
        candidate["id"] = f"a{index}"

    edges = _build_candidate_edges(candidates)
    centrality = _centrality_by_id(candidates, edges)
    assumptions: List[FoglineAssumption] = []

    for candidate in candidates:
        pattern = _pattern_by_id(catalog, candidate["pattern_id"]) or _pattern_for_category(
            catalog, candidate["category"]
        )
        breakdown = _score_breakdown(candidate, pattern, centrality.get(candidate["id"], 25))
        score = _weighted_score(breakdown)
        band = _band(score)
        assumption = FoglineAssumption(
            id=candidate["id"],
            text=candidate["text"],
            type=candidate["type"],
            category=candidate["category"],
            fragility_score=score,
            fragility_band=band,
            score_breakdown=breakdown,
            evidence_span=candidate["evidence_span"],
            why_it_matters=_safe_text(str(candidate.get("why_it_matters") or pattern.get("why_it_matters") or "")),
            pattern_id=candidate["pattern_id"],
            why_this_pattern_matches=_pattern_match_reason(candidate, pattern),
            risk_factors_detected=_dedupe_strings(candidate["risk_factors_detected"])[:6],
            missing_mitigations=_dedupe_strings(candidate["missing_mitigations"])[:5],
            monitoring_indicators=_safe_list(pattern.get("monitoring_indicators", []), 5),
            resilience_patches=_safe_list(pattern.get("resilience_patches", []), 5),
            validation_questions=_safe_list(pattern.get("validation_questions", []), 4),
            fallback_options=_safe_list(pattern.get("fallback_options", []), 4),
            rewrite_suggestion=_rewrite_suggestion(candidate),
            dependency_hints=_dedupe_strings(candidate["dependency_hints"])[:5],
            status="intact",
            confidence=round(float(candidate.get("confidence", 0.6)), 2),
            break_event_template=_break_event_template(candidate, pattern),
            game_effects=_game_effects(candidate, score),
            autopsy_tags=_autopsy_tags(candidate, band),
        )
        assumptions.append(assumption)

    graph = _build_graph(assumptions, _build_edges_from_assumptions(assumptions))
    return assumptions, graph


def _score_breakdown(
    candidate: Dict[str, Any], pattern: Dict[str, Any], dependency_centrality: float
) -> ScoreBreakdown:
    text = candidate["text"].lower()
    base_pattern_risk = _clamp_float(pattern.get("base_pattern_risk", pattern.get("base_fragility", 55)), 0, 100)

    observability_gap = 72
    if _contains_any(text, OBSERVABILITY_TERMS):
        observability_gap -= 28
    if "derived" == candidate["type"] and candidate["category"] in {"observability", "information_environment"}:
        observability_gap += 10
    if _contains_any(text, {"unknown", "unconfirmed", "unverified", "assume", "assumes"}):
        observability_gap += 10

    mitigation_gap = 70
    if _contains_any(text, MITIGATION_TERMS):
        mitigation_gap -= 30
    if _contains_any(text, SINGLE_PATH_TERMS):
        mitigation_gap += 14
    if candidate["type"] == "derived":
        mitigation_gap += 6

    recovery_difficulty = _clamp_float(pattern.get("recovery_difficulty", 55), 0, 100)
    if mitigation_gap >= 70:
        recovery_difficulty += 10
    if candidate["category"] in {"communications", "logistics", "permissions", "authority_permissions", "infrastructure"}:
        recovery_difficulty += 6

    consequence_severity = _clamp_float(pattern.get("consequence_severity", 55), 0, 100)
    if _contains_any(text, {"mission", "objective", "critical", "must", "main"}):
        consequence_severity += 10
    if candidate["category"] in {"coordination", "command_coordination", "timing", "communications"}:
        consequence_severity += 5

    volatility = _clamp_float(pattern.get("volatility", 50), 0, 100)
    if _contains_any(text, TIME_TERMS):
        volatility += 8
    if candidate["category"] in {"weather_environment", "actor_cooperation", "partner_support", "permissions", "authority_permissions"}:
        volatility += 8

    return ScoreBreakdown(
        base_pattern_risk=round(_clamp_float(base_pattern_risk, 0, 100), 1),
        observability_gap=round(_clamp_float(observability_gap, 0, 100), 1),
        mitigation_gap=round(_clamp_float(mitigation_gap, 0, 100), 1),
        dependency_centrality=round(_clamp_float(dependency_centrality, 0, 100), 1),
        recovery_difficulty=round(_clamp_float(recovery_difficulty, 0, 100), 1),
        consequence_severity=round(_clamp_float(consequence_severity, 0, 100), 1),
        volatility=round(_clamp_float(volatility, 0, 100), 1),
    )


def _weighted_score(breakdown: ScoreBreakdown) -> float:
    values = breakdown.model_dump()
    score = sum(values[name] * weight for name, weight in WEIGHTS.items())
    return round(_clamp_float(score, 0, 100), 1)


def _band(score: float) -> FragilityBand:
    if score < 35:
        return "low"
    if score < 60:
        return "medium"
    if score < 80:
        return "high"
    return "critical"


def _build_candidate_edges(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    for target in candidates:
        target_category = target["category"]
        rules = CATEGORY_DEPENDENCIES.get(target_category, set())
        hints = {str(hint).lower() for hint in target.get("dependency_hints", [])}
        scored_sources: List[Tuple[float, Dict[str, Any], str]] = []
        for source in candidates:
            if source["id"] == target["id"]:
                continue
            source_category = source["category"]
            matched = source_category in rules or source_category in hints
            if not matched:
                continue
            strength = _edge_strength(source, target, source_category in hints, source_category in rules)
            rationale = (
                f"If {source_category} degrades, it can delay or disrupt "
                f"{target_category} and add decision debt."
            )
            scored_sources.append((strength, source, rationale))
        for strength, source, rationale in sorted(scored_sources, key=lambda item: -item[0])[:2]:
            edges.append(
                {
                    "source": source["id"],
                    "target": target["id"],
                    "strength": strength,
                    "rationale": rationale,
                }
            )
    return edges[:18]


def _build_edges_from_assumptions(assumptions: List[FoglineAssumption]) -> List[FoglineGraphEdge]:
    scored_edges: List[Tuple[float, FoglineGraphEdge]] = []
    terms_by_id = {item.id: _assumption_terms(item) for item in assumptions}

    for target in assumptions:
        target_category = _canonical_category(target.category)
        dependency_rules = {_canonical_category(category) for category in CATEGORY_DEPENDENCIES.get(target_category, set())}
        target_hints = {_canonical_category(hint) for hint in target.dependency_hints}
        for source in assumptions:
            if source.id == target.id:
                continue
            source_category = _canonical_category(source.category)
            source_hints = {_canonical_category(hint) for hint in source.dependency_hints}
            rule_match = source_category in dependency_rules
            hint_match = source_category in target_hints
            reverse_hint_match = target_category in source_hints
            overlap_terms = sorted(terms_by_id[source.id] & terms_by_id[target.id])
            overlap_score = min(len(overlap_terms), 4) * 0.05

            if not (rule_match or hint_match or reverse_hint_match or len(overlap_terms) >= 2):
                continue

            strength = 0.28 + overlap_score
            if rule_match:
                strength += 0.28
            if hint_match:
                strength += 0.20
            if reverse_hint_match:
                strength += 0.08
            if source.fragility_band in {"critical", "high"}:
                strength += 0.06
            if target.fragility_band in {"critical", "high"}:
                strength += 0.04
            strength = round(_clamp_float(strength, 0.25, 0.95), 2)
            relationship = _edge_relationship(source_category, target_category, rule_match, hint_match, strength)
            reason = _edge_reason(
                source,
                target,
                relationship,
                rule_match,
                hint_match,
                reverse_hint_match,
                overlap_terms,
            )
            scored_edges.append(
                (
                    strength,
                    FoglineGraphEdge(
                        id=f"edge_{source.id}_{target.id}",
                        source=source.id,
                        target=target.id,
                        relationship=relationship,
                        strength=strength,
                        reason=reason,
                        rationale=reason,
                    ),
                )
            )

    deduped: Dict[str, FoglineGraphEdge] = {}
    for _strength, edge in sorted(scored_edges, key=lambda item: (-item[0], item[1].id)):
        target_count = sum(1 for existing in deduped.values() if existing.target == edge.target)
        source_count = sum(1 for existing in deduped.values() if existing.source == edge.source)
        if target_count >= 3 or source_count >= 4:
            continue
        deduped[edge.id] = edge
        if len(deduped) >= 28:
            break

    if not deduped and len(assumptions) >= 2:
        source, target = assumptions[0], assumptions[1]
        reason = f"{source.category} fragility can stress {target.category} because both assumptions are high-priority plan dependencies."
        deduped[f"edge_{source.id}_{target.id}"] = FoglineGraphEdge(
            id=f"edge_{source.id}_{target.id}",
            source=source.id,
            target=target.id,
            relationship="weakens",
            strength=0.45,
            reason=reason,
            rationale=reason,
        )

    return list(deduped.values())


def _assumption_terms(assumption: FoglineAssumption) -> set[str]:
    text = " ".join(
        [
            assumption.text,
            assumption.category,
            assumption.pattern_id,
            " ".join(assumption.dependency_hints),
            " ".join(assumption.risk_factors_detected),
            " ".join(assumption.missing_mitigations),
        ]
    )
    terms = {
        term
        for term in re.findall(r"[a-zA-Z][a-zA-Z_]{3,}", text.lower())
        if term not in EDGE_STOPWORDS
    }
    return {_canonical_category(term) for term in terms}


def _edge_relationship(
    source_category: str,
    target_category: str,
    rule_match: bool,
    hint_match: bool,
    strength: float,
) -> CascadeRelationship:
    if target_category in {"resource", "logistics", "infrastructure"} and source_category in {
        "infrastructure",
        "resource",
        "authority_permissions",
        "communications",
    }:
        return "blocks_recovery"
    if rule_match or hint_match:
        return "depends_on"
    if strength >= 0.72:
        return "depends_on"
    return "weakens"


def _edge_reason(
    source: FoglineAssumption,
    target: FoglineAssumption,
    relationship: CascadeRelationship,
    rule_match: bool,
    hint_match: bool,
    reverse_hint_match: bool,
    overlap_terms: List[str],
) -> str:
    clauses = []
    if rule_match:
        clauses.append(f"{target.category} is modeled as depending on {source.category}")
    if hint_match:
        clauses.append(f"{target.id} lists {source.category} as a dependency hint")
    if reverse_hint_match:
        clauses.append(f"{source.id} references {target.category}, creating a coupling")
    if overlap_terms:
        clauses.append(f"shared cues include {', '.join(overlap_terms[:3])}")
    if not clauses:
        clauses.append("both assumptions are connected by plan language")
    verb = {
        "depends_on": "depends on",
        "weakens": "can be weakened by",
        "blocks_recovery": "may have recovery blocked by",
    }[relationship]
    return _safe_text(
        f"{target.id} {verb} {source.id}: "
        f"{'; '.join(clauses)}. If {source.category} degrades, {target.category} may be stressed, delayed, or harder to recover."
    )


def _edge_strength(source: Dict[str, Any], target: Dict[str, Any], hint_match: bool, rule_match: bool) -> float:
    strength = 0.35
    if hint_match:
        strength += 0.22
    if rule_match:
        strength += 0.16
    if source.get("category") in {"communications", "coordination", "command_coordination", "logistics", "timing"}:
        strength += 0.08
    if target.get("type") == "derived":
        strength += 0.04
    return round(min(strength, 0.95), 2)


def _centrality_by_id(candidates: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, float]:
    degree = {candidate["id"]: 0 for candidate in candidates}
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1

    centrality: Dict[str, float] = {}
    for candidate in candidates:
        value = 25 + min(degree[candidate["id"]], 5) * 11
        value += min(len(candidate.get("dependency_hints", [])), 4) * 4
        if candidate["category"] in {"communications", "coordination", "command_coordination", "logistics", "timing"}:
            value += 8
        centrality[candidate["id"]] = round(_clamp_float(value, 0, 100), 1)
    return centrality


def _build_graph(assumptions: List[FoglineAssumption], edges: List[FoglineGraphEdge]) -> FoglineGraph:
    return FoglineGraph(
        nodes=[
            FoglineGraphNode(
                id=item.id,
                label=_trim(item.text, 80),
                category=item.category,
                fragility_score=item.fragility_score,
                fragility_band=item.fragility_band,
                status=item.status,
            )
            for item in assumptions
        ],
        edges=edges,
        metadata={
            "node_count": len(assumptions),
            "edge_count": len(edges),
            "edge_strength_scale": "0.0-1.0 rubric",
            "edge_inference": "dependency hints, category relationships, and keyword overlap",
        },
    )


def _renumber_assumptions(
    assumptions: List[FoglineAssumption], _graph: FoglineGraph
) -> List[FoglineAssumption]:
    old_to_new = {assumption.id: f"a{index}" for index, assumption in enumerate(assumptions, start=1)}
    renumbered: List[FoglineAssumption] = []
    for assumption in assumptions:
        data = assumption.model_dump()
        data["id"] = old_to_new[assumption.id]
        renumbered.append(FoglineAssumption(**data))
    return renumbered


def _build_summary(
    assumptions: List[FoglineAssumption], compiler_mode: str, catalog_version: str
) -> FoglineSummary:
    bands = {band: sum(1 for item in assumptions if item.fragility_band == band) for band in ["critical", "high", "medium", "low"]}
    average = round(sum(item.fragility_score for item in assumptions) / max(len(assumptions), 1), 1)
    categories: Dict[str, int] = {}
    for item in assumptions:
        categories[item.category] = categories.get(item.category, 0) + 1
    dominant_categories = [
        category for category, _ in sorted(categories.items(), key=lambda pair: (-pair[1], pair[0]))[:4]
    ]
    return FoglineSummary(
        total_assumptions=len(assumptions),
        critical_count=bands["critical"],
        high_count=bands["high"],
        medium_count=bands["medium"],
        low_count=bands["low"],
        average_fragility_score=average,
        top_fragility_ids=[item.id for item in assumptions[:5]],
        dominant_categories=dominant_categories,
        compiler_mode=compiler_mode,
        catalog_version=catalog_version,
    )


def _build_ghost_seed(assumptions: List[FoglineAssumption], graph: FoglineGraph) -> GhostCouncilSeed:
    outgoing = _outgoing_targets(graph)
    degree = _graph_degree(graph)
    focus = sorted(
        assumptions,
        key=lambda item: (
            _break_band_priority(item.fragility_band),
            -item.fragility_score,
            -item.score_breakdown.dependency_centrality,
            -degree.get(item.id, 0),
            item.id,
        ),
    )[:5]
    return GhostCouncilSeed(
        priority_targets=[
            GhostCouncilPriorityTarget(
                assumption_id=item.id,
                reason_to_target=_ghost_reason_to_target(item, degree.get(item.id, 0), outgoing.get(item.id, [])),
                fragility_score=item.fragility_score,
                expected_cascade=outgoing.get(item.id, [])[:4],
                prospect_theory_trigger=_prospect_theory_trigger(item),
                safe_pressure_frame=_safe_pressure_frame(item),
            )
            for item in focus[: max(3, min(5, len(focus)))]
        ],
        red_team_guidance=[
            "Apply abstract pressure to assumptions, not to real-world actors or systems.",
            "Use stress, delay, degraded confidence, uncertainty, and forced validation as the only pressure modes.",
            "Frame every inject as a training decision point with validate, fallback, reduce scope, coordinate, or wait options.",
            "Avoid tactical instructions, real-world operational detail, and exact historical statistics.",
        ],
        focus_assumption_ids=[item.id for item in focus],
        candidates=[
            GhostCouncilCandidate(
                assumption_id=item.id,
                text=item.text,
                fragility_score=item.fragility_score,
                fragility_band=item.fragility_band,
                why_it_matters=item.why_it_matters,
                validation_questions=item.validation_questions,
                resilience_patches=item.resilience_patches,
            )
            for item in focus
        ],
        briefing="Challenge the highest-fragility assumptions with validation, fallback, and reduced-scope options.",
    )


def _outgoing_targets(graph: FoglineGraph) -> Dict[str, List[str]]:
    outgoing: Dict[str, List[Tuple[float, str]]] = {}
    for edge in graph.edges:
        outgoing.setdefault(edge.source, []).append((edge.strength, edge.target))
    return {
        source: [target for _strength, target in sorted(targets, key=lambda item: (-item[0], item[1]))]
        for source, targets in outgoing.items()
    }


def _graph_degree(graph: FoglineGraph) -> Dict[str, int]:
    degree: Dict[str, int] = {node.id: 0 for node in graph.nodes}
    for edge in graph.edges:
        degree[edge.source] = degree.get(edge.source, 0) + 1
        degree[edge.target] = degree.get(edge.target, 0) + 1
    return degree


def _ghost_reason_to_target(
    assumption: FoglineAssumption, degree: int, expected_cascade: List[str]
) -> str:
    reasons = [
        f"{assumption.fragility_band.title()} fragility score {assumption.fragility_score}",
        f"{assumption.category} dependency",
    ]
    if degree:
        reasons.append(f"connected to {degree} graph relationship(s)")
    if expected_cascade:
        reasons.append(f"expected cascade reaches {', '.join(expected_cascade[:3])}")
    return _safe_text(f"{'; '.join(reasons)}.")


def _prospect_theory_trigger(assumption: FoglineAssumption) -> str:
    category = _canonical_category(assumption.category)
    if category in {"timing", "communications", "command_coordination"}:
        return "time pressure may push players to preserve tempo despite lower confidence"
    if category in {"logistics", "resource", "infrastructure"}:
        return "sunk-cost pressure may push players to continue using a strained plan path"
    if category in {"intelligence", "information_environment", "cyber_system"}:
        return "ambiguity aversion may push players to favor familiar assumptions over fresh validation"
    if category in {"partner_support", "authority_permissions", "civilian_behavior"}:
        return "loss aversion may push players to avoid reducing scope even when support is uncertain"
    if category in {"escalation", "weather_environment"}:
        return "status quo bias may push players to preserve the plan despite changing conditions"
    return "overconfidence may push players to treat an unverified assumption as stable"


def _safe_pressure_frame(assumption: FoglineAssumption) -> str:
    category = _canonical_category(assumption.category)
    if category == "timing":
        frame = "Introduce delayed confirmation and force the team to choose between waiting for validation or reducing mission scope."
    elif category == "communications":
        frame = "Introduce conflicting status updates and force the team to validate the shared picture before continuing dependent actions."
    elif category == "logistics":
        frame = "Introduce a resource availability delay and force the team to reroute support, reduce demand, or wait for validation."
    elif category == "infrastructure":
        frame = "Introduce uncertain infrastructure availability and force the team to validate access before committing dependent tasks."
    elif category == "resource":
        frame = "Introduce reserve capacity stress and force the team to prioritize critical tasks or reduce scope."
    elif category == "command_coordination":
        frame = "Introduce ownership uncertainty for a handoff and force the team to validate an owner before continuing."
    elif category == "intelligence":
        frame = "Introduce a stale estimate and force the team to choose between conservative action, waiting for validation, or reducing scope."
    elif category == "cyber_system":
        frame = "Introduce degraded dashboard confidence and force the team to use manual validation or a reduced-digital workflow."
    elif category == "partner_support":
        frame = "Introduce delayed partner confirmation and force the team to coordinate a reduced-scope branch."
    elif category == "authority_permissions":
        frame = "Introduce delayed approval confirmation and force the team to use an approved branch or pause dependent tasks."
    elif category == "civilian_behavior":
        frame = "Introduce public demand uncertainty and force the team to coordinate, monitor indicators, or reduce access scope."
    elif category == "weather_environment":
        frame = "Introduce changing condition thresholds and force the team to validate timing, reroute, or reduce exposed tasks."
    elif category == "escalation":
        frame = "Introduce expanded coordination uncertainty and force the team to clarify constraints before preserving the current scope."
    else:
        frame = "Introduce degraded confidence and force the team to validate, fallback, reduce scope, coordinate, or wait."
    if not any(
        safe_word in frame.lower()
        for safe_word in ["pressure", "stress", "degraded", "delay", "uncertainty", "validation", "validate"]
    ):
        frame = f"{frame} This creates uncertainty and forces validation."
    return frame


def _build_cascade_seed(assumptions: List[FoglineAssumption], graph: FoglineGraph) -> CascadeSeed:
    degree: Dict[str, int] = {item.id: 0 for item in assumptions}
    for edge in graph.edges:
        degree[edge.source] = degree.get(edge.source, 0) + 1
        degree[edge.target] = degree.get(edge.target, 0) + 1
    break_order = [
        item.id
        for item in sorted(
            assumptions,
            key=lambda item: (
                _break_band_priority(item.fragility_band),
                -item.fragility_score,
                -item.score_breakdown.dependency_centrality,
                -degree.get(item.id, 0),
                item.id,
            ),
        )
    ]
    root_ids = [assumption_id for assumption_id in break_order if degree.get(assumption_id, 0) > 0][:4]
    if not root_ids:
        root_ids = break_order[:4]
    return CascadeSeed(
        break_order=break_order,
        critical_paths=_build_critical_paths(root_ids, assumptions, graph),
        propagation_rules=_build_propagation_rules(graph),
        root_assumption_ids=root_ids,
        edge_strengths=[
            CascadeEdgeSeed(
                source=edge.source,
                target=edge.target,
                strength=edge.strength,
                rationale=edge.reason,
            )
            for edge in graph.edges
        ],
        dependency_graph=graph,
    )


def _break_band_priority(band: FragilityBand) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}[band]


def _build_critical_paths(
    root_ids: List[str], assumptions: List[FoglineAssumption], graph: FoglineGraph
) -> List[CascadeCriticalPath]:
    assumption_by_id = {item.id: item for item in assumptions}
    outgoing: Dict[str, List[FoglineGraphEdge]] = {}
    for edge in graph.edges:
        outgoing.setdefault(edge.source, []).append(edge)
    for edges in outgoing.values():
        edges.sort(key=lambda edge: (-edge.strength, edge.target))

    paths: List[CascadeCriticalPath] = []
    for root_id in root_ids:
        path = [root_id]
        visited = {root_id}
        current = root_id
        while current in outgoing and len(path) < 5:
            next_edge = next((edge for edge in outgoing[current] if edge.target not in visited), None)
            if not next_edge:
                break
            path.append(next_edge.target)
            visited.add(next_edge.target)
            current = next_edge.target
        if len(path) < 2:
            continue
        root = assumption_by_id.get(root_id)
        tail = assumption_by_id.get(path[-1])
        explanation = (
            f"{root_id} is fragile and central; degradation can propagate through "
            f"{len(path) - 1} linked assumption(s)"
        )
        if root and tail:
            explanation += f" from {root.category} toward {tail.category}."
        else:
            explanation += "."
        paths.append(
            CascadeCriticalPath(
                root_assumption_id=root_id,
                cascade_path=path,
                risk_explanation=_safe_text(explanation),
            )
        )
    return paths[:4]


def _build_propagation_rules(graph: FoglineGraph) -> List[CascadePropagationRule]:
    return [
        CascadePropagationRule(
            source=edge.source,
            target=edge.target,
            effect=_propagation_effect(edge),
            threshold=_propagation_threshold(edge),
            delay_ms=400,
            reason=edge.reason,
        )
        for edge in graph.edges
    ]


def _propagation_effect(edge: FoglineGraphEdge) -> PropagationEffect:
    if edge.relationship == "blocks_recovery" or edge.strength >= 0.82:
        return "break"
    if edge.relationship == "depends_on" or edge.strength >= 0.60:
        return "weaken"
    return "stress"


def _propagation_threshold(edge: FoglineGraphEdge) -> float:
    if edge.relationship == "blocks_recovery":
        return round(max(0.35, 0.78 - edge.strength * 0.35), 2)
    if edge.relationship == "depends_on":
        return round(max(0.40, 0.82 - edge.strength * 0.32), 2)
    return round(max(0.45, 0.90 - edge.strength * 0.30), 2)


def _build_autopsy_seed(assumptions: List[FoglineAssumption]) -> AutopsySeed:
    ranked = [
        AutopsyRankedAssumption(
            assumption_id=item.id,
            rank=index,
            reason=_autopsy_rank_reason(item),
            fragility_score=item.fragility_score,
            category=item.category,
        )
        for index, item in enumerate(assumptions, start=1)
    ]
    audit_fields = [
        "assumption_id",
        "original_status",
        "break_turn",
        "player_response",
        "new_assumptions_created",
        "resilience_delta",
        "decision_debt_delta",
        "final_status",
    ]
    patch_candidates = [
        AutopsyPatchCandidate(
            assumption_id=item.id,
            rewrite_suggestion=item.rewrite_suggestion,
            monitoring_indicators=item.monitoring_indicators,
            fallback_options=item.fallback_options,
            validation_questions=item.validation_questions,
        )
        for item in assumptions
    ]
    return AutopsySeed(
        ranked_assumptions=ranked,
        audit_fields=audit_fields,
        resilience_patch_candidates=patch_candidates,
        better_plan_principles=[
            "Validate critical assumptions before phase transitions.",
            "Add fallback options for high-centrality dependencies.",
            "Monitor unverified external actors.",
            "Add decision points when confidence drops.",
            "Reduce single-point dependencies.",
            "Define thresholds for delaying or reducing scope.",
        ],
        assumption_rank=[
            AutopsyRankItem(
                rank=index,
                assumption_id=item.id,
                fragility_score=item.fragility_score,
                fragility_band=item.fragility_band,
                autopsy_tags=item.autopsy_tags,
                failure_chain_metadata={
                    "category": item.category,
                    "pattern_id": item.pattern_id,
                    "evidence_span": item.evidence_span,
                    "rewrite_suggestion": item.rewrite_suggestion,
                },
            )
            for index, item in enumerate(assumptions, start=1)
        ],
        decision_audit_fields=audit_fields,
        legacy_resilience_patch_candidates=_dedupe_strings(
            patch for assumption in assumptions for patch in assumption.resilience_patches
        )[:8],
    )


def _autopsy_rank_reason(assumption: FoglineAssumption) -> str:
    return _safe_text(
        f"Ranked by {assumption.fragility_band} fragility score {assumption.fragility_score}, "
        f"{assumption.category} category, dependency centrality "
        f"{assumption.score_breakdown.dependency_centrality}, and recovery difficulty "
        f"{assumption.score_breakdown.recovery_difficulty}."
    )


def _break_event_template(candidate: Dict[str, Any], pattern: Dict[str, Any]) -> BreakEventTemplate:
    profile = _game_effect_profile(candidate["category"])
    short = _trim(candidate["text"], 96)
    return BreakEventTemplate(
        title=profile["title"],
        sitrep=_safe_text(f"{profile['sitrep']} Assumption reference: '{short}'"),
        immediate_effects=_safe_list(profile["effects"], 4),
        player_decision_prompt=profile["prompt"],
    )


def _game_effects(candidate: Dict[str, Any], score: float) -> GameEffects:
    band = _band(score)
    profile = _game_effect_profile(candidate["category"])
    return GameEffects(
        resilience_delta=_scaled_game_delta(score, band, "resilience"),
        decision_debt_delta=_scaled_game_delta(score, band, "decision_debt"),
        affected_metrics=_dedupe_strings(
            metric for metric in profile["metrics"] if metric in ALLOWED_AFFECTED_METRICS
        ),
    )


def _game_effect_profile(category: str) -> Dict[str, Any]:
    canonical = _canonical_category(category)
    return GAME_EFFECT_PROFILES.get(
        canonical,
        {
            "title": f"{canonical.replace('_', ' ').title()} Assumption Degraded",
            "sitrep": "A key planning assumption is delayed, degraded, or harder to validate. Mission resilience is reduced.",
            "effects": [
                "Mission resilience decreases",
                "Decision debt rises",
                "Dependent assumptions become stressed",
            ],
            "prompt": "Do you pause for validation, coordinate support, reduce scope, activate a fallback, or continue under uncertainty?",
            "metrics": ["mission_resilience", "coordination", "tempo"],
        },
    )


def _scaled_game_delta(score: float, band: FragilityBand, effect_type: str) -> int:
    score_ranges = {
        "low": (0, 34),
        "medium": (35, 59),
        "high": (60, 79),
        "critical": (80, 100),
    }
    effect_ranges = {
        "resilience": {
            "low": (-3, -6),
            "medium": (-7, -11),
            "high": (-12, -18),
            "critical": (-19, -25),
        },
        "decision_debt": {
            "low": (2, 4),
            "medium": (5, 8),
            "high": (9, 13),
            "critical": (14, 18),
        },
    }
    band_min, band_max = score_ranges[band]
    start, end = effect_ranges[effect_type][band]
    ratio = 0 if band_max == band_min else _clamp_float((score - band_min) / (band_max - band_min), 0, 1)
    return round(start + (end - start) * ratio)


def _autopsy_tags(candidate: Dict[str, Any], band: FragilityBand) -> List[str]:
    return _dedupe_strings(
        [
            f"band:{band}",
            f"category:{candidate['category']}",
            f"pattern:{candidate['pattern_id']}",
            f"source:{candidate.get('source', 'unknown')}",
        ]
    )


def _rewrite_suggestion(candidate: Dict[str, Any]) -> str:
    category = candidate["category"].replace("_", " ")
    return (
        f"Rewrite as a testable {category} assumption with a named validation signal, "
        "fallback trigger, owner, and reduced-scope option."
    )


def _pattern_match_reason(candidate: Dict[str, Any], pattern: Dict[str, Any]) -> str:
    matched = [word for word in candidate.get("matched_keywords", []) if word]
    return _match_reason_for_pattern(candidate.get("text", ""), candidate.get("category", ""), pattern, matched)


def _risk_factors(text: str, pattern: Dict[str, Any]) -> List[str]:
    lowered = text.lower()
    factors = list(pattern.get("risk_factors", []))[:4]
    if _contains_any(lowered, CERTAINTY_TERMS):
        factors.append("success condition is phrased with high certainty")
    if _contains_any(lowered, SINGLE_PATH_TERMS):
        factors.append("single-path or primary-path dependency")
    if _contains_any(lowered, TIME_TERMS):
        factors.append("timing or sequencing dependency")
    if not _contains_any(lowered, OBSERVABILITY_TERMS):
        factors.append("no explicit monitoring signal")
    return _safe_list(_dedupe_strings(factors), 6)


def _missing_mitigations(text: str, pattern: Dict[str, Any]) -> List[str]:
    lowered = text.lower()
    missing: List[str] = []
    if not _contains_any(lowered, OBSERVABILITY_TERMS):
        missing.append("monitoring or validation signal")
    if not _contains_any(lowered, MITIGATION_TERMS):
        missing.extend(pattern.get("missing_mitigations", [])[:3])
    if _contains_any(lowered, TIME_TERMS) and "timeline slack" not in missing:
        missing.append("timeline slack or delay trigger")
    return _safe_list(_dedupe_strings(missing), 5)


def _dependency_hints(text: str, pattern: Dict[str, Any]) -> List[str]:
    lowered = text.lower()
    hints = list(pattern.get("dependency_hints", []))
    keyword_map = {
        "communications": {"communicate", "comms", "message", "report", "network", "radio", "link"},
        "command_coordination": {"coordinate", "handoff", "team", "synchronize", "command", "decision"},
        "partner_support": {"partner", "support", "host", "agency", "stakeholder", "liaison"},
        "intelligence": {"intelligence", "information", "picture", "estimate", "status"},
        "information_environment": {"rumor", "public", "narrative", "perception", "messaging"},
        "logistics": {"supply", "transport", "fuel", "maintenance", "equipment", "staging"},
        "authority_permissions": {"approval", "permission", "authority", "clearance", "host"},
        "infrastructure": {"route", "bridge", "port", "harbor", "facility", "access"},
        "resource": {"resource", "capacity", "reserve", "staff", "readiness"},
        "timing": TIME_TERMS,
    }
    for category, words in keyword_map.items():
        if _contains_any(lowered, words):
            hints.append(category)
    return _dedupe_strings(hints)[:6]


def _card_match_score(plan_text: str, card: Dict[str, Any]) -> int:
    lowered = plan_text.lower()
    score = 0
    for keyword in card.get("rag_keywords", []):
        keyword_text = str(keyword).lower()
        if keyword_text and re.search(rf"\b{re.escape(keyword_text)}\b", lowered):
            score += 4
    if str(card.get("category", "")).lower() in lowered:
        score += 3
    if str(card.get("id", "")).replace("_", " ") in lowered:
        score += 2
    return score


def _compact_evidence_card(card: Dict[str, Any], plan_text: str) -> Dict[str, Any]:
    lowered = plan_text.lower()
    matched_keywords = [
        keyword
        for keyword in card.get("rag_keywords", [])
        if re.search(rf"\b{re.escape(str(keyword).lower())}\b", lowered)
    ][:6]
    return {
        "id": card.get("id"),
        "category": card.get("category"),
        "description": _trim(str(card.get("description", "")), 190),
        "risk_factors": card.get("risk_factors", [])[:3],
        "observable_indicators": card.get("observable_indicators", [])[:3],
        "mitigation_patterns": card.get("mitigation_patterns", [])[:3],
        "base_fragility": card.get("base_fragility"),
        "safe_historical_analog_summary": _trim(str(card.get("safe_historical_analog_summary", "")), 130),
        "doctrine_note": _trim(str(card.get("doctrine_note", "")), 150),
        "matched_keywords": matched_keywords,
    }


def _match_reason_for_pattern(
    assumption_text: str,
    category: str,
    pattern: Dict[str, Any],
    matched_keywords: List[str],
) -> str:
    category_match = _canonical_category(category) == pattern.get("category")
    cues = f" Matched cues: {', '.join(matched_keywords[:5])}." if matched_keywords else ""
    category_note = " Category aligns with the evidence card." if category_match else ""
    analog = pattern.get("safe_historical_analog_summary", "")
    base = (
        f"{pattern.get('description', 'This evidence card matches a planning fragility pattern')}"
        f"{category_note}{cues} Analog summary: {analog}"
    )
    return _safe_text(base)


def _safe_identifier(value: str) -> str:
    identifier = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return identifier or "command_coordination"


def _canonical_category(category: str) -> str:
    normalized = _safe_identifier(category)
    return CATEGORY_ALIASES.get(normalized, normalized)


def _safe_plain_list(values: Iterable[Any], limit: int) -> List[str]:
    return [_safe_text(str(value)) for value in list(values)[:limit] if str(value).strip()]


def _validation_questions_for_card(card: Dict[str, Any]) -> List[str]:
    category = str(card.get("category", "assumption")).replace("_", " ")
    indicators = card.get("observable_indicators", [])
    first_indicator = indicators[0] if indicators else "a named monitoring indicator"
    return [
        f"What would show this {category} assumption is no longer intact?",
        f"Who monitors {first_indicator} before the next decision point?",
        "Which branch or sequel activates if the assumption degrades?",
    ]


def _fallback_options_for_category(category: str) -> List[str]:
    base = ["validate before proceeding", "reduce scope", "coordinate support", "delay noncritical tasks"]
    if category in {"logistics", "infrastructure", "resource"}:
        return ["reroute support", "reduce resource demand", "stage only critical tasks", "delay noncritical movement"]
    if category in {"communications", "cyber_system"}:
        return ["use a backup update path", "switch to reduced reporting", "pause dependent changes", "validate manually"]
    if category in {"authority_permissions", "partner_support"}:
        return ["reduce scope", "use an approved branch", "request coordination review", "delay dependent tasks"]
    if category == "timing":
        return ["resequence tasks", "activate a delay branch", "reduce scope", "hold critical slack"]
    return base


def _patterns(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    if catalog.get("_normalized_for_fogline"):
        return [pattern for pattern in catalog.get("patterns", []) if isinstance(pattern, dict)]
    return [
        pattern
        for pattern in _normalize_catalog(catalog).get("patterns", [])
        if isinstance(pattern, dict)
    ]


def _pattern_by_id(catalog: Dict[str, Any], pattern_id: str) -> Optional[Dict[str, Any]]:
    for pattern in _patterns(catalog):
        if pattern.get("pattern_id") == pattern_id or pattern.get("id") == pattern_id:
            return pattern
    return None


def _pattern_for_category(catalog: Dict[str, Any], category: str) -> Dict[str, Any]:
    canonical = _canonical_category(category)
    for pattern in _patterns(catalog):
        if pattern.get("category") == canonical:
            return pattern
    return _patterns(catalog)[0]


def _match_pattern(
    text: str, catalog: Dict[str, Any], preferred_category: str = ""
) -> Tuple[Dict[str, Any], List[str]]:
    lowered = text.lower()
    best_pattern = _patterns(catalog)[0]
    best_score = -1
    best_matches: List[str] = []
    canonical_category = _canonical_category(preferred_category)

    for pattern in _patterns(catalog):
        keywords = [str(keyword).lower() for keyword in pattern.get("keywords", [])]
        matches = [keyword for keyword in keywords if keyword and re.search(rf"\b{re.escape(keyword)}\b", lowered)]
        score = len(matches) * 3
        if canonical_category and canonical_category == pattern.get("category"):
            score += 4
        if score > best_score:
            best_pattern = pattern
            best_score = score
            best_matches = matches
    return best_pattern, best_matches[:6]


def _cue_strength(sentence: str) -> int:
    lowered = sentence.lower()
    score = 0
    if re.search(r"\bassum(?:e|es|ed|ing)\b", lowered):
        score += 3
    if re.search(r"\b(depends on|requires?|relies? on|need(?:s)?|must|provided that|as long as)\b", lowered):
        score += 2
    if re.search(r"\b(will|should|expected to|available|ready|can)\b", lowered):
        score += 1
    if re.search(r"\bif\b", lowered):
        score += 1
    return score


def _sentence_split(text: str) -> List[str]:
    normalized = re.sub(r"[\r\n]+", ". ", text.strip())
    normalized = re.sub(r"\s*[-*]\s+", ". ", normalized)
    parts = re.split(r"(?<=[.!?;])\s+|\s+\|\s+", normalized)
    return [_trim(part.strip(" .;:-"), 260) for part in parts if part.strip(" .;:-")]


def _normalize_assumption_text(sentence: str) -> str:
    text = _safe_text(sentence.strip())
    text = re.sub(r"^(we\s+)?assum(?:e|es|ing)\s+(that\s+)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(the\s+plan\s+)?requires?\s+(that\s+)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(it\s+)?depends\s+on\s+(that\s+)?", "", text, flags=re.IGNORECASE)
    return _ensure_sentence(text[:1].upper() + text[1:])


def _infer_objective(request: FoglineAnalyzeRequest) -> str:
    if request.mission_objective:
        return _ensure_sentence(_safe_text(request.mission_objective))
    match = re.search(
        r"\b(?:mission|objective|goal)\s*:\s*(.+?)(?:[\r\n.;]|$)",
        request.plan_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return _ensure_sentence(_safe_text(_trim(match.group(1), 180)))
    sentences = _sentence_split(request.plan_text)
    if sentences:
        return _ensure_sentence(_safe_text(_trim(sentences[0], 180)))
    return "Mission objective not specified."


def _safe_text(text: str) -> str:
    safe = str(text)
    for pattern, replacement in SAFE_REPLACEMENTS:
        safe = re.sub(pattern, replacement, safe, flags=re.IGNORECASE)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe


def _safe_list(values: Iterable[Any], limit: int) -> List[str]:
    return [_ensure_sentence(_safe_text(str(value))) for value in list(values)[:limit] if str(value).strip()]


def _ensure_sentence(text: str) -> str:
    cleaned = _safe_text(text).strip()
    if not cleaned:
        return cleaned
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _trim(text: str, limit: int) -> str:
    value = _safe_text(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(str(term).lower())}\b", lowered) for term in terms)


def _dedupe_candidates(candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    seen = set()
    unique: List[Dict[str, Any]] = []
    for candidate in candidates:
        key = re.sub(r"[^a-z0-9]+", " ", candidate.get("text", "").lower()).strip()[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
        if len(unique) >= limit:
            break
    return unique


def _dedupe_strings(values: Iterable[Any]) -> List[str]:
    seen = set()
    output = []
    for value in values:
        text = _safe_text(str(value))
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _clamp_float(value: Any, low: float, high: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = low
    return max(low, min(high, numeric))


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
