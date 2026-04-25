"""Tests for Ghost Council logic — pure functions + mocked LLM calls."""
import pytest
from unittest.mock import AsyncMock, patch

from ghost import (
    _aggression,
    _exploitable_targets,
    _prospect_bias,
    _validate_output,
    run_ghost_council,
)
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


# ── _prospect_bias() ─────────────────────────────────────────────────────────

class TestProspectBias:
    def test_risk_seeking_when_red_weak(self):
        gs = GameState(game_id="g", turn=3,
                       metrics=Metrics(blue_strength=80, red_strength=35))
        assert _prospect_bias(gs) == "risk_seeking"

    def test_risk_seeking_when_blue_strong(self):
        gs = GameState(game_id="g", turn=3,
                       metrics=Metrics(blue_strength=85, red_strength=60))
        assert _prospect_bias(gs) == "risk_seeking"

    def test_loss_aversion_when_red_dominant(self):
        gs = GameState(game_id="g", turn=3,
                       metrics=Metrics(blue_strength=45, red_strength=70))
        assert _prospect_bias(gs) == "loss_aversion"

    def test_neutral_balanced(self):
        gs = GameState(game_id="g", turn=3,
                       metrics=Metrics(blue_strength=60, red_strength=60))
        assert _prospect_bias(gs) == "neutral"


# ── _aggression() ────────────────────────────────────────────────────────────

class TestAggression:
    def test_higher_with_attack_move(self, base_game_state):
        attack = BlueMove(move_type="attack", target="x", description="x", resources_committed=5)
        probe  = BlueMove(move_type="probe",  target="x", description="x", resources_committed=5)
        assert _aggression(base_game_state, attack, "neutral") > _aggression(base_game_state, probe, "neutral")

    def test_higher_with_risk_seeking(self, base_game_state, blue_move_probe):
        risk   = _aggression(base_game_state, blue_move_probe, "risk_seeking")
        neutral = _aggression(base_game_state, blue_move_probe, "neutral")
        assert risk > neutral

    def test_clamped_between_0_and_1(self, base_game_state):
        move = BlueMove(move_type="attack", target="x", description="x", resources_committed=10)
        val = _aggression(base_game_state, move, "risk_seeking")
        assert 0.0 <= val <= 1.0

    def test_rises_with_resources_committed(self, base_game_state):
        low  = BlueMove(move_type="probe", target="x", description="x", resources_committed=1)
        high = BlueMove(move_type="probe", target="x", description="x", resources_committed=9)
        assert _aggression(base_game_state, high, "neutral") > _aggression(base_game_state, low, "neutral")


# ── _exploitable_targets() ───────────────────────────────────────────────────

class TestExploitableTargets:
    def test_filters_by_exploit_window_mid(self, ghost_council_seed, base_game_state):
        # Turn 5 is in the "mid" window (4-7). A3 is mid, A1 is early, A5 is late.
        candidates = _exploitable_targets(ghost_council_seed, base_game_state, turn=5)
        ids = [c.assumption_id for c in candidates]
        assert "A3" in ids
        assert "A1" not in ids     # early window closed at turn 4
        assert "A5" not in ids     # late window starts at turn 8

    def test_fallback_when_no_window_match(self, ghost_council_seed, base_game_state):
        # Turn 20 is past all windows — should fall back to any active target
        candidates = _exploitable_targets(ghost_council_seed, base_game_state, turn=20)
        assert len(candidates) > 0

    def test_excludes_broken_assumptions(self, ghost_council_seed):
        gs = GameState(
            game_id="g", turn=5,
            metrics=Metrics(),
            assumption_statuses={"A3": "broken", "A1": "untested", "A5": "untested"},
        )
        candidates = _exploitable_targets(ghost_council_seed, gs, turn=5)
        ids = [c.assumption_id for c in candidates]
        assert "A3" not in ids

    def test_excludes_validated_assumptions(self, ghost_council_seed):
        gs = GameState(
            game_id="g", turn=5,
            metrics=Metrics(),
            assumption_statuses={"A3": "validated", "A1": "untested", "A5": "untested"},
        )
        candidates = _exploitable_targets(ghost_council_seed, gs, turn=5)
        ids = [c.assumption_id for c in candidates]
        assert "A3" not in ids

    def test_returns_max_3_candidates(self, ghost_council_seed, base_game_state):
        candidates = _exploitable_targets(ghost_council_seed, base_game_state, turn=20)
        assert len(candidates) <= 3

    def test_sorted_by_priority(self, ghost_council_seed, base_game_state):
        candidates = _exploitable_targets(ghost_council_seed, base_game_state, turn=20)
        priorities = [c.target_priority for c in candidates]
        assert priorities == sorted(priorities)

    def test_returns_empty_when_all_broken(self, ghost_council_seed):
        gs = GameState(
            game_id="g", turn=5,
            metrics=Metrics(),
            assumption_statuses={"A3": "broken", "A1": "broken", "A5": "broken"},
        )
        candidates = _exploitable_targets(ghost_council_seed, gs, turn=5)
        assert candidates == []


