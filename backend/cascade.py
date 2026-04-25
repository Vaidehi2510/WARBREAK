from __future__ import annotations
from game_state import GameState, Event, clamp_metric

def apply_event(game: GameState, event: Event) -> GameState:
    game.turn = event.turn
    for metric, delta in event.metric_deltas.items():
        if metric in game.metrics:
            game.metrics[metric] = clamp_metric(game.metrics[metric] + delta)
    game.events.append(event)
    if (game.metrics.get("blue_strength", 100) <= 10 or
        game.metrics.get("us_domestic", 72) <= 15 or
        game.metrics.get("intl_opinion", 50) <= -50):
        game.status = "failed"
    elif game.turn >= game.max_turns:
        game.status = "completed"
    return game
