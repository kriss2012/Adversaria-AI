# Adversaria AI — Adversarial Multi-Agent Creative Engine

> Not just another wrapper. A production-grade agentic pipeline with a **debate-then-synthesize** critic architecture, dynamic agent spawning, explainable design rationale (XDR), and a built-in eval harness.

## Monorepo Structure

```
Adversaria-AI/
├── Frontend/          ← React + Vite UI (TypeScript)
│   └── src/
│       ├── agentEngine.ts      ← agent simulation (replace with SSE)
│       └── components/         ← Pipeline, DebatePanel, EvalDashboard, XDR trace
└── backend/           ← FastAPI + LangGraph + Celery (Python 3.11+)
    ├── adversaria/
    │   ├── agents/             ← LangGraph graph + 8 node implementations
    │   ├── api/                ← FastAPI routes + SSE streaming
    │   ├── db/                 ← SQLAlchemy 2.0 models + async session
    │   ├── services/           ← Qdrant, embeddings, ingestion, gen router
    │   └── workers/            ← Celery tasks
    └── docker-compose.yml      ← Postgres + Redis + Qdrant + MinIO
```

## Quick Start (Backend)

```bash
cd backend
cp .env.example .env         # fill in ANTHROPIC_API_KEY at minimum

docker-compose up -d         # starts Postgres, Redis, Qdrant, MinIO

pip install -e ".[dev]"
uvicorn adversaria.main:app --reload --port 8000

# In another terminal:
celery -A adversaria.workers.celery_app.celery_app worker --loglevel=info
```

Docs: http://localhost:8000/docs | Flower: http://localhost:5555 | Qdrant: http://localhost:6333

## Quick Start (Frontend)

```bash
cd Frontend
npm install
npm run dev
```

App: http://localhost:5173
