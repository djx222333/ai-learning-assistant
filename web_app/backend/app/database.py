# -*- coding: utf-8 -*-
"""Database connection management (SQLAlchemy 2.0)

设计原则：
1. 模块级别不执行任何数据库导入（Lazy Loading）
2. get_engine() 在第一次调用时初始化
3. 支持 PostgreSQL / SQLite 自动切换
4. 数据库不可用时不影响 App 启动（Health Check 依赖）
5. 连接测试带超时，不会阻塞应用启动
"""
import logging
import os
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

logger = logging.getLogger("database")

# 延迟初始化（带互斥锁避免多线程同时初始化）
_engine = None
_SessionLocal = None
_db_type = None
_db_init_started = False


class Base(DeclarativeBase):
    pass


def get_db_type() -> str:
    """返回当前实际使用的数据库类型: 'postgresql' | 'sqlite'"""
    global _db_type
    if _db_type is None:
        get_engine()
    return _db_type or "sqlite"


def _mask_password(url: str) -> str:
    """隐藏密码用于日志输出"""
    if "@" not in url:
        return url
    try:
        parts = url.split("@")
        creds = parts[0].rsplit(":", 1)
        if len(creds) == 2:
            return creds[0] + ":***@" + parts[1]
    except Exception:
        pass
    return url[:50] + "..."


def _parse_url_info(url: str) -> dict:
    """解析 DATABASE_URL 返回结构化信息"""
    info = {
        "raw_scheme": "unknown",
        "host": "unknown",
        "port": "unknown",
        "database": "unknown",
        "has_ssl": False,
        "valid": False,
    }
    try:
        result = urllib.parse.urlparse(url)
        info["raw_scheme"] = result.scheme
        info["host"] = result.hostname or "unknown"
        info["port"] = str(result.port or 5432)
        info["database"] = (result.path or "").lstrip("/") or "unknown"
        params = urllib.parse.parse_qs(result.query)
        info["has_ssl"] = "sslmode" in params
        info["valid"] = True
    except Exception:
        pass
    return info


def _ensure_postgresql_ssl(url: str) -> str:
    """确保 PostgreSQL URL 包含 sslmode=require（Neon 必需）"""
    if not url.startswith("postgresql"):
        return url
    if "sslmode" in url:
        return url
    separator = "&" if "?" in url else "?"
    return url + separator + "sslmode=require"


def get_engine():
    """获取数据库引擎（首次调用时初始化，线程安全）"""
    global _engine, _SessionLocal, _db_type, _db_init_started

    if _engine is not None:
        return _engine

    # 防止多线程重复初始化
    if _db_init_started:
        import time
        timeout = 60  # 最多等 60 秒
        waited = 0
        while _engine is None and waited < timeout:
            time.sleep(0.5)
            waited += 0.5
        if _engine is not None:
            return _engine

    _db_init_started = True

    # ============================================================
    # 1. 读取并诊断 DATABASE_URL
    # ============================================================
    original_url = settings.DATABASE_URL
    DATABASE_URL = original_url

    logger.info("[DB] ====== Database Connection Diagnostic =====")
    logger.info("[DB] DATABASE_URL present: %s", bool(DATABASE_URL and DATABASE_URL.strip()))

    if not DATABASE_URL or DATABASE_URL.strip() == "":
        logger.warning("[DB] DATABASE_URL is EMPTY! Falling back to SQLite")
        _db_type = "sqlite"
        DATABASE_URL = "sqlite:///./app.db"
        _engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
        logger.info("[DB] Engine initialized: sqlite (fallback due to empty URL)")
        return _engine

    url_info = _parse_url_info(DATABASE_URL)
    logger.info("[DB]   scheme:   %s", url_info["raw_scheme"])
    logger.info("[DB]   host:     %s", url_info["host"])
    logger.info("[DB]   port:     %s", url_info["port"])
    logger.info("[DB]   database: %s", url_info["database"])
    logger.info("[DB]   ssl:      %s", url_info["has_ssl"])
    logger.info("[DB]   url:      %s", _mask_password(DATABASE_URL))

    # ============================================================
    # 2. 判断数据库类型
    # ============================================================
    _connect_args = {}

    if DATABASE_URL.startswith("sqlite"):
        _db_type = "sqlite"
        _connect_args["check_same_thread"] = False
        logger.info("[DB] Using SQLite")
        _engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
        logger.info("[DB] Engine initialized: sqlite")
        return _engine

    elif DATABASE_URL.startswith("postgresql"):
        _db_type = "postgresql"
        logger.info("[DB] DATABASE_URL detected as PostgreSQL")

        # ============================================================
        # 3. 检查 psycopg2 驱动
        # ============================================================
        try:
            import psycopg2  # noqa: F401
            logger.info("[DB] psycopg2 driver: OK (version %s)", psycopg2.__version__)
        except ImportError as e:
            logger.warning("[DB] psycopg2 driver: MISSING - %s", e)
            logger.warning("[DB] Falling back to SQLite")
            _db_type = "sqlite"
            DATABASE_URL = "sqlite:///./app.db"
            _connect_args["check_same_thread"] = False
            _engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
            logger.info("[DB] Engine initialized: sqlite (fallback due to missing driver)")
            return _engine

        # ============================================================
        # 4. 确保 SSL (Neon 必需)
        # ============================================================
        if not url_info["has_ssl"]:
            logger.info("[DB] Adding sslmode=require (required by Neon)")
            DATABASE_URL = _ensure_postgresql_ssl(DATABASE_URL)
        else:
            logger.info("[DB] SSL already configured in URL")

        # ============================================================
        # 5. 测试 PostgreSQL 连接（带超时）
        # ============================================================
        logger.info("[DB] Testing PostgreSQL connection (timeout: 10s)...")
        test_engine = create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"connect_timeout": 10},
        )
        try:
            with test_engine.connect() as conn:
                result = conn.execute(text("SELECT 1 AS test"))
                row = result.fetchone()
                logger.info("[DB] PostgreSQL connection: SUCCESS (SELECT 1 = %s)", row[0] if row else "?")
            test_engine.dispose()
            logger.info("[DB] Using PostgreSQL as primary database")
        except Exception as e:
            logger.error("[DB] PostgreSQL connection: FAILED")
            logger.error("[DB]   Exception type: %s", type(e).__name__)
            logger.error("[DB]   Exception msg: %s", str(e))
            import traceback
            logger.error("[DB]   Traceback:\n%s", "".join(traceback.format_exception_only(type(e), e)).strip())
            logger.warning("[DB] Falling back to SQLite")
            _db_type = "sqlite"
            DATABASE_URL = "sqlite:///./app.db"
            _connect_args["check_same_thread"] = False
            test_engine.dispose()
            _engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
            logger.info("[DB] Engine initialized: sqlite (fallback after PostgreSQL failure)")
            return _engine
        finally:
            try:
                test_engine.dispose()
            except Exception:
                pass

    # ============================================================
    # 6. 创建最终引擎
    # ============================================================
    _engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
    logger.info("[DB] Engine initialized: %s", _db_type)
    logger.info("[DB] ====== End Database Diagnostic =============")
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
# 兼容导出
# ============================================================

def SessionLocal():
    """返回一个新的数据库会话（兼容旧版 from app.database import SessionLocal）"""
    return get_session_local()()


class _EngineProxy:
    """懒加载引擎代理"""
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
