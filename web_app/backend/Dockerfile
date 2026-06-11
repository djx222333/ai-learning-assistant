# ============================================================
# Backend Dockerfile
# Context: ../.. (E:\Exploit_1)
# Includes: web_app/backend/ + supervisor_agent/
# ============================================================

# Stage 1: Builder - install Python packages
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY web_app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY supervisor_agent/ /app/supervisor_agent/
COPY web_app/backend/ /app/web_app/backend/

# Create runtime directories
RUN mkdir -p /app/web_app/backend/uploads \
             /app/web_app/backend/data \
             /app/supervisor_agent/rag_index

# Environment defaults (overridden by docker-compose)
ENV DATABASE_URL=postgresql://ai_assistant:ai_assistant@postgres:5432/ai_assistant
ENV DEEPSEEK_API_KEY=""
ENV DEEPSEEK_MODEL=deepseek-v4-flash
ENV DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
ENV UPLOAD_DIR=/app/web_app/backend/uploads
ENV PYTHONPATH=/app/web_app/backend:/app/supervisor_agent
ENV SECRET_KEY=change-me-in-production

WORKDIR /app/web_app/backend

# Health check (after embedding model loads ~40s)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint: migrate DB then start server
CMD sh -c "alembic upgrade head && \
           uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"
