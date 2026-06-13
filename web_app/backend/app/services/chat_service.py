# -*- coding: utf-8 -*-
"""Chat Service: RAG + Agent + Persistence"""
from datetime import datetime, timezone
# Lazy import: agent_adapter is loaded on first use
from . import knowledge_service
from app.database import SessionLocal
from app.models import Conversation, Message

RELEVANCE_THRESHOLD = 0.4


def _utcnow():
    return datetime.now(timezone.utc)



def _get_or_create_conversation(db, session_id, user_id, conversation_id=None):
    # 1) 优先按 conversation_id 查找（确保刷新后标题不丢失）
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        ).first()
        if conv:
            if conv.session_id != session_id:
                conv.session_id = session_id
                db.commit()
            return conv

    # 2) 回退：按 session_id 查找
    conv = db.query(Conversation).filter(
        Conversation.session_id == session_id,
        Conversation.user_id == user_id,
    ).first()
    if conv:
        return conv

    # 3) 创建新会话
    conv = Conversation(
        session_id=session_id,
        user_id=user_id,
        title="New Conversation",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _get_adapter():
    import sys
    if 'app.services.agent_adapter' not in sys.modules:
        from app.services import agent_adapter as _a
        return _a
    return sys.modules['app.services.agent_adapter']

def send_message(message, session_id=None, user_id=None, username="", conversation_id=None):
    session_id = session_id or f"anon-{user_id or 'default'}"
    citations = []
    source = "llm"
    augmented = message

    # Step 1: RAG search (always try first)
    try:
        raw_citations = knowledge_service.search(message, top_k=3, conversation_id=conversation_id)
        scores = [c["relevance_score"] for c in raw_citations] if raw_citations else []
        max_score = max(scores) if scores else 0.0

        if raw_citations and max_score >= RELEVANCE_THRESHOLD:
            context_parts = ["Below are relevant content from your uploaded documents:\\n"]
            for i, c in enumerate(raw_citations):
                context_parts.append(
                    f"[Source {i+1}] {c['document_name']} "
                    f"(relevance: {c['relevance_score']:.0%})\\n"
                    f"{c['chunk_text']}\\n"
                )
            context = "\\n".join(context_parts)
            augmented = context + "\\n---\\nPlease answer based on the above content. Cite sources.\\n\\nUser question: " + message
            citations = [c for c in raw_citations if c["relevance_score"] >= RELEVANCE_THRESHOLD]
            source = "rag"
    except Exception as e:
        print(f"RAG search failed (fallback to LLM): {e}")

    # Step 2: Call Agent
    result = _get_adapter().chat(augmented, session_id=session_id)

    # Step 3: Persist to database
    db = SessionLocal()
    try:
        conv = _get_or_create_conversation(db, session_id, user_id or "", conversation_id=conversation_id)

        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=message,
        )
        db.add(user_msg)

        ai_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=result["answer"],
            agent_type=result.get("agent_type", ""),
            agent_name=result.get("agent_name", ""),
            citations=citations if citations else None,
        )
        db.add(ai_msg)
        conv.message_count = (conv.message_count or 0) + 2
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to persist messages: {e}")
    finally:
        db.close()

    # Step 4: Return result
    result["citations"] = citations
    result["source"] = source
    return result


def get_conversation_history(session_id, user_id=None, limit=50):
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

