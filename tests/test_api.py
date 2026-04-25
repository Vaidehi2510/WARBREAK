"""FastAPI endpoint tests — LLM calls are mocked throughout."""
import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app, _ghost_history
from models import (
    BlueMove,
    CascadeSeed,
    GameState,
    GhostCouncilSeed,
    GhostOutput,
    GhostTarget,
    Metrics,
    ProcessTurnRequest,
    PropagationRule,
    StressEvent,
)

client = TestClient(app)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_turn_body(game_id: str = "test-game", turn: int = 3, override: dict | None = None) -> dict:
    body = {
        "game_id": game_id,
        "turn": turn,
        "blue_move": {
            "move_type": "attack",
            "target": "northern_zone",
            "description": "Strike northern installations",
            "resources_committed": 8,
        },
        "game_state": {
            "game_id": game_id,
            "turn": turn,
            "metrics": {
                "intl_opinion": 0, "us_domestic": 0, "red_domestic": 0,
                "allied_confidence": 0, "blue_strength": 80, "red_strength": 60,
            },
            "assumption_statuses": {
                "A1": "untested", "A2": "untested", "A3": "untested",
                "A4": "untested", "A5": "untested",
            },
            "pending_breaks": {},
            "game_over": False,
            "winner": None,
        },
        "ghost_council_seed": {
            "priority_targets": [
                {"assumption_id": "A3", "fragility_score": 0.85, "target_priority": 1, "exploit_window": "mid"},
                {"assumption_id": "A1", "fragility_score": 0.65, "target_priority": 2, "exploit_window": "early"},
            ],
            "red_team_guidance": ["Target allied will."],
        },
        "cascade_seed": {
            "break_order": ["A3", "A5"],
            "critical_paths": [],
            "propagation_rules": [
                {"from_id": "A3", "to_id": "A5", "weight": 0.75, "delay_turns": 0},
            ],
        },
        "assumptions": [
            {"id": "A1", "statement": "Air superiority is achievable", "tags": ["military"]},
            {"id": "A2", "statement": "Supply lines will hold", "tags": ["supply", "military"]},
            {"id": "A3", "statement": "Allied political will holds", "tags": ["alliance", "political"]},
            {"id": "A4", "statement": "Escalation will not occur", "tags": ["political"]},
            {"id": "A5", "statement": "Basing access remains stable", "tags": ["alliance"]},
        ],
    }
    if override:
        body.update(override)
    return body


def _mock_ghost_output() -> GhostOutput:
    return GhostOutput(
        red_move="Red launches a limited blockade.",
        targeted_assumption_id="A3",
        reasoning="Blue assumes allied cohesion holds after a limited strike.",
        escalation_level=3,
        kinetic=True,
        proposed_metric_deltas={
            "intl_opinion": -8, "us_domestic": -5, "red_domestic": 7,
            "allied_confidence": -12, "blue_strength": -4, "red_strength": -2,
        },
        stress_events=[
            StressEvent(
                assumption_id="A3",
                stress_type="exploit",
                severity=82,
                explanation="Red targets allied political will.",
            )
        ],
    )


# ── /health ──────────────────────────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["layer"] == 3


# ── POST /game/{game_id}/turn ─────────────────────────────────────────────────

