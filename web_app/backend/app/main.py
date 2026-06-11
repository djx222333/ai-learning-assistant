# -*- coding: utf-8 -*-
"""FastAPI 应用入口（生产版）

CORS 来源从 config.py 读取，支持 Railway 环境变量配置。
日志级别通过 LOG_LEVEL 环境变量控制。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, chat, knowledge, plans, tasks, reports, conversations
from app.core.config import settings
import logging

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="AI Learning Assistant API",
    description="AI 学习助手 Web 版后端服务",
    version="1.0.0",
)

# CORS - 允许生产域名（Vercel）和本地开发
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
def root():
    return {"message": "AI Learning Assistant API is running"}

