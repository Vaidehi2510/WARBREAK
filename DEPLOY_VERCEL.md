# Deploy WARBREAK on Vercel (Single Project)

This repo is configured to deploy frontend and backend together under one Vercel URL.

- Frontend: Next.js from `frontend/`
- Backend: FastAPI routed through Vercel's Python runtime from `api/index.py`

Vercel will not run `uvicorn` as a long-lived process. The FastAPI app is exposed as a Python function and invoked on API requests.
This uses Vercel Services so the Next.js frontend and FastAPI backend are built as one Vercel project.

## 1) Create one Vercel project

1. Import this repository in Vercel.
2. Keep **Root Directory** as repository root (`.`).
3. Set **Application Preset** to **Services**.
4. Do not set the root directory to `frontend/`; the root `vercel.json` deploys both services.
5. Add environment variables for the provider fallback chain:
   - `LLM_PROVIDER_ORDER` = `openrouter,gemini,openai`
   - `OPENROUTER_API_KEY` = your OpenRouter API key, if used
   - `OPENROUTER_MODEL` = `openai/gpt-4o-mini`
   - `GEMINI_API_KEY` = your Gemini API key, if used
   - `GEMINI_MODEL` = `gemini-2.5-flash`
   - `GEMINI_REASONING_EFFORT` = `none`
   - `OPENAI_API_KEY` = your OpenAI API key, if used as fallback
   - `OPENAI_MODEL` = `gpt-5.4-mini`
6. Leave `NEXT_PUBLIC_API_URL` unset in Vercel so the frontend uses Vercel's generated `NEXT_PUBLIC_BACKEND_URL` service route.
7. Deploy.

Vercel files used:
- `vercel.json` (Services configuration for frontend + backend)
- `api/index.py` (ASGI entrypoint)
- `requirements.txt` (Python dependencies for the API runtime)

## 2) Routing behavior

These paths go to FastAPI through the `/api` service prefix:
- `/api/health`
- `/api/health/startup`
- `/api/games`
- `/api/games/{game_id}`
- `/api/turn`
- `/api/intel`
- `/api/autopsy/{game_id}`

All other paths go to the Next.js frontend.

## 3) Frontend API base URL

The frontend defaults to same-origin API calls.

- `frontend/lib/api.ts` uses `NEXT_PUBLIC_API_URL` if provided.
- On Vercel Services, it uses `NEXT_PUBLIC_BACKEND_URL`, which Vercel injects as `/api`.
- For single-project deploy, you can leave `NEXT_PUBLIC_API_URL` unset.

For local development, keep using:
- `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8020`

## 4) Verify end-to-end

1. Open your Vercel URL.
2. Submit a plan.
3. Confirm the app can call:
   - `POST /api/games`
   - `POST /api/turn`
   - `POST /api/intel`
   - `GET /api/autopsy/{game_id}`
4. Confirm deployment env is valid:
   - `GET /api/health/startup` should return 200 and show at least one configured provider.
   - `GET /api/health` should show the active fallback order and models without exposing keys.

## Notes

- Backend state is in-memory, so sessions can reset on cold starts/redeploys.
- If you later split services again, set `NEXT_PUBLIC_API_URL` to your backend domain.
