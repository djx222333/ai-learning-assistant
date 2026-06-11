# -*- coding: utf-8 -*-
"""Task ???tasks ? CRUD + ??"""
from typing import Optional
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Task, Plan


def list_tasks(user_id=None, plan_id=None, status=None, agent_type=None, offset=0, limit=20):
    """????????? + ??????"""
    db = SessionLocal()
    try:
        query = db.query(Task)
        if user_id:
            query = query.join(Plan).filter(Plan.user_id == user_id)
        if plan_id:
            query = query.filter(Task.plan_id == plan_id)
        if status:
            query = query.filter(Task.status == status)
        if agent_type:
            query = query.filter(Task.agent_type == agent_type)
        total = query.count()
        tasks = query.order_by(Task.plan_id, Task.order).offset(offset).limit(limit).all()
        return {
            "total": total, "offset": offset, "limit": limit,
            "items": [{"id": t.id, "plan_id": t.plan_id, "order": t.order,
                       "description": t.description, "agent_type": t.agent_type,
                       "status": t.status, "result": t.result,
                       "created_at": t.created_at.isoformat() if t.created_at else "",
                       "updated_at": t.updated_at.isoformat() if t.updated_at else ""}
                      for t in tasks],
        }
    finally:
        db.close()


def get_task(task_id, user_id=None):
    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == task_id).first()
        if not t:
            return None
        plan = db.query(Plan).filter(Plan.id == t.plan_id).first()
        if user_id and plan and plan.user_id != user_id:
            return None
        return {
            "id": t.id, "plan_id": t.plan_id, "plan_title": plan.title if plan else "",
            "order": t.order, "description": t.description,
            "agent_type": t.agent_type, "status": t.status, "result": t.result,
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "updated_at": t.updated_at.isoformat() if t.updated_at else "",
        }
    finally:
        db.close()


def update_task_status(task_id, new_status, user_id=None):
    assert new_status in ("pending", "in_progress", "completed", "failed")
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        plan = db.query(Plan).filter(Plan.id == task.plan_id).first()
        if user_id and plan and plan.user_id != user_id:
            return False
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    except:
        db.rollback()
        raise
    finally:
        db.close()
