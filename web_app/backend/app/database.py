# -*- coding: utf-8 -*-
"""数据库连接管理（SQLAlchemy 2.0）

设计原则：
1. 同步引擎用于 CRUD + Alembic 迁移（当前场景）
2. 异步引擎用于高性能场景（预留）
3. 所有表使用 UUID 主键，兼容 PostgreSQL 和 SQLite
4. 开发环境 SQLite / 生产环境 PostgreSQL 通过 DATABASE_URL 切换

使用方式：
    from app.database import SessionLocal
    with SessionLocal() as db:
        db.query(User).all()

切换到 PostgreSQL：
    修改 .env:
    DATABASE_URL=postgresql://user:pass@localhost:5432/ai_assistant
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

# 连接参数（SQLite 需要额外配置）
_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Declarative Base"""
    pass


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表（首次启动 / 测试）"""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """删除所有表（测试用）"""
    Base.metadata.drop_all(bind=engine)
