# -*- coding: utf-8 -*-
"""对话服务：发送消息 + RAG 上下文注入 + 消息持久化

职责链：
  send_message()
    ├── 1. 获取/创建 Conversation（按 session_id + user_id）
    ├── 2. 保存用户消息到 messages 表
    ├── 3. RAG 预检索（knowledge_service.search）
    ├── 4. 调用 Agent（agent_adapter.chat）
    ├── 5. 保存 AI 回复到 messages 表
    └── 6. 返回 {answer, agent_type, citations}
"""
from datetime import datetime, timezone
from . import agent_adapter
from . import knowledge_service
from app.database import SessionLocal
from app.models import Conversation, Message

RELEVANCE_THRESHOLD = 0.3


def _utcnow():
    return datetime.now(timezone.utc)


def _get_or_create_conversation(db, session_id: str, user_id: str) -> Conversation:
    """按 session_id 查找或创建对话会话

    用户隔离逻辑：
    - 查找时同时过滤 session_id + user_id
    - 创建时写入 user_id
    - 不同用户即使使用相同 session_id，也会获得不同 Conversation
    """
    conv = db.query(Conversation).filter(
        Conversation.session_id == session_id,
        Conversation.user_id == user_id,
    ).first()

    if not conv:
        conv = Conversation(
            session_id=session_id,
            user_id=user_id,
            title="新对话",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    return conv


def send_message(
    message: str,
    session_id: str = None,
    user_id: str = None,
    username: str = "",
) -> dict:
    """发送消息：RAG 检索 -> Agent 调用 -> 持久化 -> 返回

    Args:
        message: 用户消息
        session_id: 会话 ID（用于 MemorySaver 区分会话）
        user_id: 当前用户 ID（用于数据隔离）
        username: 当前用户名（用于日志）

    Returns:
        {answer, agent_type, agent_name, citations}
    """
    session_id = session_id or f"anon-{user_id or 'default'}"
    citations = []
    augmented = message

    # ========== RAG 预检索 ==========
    try:
        raw_citations = knowledge_service.search(message, top_k=3)
        valid = [c for c in raw_citations if c["relevance_score"] >= RELEVANCE_THRESHOLD]

        if valid:
            context_parts = ["以下是你已上传文档中的相关内容：\n"]
            for i, c in enumerate(valid):
                context_parts.append(
                    f"[来源 {i+1}] 《{c['document_name']}》"
                    f"（相关度: {c['relevance_score']:.0%}）\n"
                    f"{c['chunk_text']}\n"
                )
            context = "\n".join(context_parts)
            augmented = context + "\n---\n请基于上述内容回答，并标注引用来源。\n\n用户问题：" + message
            citations = valid
    except Exception as e:
        print(f"RAG search failed (fallback): {e}")

    # ========== 调用 Agent ==========
    result = agent_adapter.chat(augmented, session_id=session_id)

    # ========== 持久化到数据库 ==========
    db = SessionLocal()
    try:
        conv = _get_or_create_conversation(db, session_id, user_id or "")

        # 保存用户消息
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=message,
        )
        db.add(user_msg)

        # 保存 AI 回复
        ai_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=result["answer"],
            agent_type=result.get("agent_type", ""),
            agent_name=result.get("agent_name", ""),
            citations=citations if citations else None,
        )
        db.add(ai_msg)

        # 更新会话元信息
        conv.message_count = (conv.message_count or 0) + 2
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Failed to persist messages: {e}")
    finally:
        db.close()

    # ========== 返回结果 ==========
    result["citations"] = citations
    return result


def get_conversation_history(
    session_id: str,
    user_id: str = None,
    limit: int = 50,
) -> list[dict]:
    """获取对话历史（按用户隔离）

    Args:
        session_id: 会话 ID
        user_id: 当前用户 ID（过滤条件）
        limit: 返回条数上限
    """
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id,
        ).first()
        if not conv:
            return []

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
            .limit(limit)
            .all()
        )

        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_type": m.agent_type,
                "agent_name": m.agent_name,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
    finally:
        db.close()