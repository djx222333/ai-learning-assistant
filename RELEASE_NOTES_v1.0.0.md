# AI Learning Assistant v1.0.0 — Release Notes

## Overview

First major release of the AI Learning Assistant — a multi-agent learning platform that routes user questions to specialized AI agents via LangGraph.

## What's Included

### Agent System
- Supervisor Agent with conditional edge routing to 6 specialized agents
- Code Agent: Python programming Q&A, calculator, file reading tools
- English Agent: English learning support
- Career Agent: Learning roadmaps, user profile management
- Search Agent: DuckDuckGo real-time web search
- Research Agent: Multi-source research with web search
- RAG Agent: PDF upload → chunking → embedding → retrieval → citation-grounded answers
- Planner Agent: Generates structured weekly learning plans with task breakdown
- Session Memory: LangGraph MemorySaver for conversational context
- Long-Term Memory: JSON-based user profile persistence across sessions

### Backend (FastAPI)
- 20 REST API endpoints, 100% JWT protected
- JWT authentication: register, login, token management
- User data isolation across all modules
- RAG engine: PDF parsing, text chunking, FAISS vector search, citation extraction
- Learning plans: weekly plans with task management and status tracking
- Reports: learning statistics and completion rates
- Conversation history: paginated CRUD with session management
- PostgreSQL via SQLAlchemy 2.0 with Alembic migrations (7 tables)

### Frontend (React + Vite + Tailwind)
- Login / Register with JWT token persistence
- Chat interface with agent-type indicators and citation display
- Conversation history sidebar with session switching
- Knowledge base management: upload, list, delete PDFs

### Infrastructure
- Docker Compose orchestration (frontend + backend + PostgreSQL + Redis)
- Docker health checks for all services
- Railway deployment configuration
- Vercel deployment configuration with SPA rewrites
- Neon PostgreSQL ready

## Security
- Bcrypt password hashing
- JWT access tokens (15-min expiry)
- All 20 business API endpoints protected with user authentication
- User-level data isolation across all modules

## Quality
- 57 unit tests across 4 test suites (100% pass rate)
- Clean architecture: Model-Repository-Service-API separation
- 7 database tables with full foreign keys, indexes, and check constraints

## Deployment
See DEPLOY.md for full production deployment guide.
