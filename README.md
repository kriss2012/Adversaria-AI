# 🧠 Adversaria AI – Adversarial Multi-Agent Creative Engine

> **A production-grade AI agent orchestration platform featuring debate-driven reasoning, dynamic agent spawning, explainable AI, and automated evaluation pipelines.**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

# 🚀 Overview

Adversaria AI is an advanced **Multi-Agent AI System** that enables multiple specialized AI agents to collaborate, debate, critique, and synthesize ideas into high-quality outputs.

Unlike traditional AI wrappers, Adversaria AI introduces an **Adversarial Reasoning Architecture**, where multiple autonomous agents challenge each other's outputs before producing a final response.

The system focuses on:

- 🧠 Multi-Agent Collaboration
- ⚔️ Debate-Driven Reasoning
- 🧩 Dynamic Agent Spawning
- 📊 Explainable Decision Making (XDR)
- 📈 Built-in Evaluation Framework
- ⚡ Production-Ready Infrastructure

---

# ✨ Features

## 🤖 Multi-Agent Pipeline

- Planner Agent
- Research Agent
- Generator Agent
- Critic Agent
- Debate Agent
- Synthesizer Agent
- Evaluator Agent
- Memory Agent

---

## ⚔️ Debate Architecture

Instead of accepting the first response, agents:

- Challenge assumptions
- Detect hallucinations
- Produce counterarguments
- Improve reasoning quality
- Vote on the best solution

---

## 🧠 Explainable AI (XDR)

Every response contains:

- Agent reasoning
- Decision path
- Evidence
- Criticism
- Confidence score

making every generated answer fully traceable.

---

## 📊 Evaluation Dashboard

Built-in evaluation system measuring:

- Response Quality
- Consistency
- Hallucination Rate
- Agent Agreement
- Confidence Score
- Processing Time

---

## ⚡ Real-Time Streaming

- Server Sent Events (SSE)
- Live agent reasoning
- Real-time pipeline visualization
- Progressive response generation

---

## 📚 Knowledge Base

Supports:

- Vector Search
- Semantic Retrieval
- Document Ingestion
- Embedding Storage
- Long-Term Memory

Powered by **Qdrant**.

---

# 🏗️ Architecture

```
                 User Prompt
                      │
                      ▼
              Planner Agent
                      │
      ┌───────────────┴───────────────┐
      ▼                               ▼
 Research Agent                Generator Agent
      │                               │
      └───────────────┬───────────────┘
                      ▼
               Debate Phase
        (Critic + Opponent Agents)
                      │
                      ▼
             Synthesizer Agent
                      │
                      ▼
             Evaluation Engine
                      │
                      ▼
              Final AI Response
```

---

# 📂 Project Structure

```
Adversaria-AI/

├── Frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── agentEngine.ts
│   │   └── main.tsx
│   │
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── adversaria/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── db/
│   │   ├── services/
│   │   ├── workers/
│   │   ├── models/
│   │   ├── prompts/
│   │   └── main.py
│   │
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── pyproject.toml
│
├── README.md
└── LICENSE
```

---

# 🛠️ Tech Stack

## Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- Framer Motion

---

## Backend

- Python 3.11+
- FastAPI
- LangGraph
- Celery
- SQLAlchemy 2.0
- AsyncIO

---

## Database

- PostgreSQL
- Redis
- Qdrant
- MinIO

---

## AI

- Anthropic Claude
- OpenAI
- LangChain
- LangGraph

---

## DevOps

- Docker
- Docker Compose
- Flower
- GitHub Actions

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/kriss2012/Adversaria-AI.git

cd Adversaria-AI
```

---

# Backend Setup

```bash
cd backend

cp .env.example .env
```

Update your API keys:

```env
ANTHROPIC_API_KEY=your_key

OPENAI_API_KEY=your_key
```

Start required services

```bash
docker-compose up -d
```

Install dependencies

```bash
pip install -e ".[dev]"
```

Run FastAPI

```bash
uvicorn adversaria.main:app --reload --port 8000
```

Run Celery Worker

```bash
celery -A adversaria.workers.celery_app.celery_app worker --loglevel=info
```

---

# Frontend Setup

```bash
cd Frontend

npm install

npm run dev
```

Frontend:

```
http://localhost:5173
```

Backend API:

```
http://localhost:8000
```

Swagger Docs:

```
http://localhost:8000/docs
```

Flower Dashboard:

```
http://localhost:5555
```

Qdrant Dashboard:

```
http://localhost:6333
```

---

# 🔄 Workflow

```
User Prompt
      │
      ▼
Planner
      │
      ▼
Dynamic Agent Spawn
      │
      ▼
Research
      │
      ▼
Generation
      │
      ▼
Critic Debate
      │
      ▼
Synthesis
      │
      ▼
Evaluation
      │
      ▼
Streaming Response
```

---

# 📊 Evaluation Metrics

Adversaria AI automatically evaluates every response using:

- Accuracy
- Faithfulness
- Completeness
- Creativity
- Confidence
- Hallucination Detection
- Latency
- Cost Estimation

---

# 🔐 Environment Variables

```env
ANTHROPIC_API_KEY=

OPENAI_API_KEY=

DATABASE_URL=

REDIS_URL=

QDRANT_URL=

MINIO_ENDPOINT=

JWT_SECRET=

LOG_LEVEL=INFO
```

---

# 📸 Screenshots

```
screenshots/

├── dashboard.png
├── debate.png
├── pipeline.png
├── xdr_trace.png
└── evaluation.png
```

---

# 🗺️ Roadmap

- Multi-model orchestration
- Voice-enabled agents
- MCP Server Integration
- Plugin Marketplace
- Self-improving agent memory
- Distributed agent clusters
- Fine-tuned evaluator models
- Agent marketplace

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository

2. Create a feature branch

```bash
git checkout -b feature-name
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push to GitHub

```bash
git push origin feature-name
```

5. Open a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

**Krishna Patil**

- GitHub: https://github.com/kriss2012

---

# ⭐ Support

If you find this project useful, please give it a ⭐ on GitHub.

Your support helps improve Adversaria AI and encourages future development.

---

## 💡 Vision

> **"The future of AI isn't a single model—it's intelligent agents that reason, debate, critique, and collaborate to solve complex problems."**

**Adversaria AI** is built to make that future a reality.


**Love By KiriGen Tech**