class TestProcessTurn:
    def setup_method(self):
        _ghost_history.clear()

    def test_successful_turn_returns_correct_shape(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/game/test-game/turn", json=_make_turn_body())

        assert resp.status_code == 200
        data = resp.json()
        assert "ghost_output" in data
        assert "cascade_output" in data
        assert "updated_game_state" in data
        assert "game_over" in data

    def test_ghost_output_contract(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/game/test-game/turn", json=_make_turn_body())

        g = resp.json()["ghost_output"]
        assert isinstance(g["red_move"], str)
        assert isinstance(g["targeted_assumption_id"], str)
        assert isinstance(g["reasoning"], str)
        assert isinstance(g["escalation_level"], int)
        assert isinstance(g["kinetic"], bool)
        assert isinstance(g["proposed_metric_deltas"], dict)
        assert isinstance(g["stress_events"], list)

    def test_cascade_output_contract(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/game/test-game/turn", json=_make_turn_body())

        c = resp.json()["cascade_output"]
        assert "updated_assumptions" in c
        assert "broken_chain" in c
        assert "metric_deltas" in c
        assert "cascade_narrative" in c
        assert "failure_flags" in c
        assert c["status"] in ("active", "failed", "completed")

    def test_cascade_breaks_a3_and_a5(self):
        """A3 breaks (severity 82) → propagates to A5 (weight 0.75)."""
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/game/test-game/turn", json=_make_turn_body())

        c = resp.json()["cascade_output"]
        assert "A3" in c["broken_chain"]
        assert "A5" in c["broken_chain"]

    def test_game_state_updated_with_metric_deltas(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/game/test-game/turn", json=_make_turn_body())

        gs = resp.json()["updated_game_state"]
        # Metrics should be lower than initial 80 (blue_strength gets hit)
        assert gs["metrics"]["blue_strength"] < 80

    def test_game_id_mismatch_returns_422(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            body = _make_turn_body(game_id="game-A")
            resp = client.post("/game/game-B/turn", json=body)  # path vs body mismatch
        assert resp.status_code == 422

    def test_game_over_returns_400(self):
        body = _make_turn_body()
        body["game_state"]["game_over"] = True
        resp = client.post("/game/test-game/turn", json=body)
        assert resp.status_code == 400

    def test_records_ghost_history(self):
        _ghost_history.clear()
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            client.post("/game/test-game/turn", json=_make_turn_body(turn=3))
            client.post("/game/test-game/turn", json=_make_turn_body(turn=4))

        resp = client.get("/game/test-game/ghost-history")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_game_over_propagates_in_response(self):
        """When blue_strength hits 0, game_over should be True."""
        body = _make_turn_body()
        body["game_state"]["metrics"]["blue_strength"] = 3  # barely alive

        dying_ghost = GhostOutput(
            red_move="Final strike.",
            targeted_assumption_id="A3",
            reasoning="x",
            escalation_level=5,
            kinetic=True,
            proposed_metric_deltas={"blue_strength": -10},    # kills it
            stress_events=[
                StressEvent(assumption_id="A3", stress_type="invalidate", severity=95, explanation="x")
            ],
        )
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=dying_ghost):
            resp = client.post("/game/test-game/turn", json=body)

        assert resp.status_code == 200
        assert resp.json()["game_over"] is True


# ── POST /ghost/preview ───────────────────────────────────────────────────────

class TestGhostPreview:
    def _preview_body(self) -> dict:
        return {
            "game_state": {
                "game_id": "preview-game",
                "turn": 3,
                "metrics": {
                    "intl_opinion": 0, "us_domestic": 0, "red_domestic": 0,
                    "allied_confidence": 0, "blue_strength": 80, "red_strength": 60,
                },
                "assumption_statuses": {"A3": "untested", "A1": "untested"},
                "pending_breaks": {}, "game_over": False, "winner": None,
            },
            "ghost_council_seed": {
                "priority_targets": [
                    {"assumption_id": "A3", "fragility_score": 0.85, "target_priority": 1, "exploit_window": "mid"},
                ],
                "red_team_guidance": [],
            },
            "cascade_seed": {"break_order": [], "critical_paths": [], "propagation_rules": []},
            "assumptions": [{"id": "A3", "statement": "Allied political will holds", "tags": ["alliance"]}],
        }

    def test_returns_ghost_output(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/ghost/preview", json=self._preview_body())
        assert resp.status_code == 200
        g = resp.json()
        assert "red_move" in g
        assert "targeted_assumption_id" in g

    def test_does_not_record_history(self):
        _ghost_history.clear()
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            client.post("/ghost/preview", json=self._preview_body())
        assert "preview-game" not in _ghost_history

    def test_accepts_without_blue_move(self):
        body = self._preview_body()
        # blue_move is Optional — omit it
        assert "blue_move" not in body
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            resp = client.post("/ghost/preview", json=body)
        assert resp.status_code == 200


# ── POST /cascade/simulate ────────────────────────────────────────────────────

class TestSimulateCascade:
    def _sim_body(self) -> dict:
        return {
            "ghost_output": {
                "red_move": "Red blockades.",
                "targeted_assumption_id": "A3",
                "reasoning": "x",
                "escalation_level": 3,
                "kinetic": True,
                "proposed_metric_deltas": {"blue_strength": -4, "allied_confidence": -12},
                "stress_events": [
                    {"assumption_id": "A3", "stress_type": "exploit", "severity": 82, "explanation": "x"}
                ],
            },
            "game_state": {
                "game_id": "sim-game",
                "turn": 2,
                "metrics": {
                    "intl_opinion": 0, "us_domestic": 0, "red_domestic": 0,
                    "allied_confidence": 0, "blue_strength": 80, "red_strength": 60,
                },
                "assumption_statuses": {"A3": "untested", "A5": "untested"},
                "pending_breaks": {}, "game_over": False, "winner": None,
            },
            "cascade_seed": {
                "break_order": ["A3"],
                "critical_paths": [],
                "propagation_rules": [
                    {"from_id": "A3", "to_id": "A5", "weight": 0.75, "delay_turns": 0}
                ],
            },
            "assumptions": [
                {"id": "A3", "statement": "Allied political will holds", "tags": ["alliance", "political"]},
                {"id": "A5", "statement": "Basing access remains stable", "tags": ["alliance"]},
            ],
            "current_turn": 2,
        }

    def test_returns_cascade_output(self):
        resp = client.post("/cascade/simulate", json=self._sim_body())
        assert resp.status_code == 200
        c = resp.json()
        assert "broken_chain" in c
        assert "cascade_narrative" in c
        assert "failure_flags" in c

    def test_breaks_propagate(self):
        resp = client.post("/cascade/simulate", json=self._sim_body())
        c = resp.json()
        assert "A3" in c["broken_chain"]
        assert "A5" in c["broken_chain"]   # propagated via 0.75 weight

    def test_invalid_assumption_id_returns_422(self):
        body = self._sim_body()
        body["ghost_output"]["targeted_assumption_id"] = "X_INVALID"
        body["ghost_output"]["stress_events"][0]["assumption_id"] = "X_INVALID"
        resp = client.post("/cascade/simulate", json=body)
        assert resp.status_code == 422


# ── GET /game/{game_id}/ghost-history ─────────────────────────────────────────

class TestGhostHistory:
    def setup_method(self):
        _ghost_history.clear()

    def test_404_when_no_history(self):
        resp = client.get("/game/nonexistent-game/ghost-history")
        assert resp.status_code == 404

    def test_returns_history_entries(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            client.post("/game/hist-game/turn", json=_make_turn_body(game_id="hist-game", turn=1))
            client.post("/game/hist-game/turn", json=_make_turn_body(game_id="hist-game", turn=2))

        resp = client.get("/game/hist-game/ghost-history")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 2
        assert entries[0]["turn"] == 1
        assert entries[1]["turn"] == 2

    def test_history_entry_structure(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            client.post("/game/hist-game/turn", json=_make_turn_body(game_id="hist-game"))

        resp = client.get("/game/hist-game/ghost-history")
        entry = resp.json()[0]
        assert "turn" in entry
        assert "ghost_output" in entry
        assert "cascade_triggered" in entry
        assert "cascade_depth" in entry

    def test_history_isolated_per_game(self):
        with patch("main.run_ghost_council", new_callable=AsyncMock, return_value=_mock_ghost_output()):
            client.post("/game/game-X/turn", json=_make_turn_body(game_id="game-X"))
            client.post("/game/game-X/turn", json=_make_turn_body(game_id="game-X"))

        resp = client.get("/game/game-Y/ghost-history")
        assert resp.status_code == 404
