# AI Learning Assistant — Production Deployment Guide

> Version: v1.0.0
> Updated: 2026-06-11

---

## 1. Architecture Overview

```mermaid
graph TB
    subgraph "Vercel (Frontend)"
        VERCEL["https://ai-learning-assistant.vercel.app"]
    end
    subgraph "Railway (Backend)"
        RAILWAY["https://ai-learning-assistant.railway.app"]
        API["FastAPI + LangGraph Agents"]
        RAG["RAG Engine + FAISS"]
    end
    subgraph "Neon (PostgreSQL)"
        PG["PostgreSQL 16"]
    end
    subgraph "DeepSeek"
        LLM["DeepSeek API"]
    end
    USER["Browser"] -->|"https://...vercel.app"| VERCEL
    VERCEL -->|"/api/* rewrite"| RAILWAY
    API -->|"SQLAlchemy"| PG
    API -->|"RAG Query"| RAG
    API -->|"DeepSeek Call"| LLM
```

## 2. Service Architecture

| Service | Platform | Role |
|---|---|---|
| Frontend | Vercel | Static SPA (React + Vite + Tailwind) |
| Backend | Railway | FastAPI + LangGraph Agents |
| Database | Neon (Railway) | PostgreSQL 16 |
| LLM | DeepSeek API | AI model for agents |
| Auth | JWT (built-in) | Token-based authentication |

---

## 3. Deployment Steps

### Step 1: Prepare Accounts

- [ ] Vercel: Create account at https://vercel.com
- [ ] Railway: Create account at https://railway.app
- [ ] Neon: Create database at https://neon.tech (or use Railway PostgreSQL plugin)
- [ ] DeepSeek: Get API key at https://platform.deepseek.com
- [ ] GitHub: Push project to a GitHub repository

### Step 2: Neon PostgreSQL

1. Go to https://neon.tech
2. Create a new project
3. Copy the connection string:
   `postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

### Step 3: Railway Backend

1. Go to Railway and create a new project
2. Select "Deploy from GitHub repo"
3. Railway auto-detects `railway.json` and builds via Dockerfile
4. Set environment variables (see section 4)

### Step 4: Vercel Frontend

1. Go to Vercel and create a new project
2. Import GitHub repository
3. Set Root Directory to `web_app/frontend`
4. Vercel auto-detects Vite framework
5. Set environment variables (see section 4)

### Step 5: Configure CORS

In Railway Dashboard, set:
```
CORS_ORIGINS=https://your-app.vercel.app
```

---

## 4. Environment Variables

### Railway (Backend)

| Variable | Required | Example | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | YES | `sk-xxxx` | DeepSeek API key |
| `DATABASE_URL` | YES | `postgresql://user:pass@neon:5432/db` | PostgreSQL connection |
| `SECRET_KEY` | YES | `random-256-bit-key` | JWT signing secret |
| `CORS_ORIGINS` | YES | `https://your-app.vercel.app` | Allowed frontend domains |
| `DEEPSEEK_MODEL` | NO | `deepseek-v4-flash` | Model name |
| `DEEPSEEK_BASE_URL` | NO | `https://api.deepseek.com/v1` | API base URL |
| `LOG_LEVEL` | NO | `info` | Log level |
| `MAX_UPLOAD_SIZE` | NO | `52428800` | Upload limit |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | NO | `15` | JWT expiry |

### Vercel (Frontend)

| Variable | Required | Example | Description |
|---|---|---|---|
| `RAILWAY_PUBLIC_DOMAIN` | YES | `app.up.railway.app` | Backend domain for rewrite |

---

## 5. CORS Configuration

Backend reads `CORS_ORIGINS` from env and splits by comma.

- **Dev default**: `http://localhost:5173,http://localhost:4173`
- **Production**: `https://your-app.vercel.app`

Multiple domains supported:
```
CORS_ORIGINS=https://app1.vercel.app,https://app2.vercel.app
```

---

## 6. Docker Build

### Local (full stack)
```bash
docker compose up -d
# Frontend: http://localhost
# Backend:  http://localhost:8000
# Health:   http://localhost:8000/health
```

### Build images manually
```bash
# Backend
docker build -t ai-backend -f web_app/backend/Dockerfile .

# Frontend
docker build -t ai-frontend -f web_app/frontend/Dockerfile .
```

---

## 7. Health Check

| Endpoint | Method | Response |
|---|---|---|
| `GET /health` | GET | `{"status": "ok", "version": "1.0.0"}` |

Railway healthcheck: `/health` with 120s timeout.
Docker HEALTHCHECK: `curl -f http://localhost:8000/health`

---

## 8. Database Migrations

Alembic runs automatically on backend startup:
```bash
alembic upgrade head && uvicorn app.main:app ...
```

Manual migration:
```bash
cd web_app/backend
alembic upgrade head
```

---

## 9. Production URLs

| Resource | URL |
|---|---|
| Frontend | `https://ai-learning-assistant.vercel.app` |
| Backend | `https://ai-learning-assistant.up.railway.app` |
| API Docs | `https://ai-learning-assistant.up.railway.app/docs` |
| Health | `https://ai-learning-assistant.up.railway.app/health` |

---

## 10. Go-Live Checklist

### Pre-Launch
- [ ] All 57 unit tests pass
- [ ] Railway backend deployed and healthy (`/health` returns 200)
- [ ] Vercel frontend deployed and accessible
- [ ] PostgreSQL migrations run successfully
- [ ] `DEEPSEEK_API_KEY` correctly configured
- [ ] `CORS_ORIGINS` set to Vercel domain
- [ ] `SECRET_KEY` set to strong random value
- [ ] `RAILWAY_PUBLIC_DOMAIN` set in Vercel
- [ ] Login/Register flow works end-to-end
- [ ] Chat flow works (messages sent/received)
- [ ] PDF upload works
- [ ] RAG QA works with citations

### Launch Day
- [ ] Domain DNS configured (if custom domain)
- [ ] SSL certificates active (auto by Vercel/Railway)
- [ ] Logging checked (no error spam)
- [ ] Backup strategy documented

### Post-Launch (48h)
- [ ] Monitor error rates
- [ ] Monitor response times
- [ ] Verify no data leakage between users

---

## 11. Estimated Monthly Costs

| Service | Plan | Cost |
|---|---|---|
| Vercel | Hobby (free) | $0 |
| Railway | Starter ($5/mo) | $5 |
| Neon PostgreSQL | Free (0.5GB) | $0 |
| DeepSeek API | Pay-as-you-go | ~$1-5 |
| **Total** | | **~$5-10/mo** |

---

## 12. Rollback Plan

**If deployment fails**:
1. Railway: Dashboard "Redeploy" to previous version
2. Vercel: Dashboard "Rollback to Production"
3. Database: Neon point-in-time recovery
4. DNS: Update A/CNAME records if custom domain

---

## 13. Known Production Considerations

| Issue | Severity | Recommendation |
|---|---|---|
| Embedding model loads ~25s on startup | P2 | Pre-warm with scheduled health check |
| No rate limiting on API | P2 | Add middleware in P2 |
| FAISS stored in-memory, lost on restart | P2 | Add persistent FAISS save/load |
| No request logging to file | P2 | Add structured logging |
| No CI/CD pipeline | P3 | Add GitHub Actions |
