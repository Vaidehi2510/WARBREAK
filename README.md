# WARBREAK

> **Every wargame shows what happens. WARBREAK shows why it was always going to happen.**

AI-powered operational planning stress-tester built for the SCSP AI+ Expo 2026 — Wargaming Track.

---

## Track

**Wargaming** — SCSP AI+ Expo 2026, Washington DC

---

## What We Built

WARBREAK is an AI-powered wargame that extracts the hidden assumptions inside your operational plan, ranks them by fragility, then runs a turn-based simulation where a psychologically realistic adversary targets your weakest assumption — not your strongest unit.

Most wargames simulate who wins the fight. WARBREAK surfaces why the plan was already broken before the first shot.

### Core Features

**FOGLINE Extraction** — LLM reads your operational plan in plain English and returns every hidden assumption with a fragility score (0–100), criticality weight, doctrine reference, cascade dependency map, and historical basis cross-referenced against CDB90, IISS Military Balance, and JP 5-0 planning doctrine.

**OSINT Intel Briefing** — Before the game starts, AI predicts adversary force composition using publicly available intelligence sources: Jane's Defence Weekly, ONI Annual Report, CSIS Asia Maritime Transparency Initiative, IISS. Returns predicted assets with confidence percentages, threat levels, capability summaries, and specific counters.

**Ghost Council** — Adversary AI grounded in Prospect Theory (Kahneman & Tversky). Loss-averse, domestically constrained, and escalation-gated. Targets the highest-fragility FOGLINE assumption each turn rather than the highest-value unit.

**Information Battlefield** — Six real-time metrics tracked independently of force attrition: International Opinion, US Domestic Support, Red Domestic Support, Allied Confidence, Blue Force Strength, Red Force Strength. Kinetic decisions produce non-kinetic consequences.

**Live Tactical Map** — Leaflet.js interactive map with animated action feedback: strike arcs, sonar rings, cyber pulses, ground movement corridors. Unit positions are scenario-specific and correspond to real geography.

**Asset Selection** — 12 real military assets (Carrier Strike Group, Virginia-class SSN, F-35C Squadron, Patriot PAC-3, EA-18G Growler, P-8 Poseidon, Aegis Destroyer, Stryker Brigade, SOF Team, MQ-9 Reaper, Cyber Command Cell, Sealift Package). Budget-constrained. Turns equal assets selected.

**Failure Autopsy** — 7-tab post-game analysis: assumption breakdown with cascade chain, full decision log, Ghost Council reasoning per turn, information battlefield verdict, failure chain trace, what-if counterfactuals (Timeline A vs optimal Timeline B), and doctrine-grounded recommendations.

### Scenarios

| Scenario | Theater | Adversary |
|---|---|---|
| Taiwan Strait 2027 | Western Pacific | PLA |
| NATO Eastern Flank | Suwalki Corridor | Russian Federation |
| Embassy Evacuation | Capital NEO | Local Forces |
| Cyber Grid Attack | US Northeast Grid | APT Group |

---

## Datasets and APIs Used

| Source | Usage |
|---|---|
| **OpenRouter API** | LLM inference — Gemini Flash free tier |
| **CDB90** (Center for Naval Analyses) | Historical conflict data for assumption fragility scoring |
| **IISS Military Balance 2024** | Adversary force composition baselines for OSINT engine |
| **Jane's Defence Weekly** | Asset capability data referenced in OSINT predictions |
| **ONI Annual Report** (Office of Naval Intelligence) | PLA naval order of battle |
| **CSIS Asia Maritime Transparency Initiative** | PLA missile and basing data |
| **Correlates of War Project** | Historical conflict outcomes for fragility calibration |
| **JP 5-0** (Joint Planning) | Doctrine references in assumption extraction and autopsy |
| **FM 6-0** (Commander and Staff Organization) | Command coordination assumption categories |
| **CartoDB Dark Matter** | Tactical map tile layer via Leaflet.js |
| **Prospect Theory** (Kahneman & Tversky 1979) | Ghost Council adversary behavioral model |

