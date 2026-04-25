# Layer 3 — Ghost Council Adversary & Cascade Engine

## Overview

Layer 3 is the adversarial core of WARBREAK. It sits between the Wargame Engine (Layer 2) and the Failure Autopsy (Layer 5). Every turn, it decides what the enemy does, which assumption to attack, and how the failure propagates through the plan.

Two subsystems:

| Subsystem | File | LLM? | Role |
|---|---|---|---|
| Ghost Council | `ghost.py` | Yes (Groq via OpenRouter) | Reads the assumption map, picks a target using Prospect Theory, generates the red move and stress events |
| Cascade Engine | `cascade.py` | No | Takes the Ghost's output, propagates breaks through the dependency graph, computes final metric deltas |

---

## File Reference

### `models.py`

Single source of truth for all data contracts. Every type used by Layer 3 lives here.

**Shared types:**

```python
Metrics              # Six strategic metrics: intl_opinion, us_domestic, red_domestic,
                     # allied_confidence, blue_strength, red_strength

GameState            # Current state: metrics, assumption_statuses, pending_breaks
BlueMove             # Player's move this turn
```

**Ghost output** (matches TypeScript `GhostOutput` contract exactly):

```python
StressEvent          # One assumption targeted: id, stress_type, severity, explanation
GhostOutput          # red_move, targeted_assumption_id, reasoning, escalation_level,
                     # kinetic, proposed_metric_deltas, stress_events
```

**Cascade output** (matches TypeScript `CascadeOutput` contract exactly):

```python
AssumptionPatch      # id, status ("untested"|"stressed"|"broken"|"validated"), turn_broken
FailureFlags         # military_failure, political_failure, alliance_failure, escalation_failure
CascadeOutput        # updated_assumptions, broken_chain, metric_deltas, cascade_narrative,
                     # failure_flags, status ("active"|"failed"|"completed")
```

**FOGLINE seeds** (passed through from Layer 2, never modified by Layer 3):

```python
GhostTarget          # assumption_id, fragility_score, target_priority, exploit_window
GhostCouncilSeed     # priority_targets, red_team_guidance
PropagationRule      # from_id, to_id, weight (0-1), delay_turns
CascadeSeed          # break_order, critical_paths, propagation_rules
```

**API types:**

```python
ProcessTurnRequest   # game_id, turn, blue_move, game_state, seeds, assumptions
ProcessTurnResponse  # ghost_output, cascade_output, updated_game_state, game_over
GhostHistoryEntry    # turn, ghost_output, cascade_triggered, cascade_depth
PreviewRequest       # game_state, seeds, assumptions, optional blue_move
SimulateCascadeRequest  # ghost_output, game_state, cascade_seed, assumptions, current_turn
```

---

### `ghost.py`

**Entry point:** `async def run_ghost_council(req: ProcessTurnRequest) -> GhostOutput`

**Flow:**

```
1. _prospect_bias(game_state)
      red_strength < 40 or blue_strength > 80  →  risk_seeking
      red_strength > 65 and blue_strength < 50 →  loss_aversion
      otherwise                                →  neutral

2. _aggression(game_state, blue_move, bias)
      base = 0.30
      + 0.20 if blue_move is "attack"
      + (resources_committed / 10) * 0.30
      + 0.20 if risk_seeking, - 0.10 if loss_aversion
      + min(turn * 0.02, 0.15)          # rises with turn number
      clamped 0.0 – 1.0

3. _exploitable_targets(seed, game_state, turn)
      Filters priority_targets to those whose exploit_window contains current turn:
        early = turns 1-3, mid = turns 4-7, late = turns 8+
      Falls back to any active target if no window matches.
      Returns top 3 by target_priority.

4. Single LLM call → raw JSON → _validate_output()

5. _validate_output() guards:
      - targeted_assumption_id not in candidates → fall back to candidates[0]
      - unknown metric keys → stripped
      - escalation_level clamped 0-5, severity clamped 0-100
      - hallucinated stress event assumption_ids → removed
      - primary target missing from stress_events → injected with severity=70
```

