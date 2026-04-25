"""Shared fixtures for all test modules."""
import sys
import os

# Ensure backend/ is on the path so imports work from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from models import (
    AssumptionPatch,
    BlueMove,
    CascadeSeed,
    CriticalPath,
    FailureFlags,
    GameState,
    GhostCouncilSeed,
    GhostOutput,
    GhostTarget,
    Metrics,
    PropagationRule,
    StressEvent,
)


@pytest.fixture
def base_metrics() -> Metrics:
    return Metrics(
        intl_opinion=0,
        us_domestic=0,
        red_domestic=0,
        allied_confidence=0,
        blue_strength=80,
        red_strength=60,
    )


@pytest.fixture
def base_game_state(base_metrics) -> GameState:
    return GameState(
        game_id="test-game-1",
        turn=3,
        metrics=base_metrics,
        assumption_statuses={
            "A1": "untested",
            "A2": "untested",
            "A3": "untested",
            "A4": "untested",
            "A5": "untested",
        },
    )


@pytest.fixture
def ghost_council_seed() -> GhostCouncilSeed:
    return GhostCouncilSeed(
        priority_targets=[
            GhostTarget(assumption_id="A3", fragility_score=0.85, target_priority=1, exploit_window="mid"),
            GhostTarget(assumption_id="A1", fragility_score=0.65, target_priority=2, exploit_window="early"),
            GhostTarget(assumption_id="A5", fragility_score=0.50, target_priority=3, exploit_window="late"),
        ],
        red_team_guidance=[
            "Target allied political will — it's the weakest link.",
            "Exploit Blue's assumption that escalation won't occur.",
        ],
    )


@pytest.fixture
def cascade_seed() -> CascadeSeed:
    """
    Graph: A3 → A5 (0.75), A3 → A2 (0.45), A5 → A4 (0.25), A3 → A1 (0.20)
    So breaking A3 should: cascade-break A5, stress A2, miss A4/A1.
    """
    return CascadeSeed(
        break_order=["A3", "A5", "A1"],
        critical_paths=[
            CriticalPath(path=["A3", "A5", "A2"], path_weight=0.8),
        ],
        propagation_rules=[
            PropagationRule(from_id="A3", to_id="A5", weight=0.75, delay_turns=0),
            PropagationRule(from_id="A3", to_id="A2", weight=0.45, delay_turns=0),
            PropagationRule(from_id="A5", to_id="A4", weight=0.25, delay_turns=0),
            PropagationRule(from_id="A3", to_id="A1", weight=0.20, delay_turns=0),
        ],
    )


@pytest.fixture
def sample_assumptions() -> list[dict]:
    return [
        {"id": "A1", "statement": "Air superiority is achievable", "tags": ["military"]},
        {"id": "A2", "statement": "Supply lines will hold", "tags": ["supply", "military"]},
        {"id": "A3", "statement": "Allied political will holds", "tags": ["alliance", "political"]},
        {"id": "A4", "statement": "Escalation will not occur", "tags": ["political"]},
        {"id": "A5", "statement": "Basing access remains stable", "tags": ["alliance"]},
    ]


@pytest.fixture
def blue_move_attack() -> BlueMove:
    return BlueMove(
        move_type="attack",
        target="northern_zone",
        description="Launch strike on northern installations",
        resources_committed=8,
    )


@pytest.fixture
def blue_move_probe() -> BlueMove:
    return BlueMove(
        move_type="probe",
        target="eastern_flank",
        description="Reconnaissance probe",
        resources_committed=3,
    )


@pytest.fixture
def ghost_output_breaking() -> GhostOutput:
    """A GhostOutput that breaks A3 (severity 82 → breaks)."""
    return GhostOutput(
        red_move="Red launches a limited blockade and information campaign framing Blue as the escalator.",
        targeted_assumption_id="A3",
        reasoning="Blue assumes allied cohesion will hold after a limited strike. Red exploits this.",
        escalation_level=3,
        kinetic=True,
        proposed_metric_deltas={
            "intl_opinion": -8,
            "us_domestic": -5,
            "red_domestic": 7,
            "allied_confidence": -12,
            "blue_strength": -4,
            "red_strength": -2,
        },
        stress_events=[
            StressEvent(
                assumption_id="A3",
                stress_type="exploit",
                severity=82,
                explanation="Red targets allied political will by making continued support appear costly.",
            )
        ],
    )


@pytest.fixture
def ghost_output_probing() -> GhostOutput:
    """A GhostOutput that only stresses A1 (severity 40 → stressed, not broken)."""
    return GhostOutput(
        red_move="Red conducts a limited reconnaissance in force along the eastern axis.",
        targeted_assumption_id="A1",
        reasoning="Red probes air defense coverage to assess Blue's response time.",
        escalation_level=1,
        kinetic=False,
        proposed_metric_deltas={
            "intl_opinion": -2,
            "blue_strength": -1,
        },
        stress_events=[
            StressEvent(
                assumption_id="A1",
                stress_type="probe",
                severity=40,
                explanation="Air defense gaps identified but not yet exploited.",
            )
        ],
    )
