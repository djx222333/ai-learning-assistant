# -*- coding: utf-8 -*-
"""对话历史服务

职责：
1. 列表查询（分页 + 排序 + 用户隔离）
2. 详情查询
3. 消息查询（分页 + 排序）
4. 删除会话（级联删除消息）

依赖：
- conversations.user_id 实现用户隔离
- messages.conversation_id 关联查询
- cascade="all, delete-orphan" 自动级联删除
"""
from app.database import SessionLocal
from app.models import Conversation, Message


def list_conversations(
    user_id: str,
    offset: int = 0,
    limit: int = 20,
) -> dict:
    """获取当前用户的会话列表（按更新时间倒序）

    Args:
        user_id: 当前用户 ID（过滤条件）
        offset: 分页偏移
        limit: 每页条数

    Returns:
        {
            "total": int,
            "offset": int,
            "limit": int,
            "items": [{id, session_id, title, message_count,
                       last_message, created_at, updated_at}]
        }
    """
    db = SessionLocal()
    try:
        # 查询总数
        total = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .count()
        )

        # 查询分页数据（按 updated_at DESC）
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for conv in conversations:
            # 获取最新一条消息作为摘要预览
            last_msg = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .first()
            )
            last_message = ""
            if last_msg:
                last_message = last_msg.content[:100]

            items.append({
                "id": conv.id,
                "session_id": conv.session_id,
                "title": conv.title or "新对话",
                "message_count": conv.message_count or 0,
                "last_message": last_message,
                "created_at": conv.created_at.isoformat() if conv.created_at else "",
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else "",
            })

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": items,
        }
    finally:
        db.close()


def get_conversation(conversation_id: str, user_id: str) -> dict | None:
    """获取会话详情（校验用户归属）

    Args:
        conversation_id: 会话 UUID
        user_id: 当前用户 ID

    Returns:
        dict 或 None（不存在或无权限）
    """
    db = SessionLocal()
    try:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if not conv:
            return None

        return {
            "id": conv.id,
            "session_id": conv.session_id,
            "title": conv.title or "新对话",
            "message_count": conv.message_count or 0,
            "created_at": conv.created_at.isoformat() if conv.created_at else "",
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else "",
        }
    finally:
        db.close()


def get_conversation_messages(
    conversation_id: str,
    user_id: str,
    offset: int = 0,
    limit: int = 50,
) -> dict | None:
    """获取会话消息列表（按时间正序）

    先校验用户归属，再返回消息。

    Args:
        conversation_id: 会话 UUID
        user_id: 当前用户 ID
        offset: 分页偏移
        limit: 每页条数

    Returns:
        {"total": int, "offset": int, "limit": int, "items": [...]}
        或 None（不存在或无权限）
    """
    db = SessionLocal()
    try:
        # 校验归属
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if not conv:
            return None

        # 查询消息总数
        total = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .count()
        )

        # 查询消息（按 created_at ASC）
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "agent_type": m.agent_type,
                    "agent_name": m.agent_name,
                    "citations": m.citations,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in messages
            ],
        }
    finally:
        db.close()


def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """删除会话（校验用户归属后级联删除消息）

    Args:
        conversation_id: 会话 UUID
        user_id: 当前用户 ID

    Returns:
        True 删除成功 / False 不存在或无权限
    """
    db = SessionLocal()
    try:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if not conv:
            return False

        db.delete(conv)  # cascade 自动删除 messages
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()