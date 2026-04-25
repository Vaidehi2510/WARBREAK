from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from extraction import extract_assumptions
from adjudication import adjudicate
from cascade import apply_event
from autopsy import generate_autopsy
from game_state import GameState, NewGameRequest, TurnRequest, save_game, get_game

app = FastAPI(title="WARBREAK API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True, "model": "meta-llama/llama-3.3-70b-instruct:free"}

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

@app.get("/autopsy/{game_id}")
def autopsy(game_id: str):
    try:
        game = get_game(game_id)
    except KeyError:
        raise HTTPException(404, "Game not found")
    return generate_autopsy(game)
