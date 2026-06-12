# -*- coding: utf-8 -*-
"""FastAPI application entrypoint"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# === Startup logging ===
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("startup")
logger.info("FastAPI starting...")

# === Lazy imports for heavy modules ===
_adapter = None

def get_adapter():
    global _adapter
    if _adapter is None:
        logger.info("Loading agent adapter (first request)...")
        from app.services import agent_adapter
        _adapter = agent_adapter
        logger.info("Agent adapter loaded")
    return _adapter

app = FastAPI(
    title="AI Learning Assistant API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.v1 import auth, knowledge, plans, tasks, reports, conversations
app.include_router(auth.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")

# Chat router uses lazy adapter
from app.api.v1 import chat
app.include_router(chat.router, prefix="/api")

@app.on_event("startup")
async def startup():
    """Startup: initialize database and log connection status"""
    import urllib.parse
    from app.database import get_db_type, get_engine
    from app.core.config import settings, check_env_vars, get_database_url_from_any_env

    logger.info("[BOOT] ====== Environment Variable Check ======")

    # Check ALL possible PostgreSQL env vars
    env_vars = check_env_vars()
    for ev in env_vars:
        if ev["exists"]:
            logger.info("[BOOT]   %s = %s", ev["name"], ev["value_masked"])
        else:
            logger.info("[BOOT]   %s = (not set)", ev["name"])

    # Check what DATABASE_URL is actually used
    logger.info("[BOOT] settings.DATABASE_URL = %s", settings.DATABASE_URL[:50] + "..." if len(settings.DATABASE_URL) > 50 else settings.DATABASE_URL or "(empty string)")
    logger.info("[BOOT] settings.DATABASE_URL present: %s", bool(settings.DATABASE_URL and settings.DATABASE_URL.strip()))

    # Try to find PostgreSQL URL from any env var
    pg_url = get_database_url_from_any_env()
    if pg_url:
        logger.info("[BOOT] PostgreSQL URL found via env: %s", pg_url[:40] + "...")
    else:
        logger.info("[BOOT] No PostgreSQL URL found in any env var")

    if settings.DATABASE_URL:
        try:
            r = urllib.parse.urlparse(settings.DATABASE_URL)
            logger.info("[BOOT]   scheme: %s  host: %s  port: %s  db: %s",
                        r.scheme, r.hostname, r.port, (r.path or "").lstrip("/"))
        except Exception:
            pass

    logger.info("[BOOT] ====== DB Initialization ======")
    try:
        engine = get_engine()
        db_type = get_db_type()
        logger.info("[BOOT] Startup complete - database: %s", db_type)
    except Exception as e:
        logger.warning("[BOOT] Startup database init failed: %s", e)
        import traceback
        logger.warning("[BOOT] Traceback:\n%s", traceback.format_exc())
    logger.info("[BOOT] Startup event finished")

@app.get("/health")
def health_check():
    from app.database import get_db_type
    return {
        "status": "ok",
        "version": "1.0.0",
        "database": get_db_type(),
    }

@app.get("/db-status")
def db_status():
    from app.database import get_db_type, get_engine
    from app.core.config import settings
    import urllib.parse

    url = settings.DATABASE_URL
    info = {
        "present": bool(url and url.strip()),
        "url_prefix": (url[:30] + "...") if url and len(url) > 40 else (url or "empty"),
    }
    if url and "@" in url:
        parts = url.split("@")
        creds = parts[0].rsplit(":", 1)
        if len(creds) == 2:
            info["url_prefix"] = creds[0] + ":***@" + parts[1]

    # Parse URL
    parsed = {}
    try:
        r = urllib.parse.urlparse(url or "")
        parsed["scheme"] = r.scheme
        parsed["host"] = r.hostname
        parsed["port"] = r.port
        parsed["database"] = (r.path or "").lstrip("/")
        params = urllib.parse.parse_qs(r.query)
        parsed["sslmode"] = params.get("sslmode", [None])[0]
    except Exception:
        pass

    engine_ok = False
    connection_ok = False
    error = None
    try:
        e = get_engine()
        engine_ok = True
        from sqlalchemy import text
        with e.connect() as conn:
            conn.execute(text("SELECT 1"))
            connection_ok = True
    except Exception as ex:
        error = str(ex)[:200]

    return {
        "database_type": get_db_type(),
        "database_url_present": info["present"],
        "database_url_masked": info["url_prefix"],
        "url_details": parsed,
        "engine_initialized": engine_ok,
        "connection_ok": connection_ok,
        "error": error,
    }

@app.get("/env-check")
def env_check():
    """诊断: 检查所有可能的 PostgreSQL 环境变量
    
    Railway 可能使用以下任一变量注入数据库连接:
      - DATABASE_URL (标准)
      - POSTGRES_URL (Railway 早期)
      - POSTGRESQL_URL
      - PGHOST + PGPORT + PGDATABASE + PGUSER + PGPASSWORD (独立参数)
    """
    from app.core.config import check_env_vars, get_database_url_from_any_env, POSTGRES_ENV_VARS

    # 1. 逐个检查环境变量
    vars_report = check_env_vars()

    # 2. 尝试从任意变量构建 DATABASE_URL
    constructed_url = get_database_url_from_any_env()

    # 3. 当前 settings 实际使用的 URL
    from app.core.config import settings
    current_url = settings.DATABASE_URL

    # 4. 检查 Dockerfile 是否可能覆盖
    dockerfile_default = current_url == "sqlite:///./app.db"

    return {
        "environment_variables": vars_report,
        "constructed_postgresql_url_exists": constructed_url is not None,
        "constructed_postgresql_url": (constructed_url[:40] + "...") if constructed_url else None,
        "current_settings_database_url": (current_url[:40] + "...") if current_url and len(current_url) > 40 else (current_url or "(empty)"),
        "likely_using_dockerfile_default": dockerfile_default,
        "conclusion": _diagnose_db_env(vars_report),
    }


def _diagnose_db_env(vars_report: list[dict]) -> str:
    """根据环境变量检查结果给出诊断结论"""
    # 检查是否有任何 PostgreSQL URL 变量
    has_database_url = any(
        v["exists"] for v in vars_report
        if v["name"] in ("DATABASE_URL",)
    )
    has_postgres_url = any(
        v["exists"] for v in vars_report
        if v["name"] in ("POSTGRES_URL", "POSTGRESQL_URL", "NEON_DATABASE_URL", "RAILWAY_DATABASE_URL")
    )
    has_pg_host = any(
        v["exists"] for v in vars_report
        if v["name"] in ("PGHOST",)
    )

    if has_database_url:
        return "A: DATABASE_URL is set by Railway"
    if has_postgres_url:
        return "B: POSTGRES_URL/POSTGRESQL_URL is set but config.py reads DATABASE_URL (variable name mismatch)"
    if has_pg_host:
        return "B: PGHOST is set but config reads DATABASE_URL (need to combine PGHOST+PGPORT+PGDATABASE...)"
    return "A: Railway NOT injecting any PostgreSQL variable - check if Neon/PostgreSQL plugin is attached"


@app.get("/")
def root():
    return {"message": "AI Learning Assistant API is running"}
