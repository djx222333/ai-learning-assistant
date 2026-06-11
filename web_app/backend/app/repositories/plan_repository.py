# -*- coding: utf-8 -*-
"""Plan ???plans ? CRUD + ??"""
from typing import Optional
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import Plan, Task


def list_plans(user_id=None, status=None, offset=0, limit=20):
    """????????? + ???"""
    db = SessionLocal()
    try:
        query = db.query(Plan)
        if user_id:
            query = query.filter(Plan.user_id == user_id)
        if status:
            query = query.filter(Plan.status == status)
        total = query.count()
        plans = query.order_by(Plan.created_at.desc()).offset(offset).limit(limit).all()
        items = []
        for p in plans:
            all_t = db.query(Task).filter(Task.plan_id == p.id)
            items.append({
                "id": p.id, "title": p.title, "goal": p.goal,
                "status": p.status,
                "task_count": all_t.count(),
                "completed_count": all_t.filter(Task.status == "completed").count(),
                "created_at": p.created_at.isoformat() if p.created_at else "",
            })
        return {"total": total, "offset": offset, "limit": limit, "items": items}
    finally:
        db.close()


def get_plan(plan_id, user_id=None):
    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if plan and user_id and plan.user_id != user_id:
            return None
        if not plan:
            return None
        tasks = db.query(Task).filter(Task.plan_id == plan_id).order_by(Task.order).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed")
        return {
            "id": plan.id, "title": plan.title, "goal": plan.goal,
            "status": plan.status, "task_count": total,
            "completed_count": completed,
            "completion_rate": round(completed / total * 100, 1) if total else 0.0,
            "tasks": [{"id": t.id, "order": t.order, "description": t.description,
                       "agent_type": t.agent_type, "status": t.status, "result": t.result,
                       "created_at": t.created_at.isoformat() if t.created_at else "",
                       "updated_at": t.updated_at.isoformat() if t.updated_at else ""}
                      for t in tasks],
            "created_at": plan.created_at.isoformat() if plan.created_at else "",
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else "",
        }
    finally:
        db.close()


def delete_plan(plan_id, user_id=None):
    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if plan and user_id and plan.user_id != user_id:
            return None
        if not plan:
            return False
        db.delete(plan)
        db.commit()
        return True
    except:
        db.rollback()
        raise
    finally:
        db.close()


def get_plan_stats(plan_id, user_id=None):
    from sqlalchemy import func
    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if plan and user_id and plan.user_id != user_id:
            return None
        if not plan:
            return None
        rows = db.query(Task.status, func.count(Task.id)).filter(
            Task.plan_id == plan_id
        ).group_by(Task.status).all()
        sc = {r[0]: r[1] for r in rows}
        total = sum(sc.values()) or 1
        return {
            "plan_id": plan_id, "title": plan.title,
            "total": sum(sc.values()), "pending": sc.get("pending", 0),
            "in_progress": sc.get("in_progress", 0),
            "completed": sc.get("completed", 0), "failed": sc.get("failed", 0),
            "completion_rate": round(sc.get("completed", 0) / total * 100, 1),
        }
    finally:
        db.close()
