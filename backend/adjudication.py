from __future__ import annotations
from game_state import GameState, Event
from ghost import ghost_response

ACTION_SHIFTS: dict[str, dict[str, int]] = {
    "airstrike":  {"blue_strength":-15,"red_strength":-40,"intl_opinion":-12,"us_domestic":-5,"red_domestic":14,"allied_confidence":6},
    "strike":     {"blue_strength":-15,"red_strength":-40,"intl_opinion":-12,"us_domestic":-5,"red_domestic":14,"allied_confidence":6},
    "attack":     {"blue_strength":-12,"red_strength":-35,"intl_opinion":-10,"us_domestic":-4,"red_domestic":12,"allied_confidence":5},
    "submarine":  {"blue_strength":-2,"red_strength":-20,"intl_opinion":4,"us_domestic":3,"red_domestic":-3,"allied_confidence":8},
    "defense":    {"blue_strength":3,"red_strength":-8,"intl_opinion":3,"us_domestic":2,"red_domestic":-1,"allied_confidence":6},
    "reposition": {"blue_strength":0,"red_strength":0,"intl_opinion":2,"us_domestic":-8,"red_domestic":8,"allied_confidence":-10},
    "withdraw":   {"blue_strength":0,"red_strength":0,"intl_opinion":2,"us_domestic":-8,"red_domestic":8,"allied_confidence":-10},
    "sanctions":  {"blue_strength":0,"red_strength":-5,"intl_opinion":14,"us_domestic":5,"red_domestic":6,"allied_confidence":4},
    "negotiate":  {"blue_strength":0,"red_strength":0,"intl_opinion":10,"us_domestic":2,"red_domestic":-4,"allied_confidence":6},
    "cyber":      {"blue_strength":-3,"red_strength":-15,"intl_opinion":-4,"us_domestic":1,"red_domestic":5,"allied_confidence":3},
    "deceive":    {"blue_strength":-2,"red_strength":-10,"intl_opinion":2,"us_domestic":2,"red_domestic":-2,"allied_confidence":4},
    "surge":      {"blue_strength":-10,"red_strength":-30,"intl_opinion":-8,"us_domestic":-3,"red_domestic":12,"allied_confidence":5},
    "pause":      {"blue_strength":0,"red_strength":0,"intl_opinion":3,"us_domestic":1,"red_domestic":-1,"allied_confidence":2},
    "isr":        {"blue_strength":0,"red_strength":0,"intl_opinion":1,"us_domestic":2,"red_domestic":-1,"allied_confidence":3},
    "coalition":  {"blue_strength":0,"red_strength":0,"intl_opinion":8,"us_domestic":4,"red_domestic":-3,"allied_confidence":12},
    "evacuate":   {"blue_strength":-2,"red_strength":0,"intl_opinion":5,"us_domestic":3,"red_domestic":-2,"allied_confidence":4},
    "logistics":  {"blue_strength":5,"red_strength":0,"intl_opinion":0,"us_domestic":2,"red_domestic":0,"allied_confidence":2},
    "adapt":      {"blue_strength":0,"red_strength":0,"intl_opinion":2,"us_domestic":3,"red_domestic":-1,"allied_confidence":2},
    "default":    {"blue_strength":-5,"red_strength":-5,"intl_opinion":-2,"us_domestic":-2,"red_domestic":3,"allied_confidence":-2},
}

ACTION_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("logistics", ("sealift", "logistics", "sustainment", "repair", "resupply")),
    ("isr", ("p-8", "poseidon", "mq-9", "reaper", "drone", "isr", "patrol", "watch", "track", "surveillance", "hunt")),
    ("defense", ("aegis", "patriot", "pac-3", "missile defense", "defend", "protect", "intercept")),
    ("cyber", ("cyber", "electronic", "growler", "network")),
    ("submarine", ("virginia", "submarine", "underwater", "sea lanes")),
    ("coalition", ("coalition", "allied support", "partner support")),
    ("evacuate", ("evacuate", "evacuation")),
    ("strike", ("carrier strike", "f-35", "airstrike", "strike", "raid", "hit")),
    ("attack", ("attack",)),
    ("surge", ("surge",)),
    ("pause", ("pause",)),
    ("adapt", ("adapt",)),
]

STABILIZING_ACTIONS = {"isr", "defense", "logistics", "coalition", "evacuate"}

def _action_key(action: str) -> str:
    a = action.lower()
    for key, patterns in ACTION_PATTERNS:
        if any(pattern in a for pattern in patterns):
            return key
    return "default"

def _shifts(action: str) -> dict[str, int]:
    return ACTION_SHIFTS[_action_key(action)]

def _apply_assumption_pressure(game: GameState, targeted_id: str, action_key: str, shifts: dict[str, int]) -> list[str]:
    if not targeted_id:
        return []

    if action_key in STABILIZING_ACTIONS:
        assumption = next((x for x in game.assumptions if x.id == targeted_id), None)
        if assumption and assumption.status in {"untested", "stressed"}:
            assumption.status = "validated"
        return []

    broken_chain: list[str] = []
    queue = [targeted_id]
    while queue:
        cid = queue.pop(0)
        a = next((x for x in game.assumptions if x.id == cid), None)
        if not a or a.status == "broken":
            continue
        if a.status in {"untested", "validated"}:
            a.status = "stressed"
        else:
            a.status = "broken"
            a.turn_broken = game.turn + 1
            broken_chain.append(cid)
            p = a.fragility / 100
            shifts["blue_strength"] = shifts.get("blue_strength", 0) - int(p * 15)
            shifts["intl_opinion"] = shifts.get("intl_opinion", 0) - int(p * 8)
            shifts["us_domestic"] = shifts.get("us_domestic", 0) - int(p * 5)
            for dep in a.dependencies:
                if dep not in broken_chain:
                    queue.append(dep)
    return broken_chain

def preview_adjudication(player_action: str, turn: int = 1) -> Event:
    shifts = dict(_shifts(player_action))
    return Event(
        turn=turn,
        title=f"Turn {turn} BDA preview",
        description="Fast deterministic battle-damage preview from the adjudication metric model.",
        blue_move=player_action,
        red_move="Full Ghost Council response still processing.",
        ghost_reasoning="Preliminary BDA only; final adjudication may refine the opponent response and assumption chain.",
        ghost_state_text="Preview mode.",
        targeted_assumption_id="",
        broken_chain=[],
        metric_deltas=shifts,
        options=[],
    )

def adjudicate(game: GameState, player_action: str) -> Event:
    action_key = _action_key(player_action)
    shifts = dict(_shifts(player_action))
    ghost = ghost_response(game, player_action)
    targeted_id = ghost.get("targeted_assumption_id", "")
    broken_chain = _apply_assumption_pressure(game, targeted_id, action_key, shifts)

    options = (
        ["Activate contingency protocol", "Rewrite vulnerable assumption",
         "Request allied support", "Fall back to defensive posture"]
        if broken_chain else
        ["Adapt the plan", "Accept risk", "Pause for intelligence", "Shift to coalition messaging"]
    )

    return Event(
        turn=game.turn + 1,
        title=f"Turn {game.turn + 1} resolved",
        description=ghost.get("reasoning", "The adversary has responded."),
        blue_move=player_action,
        red_move=ghost.get("red_move", ""),
        ghost_reasoning=ghost.get("reasoning", ""),
        ghost_state_text=ghost.get("ghost_state", ""),
        targeted_assumption_id=targeted_id,
        broken_chain=broken_chain,
        metric_deltas=shifts,
        options=options,
    )