# ── _validate_output() ───────────────────────────────────────────────────────

class TestValidateOutput:
    def _candidates(self):
        return [
            GhostTarget(assumption_id="A3", fragility_score=0.85, target_priority=1, exploit_window="mid"),
            GhostTarget(assumption_id="A1", fragility_score=0.65, target_priority=2, exploit_window="early"),
        ]

    def test_accepts_valid_output(self):
        raw = {
            "red_move": "Red strikes.",
            "targeted_assumption_id": "A3",
            "reasoning": "Good target.",
            "escalation_level": 3,
            "kinetic": True,
            "proposed_metric_deltas": {"blue_strength": -5, "intl_opinion": -8},
            "stress_events": [
                {"assumption_id": "A3", "stress_type": "exploit", "severity": 82, "explanation": "x"}
            ],
        }
        result = _validate_output(raw, self._candidates())
        assert result.targeted_assumption_id == "A3"
        assert result.escalation_level == 3

    def test_falls_back_on_hallucinated_target_id(self):
        raw = {
            "red_move": "x",
            "targeted_assumption_id": "A99",    # hallucinated
            "reasoning": "x",
            "escalation_level": 2,
            "kinetic": False,
            "proposed_metric_deltas": {},
            "stress_events": [],
        }
        result = _validate_output(raw, self._candidates())
        assert result.targeted_assumption_id == "A3"   # falls back to top candidate

    def test_strips_unknown_metric_keys(self):
        raw = {
            "red_move": "x", "targeted_assumption_id": "A3", "reasoning": "x",
            "escalation_level": 1, "kinetic": False,
            "proposed_metric_deltas": {"blue_strength": -3, "unknown_key": -99},
            "stress_events": [],
        }
        result = _validate_output(raw, self._candidates())
        assert "unknown_key" not in result.proposed_metric_deltas
        assert "blue_strength" in result.proposed_metric_deltas

    def test_removes_hallucinated_stress_event_ids(self):
        raw = {
            "red_move": "x", "targeted_assumption_id": "A3", "reasoning": "x",
            "escalation_level": 2, "kinetic": False,
            "proposed_metric_deltas": {},
            "stress_events": [
                {"assumption_id": "A99", "stress_type": "probe", "severity": 50, "explanation": "x"},
                {"assumption_id": "A3", "stress_type": "exploit", "severity": 80, "explanation": "y"},
            ],
        }
        result = _validate_output(raw, self._candidates())
        ids = [e.assumption_id for e in result.stress_events]
        assert "A99" not in ids
        assert "A3" in ids

    def test_injects_primary_stress_event_when_missing(self):
        raw = {
            "red_move": "x", "targeted_assumption_id": "A3", "reasoning": "x",
            "escalation_level": 2, "kinetic": False,
            "proposed_metric_deltas": {},
            "stress_events": [],             # no events for A3
        }
        result = _validate_output(raw, self._candidates())
        ids = [e.assumption_id for e in result.stress_events]
        assert "A3" in ids                   # injected

    def test_clamps_escalation_level(self):
        raw = {
            "red_move": "x", "targeted_assumption_id": "A3", "reasoning": "x",
            "escalation_level": 99,          # out of bounds
            "kinetic": True,
            "proposed_metric_deltas": {},
            "stress_events": [],
        }
        result = _validate_output(raw, self._candidates())
        assert result.escalation_level == 5  # clamped

    def test_clamps_severity(self):
        raw = {
            "red_move": "x", "targeted_assumption_id": "A3", "reasoning": "x",
            "escalation_level": 2, "kinetic": False,
            "proposed_metric_deltas": {},
            "stress_events": [
                {"assumption_id": "A3", "stress_type": "probe", "severity": 150, "explanation": "x"}
            ],
        }
        result = _validate_output(raw, self._candidates())
        assert result.stress_events[0].severity == 100   # clamped


