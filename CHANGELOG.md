# Changelog

## v1.0.0 (2026-06-11)

### 🎉 First Major Release — AI Learning Assistant

AI Learning Assistant is a full-stack multi-agent learning platform powered by LangGraph, FastAPI, and React.

### 🚀 Features

**Agent System**
- Supervisor Agent — automatic routing across 5 specialized agents
- Code Agent — Python programming Q&A and code generation
- Career Agent — learning roadmaps and career planning
- Search Agent — real-time web search via DuckDuckGo
- Research Agent — multi-source research and report generation
- RAG Agent — PDF upload → chunking → embedding → retrieval → citation-grounded answers
- Planner Agent — generates structured weekly learning plans with task breakdown
- Session Memory — conversation history remembered within session
- Long-Term Memory — user profile persistence across sessions

**Backend (FastAPI)**
- JWT authentication: register, login, token-based session management
- User data isolation: all queries filtered by user_id
- RAG engine: PDF ingestion, text chunking, FAISS vector search, citation extraction
- Learning plans: auto-generated weekly plans with task management
- Reports: learning statistics and completion rate tracking
- Conversation history: full CRUD with pagination
- PostgreSQL (SQLAlchemy 2.0 + Alembic migrations)

**Frontend (React + Vite + Tailwind)**
- Login / Register with JWT token management
- Chat interface with agent-type indicators and citation display
- Conversation history sidebar with session switching
- Knowledge base management: upload, list, delete PDFs
- Learning plans: view plans and track task progress
- Learning reports: dashboard with statistics

**Infrastructure**
- Docker Compose: frontend + backend + PostgreSQL + Redis
- Docker health checks for all services
- Railway deployment configuration
- Vercel deployment configuration
- Neon PostgreSQL ready
- CORS configuration for production

### 🔒 Security
- Bcrypt password hashing
- JWT access tokens (15-min expiry)
- All API endpoints protected with user authentication
- User-level data isolation across all modules
- API keys removed from repository

### 📁 Project Structure
- `web_app/backend/` — FastAPI + LangGraph + SQLAlchemy
- `web_app/frontend/` — React + Vite + Tailwind
- `supervisor_agent/` — LangGraph multi-agent orchestration
- `docker-compose.yml` — One-command deployment

### ✅ Release Status
- All P0 blockers resolved
- 37/37 acceptance tests passed
- Health checks: PostgreSQL ✅ Redis ✅ Backend ✅ Frontend ✅
