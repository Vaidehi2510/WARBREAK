# Deploy WARBREAK on Vercel

Deploy WARBREAK as two separate Vercel projects from the same GitHub repo.

- Backend project: FastAPI, root directory `backend/`
- Frontend project: Next.js, root directory `frontend/`

Deploy the backend first, then give the frontend the backend URL through `NEXT_PUBLIC_API_URL`.

## 1) Backend Project

Create a Vercel project from `Nikhil123n/WARBREAK` with these settings:

- Root Directory: `backend`
- Framework Preset: `FastAPI`
- Build Command: leave default/empty
- Install Command: leave default

The backend uses [backend/vercel.json](backend/vercel.json). Vercel will install [backend/requirements.txt](backend/requirements.txt) and expose the FastAPI app from [backend/main.py](backend/main.py).

Set backend environment variables in Vercel:

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

Only the provider keys you use need values, but at least one provider key must be set for full gameplay.

After deployment, verify:

- `https://YOUR-BACKEND.vercel.app/health`
- `https://YOUR-BACKEND.vercel.app/health/startup`

Backend API paths:

- `/health`
- `/health/startup`
- `/games`
- `/games/{game_id}`
- `/turn`
- `/intel`
- `/autopsy/{game_id}`

## 2) Frontend Project

Create a second Vercel project from `Nikhil123n/WARBREAK` with these settings:

- Root Directory: `frontend`
- Framework Preset: `Next.js`
- Build Command: `npm run build`
- Install Command: leave default

The frontend uses [frontend/vercel.json](frontend/vercel.json).

Set this frontend environment variable:

```env
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND.vercel.app
```

Do not add a trailing slash. Do not add `/api`; the backend routes are served from the backend domain root.
Because `NEXT_PUBLIC_API_URL` is compiled into the Next.js build, redeploy the frontend after changing this value.

After deployment, verify:

1. Open the frontend Vercel URL.
2. Submit a plan.
3. Confirm browser requests go to `https://YOUR-BACKEND.vercel.app/games`, `/turn`, `/intel`, and `/autopsy/{game_id}`.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8020
```

Frontend:

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8020" > .env.local
npm run dev -- --hostname 127.0.0.1 --port 3010
```

Open `http://127.0.0.1:3010`.
