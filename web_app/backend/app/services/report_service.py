# -*- coding: utf-8 -*-
"""?????????????

???
1. ? 5 ???plans, tasks, documents, conversations, messages?????
2. ????????
3. ?????? SQLAlchemy ORM ????
"""
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Plan, Task, Document, Conversation, Message


def get_overview(user_id: str = None) -> dict:
    """???????????????

    Args:
        user_id: ???? ID????????

    Returns:
        {plans, tasks, completed_tasks, completion_rate, documents,
         conversations, messages, agent_distribution, plans_by_status}
    """
    db = SessionLocal()
    try:
        # Plans
        q = db.query(func.count(Plan.id))
        if user_id:
            q = q.filter(Plan.user_id == user_id)
        plans_count = q.scalar() or 0

        # Tasks
        tq = db.query(func.count(Task.id))
        if user_id:
            tq = tq.join(Plan).filter(Plan.user_id == user_id)
        tasks_total = tq.scalar() or 0

        tcq = db.query(func.count(Task.id)).filter(Task.status == "completed")
        if user_id:
            tcq = tcq.join(Plan).filter(Plan.user_id == user_id)
        tasks_completed = tcq.scalar() or 0

        # Documents
        dq = db.query(func.count(Document.id)).filter(Document.index_status == "ready")
        if user_id:
            dq = dq.filter(Document.user_id == user_id)
        documents_ready = dq.scalar() or 0

        # Conversations
        cvq = db.query(func.count(Conversation.id))
        if user_id:
            cvq = cvq.filter(Conversation.user_id == user_id)
        conversations_count = cvq.scalar() or 0

        # Messages
        msq = db.query(func.count(Message.id))
        if user_id:
            msq = msq.join(Conversation).filter(Conversation.user_id == user_id)
        messages_count = msq.scalar() or 0

        # Agent distribution
        agq = db.query(Task.agent_type, func.count(Task.id))
        if user_id:
            agq = agq.join(Plan).filter(Plan.user_id == user_id)
        agent_dist = dict(agq.group_by(Task.agent_type).all())

        # Plans by status
        pbsq = db.query(Plan.status, func.count(Plan.id))
        if user_id:
            pbsq = pbsq.filter(Plan.user_id == user_id)
        plans_by_status = dict(pbsq.group_by(Plan.status).all())

        completion_rate = (
            round(tasks_completed / tasks_total * 100, 1)
            if tasks_total > 0
            else 0.0
        )

        return {
            "plans": plans_count,
            "tasks": tasks_total,
            "completed_tasks": tasks_completed,
            "completion_rate": completion_rate,
            "documents": documents_ready,
            "conversations": conversations_count,
            "messages": messages_count,
            "agent_distribution": agent_dist,
            "plans_by_status": plans_by_status,
        }
    finally:
        db.close()
