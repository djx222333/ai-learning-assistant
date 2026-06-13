"""Alembic 迁移环境配置

连接到我们的数据库和 ORM 模型。
支持 SQLite 开发 / PostgreSQL 生产。
"""
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入所有 ORM 模型（确保 Base.metadata 包含所有表）
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database import Base
from app.models import (  # noqa: F401 — 确保模型被注册
    User, Conversation, Message,
    Document, Chunk, Plan, Task,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线迁移（不连接数据库，生成 SQL 脚本）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线迁移（从 settings 获取 DATABASE_URL 连接数据库执行）"""
    from app.core.config import settings
    from sqlalchemy import create_engine

    url = settings.DATABASE_URL

    # Auto-add sslmode=require (Neon PostgreSQL required)
    if url.startswith("postgresql") and "sslmode" not in url:
        separator = "&" if "?" in url else "?"
        url = url + separator + "sslmode=require"

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
