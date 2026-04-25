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
# edit .env and add your OpenRouter API key
uvicorn main:app --reload --port 8000
```

### Frontend (new terminal)
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000

## Stack
- Backend: FastAPI + Python
- AI: Llama 3.3 70B via OpenRouter (free)
- Frontend: Next.js + TypeScript

## Get OpenRouter key
1. Go to openrouter.ai
2. Create free account
3. Copy API key
4. Paste into backend/.env
