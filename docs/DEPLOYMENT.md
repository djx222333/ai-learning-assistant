# Deployment Guide

## Architecture (Production)

`
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Vercel    │────▶│   Railway    │────▶│    Neon     │
│  (Frontend) │     │  (Backend)   │     │ (PostgreSQL)│
│  React/Vite │     │  FastAPI     │     │             │
│  Nginx      │     │  LangGraph   │     │             │
│             │     │  FAISS       │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  DeepSeek    │
                   │  API         │
                   │  (External)  │
                   └──────────────┘
`

## Option 1: Docker (Recommended)

### Prerequisites

- Docker & Docker Compose installed
- DeepSeek API key

### Steps

`ash
# 1. Clone
git clone https://github.com/yourusername/ai-learning-assistant.git
cd ai-learning-assistant

# 2. Set environment variables
export DEEPSEEK_API_KEY=sk-your-key-here
export SECRET_KEY=

# 3. Start all services
docker compose up -d

# 4. Verify
curl http://localhost:8000/health
# → {"status":"ok","version":"1.0.0"}

# 5. Open
open http://localhost  # Frontend
open http://localhost:8000/docs  # API
`

### Stop

`ash
docker compose down -v  # Also removes volumes (data)
`

## Option 2: Railway + Vercel + Neon

### Prerequisites

- Railway account
- Vercel account
- Neon account (free PostgreSQL)

### Step 1: Neon Database

1. Go to [neon.tech](https://neon.tech) → Create project
2. Copy the connection string (`DATABASE_URL`)
3. Note: Neon provides a free 0.5 GB PostgreSQL instance

### Step 2: Railway Backend

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Deploy:
`ash
cd web_app/backend
railway init
railway up
`

4. Set environment variables in Railway Dashboard:
   - `DEEPSEEK_API_KEY`
   - `DATABASE_URL` (from Neon)
   - `SECRET_KEY` (generate with `openssl rand -hex 32`)
   - `CORS_ORIGINS` (your Vercel domain)

5. Run migrations: `railway run alembic upgrade head`

### Step 3: Vercel Frontend

1. Install Vercel CLI: `npm i -g vercel`
2. Deploy:
`ash
cd web_app/frontend
vercel --prod
`

3. Set environment variable in Vercel Dashboard:
   - `VITE_API_URL` (your Railway backend URL)

### Step 4: Verify

`ash
# Health check
curl https://your-app.railway.app/health

# Login test
curl -X POST https://your-app.railway.app/api/v1/auth/login \\
  -d \"username=admin&password=test123\"
`

## Production Checklist

### Security
- [ ] `SECRET_KEY` changed from default (generate with `openssl rand -hex 32`)
- [ ] `CORS_ORIGINS` set to your domain only
- [ ] PostgreSQL password changed from default
- [ ] HTTPS enabled (Vercel/Cloudflare)
- [ ] Rate limiting configured
- [ ] Environment variables set (not in .env files)

### Performance
- [ ] Embedding model cached (`TRANSFORMERS_OFFLINE=1`)
- [ ] Database connection pooling tuned
- [ ] Static assets served via CDN (Vercel does this automatically)

### Monitoring
- [ ] Railway dashboard for backend logs
- [ ] Vercel analytics for frontend
- [ ] PostgreSQL query performance (Neon dashboard)
- [ ] Error tracking (Sentry optional)

## Database Migrations

`ash
# Create migration
cd web_app/backend
alembic revision --autogenerate -m \"description\"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
`

## Troubleshooting

### Backend won't start
`ash
# Check logs
docker compose logs backend

# Verify API key
curl https://api.deepseek.com/v1/models \\
  -H \"Authorization: Bearer \\"
`

### Embedding model slow
The `all-MiniLM-L6-v2` model downloads on first start (~50s).
Set `TRANSFORMERS_OFFLINE=1` after first start to skip network check.

### Database connection failed
`ash
# Verify PostgreSQL is running
docker compose exec postgres pg_isready

# Test connection
docker compose exec backend python -c \\
  \"from app.database import engine; engine.connect()\"
`

## Cost Estimate

| Service | Plan | Monthly Cost |
|---------|------|-------------|
| Railway | Starter (5 USD credit) | -5 |
| Vercel | Pro (Hobby free) |  |
| Neon | Free (0.5 GB) |  |
| DeepSeek API | Pay-as-you-go | -5 |
| **Total** | | **-10/month** |
