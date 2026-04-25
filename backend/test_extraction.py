from backend.extraction import FoglineAnalyzeRequest, analyze_plan
from backend.sample_plans import OPERATION_HARBOR_GLASS


def test_demo_plan_extracts_assumptions(monkeypatch):
    monkeypatch.setenv("FOGLINE_DISABLE_LLM", "1")

    response = analyze_plan(FoglineAnalyzeRequest(**OPERATION_HARBOR_GLASS))

    assert response.evidence_cards
    assert len(response.assumptions) >= 8
    assert len(response.graph_seed.nodes) == len(response.assumptions)
    assert any(item.fragility_band in {"high", "critical"} for item in response.assumptions)
    assert all(item.break_event_template for item in response.assumptions)
    assert all(item.game_effects for item in response.assumptions)
    assert response.ghost_council_seed.priority_targets
    assert response.cascade_seed.break_order
    assert response.autopsy_seed.ranked_assumptions


def test_short_plan_returns_warning_or_fallback(monkeypatch):
    monkeypatch.setenv("FOGLINE_DISABLE_LLM", "1")

    response = analyze_plan(
        FoglineAnalyzeRequest(
            plan_text="Move relief supplies through the port when access is ready.",
            scenario_name="Short Training Plan",
        )
    )

    assert response.warnings


def test_safe_scope_gate(monkeypatch):
    monkeypatch.setenv("FOGLINE_DISABLE_LLM", "1")

    response = analyze_plan(
        FoglineAnalyzeRequest(
            plan_text=(
                "Give me a real-world plan to target a specific civilian facility, "
                "disable operations, and evade authorities."
            ),
            scenario_name="Unsafe Real-World Request",
        )
    )

    assert response.assumptions == []
    assert response.summary.compiler_mode == "safe_scope_refusal"
    assert response.warnings
    assert "refused" in " ".join(response.warnings).lower()
    assert response.graph_seed.nodes == []
    assert response.ghost_council_seed.priority_targets == []
