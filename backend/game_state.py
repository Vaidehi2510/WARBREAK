from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional
from uuid import uuid4
from datetime import datetime, timezone

class Assumption(BaseModel):
    id: str
    text: str
    category: str = "operational"
    confidence: float = Field(ge=0, le=1, default=0.55)
    criticality: float = Field(ge=0, le=1, default=0.55)
    fragility: int = Field(ge=0, le=100, default=60)
    basis: str = ""
    doctrine_ref: str = ""
    dependencies: List[str] = []
    cascade_effect: str = ""
    status: Literal["untested", "stressed", "broken", "validated"] = "untested"
    turn_broken: Optional[int] = None

class Event(BaseModel):
    turn: int
    title: str
    description: str
    blue_move: str = ""
    red_move: str = ""
    ghost_reasoning: str = ""
    ghost_state_text: str = ""
    targeted_assumption_id: str = ""
    broken_chain: List[str] = []
    metric_deltas: Dict[str, int] = {}
    options: List[str] = []

class GameState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    plan: str
    assumptions: List[Assumption]
    turn: int = 0
    max_turns: int = 3
    metrics: Dict[str, int] = Field(default_factory=lambda: {
        "intl_opinion": 50,
        "us_domestic": 72,
        "red_domestic": 61,
        "allied_confidence": 58,
        "blue_strength": 100,
        "red_strength": 100,
    })
    events: List[Event] = []
    status: Literal["active", "failed", "completed"] = "active"
    ghost_loss_aversion: float = 0.8
    ghost_escalation_threshold: float = 0.45

class NewGameRequest(BaseModel):
    plan: str

class TurnRequest(BaseModel):
    game_id: str
    player_action: str

GAMES: dict[str, GameState] = {}

def clamp_metric(value: int) -> int:
    return max(0, min(100, value))

def save_game(game: GameState) -> GameState:
    GAMES[game.id] = game
    return game

def get_game(game_id: str) -> GameState:
    if game_id not in GAMES:
        raise KeyError(f"Game {game_id} not found")
    return GAMES[game_id]