---

## How to Run It

### Prerequisites

- Python 3.11+
- Node.js 18+
- Free OpenRouter API key — get one at [openrouter.ai](https://openrouter.ai) (no credit card required)

### 1. Clone the repo

```bash
git clone https://github.com/Vaidehi2510/WARBREAK.git
cd WARBREAK
git checkout vaidehi
```

### 2. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create environment file
echo "OPENROUTER_API_KEY=your_key_here" > .env

uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`

Verify: `curl http://localhost:8000/health`

### 3. Start the frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### 4. Play

1. Go to `http://localhost:3000`
2. Select a scenario or write your own operational plan
3. Click **Deploy Mission** — FOGLINE extracts assumptions
4. On the Assets page, run **Identify Opponent Assets** for the OSINT briefing
5. Select your Blue force package and enter the wargame
6. Execute moves — watch the map animate and assumptions stress/break
7. After all turns, read the Failure Autopsy

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                       │
│                   Next.js 15 + TypeScript                       │
│                                                                 │
│  /              /assets          /game           /autopsy       │
│  Scenario       Asset select     Tactical map    7-tab report   │
│  selector       OSINT panel      Ghost Council   Timeline A/B   │
│  Plan editor    Budget system    Action dock     Failure chain  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST / JSON
┌────────────────────────────▼────────────────────────────────────┐
│                          API LAYER                              │
│                   FastAPI + Python 3.11                         │
│                                                                 │
│  POST /games      →  FOGLINE extraction                         │
│  POST /turn       →  Ghost Council + adjudication               │
│  POST /intel      →  OSINT threat briefing                      │
│  GET  /autopsy    →  7-section failure report                   │
│  GET  /health     →  status                                     │
└──────┬──────────────────┬───────────────────┬───────────────────┘
       │                  │                   │
┌──────▼──────┐  ┌────────▼────────┐  ┌──────▼──────────────────┐
│  AI ENGINE  │  │  GAME ENGINE    │  │     DATA SOURCES        │
│             │  │                 │  │                         │
│ Gemini Flash│  │ extraction.py   │  │ CDB90 conflict DB       │
│ via         │  │ ghost.py        │  │ IISS Military Balance   │
│ OpenRouter  │  │ adjudication.py │  │ Jane's Defence Weekly   │
│ (free tier) │  │ cascade.py      │  │ ONI Annual Report       │
│             │  │ autopsy.py      │  │ CSIS AMTI               │
│             │  │ intel.py        │  │ Correlates of War       │
└─────────────┘  └─────────────────┘  │ JP 5-0 / FM 6-0        │
                                       └─────────────────────────┘
```

### Backend modules

| File | Purpose |
|---|---|
| `main.py` | FastAPI app, all routes |
| `extraction.py` | FOGLINE assumption extraction |
| `ghost.py` | Ghost Council adversary AI |
| `adjudication.py` | Turn resolution |
| `cascade.py` | Assumption cascade engine |
| `autopsy.py` | Failure report generation |
| `intel.py` | OSINT adversary prediction |
| `game_state.py` | Pydantic models, in-memory store |
| `llm_client.py` | OpenRouter LLM client |

### API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/games` | Create game, run FOGLINE |
| `GET` | `/games/{id}` | Get game state |
| `POST` | `/turn` | Execute turn, trigger Ghost Council |
| `POST` | `/intel` | OSINT adversary prediction |
| `GET` | `/autopsy/{id}` | Generate failure autopsy |
| `GET` | `/health` | Status check |

---

## Deployment

Backend on Railway. Frontend on Vercel.

```bash
# Backend (Railway)
npm install -g @railway/cli
railway login && railway init && railway up
railway variables set OPENROUTER_API_KEY=your_key_here

# Frontend (Vercel)
cd frontend
npx vercel --prod
# Set NEXT_PUBLIC_API_URL to your Railway backend URL
```

---

## License

MIT — see `LICENSE`

---

*WARBREAK is not a game. It is a planning instrument. The game is the interface.*
