from __future__ import annotations
from game_state import GameState, Event
from ghost import ghost_response

ACTION_SHIFTS: dict[str, dict[str, int]] = {
    "airstrike":  {"blue_strength":-15,"red_strength":-40,"intl_opinion":-12,"us_domestic":-5,"red_domestic":14,"allied_confidence":6},
    "strike":     {"blue_strength":-15,"red_strength":-40,"intl_opinion":-12,"us_domestic":-5,"red_domestic":14,"allied_confidence":6},
    "attack":     {"blue_strength":-12,"red_strength":-35,"intl_opinion":-10,"us_domestic":-4,"red_domestic":12,"allied_confidence":5},
    "submarine":  {"blue_strength":-2,"red_strength":-20,"intl_opinion":4,"us_domestic":3,"red_domestic":-3,"allied_confidence":8},
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

def _shifts(action: str) -> dict[str, int]:
    a = action.lower()
    for key in ACTION_SHIFTS:
        if key != "default" and key in a:
            return ACTION_SHIFTS[key]
    return ACTION_SHIFTS["default"]

def adjudicate(game: GameState, player_action: str) -> Event:
    shifts = dict(_shifts(player_action))
    ghost = ghost_response(game, player_action)
    targeted_id = ghost.get("targeted_assumption_id", "")
    broken_chain: list[str] = []

    if targeted_id:
        queue = [targeted_id]
        while queue:
            cid = queue.pop(0)
            a = next((x for x in game.assumptions if x.id == cid), None)
            if not a or a.status == "broken":
                continue
            if a.status == "untested":
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
