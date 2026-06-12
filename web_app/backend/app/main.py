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
    from app.database import get_db_type, get_engine
    try:
        engine = get_engine()
        db_type = get_db_type()
        logger.info("[DB] Startup complete - database: %s", db_type)
    except Exception as e:
        logger.warning("[DB] Startup database init failed: %s", e)
    logger.info("Startup event: app is ready")

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
    from app.database import get_db_type
    return {
        "database": get_db_type(),
        "status": "connected",
    }

@app.get("/")
def root():
    return {"message": "AI Learning Assistant API is running"}