**LLM call:**

- Provider: OpenRouter (`https://openrouter.ai/api/v1/chat/completions`)
- Model: `meta-llama/llama-3.3-70b-instruct`
- Format: `response_format: { type: "json_object" }`
- Temperature: 0.75, max_tokens: 600
- Env var: `OPENROUTER_API_KEY`

**No-candidate path:** If all assumptions are broken/validated, returns a zero-escalation probe immediately without calling the LLM.

---

### `cascade.py`

**Entry points:**
- `trigger(ghost_output, game_state, cascade_seed, assumptions, current_turn) → CascadeOutput`
- `apply_delta(game_state, cascade_output) → GameState`

**`trigger` flow:**

```
Step 1 — process stress_events from Ghost
    severity >= 70  →  broken   (added to broken_chain)
    severity >= 30  →  stressed (added to stressed_ids)
    severity <  30  →  no change

Step 2 — BFS from every node in broken_chain
    For each downstream neighbor via propagation_rules:
      delay_turns > 0         →  mark stressed (deferred; fires in a future turn)
      weight >= 0.70          →  cascade_break (added to broken_chain, BFS continues)
      weight >= 0.30          →  stressed
      weight <  0.30          →  no change (below cascade threshold)

Step 3 — amplify metric deltas
    cascade_breaks = max(0, len(broken_chain) - 1)   # exclude primary
    amplification  = min(1.0 + cascade_breaks * 0.30, 2.0)
    final metric_deltas = { k: int(v * amplification)
                            for k, v in ghost.proposed_metric_deltas.items() }

Step 4 — failure_flags
    military_failure   →  "military"|"supply"|"air"|"naval" tags in broken chain
                          OR blue_strength delta <= -15
    political_failure  →  "political"|"domestic" tags in broken chain
                          OR us_domestic delta <= -10 OR intl_opinion delta <= -12
    alliance_failure   →  "alliance"|"allied"|"coalition" tags in broken chain
                          OR allied_confidence delta <= -12
    escalation_failure →  escalation_level >= 4

Step 5 — status
    "failed"  →  no active assumptions remain OR blue_strength drops to <= 0
    "active"  →  otherwise
```

**`apply_delta` flow:**

```
- Apply metric_deltas to game_state.metrics
- Apply assumption patches (updated_assumptions) to game_state.assumption_statuses
- Fire any pending_breaks whose turn_number <= game_state.turn
- Set game_over = True + winner = "red" if blue_strength <= 0 or no active assumptions
- Returns deepcopy — never mutates the input
```

---

### `main.py`

FastAPI app. Four endpoints, one in-memory ghost history store per game_id.

| Method | Path | Description |
|---|---|---|
| `POST` | `/game/{game_id}/turn` | **Primary.** Ghost → Cascade → updated state. Called by Wargame Engine each turn. |
| `POST` | `/ghost/preview` | Dry-run Ghost Council. No state mutation, no history. Integration testing. |
| `POST` | `/cascade/simulate` | Directly trigger a cascade from a pre-built `GhostOutput`. Frontend animation testing. |
| `GET`  | `/game/{game_id}/ghost-history` | Full adversary decision log. Consumed by Failure Autopsy (Layer 5). |
| `GET`  | `/health` | Returns `{ status: "ok", layer: 3 }` |

**Error codes:**

| Code | Condition |
|---|---|
| 400 | `game_over` is already `true` on the game state |
| 404 | No ghost history found for `game_id` |
| 422 | `game_id` in path and body do not match; or `targeted_assumption_id` not in `assumption_statuses` |

---

## API Contract

### `POST /game/{game_id}/turn`

