import json

from fastapi.testclient import TestClient

from backend.extraction import (
    FoglineAnalyzeRequest,
    WEIGHTS,
    _parse_llm_json_with_repair,
    analyze_plan,
    build_rag_context,
    load_evidence_catalog,
    match_assumption_to_pattern,
)
from backend.main import app
from backend.sample_plans import OPERATION_HARBOR_GLASS


GAME_RANGES = {
    "low": {"resilience": (-6, -3), "debt": (2, 4)},
    "medium": {"resilience": (-11, -7), "debt": (5, 8)},
    "high": {"resilience": (-18, -12), "debt": (9, 13)},
    "critical": {"resilience": (-25, -19), "debt": (14, 18)},
}

ALLOWED_GAME_METRICS = {
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


def test_fallback_analyze_plan_returns_stable_seeds(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.setenv("FOGLINE_DISABLE_LLM", "1")

    response = analyze_plan(FoglineAnalyzeRequest(**OPERATION_HARBOR_GLASS))
    catalog = load_evidence_catalog()
    valid_pattern_ids = {card["id"] for card in catalog["pattern_cards"]}

    assert response.scenario_name == "Operation Harbor Glass"
    assert response.evidence_cards
    assert response.assumptions
    assert 10 <= len(response.assumptions) <= 14
    assert response.graph_seed.nodes
    assert response.graph_seed.edges
    assert response.ghost_council_seed.focus_assumption_ids
    assert 3 <= len(response.ghost_council_seed.priority_targets) <= 5
    assert response.ghost_council_seed.red_team_guidance
    assert response.cascade_seed.dependency_graph.nodes
    assert response.cascade_seed.break_order
    assert response.cascade_seed.critical_paths
    assert response.cascade_seed.propagation_rules
    assert response.autopsy_seed.assumption_rank
    assert response.autopsy_seed.ranked_assumptions
    assert response.autopsy_seed.audit_fields == [
        "assumption_id",
        "original_status",
        "break_turn",
        "player_response",
        "new_assumptions_created",
        "resilience_delta",
        "decision_debt_delta",
        "final_status",
    ]
    assert response.autopsy_seed.resilience_patch_candidates
    assert len(response.autopsy_seed.better_plan_principles) >= 6
    assert response.warnings

    first = response.assumptions[0]
    expected_score = round(
        sum(getattr(first.score_breakdown, name) * weight for name, weight in WEIGHTS.items()),
        1,
    )
    assert first.fragility_score == expected_score
    assert 0 <= first.fragility_score <= 100
    assert first.status == "intact"
    assert first.break_event_template.player_decision_prompt
    assert response.autopsy_seed.ranked_assumptions[0].assumption_id == first.id
    assert response.autopsy_seed.ranked_assumptions[0].rank == 1
    assert response.autopsy_seed.ranked_assumptions[0].reason
    assert response.autopsy_seed.ranked_assumptions[0].fragility_score == first.fragility_score
    for assumption in response.assumptions:
        assert assumption.pattern_id in valid_pattern_ids
        assert assumption.why_this_pattern_matches
        assert assumption.monitoring_indicators
        assert assumption.resilience_patches
        assert assumption.break_event_template.title
        assert assumption.break_event_template.sitrep
        assert assumption.break_event_template.immediate_effects
        assert assumption.break_event_template.player_decision_prompt
        resilience_min, resilience_max = GAME_RANGES[assumption.fragility_band]["resilience"]
        debt_min, debt_max = GAME_RANGES[assumption.fragility_band]["debt"]
        assert resilience_min <= assumption.game_effects.resilience_delta <= resilience_max
        assert debt_min <= assumption.game_effects.decision_debt_delta <= debt_max
        assert assumption.game_effects.affected_metrics
        assert set(assumption.game_effects.affected_metrics).issubset(ALLOWED_GAME_METRICS)
    for node in response.graph_seed.nodes:
        assert node.status == "intact"
    for edge in response.graph_seed.edges:
        assert edge.id == f"edge_{edge.source}_{edge.target}"
        assert edge.relationship in {"depends_on", "weakens", "blocks_recovery"}
        assert edge.reason
    for rule in response.cascade_seed.propagation_rules:
        assert rule.effect in {"stress", "weaken", "break"}
        assert 0 <= rule.threshold <= 1
        assert rule.delay_ms == 400
        assert rule.reason
    for target in response.ghost_council_seed.priority_targets:
        assert target.assumption_id
        assert target.reason_to_target
        assert target.fragility_score >= 0
        assert isinstance(target.expected_cascade, list)
        assert any(
            trigger in target.prospect_theory_trigger
            for trigger in [
                "loss aversion",
                "overconfidence",
                "sunk-cost pressure",
                "ambiguity aversion",
                "status quo bias",
                "time pressure",
            ]
        )
        assert any(
            safe_word in target.safe_pressure_frame.lower()
            for safe_word in ["pressure", "stress", "degraded", "delay", "uncertainty", "validation", "validate"]
        )
        assert "attack" not in target.safe_pressure_frame.lower()
    for patch in response.autopsy_seed.resilience_patch_candidates:
        assert patch.assumption_id
        assert patch.rewrite_suggestion
        assert patch.monitoring_indicators
        assert patch.fallback_options
        assert patch.validation_questions
    assert "validate critical assumptions before phase transitions" in {
        principle.lower().rstrip(".") for principle in response.autopsy_seed.better_plan_principles
    }

    stable_json = json.dumps(response.model_dump(), sort_keys=True)
    assert "fragility_score" in stable_json
    assert "exact historical statistics" in stable_json


def test_extract_endpoint_works_with_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.setenv("FOGLINE_DISABLE_LLM", "1")

    client = TestClient(app)
    response = client.post("/extract", json=OPERATION_HARBOR_GLASS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "Operation Harbor Glass"
    assert payload["evidence_cards"]
    assert payload["assumptions"]
    assert {"break_event_template", "game_effects"}.issubset(payload["assumptions"][0])
    assert payload["assumptions"][0]["break_event_template"]["immediate_effects"]
    assert payload["assumptions"][0]["game_effects"]["affected_metrics"]
    assert payload["summary"]["total_assumptions"] == len(payload["assumptions"])
    assert payload["graph_seed"]["edges"]
    assert {"id", "source", "target", "relationship", "strength", "reason"}.issubset(
        payload["graph_seed"]["edges"][0]
    )
    assert payload["ghost_council_seed"]["priority_targets"]
    assert payload["ghost_council_seed"]["red_team_guidance"]
    assert {
        "assumption_id",
        "reason_to_target",
        "fragility_score",
        "expected_cascade",
        "prospect_theory_trigger",
        "safe_pressure_frame",
    }.issubset(payload["ghost_council_seed"]["priority_targets"][0])
    assert payload["cascade_seed"]["break_order"]
    assert payload["cascade_seed"]["critical_paths"]
    assert payload["cascade_seed"]["propagation_rules"]
    assert payload["autopsy_seed"]["ranked_assumptions"]
    assert payload["autopsy_seed"]["audit_fields"] == [
        "assumption_id",
        "original_status",
        "break_turn",
        "player_response",
        "new_assumptions_created",
        "resilience_delta",
        "decision_debt_delta",
        "final_status",
    ]
    assert payload["autopsy_seed"]["resilience_patch_candidates"]
    assert payload["autopsy_seed"]["better_plan_principles"]
    assert payload["graph_seed"]["metadata"]["edge_strength_scale"] == "0.0-1.0 rubric"


def test_demo_plan_endpoint():
    client = TestClient(app)
    response = client.get("/demo-plan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_name"] == "Operation Harbor Glass"
    assert payload["domain"] == "fictional_crisis_training"
    assert payload["timeline"] == "48 hours"
    assert "Coalition partner" in payload["actors"]
    assert "Lydora Island" in payload["plan_text"]


def test_evidence_catalog_and_rag_helpers():
    catalog = load_evidence_catalog()
    required_fields = {
        "id",
        "category",
        "description",
        "risk_factors",
        "observable_indicators",
        "mitigation_patterns",
        "base_fragility",
        "safe_historical_analog_summary",
        "doctrine_note",
        "rag_keywords",
    }

    assert len(catalog["pattern_cards"]) == 14
    assert {card["id"] for card in catalog["pattern_cards"]} == {
        "partner_support_stability",
        "logistics_continuity",
        "communications_integrity",
        "intelligence_reliability",
        "civilian_behavior_predictability",
        "infrastructure_availability",
        "weather_environment_stability",
        "cyber_system_availability",
        "timing_synchronization",
        "escalation_containment",
        "authority_and_permissions",
        "resource_sufficiency",
        "command_coordination",
        "information_environment_stability",
    }
    for card in catalog["pattern_cards"]:
        assert required_fields.issubset(card)

    context = build_rag_context(OPERATION_HARBOR_GLASS["plan_text"], catalog)
    assert context
    assert len(json.dumps(context)) < len(json.dumps(catalog))
    assert all("rag_keywords" not in card for card in context)

    match = match_assumption_to_pattern(
        "Partner support will remain aligned through the harbor access window.",
        "partner_support",
        catalog,
    )
    assert match["id"] == "partner_support_stability"
    assert match["matched_keywords"]
    assert match["why_this_pattern_matches"]


def test_llm_json_repair_accepts_strict_or_fenced_json():
    strict_payload, strict_warning = _parse_llm_json_with_repair('{"assumptions": [], "warnings": []}')
    fenced_payload, fenced_warning = _parse_llm_json_with_repair(
        '```json\n{"assumptions": [], "mission_objective_detected": "", "warnings": []}\n```'
    )
    invalid_payload, invalid_warning = _parse_llm_json_with_repair("Here is the JSON: {'assumptions': []}")

    assert strict_payload["assumptions"] == []
    assert strict_warning is None
    assert fenced_payload["assumptions"] == []
    assert fenced_warning is None
    assert invalid_payload == {}
    assert "invalid JSON" in invalid_warning