# ── run_ghost_council() with mocked LLM ──────────────────────────────────────

class TestRunGhostCouncilMocked:
    def _make_request(self, game_state, ghost_council_seed, cascade_seed, blue_move, turn: int | None = None):
        from models import ProcessTurnRequest
        return ProcessTurnRequest(
            game_id=game_state.game_id,
            turn=turn if turn is not None else game_state.turn,
            blue_move=blue_move,
            game_state=game_state,
            ghost_council_seed=ghost_council_seed,
            cascade_seed=cascade_seed,
            assumptions=[
                {"id": "A3", "statement": "Allied political will holds", "tags": ["alliance"]},
                {"id": "A1", "statement": "Air superiority is achievable", "tags": ["military"]},
                {"id": "A5", "statement": "Basing access remains stable", "tags": ["alliance"]},
            ],
        )

    @pytest.mark.asyncio
    async def test_returns_ghost_output_on_success(
        self, base_game_state, ghost_council_seed, cascade_seed, blue_move_attack
    ):
        mock_llm_response = {
            "red_move": "Red launches a limited blockade.",
            "targeted_assumption_id": "A3",
            "reasoning": "Blue assumes allied cohesion holds.",
            "escalation_level": 3,
            "kinetic": True,
            "proposed_metric_deltas": {
                "intl_opinion": -8, "us_domestic": -5, "red_domestic": 7,
                "allied_confidence": -12, "blue_strength": -4, "red_strength": -2,
            },
            "stress_events": [
                {"assumption_id": "A3", "stress_type": "exploit", "severity": 82,
                 "explanation": "Red targets allied political will."}
            ],
        }
        # Use turn=5 so A3 (mid window=4-8) is an exploitable candidate
        req = self._make_request(base_game_state, ghost_council_seed, cascade_seed, blue_move_attack, turn=5)
        with patch("ghost._call_llm", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await run_ghost_council(req)

        assert isinstance(result, GhostOutput)
        assert result.targeted_assumption_id == "A3"
        assert result.escalation_level == 3
        assert result.kinetic is True
        assert result.proposed_metric_deltas["allied_confidence"] == -12

    @pytest.mark.asyncio
    async def test_returns_quiet_probe_when_no_candidates(
        self, ghost_council_seed, cascade_seed, blue_move_probe
    ):
        """When all assumptions are broken, Ghost returns a no-op probe."""
        gs = GameState(
            game_id="test", turn=3,
            metrics=Metrics(blue_strength=80, red_strength=60),
            assumption_statuses={"A3": "broken", "A1": "broken", "A5": "broken"},
        )
        req = self._make_request(gs, ghost_council_seed, cascade_seed, blue_move_probe)
        # _call_llm should NOT be called when there are no candidates
        with patch("ghost._call_llm", new_callable=AsyncMock) as mock_llm:
            result = await run_ghost_council(req)
            mock_llm.assert_not_called()

        assert result.escalation_level == 0
        assert result.targeted_assumption_id == ""

    @pytest.mark.asyncio
    async def test_validates_target_against_candidates(
        self, base_game_state, ghost_council_seed, cascade_seed, blue_move_attack
    ):
        """LLM hallucinating target_id → falls back to top candidate."""
        mock_llm_response = {
            "red_move": "x", "targeted_assumption_id": "X_HALLUCINATED",
            "reasoning": "x", "escalation_level": 2, "kinetic": False,
            "proposed_metric_deltas": {}, "stress_events": [],
        }
        req = self._make_request(base_game_state, ghost_council_seed, cascade_seed, blue_move_attack)
        with patch("ghost._call_llm", new_callable=AsyncMock, return_value=mock_llm_response):
            result = await run_ghost_council(req)

        # Should fall back to A3 (highest priority mid-window candidate at turn=3... actually turn=3 is early-mid boundary)
        # At turn 3, "early" window is range(1,4) so A1 is valid; A3 is "mid" range(4,8) so not in window
        # Fallback is candidates[0] which is whatever comes first after window filter
        assert result.targeted_assumption_id in ("A3", "A1", "A5")  # a valid candidate, not hallucinated
