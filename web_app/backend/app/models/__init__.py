# -*- coding: utf-8 -*-
"""SQLAlchemy 2.0 ORM 模型

7 张表的 ER 关系：

users ──1:N── conversations ──1:N── messages
users ──1:N── documents ──1:N── chunks
users ──1:N── plans ──1:N── tasks

字段设计原则：
1. 所有表使用 UUID 主键（兼容 PostgreSQL / SQLite）
2. 外键使用 UUID 字符串（SQLite 不支持 UUID 原生类型）
3. 使用 UTC 时间戳
4. JSON 字段用于非索引的结构化数据（message.citations）
5. 枚举字段使用 String + CheckConstraint（兼容所有数据库）
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean,
    DateTime, ForeignKey, JSON, CheckConstraint, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ============================================================
# 用户表
# ============================================================

class User(Base):
    """注册用户

    当前设计：允许匿名使用（user_id 可为空）。
    正式上线后新增功能：注册 → 登录 → JWT → 关联所有数据。
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    hashed_password = Column(String(256), nullable=False)
    display_name = Column(String(64), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    conversations = relationship("Conversation", back_populates="user")
    documents = relationship("Document", back_populates="user")
    plans = relationship("Plan", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"


# ============================================================
# 会话表
# ============================================================

class Conversation(Base):
    """对话会话

    对应前端的 session_id。
    一个会话包含多轮问答（messages）。
    当前使用 session_id 作为外部标识。
    """
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(256), default="新对话")
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Conversation {self.session_id}>"


# ============================================================
# 消息表
# ============================================================

class Message(Base):
    """对话消息

    用户消息 → HumanMessage
    AI 回应 → AssistantMessage（含 agent_type, agent_name, citations）

    citations 存储为 JSON：
    [
        {
            "document_name": "Python基础.pdf",
            "chunk_id": 15,
            "chunk_text": "...",
            "relevance_score": 0.92
        }
    ]
    """
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)

    # AI 消息特有字段
    agent_type = Column(String(32), nullable=True)  # code / english / career / search / research / rag / planner
    agent_name = Column(String(64), nullable=True)

    # 引用来源（JSON 数组）
    citations = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=_utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            role.in_(["user", "assistant"]),
            name="ck_message_role",
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    def __repr__(self):
        return f"<Message {self.role} [{self.created_at}]>"


# ============================================================
# 文档表
# ============================================================

class Document(Base):
    """上传文档

    替换 documents.json。
    与 chunks 一对多关联。
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    index_status = Column(String(16), default="processing")  # processing / ready / failed
    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    user = relationship("User", back_populates="documents")
    chunks = relationship(
        "Chunk", back_populates="document",
        order_by="Chunk.chunk_index",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            index_status.in_(["processing", "ready", "failed"]),
            name="ck_document_status",
        ),
    )

    def __repr__(self):
        return f"<Document {self.filename} [{self.index_status}]>"


# ============================================================
# 文本块表
# ============================================================

class Chunk(Base):
    """文档切块

    替换 chunk_metadata.json。
    每个 chunk 对应一个文本块 + 所属文档。
    embedding_idx 记录 chunk 在 FAISS 索引中的位置。
    """
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_idx = Column(Integer, nullable=True)  # FAISS 索引中的位置
    created_at = Column(DateTime, default=_utcnow)

    # 关系
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index", unique=True),
    )

    def __repr__(self):
        return f"<Chunk {self.chunk_index} of {self.document_id}>"


# ============================================================
# 学习计划表
# ============================================================

class Plan(Base):
    """学习计划

    Planner Agent 生成的长期学习计划。
    包含多个 Task（子任务）。
    """
    __tablename__ = "plans"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(256), nullable=False)
    goal = Column(Text, nullable=True)  # 用户设定的学习目标
    status = Column(String(16), default="active")  # active / completed / abandoned
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    user = relationship("User", back_populates="plans")
    tasks = relationship(
        "Task", back_populates="plan",
        order_by="Task.order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            status.in_(["active", "completed", "abandoned"]),
            name="ck_plan_status",
        ),
    )

    def __repr__(self):
        return f"<Plan {self.title} [{self.status}]>"


# ============================================================
# 任务表
# ============================================================

class Task(Base):
    """学习计划子任务

    Planner Agent 拆解出的具体执行步骤。
    每个任务分配给一个子 Agent 执行。
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=_uuid)
    plan_id = Column(String(36), ForeignKey("plans.id"), nullable=False, index=True)
    order = Column(Integer, nullable=False)  # 执行顺序
    agent_type = Column(String(32), nullable=False)  # 分配给哪个 Agent
    description = Column(Text, nullable=False)  # 任务描述
    status = Column(String(16), default="pending")  # pending/in_progress/completed/failed
    result = Column(Text, nullable=True)  # 执行结果
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    plan = relationship("Plan", back_populates="tasks")

    __table_args__ = (
        CheckConstraint(
            status.in_(["pending", "in_progress", "completed", "failed"]),
            name="ck_task_status",
        ),
    )

    def __repr__(self):
        return f"<Task {self.order}: {self.agent_type} [{self.status}]>"
