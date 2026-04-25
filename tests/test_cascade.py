"""Tests for the Cascade Engine — pure deterministic logic, no LLM."""
import pytest

from cascade import (
    _build_adjacency,
    _compute_failure_flags,
    _build_narrative,
    apply_delta,
    trigger,
)
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


# ── trigger() ────────────────────────────────────────────────────────────────

class TestTrigger:
    def test_primary_break_severity_above_70(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        """severity=82 on A3 → A3 breaks, appears in broken_chain."""
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        assert "A3" in result.broken_chain
        assert result.broken_chain[0] == "A3"

    def test_cascades_downstream_on_strong_link(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        """A3 → A5 weight=0.75 (>= 0.70) → A5 should also break."""
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        assert "A5" in result.broken_chain

    def test_stress_on_medium_link(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        """A3 → A2 weight=0.45 (>= 0.30, < 0.70) → A2 stressed, not broken."""
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        assert "A2" not in result.broken_chain
        stressed_ids = {p.id for p in result.updated_assumptions if p.status == "stressed"}
        assert "A2" in stressed_ids

    def test_near_miss_below_threshold(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        """A3 → A1 weight=0.20 (< 0.30) → A1 not broken, not stressed."""
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        assert "A1" not in result.broken_chain
        patched_ids = {p.id for p in result.updated_assumptions}
        assert "A1" not in patched_ids

    def test_probe_severity_stresses_not_breaks(
        self, ghost_output_probing, base_game_state, cascade_seed, sample_assumptions
    ):
        """severity=40 on A1 → A1 stressed, not broken."""
        result = trigger(ghost_output_probing, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        assert "A1" not in result.broken_chain
        stressed_ids = {p.id for p in result.updated_assumptions if p.status == "stressed"}
        assert "A1" in stressed_ids

    def test_severity_below_30_no_change(
        self, base_game_state, cascade_seed, sample_assumptions
    ):
        """severity=20 < 30 → no status change for assumption."""
        ghost_out = GhostOutput(
            red_move="Quiet probe.",
            targeted_assumption_id="A4",
            reasoning="Testing low severity.",
            escalation_level=0,
            kinetic=False,
            proposed_metric_deltas={},
            stress_events=[
                StressEvent(assumption_id="A4", stress_type="probe", severity=20, explanation="Minor probe.")
            ],
        )
        result = trigger(ghost_out, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        assert "A4" not in result.broken_chain
        patched_ids = {p.id for p in result.updated_assumptions}
        assert "A4" not in patched_ids

    def test_does_not_cascade_already_broken(
        self, ghost_output_breaking, cascade_seed, sample_assumptions
    ):
        """Already-broken assumptions are skipped during propagation."""
        state = GameState(
            game_id="test",
            turn=3,
            metrics=Metrics(blue_strength=80, red_strength=60),
            assumption_statuses={
                "A1": "untested",
                "A2": "untested",
                "A3": "untested",
                "A4": "untested",
                "A5": "broken",         # already broken
            },
        )
        result = trigger(ghost_output_breaking, state, cascade_seed, sample_assumptions, current_turn=3)
        # A5 is already broken — should not appear twice in broken_chain
        assert result.broken_chain.count("A5") <= 1

    def test_deferred_break_marks_stressed(
        self, base_game_state, sample_assumptions
    ):
        """delay_turns > 0 → assumption is marked stressed, not broken."""
        seed = CascadeSeed(
            break_order=["A3"],
            critical_paths=[],
            propagation_rules=[
                PropagationRule(from_id="A3", to_id="A5", weight=0.80, delay_turns=2),
            ],
        )
        ghost_out = GhostOutput(
            red_move="Strike.", targeted_assumption_id="A3", reasoning="x",
            escalation_level=3, kinetic=True,
            proposed_metric_deltas={"blue_strength": -5},
            stress_events=[StressEvent(assumption_id="A3", stress_type="invalidate", severity=90, explanation="x")],
        )
        result = trigger(ghost_out, base_game_state, seed, sample_assumptions, current_turn=3)
        assert "A3" in result.broken_chain
        assert "A5" not in result.broken_chain
        stressed_ids = {p.id for p in result.updated_assumptions if p.status == "stressed"}
        assert "A5" in stressed_ids

    def test_metric_amplification_with_cascade(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        """Cascading additional breaks amplify metric deltas beyond ghost's proposal."""
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        # 2 cascade breaks (A3 primary, A5 cascade) → amplification = 1 + 1*0.30 = 1.30
        # blue_strength proposed = -4, amplified → int(-4 * 1.30) = -5
        assert result.metric_deltas.get("blue_strength", 0) <= -4    # amplified or equal
        assert result.metric_deltas.get("blue_strength", 0) >= -8    # sanity cap

    def test_no_amplification_when_no_cascade(
        self, ghost_output_probing, base_game_state, cascade_seed, sample_assumptions
    ):
        """No cascade breaks → metric_deltas equal to proposed (amplification = 1.0)."""
        result = trigger(ghost_output_probing, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        # A1 has no outgoing rules → no cascades
        assert result.metric_deltas.get("blue_strength") == int(-1 * 1.0)

    def test_turn_broken_set_correctly(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        """Broken assumptions should have turn_broken = current_turn."""
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=5)
        for patch in result.updated_assumptions:
            if patch.status == "broken":
                assert patch.turn_broken == 5

    def test_status_active_when_assumptions_remain(
        self, ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions
    ):
        result = trigger(ghost_output_breaking, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        # A1, A4 remain active after the cascade
        assert result.status == "active"

    def test_status_failed_when_all_broken(
        self, cascade_seed, sample_assumptions
    ):
        """If blue_strength drops to zero, status = failed."""
        state = GameState(
            game_id="test",
            turn=3,
            metrics=Metrics(blue_strength=3, red_strength=60),   # nearly dead
            assumption_statuses={"A3": "untested"},
        )
        ghost_out = GhostOutput(
            red_move="Final blow.", targeted_assumption_id="A3", reasoning="x",
            escalation_level=5, kinetic=True,
            proposed_metric_deltas={"blue_strength": -10},        # kills it
            stress_events=[StressEvent(assumption_id="A3", stress_type="invalidate", severity=95, explanation="x")],
        )
        no_prop_seed = CascadeSeed(break_order=[], critical_paths=[], propagation_rules=[])
        result = trigger(ghost_out, state, no_prop_seed, sample_assumptions, current_turn=3)
        assert result.status == "failed"

    def test_updated_assumptions_only_changed(
        self, ghost_output_probing, base_game_state, cascade_seed, sample_assumptions
    ):
        """Only assumptions that changed status appear in updated_assumptions."""
        result = trigger(ghost_output_probing, base_game_state, cascade_seed, sample_assumptions, current_turn=3)
        patched_ids = {p.id for p in result.updated_assumptions}
        # Only A1 changes (probe → stressed)
        assert "A1" in patched_ids
        assert "A3" not in patched_ids     # not targeted by probe ghost_output
        assert "A4" not in patched_ids


# ── _compute_failure_flags() ─────────────────────────────────────────────────

class TestFailureFlags:
    def test_alliance_failure_from_tags(self, sample_assumptions):
        flags = _compute_failure_flags(
            broken_chain=["A3"],        # A3 has "alliance" tag
            metric_deltas={"allied_confidence": -5},
            escalation_level=2,
            assumptions=sample_assumptions,
        )
        assert flags.alliance_failure is True

    def test_military_failure_from_metric(self, sample_assumptions):
        flags = _compute_failure_flags(
            broken_chain=["A4"],        # A4 has "political" tag only
            metric_deltas={"blue_strength": -16},   # crosses -15 threshold
            escalation_level=2,
            assumptions=sample_assumptions,
        )
        assert flags.military_failure is True

    def test_political_failure_from_tags(self, sample_assumptions):
        flags = _compute_failure_flags(
            broken_chain=["A4"],        # A4 has "political" tag
            metric_deltas={},
            escalation_level=1,
            assumptions=sample_assumptions,
        )
        assert flags.political_failure is True

    def test_escalation_failure_at_level_4(self, sample_assumptions):
        flags = _compute_failure_flags(
            broken_chain=[],
            metric_deltas={},
            escalation_level=4,
            assumptions=sample_assumptions,
        )
        assert flags.escalation_failure is True

    def test_no_flags_when_clean(self, sample_assumptions):
        flags = _compute_failure_flags(
            broken_chain=[],
            metric_deltas={"blue_strength": -3},
            escalation_level=1,
            assumptions=sample_assumptions,
        )
        assert flags.military_failure is False
        assert flags.political_failure is False
        assert flags.alliance_failure is False
        assert flags.escalation_failure is False


# ── apply_delta() ────────────────────────────────────────────────────────────

class TestApplyDelta:
    def test_metrics_updated(self, base_game_state):
        cascade_out = CascadeOutput(
            updated_assumptions=[],
            broken_chain=[],
            metric_deltas={"blue_strength": -10, "intl_opinion": -5},
            cascade_narrative="Test.",
            failure_flags=FailureFlags(),
            status="active",
        )
        updated = apply_delta(base_game_state, cascade_out)
        assert updated.metrics.blue_strength == 70   # 80 - 10
        assert updated.metrics.intl_opinion == -5

    def test_assumption_patches_applied(self, base_game_state):
        cascade_out = CascadeOutput(
            updated_assumptions=[
                AssumptionPatch(id="A3", status="broken", turn_broken=3),
                AssumptionPatch(id="A5", status="stressed"),
            ],
            broken_chain=["A3"],
            metric_deltas={},
            cascade_narrative="Test.",
            failure_flags=FailureFlags(),
            status="active",
        )
        updated = apply_delta(base_game_state, cascade_out)
        assert updated.assumption_statuses["A3"] == "broken"
        assert updated.assumption_statuses["A5"] == "stressed"

    def test_game_over_when_blue_strength_zero(self, base_game_state):
        cascade_out = CascadeOutput(
            updated_assumptions=[],
            broken_chain=[],
            metric_deltas={"blue_strength": -100},   # drops to 0
            cascade_narrative="x",
            failure_flags=FailureFlags(),
            status="failed",
        )
        updated = apply_delta(base_game_state, cascade_out)
        assert updated.game_over is True
        assert updated.winner == "red"

    def test_game_over_when_no_active_assumptions(self, base_game_state):
        # Mark all assumptions broken via patches
        patches = [AssumptionPatch(id=aid, status="broken") for aid in base_game_state.assumption_statuses]
        cascade_out = CascadeOutput(
            updated_assumptions=patches,
            broken_chain=list(base_game_state.assumption_statuses.keys()),
            metric_deltas={},
            cascade_narrative="x",
            failure_flags=FailureFlags(),
            status="failed",
        )
        updated = apply_delta(base_game_state, cascade_out)
        assert updated.game_over is True

    def test_does_not_mutate_input(self, base_game_state):
        original_strength = base_game_state.metrics.blue_strength
        cascade_out = CascadeOutput(
            updated_assumptions=[],
            broken_chain=[],
            metric_deltas={"blue_strength": -20},
            cascade_narrative="x",
            failure_flags=FailureFlags(),
            status="active",
        )
        apply_delta(base_game_state, cascade_out)
        assert base_game_state.metrics.blue_strength == original_strength   # unchanged

    def test_pending_breaks_fire_on_turn(self):
        gs = GameState(
            game_id="test",
            turn=5,
            metrics=Metrics(blue_strength=80, red_strength=60),
            assumption_statuses={"A1": "stressed", "A2": "untested"},
            pending_breaks={"A1": 5},   # fires this turn
        )
        cascade_out = CascadeOutput(
            updated_assumptions=[],
            broken_chain=[],
            metric_deltas={},
            cascade_narrative="x",
            failure_flags=FailureFlags(),
            status="active",
        )
        updated = apply_delta(gs, cascade_out)
        assert updated.assumption_statuses["A1"] == "broken"
        assert "A1" not in updated.pending_breaks

    def test_pending_breaks_do_not_fire_early(self):
        gs = GameState(
            game_id="test",
            turn=4,
            metrics=Metrics(blue_strength=80, red_strength=60),
            assumption_statuses={"A1": "stressed"},
            pending_breaks={"A1": 6},   # fires on turn 6, not now
        )
        cascade_out = CascadeOutput(
            updated_assumptions=[],
            broken_chain=[],
            metric_deltas={},
            cascade_narrative="x",
            failure_flags=FailureFlags(),
            status="active",
        )
        updated = apply_delta(gs, cascade_out)
        assert updated.assumption_statuses["A1"] == "stressed"  # not broken yet
        assert "A1" in updated.pending_breaks


# ── _build_adjacency() ───────────────────────────────────────────────────────

class TestBuildAdjacency:
    def test_correct_structure(self, cascade_seed):
        adj = _build_adjacency(cascade_seed)
        assert "A3" in adj
        neighbors = {t[0] for t in adj["A3"]}
        assert neighbors == {"A5", "A2", "A1"}

    def test_weights_preserved(self, cascade_seed):
        adj = _build_adjacency(cascade_seed)
        a3_neighbors = {t[0]: t[1] for t in adj["A3"]}
        assert a3_neighbors["A5"] == 0.75
        assert a3_neighbors["A2"] == 0.45

    def test_no_outgoing_from_leaf(self, cascade_seed):
        adj = _build_adjacency(cascade_seed)
        assert "A1" not in adj or adj.get("A1") == []
