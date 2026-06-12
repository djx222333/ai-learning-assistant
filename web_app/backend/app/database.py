# -*- coding: utf-8 -*-
"""Database connection management (SQLAlchemy 2.0)

设计原则：
1. 模块级别不执行任何数据库导入（Lazy Loading）
2. get_engine() 在第一次调用时初始化
3. 支持 PostgreSQL / SQLite 自动切换
4. 数据库不可用时不影响 App 启动（Health Check 依赖）
"""
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

logger = logging.getLogger("database")

# 延迟初始化
_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def get_engine():
    """获取数据库引擎（首次调用时初始化）"""
    global _engine
    if _engine is not None:
        return _engine

    DATABASE_URL = settings.DATABASE_URL
    logger.info("Initializing database engine: %s...", DATABASE_URL[:40])

    _connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        _connect_args["check_same_thread"] = False
    elif DATABASE_URL.startswith("postgresql"):
        # 检查 PostgreSQL 驱动是否可用
        try:
            import psycopg2  # noqa: F401
            logger.info("psycopg2 driver available")
        except ImportError:
            logger.warning("psycopg2 not installed, falling back to SQLite")
            DATABASE_URL = "sqlite:///./app.db"
            _connect_args["check_same_thread"] = False

    _engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
    logger.info("Database engine initialized successfully")
    return _engine


def get_session_local():
    """获取 SessionLocal（首次调用时初始化）"""
    global _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal

    engine = get_engine()
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db():
    """FastAPI Dependency: 获取数据库会话"""
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def drop_db():
    """删除所有表（仅用于测试）"""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped")


# ============================================================
# 兼容导出（保持旧代码正常工作）
# 原 SessionLocal 是 sessionmaker 实例（可调用，返回 session）
# 新实现：SessionLocal() 内部延迟初始化引擎
# ============================================================

# 兼容导出 — 保持旧代码正常运行
# 原用法: SessionLocal() -> session
#   用法: inspect(engine) -> engine object
def SessionLocal():
    """返回一个新的数据库会话（兼容旧版 from app.database import SessionLocal）"""
    return get_session_local()()


# engine 兼容: 允许 from app.database import engine; inspect(engine)
class _EngineProxy:
    """懒加载引擎代理 — 首次访问时才初始化"""
    _instance = None

    def _get(self):
        if self._instance is None:
            self._instance = get_engine()
        return self._instance

    def __getattr__(self, name):
        return getattr(self._get(), name)

    def __repr__(self):
        return repr(self._get())


engine = _EngineProxy()

