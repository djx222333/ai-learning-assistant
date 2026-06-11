# AI Learning Assistant

> A multi-agent AI learning assistant powered by **LangGraph**, **FastAPI**, and **React**.
> Routes your questions to specialized AI agents: code tutor, English teacher, career advisor, web researcher, and RAG knowledge base.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-0.4+-orange.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License">
</p>

---

## Features

- **Multi-Agent System** -- 6 LangGraph agents routed by Supervisor via conditional edges
- **RAG Knowledge Base** -- Upload PDFs, AI chunks/indexes, retrieves with source citations
- **JWT Authentication** -- Register/login with bcrypt + JWT, user data isolation across all modules
- **Conversation History** -- Full CRUD with session switching sidebar
- **Learning Plans** -- AI generates weekly plans with task breakdown (Planner Agent + LLM)
- **Task Management** -- Track progress with 4 statuses: pending/in_progress/completed/failed
- **Session + Long-Term Memory** -- MemorySaver for context, JSON-based user profile persistence

## Agent Architecture

```
User Question
     |
     v
Supervisor (LLM Router)
     |
     +---> Code Agent      (Python Q&A + calc + file read)
     +---> English Agent    (English learning)
     +---> Career Agent     (Roadmap + user profile)
     +---> Search Agent     (DuckDuckGo search)
     +---> Research Agent   (Multi-source research)
     +---> RAG Agent        (PDF knowledge base)
     |
     v
DeepSeek LLM
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, TypeScript |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic |
| AI Engine | LangGraph (StateGraph, MemorySaver, create_react_agent) |
| Database | PostgreSQL 16 (SQLite compatible for dev) |
| Vector Store | FAISS + Sentence-Transformers (all-MiniLM-L6-v2) |
| LLM | DeepSeek API |
| Search | DuckDuckGo (ddgs) |
| PDF | PyMuPDF |
| Deployment | Docker, Railway, Vercel, Neon |

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/your-username/ai-learning-assistant.git
cd ai-learning-assistant
cp web_app/backend/.env.example web_app/backend/.env
# Edit .env, set DEEPSEEK_API_KEY
docker compose up -d
# Frontend: http://localhost
# Backend: http://localhost:8000/docs
```

### Local Development

```bash
# Backend
cd web_app/backend && pip install -r requirements.txt
alembic upgrade head && uvicorn app.main:app --reload --port 8000

# Frontend
cd web_app/frontend && npm install && npm run dev
```

### Run Tests

```bash
cd web_app/backend
pytest test_auth_service.py test_auth_api.py -v --tb=short
pytest test_conversations.py test_knowledge_auth.py -v --tb=short
# 57 tests, 100% pass rate
```

## Project Structure

```
ai-learning-assistant/
  supervisor_agent/         # LangGraph AI Agent core
    agent_graph.py          # Supervisor + 6 Agents + Router
    agent_tools.py          # Tool registrations
    rag_engine.py           # RAG: PDF -> chunk -> embed -> search
  web_app/
    backend/                # FastAPI server
      app/api/v1/           # 7 route files, 20 endpoints
      app/models/           # 7 SQLAlchemy ORM tables
      app/services/         # Business logic
      alembic/              # DB migrations
      Dockerfile
    frontend/               # React SPA
      src/pages/            # 5 pages (Chat, Knowledge, Login, etc.)
      vercel.json
      Dockerfile
  docker-compose.yml        # Full stack orchestration
  railway.json              # Railway deployment
```

## API Overview

All endpoints (except /health) require JWT Bearer token. 20 endpoints total, 100% JWT protected.

| Method | Path | Description |
|---|---|---|
| POST | /api/v1/auth/register | Register user |
| POST | /api/v1/auth/login | Login, returns JWT |
| GET | /api/v1/auth/me | Current user info |
| POST | /api/v1/chat | Send message to AI |
| GET | /api/v1/conversations | List sessions |
| DELETE | /api/v1/conversations/{id} | Delete session |
| POST | /api/v1/knowledge/upload | Upload PDF |
| GET | /api/v1/knowledge/files | List files |
| DELETE | /api/v1/knowledge/{id} | Delete file |
| POST | /api/v1/plans/generate | Generate plan |
| GET | /api/v1/plans | List plans |
| PATCH | /api/v1/tasks/{id} | Update task |
| GET | /api/v1/reports/overview | Get stats |

## Deployment

See [DEPLOY.md](DEPLOY.md) for Railway + Vercel + Neon production deployment guide.

## License

[MIT](LICENSE)