# Deploy WARBREAK on Vercel

This repo is configured as one stable FastAPI Vercel project.

- `main.py` is the Vercel entrypoint.
- The backend FastAPI app is mounted at `/api`.
- The frontend is exported from `frontend/` as static files during the Vercel build.
- The exported frontend is served by the same FastAPI app, so no Vercel Services beta access is required.

## 1) Import the project

1. Import this repository in Vercel.
2. Keep Root Directory as repository root (`.`).
3. Use the FastAPI framework preset. The root `vercel.json` also sets `"framework": "fastapi"`.
4. Do not set the root directory to `frontend/`.
5. Do not use the Services preset for this repo.

Vercel uses this root build command from `vercel.json`:

```bash
cd frontend && npm ci && npm run build
```

The frontend build runs with `output: "export"` and writes static files to `frontend/out/`. The Vercel function includes that directory and serves it at `/`.

## 2) Environment variables

Leave `NEXT_PUBLIC_API_URL` unset for the single-project Vercel deployment. The frontend defaults to same-origin API calls under `/api`.

Add at least one LLM provider key:

```env
LLM_PROVIDER_ORDER=openrouter,gemini,openai
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_REASONING_EFFORT=none
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
```

Only the keys for providers you use need values.

## 3) Routing

Frontend pages:

- `/`
- `/assets`
- `/game`
- `/autopsy`

Backend API paths:

- `/api/health`
- `/api/health/startup`
- `/api/games`
- `/api/games/{game_id}`
- `/api/turn`
- `/api/intel`
- `/api/autopsy/{game_id}`

## 4) Verify

After deployment:

1. Open the Vercel URL and confirm the WARBREAK UI loads.
2. Open `/api/health/startup` and confirm it returns HTTP 200.
3. Submit a plan from the homepage.
4. Confirm the app can call `POST /api/games`, `POST /api/turn`, `POST /api/intel`, and `GET /api/autopsy/{game_id}`.

## Local development

The split local workflow still works:

```bash
cd backend
uvicorn main:app --reload --port 8020
```

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8020" > .env.local
npm run dev -- --hostname 127.0.0.1 --port 3010
```

You can also test the Vercel-style entrypoint locally after building the frontend:

```bash
cd frontend
npm run build
cd ..
uvicorn main:app --reload --port 8020
```

Then open `http://127.0.0.1:8020`.
