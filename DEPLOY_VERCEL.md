# Deploy WARBREAK on Vercel (Single Project)

This repo is configured to deploy frontend and backend together under one Vercel URL.

- Frontend: Next.js from `frontend/`
- Backend: FastAPI routed through Vercel's Python runtime from `api/index.py`

Vercel will not run `uvicorn` as a long-lived process. The FastAPI app is exposed as a Python function and invoked on API requests.

## 1) Create one Vercel project

1. Import this repository in Vercel.
2. Keep **Root Directory** as repository root (`.`).
3. Do not set the root directory to `frontend/`; the root `vercel.json` deploys both runtimes.
4. Add environment variable:
   - `OPENROUTER_API_KEY` = your OpenRouter key
5. Leave `NEXT_PUBLIC_API_URL` unset in Vercel so the frontend uses same-origin API calls.
6. Deploy.

Vercel files used:
- `vercel.json` (root routing for frontend + backend)
- `api/index.py` (ASGI entrypoint)
- `requirements.txt` (Python dependencies for the API runtime)

## 2) Routing behavior

These paths go to FastAPI:
- `/health`
- `/health/startup`
- `/games`
- `/games/{game_id}`
- `/turn`
- `/intel`
- `/autopsy/{game_id}`

All other paths go to Next.js frontend.

## 3) Frontend API base URL

The frontend defaults to same-origin API calls.

- `frontend/lib/api.ts` uses `NEXT_PUBLIC_API_URL` only if provided.
- For single-project deploy, you can leave `NEXT_PUBLIC_API_URL` unset.

For local development, keep using:
- `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`

## 4) Verify end-to-end

1. Open your Vercel URL.
2. Submit a plan.
3. Confirm the app can call:
   - `POST /games`
   - `POST /turn`
   - `POST /intel`
   - `GET /autopsy/{game_id}`
4. Confirm deployment env is valid:
   - `GET /health/startup` should return 200 and `openrouter_configured: true`

## Notes

- Backend state is in-memory, so sessions can reset on cold starts/redeploys.
- If you later split services again, set `NEXT_PUBLIC_API_URL` to your backend domain.
