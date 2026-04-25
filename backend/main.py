from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from cascade import apply_delta, trigger
from ghost import run_ghost_council
from models import (
    BlueMove,
    CascadeOutput,
    GhostHistoryEntry,
    GhostOutput,
    PreviewRequest,
    ProcessTurnRequest,
    ProcessTurnResponse,
    SimulateCascadeRequest,
)

app = FastAPI(
    title="WARBREAK — Layer 3: Ghost Council & Cascade Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory ghost history per game_id
_ghost_history: dict[str, list[GhostHistoryEntry]] = defaultdict(list)

_NEUTRAL_PROBE = BlueMove(
    move_type="probe",
    target="unknown",
    description="preview call — neutral probe",
    resources_committed=5,
)


# ─── Primary endpoint (called by Wargame Engine each turn) ──────────────────

@app.post("/game/{game_id}/turn", response_model=ProcessTurnResponse)
async def process_turn(game_id: str, req: ProcessTurnRequest):
    """
    Ghost Council decides what Red does and which assumption to stress.
    Cascade Engine propagates the break and computes final metric deltas.
    Returns updated game state and full outputs for both subsystems.
    """
    if req.game_id != game_id:
        raise HTTPException(status_code=422, detail="game_id in path and body must match")
    if req.game_state.game_over:
        raise HTTPException(status_code=400, detail="Game is already over")

    ghost_out: GhostOutput = await run_ghost_council(req)

    updated_state = deepcopy(req.game_state)
    updated_state.turn = req.turn

    cascade_out: CascadeOutput = trigger(
        ghost_output=ghost_out,
        game_state=updated_state,
        cascade_seed=req.cascade_seed,
        assumptions=req.assumptions,
        current_turn=req.turn,
    )
    updated_state = apply_delta(updated_state, cascade_out)

    _ghost_history[game_id].append(GhostHistoryEntry(
        turn=req.turn,
        ghost_output=ghost_out,
        cascade_triggered=bool(cascade_out.broken_chain),
        cascade_depth=len(cascade_out.broken_chain),
    ))

    return ProcessTurnResponse(
        ghost_output=ghost_out,
        cascade_output=cascade_out,
        updated_game_state=updated_state,
        game_over=updated_state.game_over,
    )


# ─── Debug / integration endpoints ──────────────────────────────────────────

@app.post("/ghost/preview", response_model=GhostOutput)
async def ghost_preview(req: PreviewRequest):
    """
    Dry-run Ghost Council without state mutation or history recording.
    Wargame Engine and frontend teams use this to validate integration.
    """
    turn_req = ProcessTurnRequest(
        game_id=req.game_state.game_id,
        turn=req.game_state.turn,
        blue_move=req.blue_move or _NEUTRAL_PROBE,
        game_state=req.game_state,
        ghost_council_seed=req.ghost_council_seed,
        cascade_seed=req.cascade_seed,
        assumptions=req.assumptions,
    )
    return await run_ghost_council(turn_req)


@app.post("/cascade/simulate", response_model=CascadeOutput)
async def simulate_cascade(req: SimulateCascadeRequest):
    """
    Directly trigger a cascade using a pre-built GhostOutput.
    Frontend uses this to test CascadeOverlay animations without a full turn.
    """
    aid = req.ghost_output.targeted_assumption_id
    if aid and aid not in req.game_state.assumption_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"'{aid}' is not in assumption_statuses",
        )
    return trigger(
        ghost_output=req.ghost_output,
        game_state=req.game_state,
        cascade_seed=req.cascade_seed,
        assumptions=req.assumptions,
        current_turn=req.current_turn,
    )


@app.get("/game/{game_id}/ghost-history", response_model=list[GhostHistoryEntry])
async def get_ghost_history(game_id: str):
    """
    Full adversary decision log. Consumed by Failure Autopsy (Layer 5)
    to reconstruct the enemy's strategy and reasoning turn by turn.
    """
    if game_id not in _ghost_history:
        raise HTTPException(status_code=404, detail=f"No history for game '{game_id}'")
    return _ghost_history[game_id]


@app.get("/health")
def health():
    return {"status": "ok", "layer": 3}
