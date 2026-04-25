# Deploy WARBREAK on Vercel (Single Project)

This repo is configured to deploy frontend and backend together under one Vercel URL.

- Frontend: Next.js from `frontend/`
- Backend: FastAPI routed from `api/index.py` (imports app from `backend/main.py`)

## 1) Create one Vercel project

1. Import this repository in Vercel.
2. Keep **Root Directory** as repository root (`.`).
3. Add environment variable:
   - `OPENROUTER_API_KEY` = your OpenRouter key
4. Deploy.

Vercel files used:
- `vercel.json` (root routing for frontend + backend)
- `api/index.py` (ASGI entrypoint)

## 2) Routing behavior

These paths go to FastAPI:
- `/health`
- `/health/startup`
- `/games`
- `/games/{game_id}`
- `/turn`
- `/autopsy/{game_id}`

All other paths go to Next.js frontend.

## 3) Frontend API base URL

The frontend now defaults to same-origin API calls.

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
   - `GET /autopsy/{game_id}`
4. Confirm deployment env is valid:
   - `GET /health/startup` should return 200

## Notes

- Backend state is in-memory, so sessions can reset on cold starts/redeploys.
- If you later split services again, set `NEXT_PUBLIC_API_URL` to your backend domain.
