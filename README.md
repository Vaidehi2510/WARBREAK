# WARBREAK FOGLINE

FOGLINE is the compiler layer for WARBREAK planning exercises. It turns a free-text fictional training plan into stable JSON for downstream engines:

- assumptions with transparent fragility scores
- matched evidence cards from a local catalog
- cascade graph seed and propagation rules
- Ghost Council target seed
- Wargame break-event templates and game effects
- Failure Autopsy seed data

The implementation is intentionally lightweight. It can use Anthropic when `ANTHROPIC_API_KEY` is present, but deterministic fallback extraction works without external services.

## Run

```powershell
python -m uvicorn backend.main:app --reload
```

Endpoints:

- `GET /demo-plan` returns the Operation Harbor Glass demo plan.
- `POST /extract` compiles a plan into FOGLINE output.

## Test

```powershell
python -m pytest -q
```

## Safety Scope

FOGLINE is for fictional, unclassified crisis-training scenarios. It uses abstract language such as stress, degrade, delay, validate, fallback, monitor, coordinate, reroute, and reduce scope. Unsafe real-world targeting requests are refused by the scope gate.

See [docs/FOGLINE.md](docs/FOGLINE.md) for the response contract and downstream handoff details.

