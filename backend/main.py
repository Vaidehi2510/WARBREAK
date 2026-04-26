from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from extraction import extract_assumptions
from adjudication import adjudicate
from cascade import apply_event
from autopsy import generate_autopsy
from intel import generate_intel_briefing
from game_state import GameState, NewGameRequest, TurnRequest, save_game, get_game

app = FastAPI(title="WARBREAK API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"ok": True, "version": "2.0.0", "model": "meta-llama/llama-3.3-70b-instruct:free"}

# ── Intel Briefing (OSINT prediction) ────────────────────────────────────────
class IntelRequest(BaseModel):
    scenario: str
    adversary: str
    blue_assets: List[str] = []

@app.post("/intel")
def intel_briefing(req: IntelRequest):
    try:
        return generate_intel_briefing(req.scenario, req.adversary, req.blue_assets)
    except Exception as e:
        raise HTTPException(500, f"Intel generation failed: {str(e)}")

# ── Game CRUD ─────────────────────────────────────────────────────────────────
@app.post("/games", response_model=GameState)
def create_game(req: NewGameRequest):
    if len(req.plan.strip()) < 20:
        raise HTTPException(400, "Plan must be at least 20 characters.")
    game = GameState(plan=req.plan, assumptions=extract_assumptions(req.plan))
    return save_game(game)

@app.get("/games/{game_id}", response_model=GameState)
def read_game(game_id: str):
    try:
        return get_game(game_id)
    except KeyError:
        raise HTTPException(404, "Game not found")

# ── Turn ──────────────────────────────────────────────────────────────────────
@app.post("/turn", response_model=GameState)
def play_turn(req: TurnRequest):
    try:
        game = get_game(req.game_id)
    except KeyError:
        raise HTTPException(404, "Game not found")
    if game.status != "active":
        raise HTTPException(400, f"Game is {game.status}. Fetch /autopsy/{req.game_id}")
    event = adjudicate(game, req.player_action)
    return save_game(apply_event(game, event))

# ── Autopsy ───────────────────────────────────────────────────────────────────
@app.get("/autopsy/{game_id}")
def autopsy(game_id: str):
    try:
        game = get_game(game_id)
    except KeyError:
        raise HTTPException(404, "Game not found")
    return generate_autopsy(game)
