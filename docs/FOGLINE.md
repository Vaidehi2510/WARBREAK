# FOGLINE Compiler Documentation

FOGLINE compiles a free-text fictional training plan into structured assumptions and downstream seeds. It is not a wargame engine, Ghost Council, cascade engine, or autopsy writer. It prepares the data those systems need.

## Files

- `backend/extraction.py`: Pydantic models, extraction flow, scoring, graph generation, and downstream seed builders.
- `backend/evidence_catalog.json`: local structured evidence/RAG catalog.
- `backend/sample_plans.py`: polished demo input, `OPERATION_HARBOR_GLASS`.
- `backend/main.py`: FastAPI endpoints.
- `backend/test_extraction.py`: lightweight FOGLINE tests.

## Endpoints

### `GET /demo-plan`

Returns `OPERATION_HARBOR_GLASS`, a fictional island-port crisis training plan. The plan includes coalition dependency, logistics pressure, cyber/system degradation, civilian uncertainty, infrastructure fragility, timing constraints, authority friction, communications uncertainty, public information pressure, and resource limits.

### `POST /extract`

Input:

```json
{
  "plan_text": "string",
  "scenario_name": "string optional",
  "domain": "string optional",
  "actors": ["string optional"],
  "timeline": "string optional",
  "mission_objective": "string optional"
}
```

Output:

```json
{
  "scenario_name": "string",
  "mission_objective": "string",
  "evidence_cards": [],
  "assumptions": [],
  "summary": {},
  "graph_seed": {},
  "ghost_council_seed": {},
  "cascade_seed": {},
  "autopsy_seed": {},
  "warnings": []
}
```

## Extraction Flow

1. Load and normalize `backend/evidence_catalog.json`.
2. Apply a safe-scope gate for unsafe real-world targeting requests.
3. Use Anthropic extraction when available.
4. Fall back to deterministic heuristic extraction when Anthropic is unavailable, disabled, or returns invalid JSON.
5. Match each assumption to an evidence card.
6. Score each assumption in Python using the transparent rubric.
7. Generate graph, Ghost Council, Cascade, Wargame, and Autopsy handoff data.

Set `FOGLINE_DISABLE_LLM=1` to force fallback mode.

## Fragility Scoring

Final scoring is deterministic in Python. The model may suggest score components, but FOGLINE does not trust model scores for final output.

Formula:

```text
fragility_score =
  base_pattern_risk * 0.20
+ observability_gap * 0.15
+ mitigation_gap * 0.15
+ dependency_centrality * 0.15
+ recovery_difficulty * 0.15
+ consequence_severity * 0.15
+ volatility * 0.05
```

Bands:

- `low`: 0-34
- `medium`: 35-59
- `high`: 60-79
- `critical`: 80-100

No exact historical statistics are claimed.

## Evidence Cards

The local catalog contains qualitative pattern cards. Each card includes:

- `id`
- `category`
- `description`
- `risk_factors`
- `observable_indicators`
- `mitigation_patterns`
- `base_fragility`
- `safe_historical_analog_summary`
- `doctrine_note`
- `rag_keywords`

`/extract` returns compact matched `evidence_cards` so the frontend can show evidence context without loading the whole catalog.

## Assumption Output

Each assumption includes:

- stable ID, text, type, category, status, confidence
- fragility score, band, and score breakdown
- evidence span and matched pattern ID
- risk factors, missing mitigations, indicators, validation questions, fallback options, and rewrite suggestion
- dependency hints
- Wargame handoff fields:
  - `break_event_template`
  - `game_effects`
- autopsy tags

## Wargame Handoff

`break_event_template` gives the wargame engine a safe default event for a basic assumption break:

- `title`
- `sitrep`
- `immediate_effects`
- `player_decision_prompt`

`game_effects` includes:

- `resilience_delta`
- `decision_debt_delta`
- `affected_metrics`

Affected metrics are limited to:

- `logistics`
- `tempo`
- `coordination`
- `communications`
- `public_confidence`
- `intelligence_confidence`
- `infrastructure`
- `cyber_availability`
- `escalation_risk`
- `resource_margin`
- `authority_clarity`
- `mission_resilience`

## Cascade Handoff

`graph_seed` contains animation-ready nodes and edges:

- nodes include ID, label, category, fragility score, band, and status
- edges include ID, source, target, relationship, strength, and human-readable reason

`cascade_seed` contains:

- `break_order`
- `critical_paths`
- `propagation_rules`
- legacy-compatible root and edge fields

Edges are inferred from dependency hints, category relationships, and keyword overlap.

## Ghost Council Handoff

`ghost_council_seed` prepares data only. It does not implement Ghost Council logic.

It includes:

- `priority_targets`
- `red_team_guidance`
- legacy-compatible focus and candidate fields

Priority targets use safe pressure frames such as delayed confirmation, degraded confidence, uncertainty, forced validation, and reduced-scope decisions. They do not use attack language.

## Autopsy Handoff

`autopsy_seed` prepares structured data for failure-autopsy generation:

- `ranked_assumptions`
- `audit_fields`
- `resilience_patch_candidates`
- `better_plan_principles`
- legacy-compatible rank and audit fields

Better-plan principles are generic:

- validate critical assumptions before phase transitions
- add fallback options for high-centrality dependencies
- monitor unverified external actors
- add decision points when confidence drops
- reduce single-point dependencies
- define thresholds for delaying or reducing scope

## Safety

FOGLINE is scoped to fictional, unclassified training software. It avoids tactical guidance and refuses unsafe real-world targeting requests. Safe language should remain abstract: stress, degrade, delay, disrupt, validate, fallback, monitor, coordinate, reroute, reduce scope.

