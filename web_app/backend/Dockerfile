# ============================================================
# Backend Dockerfile
# Single-stage build (eliminates multi-stage COPY issues)
# Context: project root (E:\Exploit_1)
# ============================================================

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (leverage Docker cache)
COPY web_app/backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# [DIAGNOSTIC] Verify psycopg2 installation
RUN pip list 2>/dev/null | grep -i psycopg || echo "[WARN] psycopg2 NOT found in pip list"
RUN python -c "import psycopg2; print('[DIAG] psycopg2 OK, version:', psycopg2.__version__)" 2>&1 || echo "[WARN] psycopg2 import FAILED"

# Install FAISS (cpu) explicitly
RUN pip install --no-cache-dir faiss-cpu

# Copy application code
COPY supervisor_agent/ /app/supervisor_agent/
COPY web_app/backend/ /app/web_app/backend/

# Create runtime directories
RUN mkdir -p /app/web_app/backend/uploads \
             /app/web_app/backend/data \
             /app/supervisor_agent/rag_index

# [DIAGNOSTIC] Final psycopg2 check
RUN python -c "import psycopg2; print('[OK] psycopg2-binary', psycopg2.__version__, 'READY')"

# Environment defaults (overridden by Railway)
ENV DATABASE_URL=postgresql://ai_assistant:ai_assistant@postgres:5432/ai_assistant
ENV DEEPSEEK_API_KEY=""
ENV DEEPSEEK_MODEL=deepseek-chat
ENV DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
ENV UPLOAD_DIR=/app/web_app/backend/uploads
ENV PYTHONPATH=/app/web_app/backend:/app/supervisor_agent
ENV SECRET_KEY=change-me-in-production

WORKDIR /app/web_app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Startup
CMD echo "[BOOT] Starting container" && \
    python -c "import psycopg2; print('[BOOT] psycopg2', psycopg2.__version__, 'OK')" && \
    echo "[BOOT] Running migrations..." && \
    alembic upgrade head 2>&1 || echo "[WARN] Migration failed, continuing..." && \
    echo "[BOOT] Starting FastAPI on port ${PORT:-8000}" && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
