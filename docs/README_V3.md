# AI Learning Assistant

<p align="center">
  <img src="docs/screenshots/chat.png" alt="AI Learning Assistant" width="600"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react" alt="React"/>
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/LangGraph-0.4-FF6F00?style=flat" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/RAG-FAISS-FF6F00?style=flat" alt="RAG"/>
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker" alt="Docker"/>
  <img src="https://img.shields.io/badge/Railway-deployed-131415?style=flat&logo=railway" alt="Railway"/>
</p>

## Overview

AI Learning Assistant is a multi-agent conversational learning platform powered by LangGraph and DeepSeek LLM. It provides personalized tutoring across programming, English learning, career planning, and research.

### Target Users
- **Students**: Get AI-powered personalized learning plans
- **Developers**: Reference for FastAPI + React + LangGraph architecture
- **Recruiters**: Demo of production-grade full-stack AI application

---

## Features

| Feature | Description |
|---------|-------------|
|  Multi-Agent Chat | Code, English, Career, Research, Planner agents |
|  RAG Knowledge Base | Upload PDFs, ask questions with source citations |
|  Conversation Isolation | Each session has its own knowledge base scope |
|  JWT Auth | Email/password registration and login |
|  Session History | Persistent conversation history with rename |
|  Real-time Streaming | Typing indicators and smooth message delivery |
|  Production Ready | Docker, Railway, PostgreSQL (Neon) support |

---

## Tech Stack

```
Frontend                     Backend                    AI / Infra
┌─────────────┐            ┌──────────────┐           ┌─────────────┐
│   React 19  │            │   FastAPI    │           │  LangGraph  │
│  TypeScript │  REST API  │  SQLAlchemy  │  RAG/LLM  │   DeepSeek  │
│    Vite     │◄──────────►│    JWT Auth  │◄─────────►│   FAISS     │
│ TailwindCSS │            │  PostgreSQL  │           │ Sentence-T  │
└─────────────┘            └──────────────┘           └─────────────┘
```

---

## Screenshots

| Login | Chat | Knowledge |
|-------|------|-----------|
| ![Login](docs/screenshots/login.png) | ![Chat](docs/screenshots/chat.png) | ![Knowledge](docs/screenshots/knowledge_upload.png) |
| **Plans** | **Profile** | **API Docs** |
| ![Plans](docs/screenshots/plans.png) | ![Profile](docs/screenshots/profile.png) | ![Swagger](docs/screenshots/swagger.png) |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) Docker

### Backend

```bash
cd web_app/backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # Edit API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd web_app/frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### Docker (Alternative)

```bash
docker compose up --build
```

---

## Testing

```bash
# Backend tests
cd web_app/backend
pytest

# Frontend build check
cd web_app/frontend
npm run build
```

---

## Deployment

### Railway (Backend)

```bash
railway login
railway init
railway up

# Set environment variables:
#   DATABASE_URL=postgresql://...
#   DEEPSEEK_API_KEY=sk-...
#   SECRET_KEY=<random-string>
#   DEBUG=false
```

### Vercel (Frontend)

```
Import web_app/frontend/ to Vercel
Set VITE_API_URL=https://your-app.railway.app
```

---

## Project Structure

```
web_app/
├── backend/
│   ├── app/               # FastAPI application
│   │   ├── api/v1/        # REST endpoints
│   │   ├── models/        # SQLAlchemy models
│   │   └── services/      # Business logic + RAG
│   ├── alembic/           # Database migrations
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page views
│   │   ├── api/           # API client
│   │   └── types/         # TypeScript types
│   └── package.json
└── supervisor_agent/      # LangGraph agent definitions
```

---

## Architecture

```mermaid
graph TD
    User[User] --> React[React Frontend]
    React --> API[FastAPI REST API]
    API --> Auth[JWT Auth]
    API --> Chat[Chat Service]
    Chat --> Agents[LangGraph Multi-Agent]
    Agents --> Code[Code Agent]
    Agents --> English[English Agent]
    Agents --> Career[Career Agent]
    Agents --> Planner[Planner Agent]
    Agents --> Research[Research Agent]
    Agents --> RAG[RAG Engine]
    RAG --> VectorDB[(FAISS Vector Store)]
    RAG --> LLM[DeepSeek LLM]
    Chat --> DB[(PostgreSQL / SQLite)]
    API --> Knowledge[Knowledge Service]
    Knowledge --> RAG
```

---

## License

MIT
