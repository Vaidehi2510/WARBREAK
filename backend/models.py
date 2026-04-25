from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ─── Shared Metrics (both Ghost and Cascade outputs use this) ────────────────

class Metrics(BaseModel):
    intl_opinion: int = 0
    us_domestic: int = 0
    red_domestic: int = 0
    allied_confidence: int = 0
    blue_strength: int = 100
    red_strength: int = 100


# ─── FOGLINE seeds (passed through from Layer 2) ────────────────────────────

class GhostTarget(BaseModel):
    assumption_id: str
    fragility_score: float = Field(ge=0.0, le=1.0)
    target_priority: int = Field(ge=1)
    exploit_window: Literal["early", "mid", "late"]


class PropagationRule(BaseModel):
    from_id: str
    to_id: str
    weight: float = Field(ge=0.0, le=1.0)
    delay_turns: int = Field(ge=0, default=0)


class CriticalPath(BaseModel):
    path: list[str]
    path_weight: float


class GhostCouncilSeed(BaseModel):
    priority_targets: list[GhostTarget]
    red_team_guidance: list[str]


class CascadeSeed(BaseModel):
    break_order: list[str]
    critical_paths: list[CriticalPath]
    propagation_rules: list[PropagationRule]


# ─── Game state ──────────────────────────────────────────────────────────────

class GameState(BaseModel):
    game_id: str
    turn: int = Field(ge=0)
    metrics: Metrics
    # Maps assumption_id → current status; untested = not yet interacted with
    assumption_statuses: dict[str, Literal["untested", "stressed", "broken", "validated"]] = {}
    pending_breaks: dict[str, int] = {}     # id → turn number it fires
    game_over: bool = False
    winner: Optional[Literal["blue", "red"]] = None


class BlueMove(BaseModel):
    move_type: Literal["attack", "defend", "reposition", "resupply", "probe", "withdraw"]
    target: str
    description: str
    resources_committed: int = Field(ge=1, le=10)


# ─── Ghost Council output (exact TypeScript contract) ───────────────────────

class StressEvent(BaseModel):
    assumption_id: str
    stress_type: Literal["probe", "contradict", "exploit", "invalidate"]
    severity: int = Field(ge=0, le=100)
    explanation: str


class GhostOutput(BaseModel):
    red_move: str
    targeted_assumption_id: str
    reasoning: str
    escalation_level: int = Field(ge=0, le=5)
    kinetic: bool
    proposed_metric_deltas: dict[str, int]  # Partial<Metrics>
    stress_events: list[StressEvent]


# ─── Cascade Engine output (exact TypeScript contract) ──────────────────────

class AssumptionPatch(BaseModel):
    id: str
    status: Literal["untested", "stressed", "broken", "validated"]
    turn_broken: Optional[int] = None


class FailureFlags(BaseModel):
    military_failure: bool = False
    political_failure: bool = False
    alliance_failure: bool = False
    escalation_failure: bool = False


class CascadeOutput(BaseModel):
    updated_assumptions: list[AssumptionPatch]
    broken_chain: list[str]
    metric_deltas: dict[str, int]           # Partial<Metrics>, actual applied deltas
    cascade_narrative: str
    failure_flags: FailureFlags
    status: Literal["active", "failed", "completed"]


# ─── API request / response ──────────────────────────────────────────────────

class ProcessTurnRequest(BaseModel):
    game_id: str
    turn: int
    blue_move: BlueMove
    game_state: GameState
    ghost_council_seed: GhostCouncilSeed
    cascade_seed: CascadeSeed
    assumptions: list[dict[str, Any]]       # full FOGLINE assumption objects


class ProcessTurnResponse(BaseModel):
    ghost_output: GhostOutput
    cascade_output: CascadeOutput
    updated_game_state: GameState
    game_over: bool


class GhostHistoryEntry(BaseModel):
    turn: int
    ghost_output: GhostOutput
    cascade_triggered: bool
    cascade_depth: int                      # number of nodes in broken_chain


class PreviewRequest(BaseModel):
    game_state: GameState
    ghost_council_seed: GhostCouncilSeed
    cascade_seed: CascadeSeed
    assumptions: list[dict[str, Any]]
    blue_move: Optional[BlueMove] = None    # defaults to neutral probe if omitted


class SimulateCascadeRequest(BaseModel):
    ghost_output: GhostOutput               # pass a constructed GhostOutput directly
    game_state: GameState
    cascade_seed: CascadeSeed
    assumptions: list[dict[str, Any]]
    current_turn: int
