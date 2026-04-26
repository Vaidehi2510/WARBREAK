from __future__ import annotations
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIStatusError, OpenAIError
from pydantic import BaseModel, Field
from typing import Any, List

from extraction import FoglineAnalyzeRequest, FoglineAnalyzeResponse, analyze_plan, extract_assumptions
from adjudication import adjudicate, preview_adjudication
from cascade import apply_event
from autopsy import generate_autopsy
from intel import generate_intel_briefing
from game_state import BDAPreviewRequest, GameState, NewGameRequest, TurnRequest, clamp_metric, save_game, get_game
from llm_client import MODEL, PROVIDER, provider_status

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
    return {
        "ok": True,
        "version": "2.0.0",
        "provider": PROVIDER,
        "model": MODEL,
        "providers": provider_status,
    }

@app.get("/health/startup")
def startup_health():
    return {
        "ok": True,
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API")),
        "provider_order": os.getenv("LLM_PROVIDER_ORDER", "openrouter,gemini,openai"),
        "runtime": "vercel" if os.getenv("VERCEL") else "local",
    }

def ai_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, APIStatusError):
        message = str(exc)
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = str(error["message"])
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        return HTTPException(status_code=status_code, detail=message)
    if isinstance(exc, OpenAIError):
        return HTTPException(502, "LLM provider request failed. Check API keys, model names, and network connection.")
    if isinstance(exc, RuntimeError):
        message = str(exc)
        if "No LLM providers configured" in message or "API key is not configured" in message:
            return HTTPException(503, message)
        if "All LLM providers failed" in message:
            return HTTPException(502, message)
    if isinstance(exc, json.JSONDecodeError):
        return HTTPException(502, "LLM provider returned invalid JSON. Try again, or use a more explicit plan.")
    if isinstance(exc, ValueError):
        return HTTPException(502, str(exc))
    return HTTPException(500, "AI generation failed. Check the backend logs for details.")

# ── Intel Briefing (OSINT prediction) ────────────────────────────────────────
class IntelRequest(BaseModel):
    scenario: str
    adversary: str
    blue_assets: List[Any] = Field(default_factory=list)

def normalize_blue_assets(assets: List[Any]) -> List[str]:
    names: List[str] = []
    for asset in assets:
        if isinstance(asset, str):
            name = asset
        elif isinstance(asset, dict):
            name = str(asset.get("name") or asset.get("id") or "")
        else:
            name = str(asset)
        name = name.strip()
        if name:
            names.append(name)
    return names

@app.post("/intel")
def intel_briefing(req: IntelRequest):
    try:
        return generate_intel_briefing(req.scenario, req.adversary, normalize_blue_assets(req.blue_assets))
    except (APIStatusError, OpenAIError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        raise ai_http_error(exc) from exc

# ── FOGLINE compiler ──────────────────────────────────────────────────────────
@app.post("/extract", response_model=FoglineAnalyzeResponse)
def extract_fogline(req: FoglineAnalyzeRequest):
    return analyze_plan(req)

# ── Game CRUD ─────────────────────────────────────────────────────────────────
@app.post("/games", response_model=GameState)
def create_game(req: NewGameRequest):
    if len(req.plan.strip()) < 20:
        raise HTTPException(400, "Plan must be at least 20 characters.")
    try:
        assumptions = extract_assumptions(req.plan)
    except (APIStatusError, OpenAIError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        raise ai_http_error(exc) from exc
    max_turns = max(1, min(12, int(req.max_turns or 3)))
    game = GameState(plan=req.plan, assumptions=assumptions, max_turns=max_turns)
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
    try:
        event = adjudicate(game, req.player_action)
    except (APIStatusError, OpenAIError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        raise ai_http_error(exc) from exc
    return save_game(apply_event(game, event))

@app.post("/turn/preview")
def preview_turn(req: BDAPreviewRequest):
    event = preview_adjudication(req.player_action, max(1, int(req.turn or 1)))
    metrics = dict(req.metrics or {})
    for metric, delta in event.metric_deltas.items():
        if metric in metrics:
            metrics[metric] = clamp_metric(int(metrics[metric]) + int(delta))

    event_data = event.model_dump() if hasattr(event, "model_dump") else event.dict()
    event_data["preview"] = True
    return {
        "preview": True,
        "turn": event.turn,
        "max_turns": max(1, min(12, int(req.max_turns or 3))),
        "metrics": metrics,
        "events": [event_data],
    }

# ── Autopsy ───────────────────────────────────────────────────────────────────
@app.get("/autopsy/{game_id}")
def autopsy(game_id: str):
    try:
        game = get_game(game_id)
    except KeyError:
        raise HTTPException(404, "Game not found")
    try:
        return generate_autopsy(game)
    except (APIStatusError, OpenAIError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        raise ai_http_error(exc) from exc