**Request body** — `ProcessTurnRequest`:
```json
{
  "game_id": "string",
  "turn": 3,
  "blue_move": {
    "move_type": "attack|defend|reposition|resupply|probe|withdraw",
    "target": "string",
    "description": "string",
    "resources_committed": 8
  },
  "game_state": {
    "game_id": "string",
    "turn": 3,
    "metrics": {
      "intl_opinion": 0, "us_domestic": 0, "red_domestic": 0,
      "allied_confidence": 0, "blue_strength": 80, "red_strength": 60
    },
    "assumption_statuses": { "A1": "untested", "A3": "untested" },
    "pending_breaks": {},
    "game_over": false,
    "winner": null
  },
  "ghost_council_seed": { "priority_targets": [...], "red_team_guidance": [...] },
  "cascade_seed": { "break_order": [...], "critical_paths": [...], "propagation_rules": [...] },
  "assumptions": [{ "id": "A3", "statement": "...", "tags": ["alliance"] }]
}
```

**Response body** — `ProcessTurnResponse`:
```json
{
  "ghost_output": {
    "red_move": "Red launches a limited blockade...",
    "targeted_assumption_id": "A3",
    "reasoning": "Blue assumes allied cohesion will hold...",
    "escalation_level": 3,
    "kinetic": true,
    "proposed_metric_deltas": {
      "intl_opinion": -8, "us_domestic": -5, "red_domestic": 7,
      "allied_confidence": -12, "blue_strength": -4, "red_strength": -2
    },
    "stress_events": [
      {
        "assumption_id": "A3",
        "stress_type": "exploit",
        "severity": 82,
        "explanation": "Red targets allied political will..."
      }
    ]
  },
  "cascade_output": {
    "updated_assumptions": [
      { "id": "A3", "status": "broken", "turn_broken": 2 },
      { "id": "A5", "status": "stressed" }
    ],
    "broken_chain": ["A3", "A5"],
    "metric_deltas": {
      "intl_opinion": -10, "allied_confidence": -18, "blue_strength": -6
    },
    "cascade_narrative": "Once 'Allied political will holds' collapsed...",
    "failure_flags": {
      "military_failure": false, "political_failure": true,
      "alliance_failure": true, "escalation_failure": false
    },
    "status": "active"
  },
  "updated_game_state": { ... },
  "game_over": false
}
```

---

## Integration Points

| Layer | Direction | Transport |
|---|---|---|
| **FOGLINE (Layer 2)** | Seeds come in once at game start | Bundled in `ProcessTurnRequest` every turn (stateless) |
| **Wargame Engine** | Calls us after every blue move | `POST /game/{id}/turn` |
| **Wargame Engine** | Receives updated state back | `ProcessTurnResponse.updated_game_state` |
| **Frontend — CascadeOverlay** | Reads cascade events | `cascade_output.updated_assumptions` — sequence index gives 400ms stagger |
| **Failure Autopsy (Layer 5)** | Reads full adversary log at game end | `GET /game/{id}/ghost-history` |

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set env
cp .env.example .env
# fill in: OPENROUTER_API_KEY=sk-or-...

# 3. Start server
uvicorn main:app --reload --port 8000

# 4. Run tests (no API key needed — LLM is mocked)
python -m pytest tests/ -v
```

---

## Testing

```
tests/
├── conftest.py          Fixtures: game states, seeds, assumption lists, ghost outputs
├── test_models.py       Schema validation, enum bounds, contract compliance (17 tests)
├── test_cascade.py      BFS propagation, severity thresholds, amplification, apply_delta (24 tests)
├── test_ghost.py        Prospect bias, aggression, window filtering, LLM guard logic (24 tests)
└── test_api.py          All endpoints, error codes, history isolation (20 tests)
```

**LLM is always mocked in tests.** `unittest.mock.AsyncMock` patches `ghost._call_llm` and `main.run_ghost_council` so tests run offline and deterministically.

Key cascade invariants tested:
- `severity >= 70` → breaks; `30-69` → stressed; `< 30` → no change
- BFS does not re-visit already-broken nodes
- Deferred breaks (`delay_turns > 0`) mark stressed, never immediately break
- Metric amplification: each cascade break adds 30%, capped at 2×; no-cascade case = 1× exactly
- `apply_delta` is pure — never mutates the input `GameState`
