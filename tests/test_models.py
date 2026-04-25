"""Tests for model schema validation and contract compliance."""
import pytest
from pydantic import ValidationError

from models import (
    AssumptionPatch,
    CascadeOutput,
    CascadeSeed,
    FailureFlags,
    GameState,
    GhostOutput,
    Metrics,
    PropagationRule,
    StressEvent,
)


class TestMetrics:
    def test_defaults(self):
        m = Metrics()
        assert m.blue_strength == 100
        assert m.red_strength == 100
        assert m.intl_opinion == 0

    def test_all_fields_present(self):
        keys = set(Metrics.model_fields.keys())
        assert keys == {"intl_opinion", "us_domestic", "red_domestic",
                        "allied_confidence", "blue_strength", "red_strength"}

    def test_serializes_to_dict(self):
        m = Metrics(blue_strength=80, red_strength=60)
        d = m.model_dump()
        assert d["blue_strength"] == 80
        assert d["red_strength"] == 60


class TestStressEvent:
    def test_valid(self):
        e = StressEvent(
            assumption_id="A3",
            stress_type="exploit",
            severity=82,
            explanation="Test explanation.",
        )
        assert e.severity == 82

    def test_invalid_stress_type(self):
        with pytest.raises(ValidationError):
            StressEvent(
                assumption_id="A3",
                stress_type="destroy",       # not in enum
                severity=50,
                explanation="Bad type.",
            )

    def test_severity_clamped(self):
        with pytest.raises(ValidationError):
            StressEvent(assumption_id="A1", stress_type="probe", severity=101, explanation="x")
        with pytest.raises(ValidationError):
            StressEvent(assumption_id="A1", stress_type="probe", severity=-1, explanation="x")


class TestGhostOutput:
    def test_matches_contract(self, ghost_output_breaking):
        g = ghost_output_breaking
        assert isinstance(g.red_move, str)
        assert isinstance(g.targeted_assumption_id, str)
        assert isinstance(g.reasoning, str)
        assert 0 <= g.escalation_level <= 5
        assert isinstance(g.kinetic, bool)
        assert isinstance(g.proposed_metric_deltas, dict)
        assert isinstance(g.stress_events, list)

    def test_escalation_level_bounds(self):
        with pytest.raises(ValidationError):
            GhostOutput(
                red_move="x", targeted_assumption_id="A1", reasoning="x",
                escalation_level=6,     # out of bounds
                kinetic=False,
                proposed_metric_deltas={},
                stress_events=[],
            )

    def test_proposed_metric_deltas_partial(self):
        # Contract says Partial<Metrics> — not all keys required
        g = GhostOutput(
            red_move="x", targeted_assumption_id="A1", reasoning="x",
            escalation_level=2, kinetic=False,
            proposed_metric_deltas={"blue_strength": -5},
            stress_events=[],
        )
        assert g.proposed_metric_deltas == {"blue_strength": -5}


class TestAssumptionPatch:
    def test_valid_statuses(self):
        for status in ("untested", "stressed", "broken", "validated"):
            p = AssumptionPatch(id="A1", status=status)
            assert p.status == status

    def test_turn_broken_optional(self):
        p = AssumptionPatch(id="A1", status="broken")
        assert p.turn_broken is None
        p2 = AssumptionPatch(id="A1", status="broken", turn_broken=3)
        assert p2.turn_broken == 3

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            AssumptionPatch(id="A1", status="destroyed")     # not in enum


class TestCascadeOutput:
    def test_matches_contract(self):
        out = CascadeOutput(
            updated_assumptions=[AssumptionPatch(id="A3", status="broken", turn_broken=2)],
            broken_chain=["A3"],
            metric_deltas={"intl_opinion": -10, "allied_confidence": -18, "blue_strength": -6},
            cascade_narrative="Once allied cohesion broke...",
            failure_flags=FailureFlags(political_failure=True, alliance_failure=True),
            status="active",
        )
        assert out.status == "active"
        assert "A3" in out.broken_chain
        assert out.failure_flags.alliance_failure is True

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            CascadeOutput(
                updated_assumptions=[],
                broken_chain=[],
                metric_deltas={},
                cascade_narrative="",
                failure_flags=FailureFlags(),
                status="winning",   # not in enum
            )


class TestGameState:
    def test_assumption_statuses_default_empty(self):
        gs = GameState(game_id="g1", turn=0, metrics=Metrics())
        assert gs.assumption_statuses == {}

    def test_pending_breaks_default_empty(self):
        gs = GameState(game_id="g1", turn=0, metrics=Metrics())
        assert gs.pending_breaks == {}

    def test_game_over_default_false(self):
        gs = GameState(game_id="g1", turn=0, metrics=Metrics())
        assert gs.game_over is False
        assert gs.winner is None


class TestPropagationRule:
    def test_weight_bounds(self):
        with pytest.raises(ValidationError):
            PropagationRule(from_id="A1", to_id="A2", weight=1.1)
        with pytest.raises(ValidationError):
            PropagationRule(from_id="A1", to_id="A2", weight=-0.1)

    def test_delay_turns_non_negative(self):
        with pytest.raises(ValidationError):
            PropagationRule(from_id="A1", to_id="A2", weight=0.5, delay_turns=-1)
