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
# agent_adapter imports agent_graph -> RAGEngine (SentenceTransformer)
# which takes 10-50s to load. Defer to first request.
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

# Register routers (note: chat is lazy-loaded)
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
    logger.info("Startup event: app is ready")
    logger.info(f"Database: {settings.DATABASE_URL[:30]}...")

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
def root():
    return {"message": "AI Learning Assistant API is running"}
