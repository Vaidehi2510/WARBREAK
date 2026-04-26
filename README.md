# WARBREAK

Every wargame shows you what happens. WARBREAK shows you why it was always going to happen.

## Quick start

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and add one or more provider keys
uvicorn main:app --reload --port 8020
```

### Frontend (new terminal)
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8020" > .env.local
npm run dev -- --hostname 127.0.0.1 --port 3010
```

Open http://127.0.0.1:3010

## Stack
- Backend: FastAPI + Python
- AI: Provider fallback chain through the OpenAI SDK
  - OpenRouter when `OPENROUTER_API_KEY` is set
  - Gemini when `GEMINI_API_KEY` is set
  - OpenAI when `OPENAI_API_KEY` is set
- Frontend: Next.js + TypeScript

## Deploy on Vercel

This repo is configured for two separate Vercel projects:
- Backend project rooted at `backend/`
- Frontend project rooted at `frontend/`

See [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md) for the exact setup steps and required environment variables.

## LLM keys
Set the fallback order in `backend/.env`:

```env
LLM_PROVIDER_ORDER=openrouter,gemini,openai
```

Then add whichever keys you want available:

```env
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...
OPENAI_API_KEY=...
```
