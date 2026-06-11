# -*- coding: utf-8 -*-
"""????????????

???
1. ???????LLM + DB ????
2. ??/??? CRUD ??? Repository
3. ??/????
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.database import SessionLocal
from app.models import Plan, Task
from app.repositories import plan_repository, task_repository

import sys, os
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERVISOR_DIR = os.path.abspath(os.path.join(ADAPTER_DIR, "..", "..", "..", "..", "supervisor_agent"))
if SUPERVISOR_DIR not in sys.path:
    sys.path.insert(0, SUPERVISOR_DIR)
from agent_graph import get_llm


PLANNER_PROMPT = """?????????????
???????????????????????
?????? JSON??? markdown ????

{
  "title": "????",
  "weeks": [
    {
      "week": 1,
      "topic": "????",
      "description": "??????",
      "tasks": [
        {"order": 1, "description": "????", "agent_type": "code"}
      ]
    }
  ]
}
?? 3-5 ?????????agent_type ?? code/english/career/search/research?
"""


def generate_plan(goal, duration_weeks=8, user_id=None):
    """LLM ???? + DB ???"""
    response = get_llm().invoke([
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": f"?????{goal}\n?????{duration_weeks}?"},
    ])
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content
        if "```" in content:
            content = content.rsplit("```", 1)[0]
    start, end = content.find("{"), content.rfind("}")
    if start >= 0 and end > start:
        content = content[start:end+1]
    plan_data = json.loads(content)
    if "title" not in plan_data:
        plan_data["title"] = f"{goal} ????"

    db = SessionLocal()
    try:
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        plan = Plan(id=plan_id, user_id=user_id, title=plan_data["title"],
                    goal=goal, status="active", created_at=now, updated_at=now)
        db.add(plan)
        db.flush()
        order = 0
        for w in plan_data.get("weeks", []):
            wn = w.get("week", 1)
            for t in w.get("tasks", []):
                order += 1
                db.add(Task(plan_id=plan_id, order=order,
                        agent_type=t.get("agent_type", "code"),
                        description=f"Week{wn}: {t['description']}",
                        status="pending", created_at=now, updated_at=now))
        db.commit()
        weeks = [{"week": w["week"], "topic": w["topic"],
                  "description": w.get("description", ""),
                  "tasks": [{"order": t.get("order", i+1),
                             "description": t["description"],
                             "agent_type": t.get("agent_type", "code")}
                            for i, t in enumerate(w.get("tasks", []))]}
                 for w in plan_data.get("weeks", [])]
        return {"id": plan_id, "title": plan_data["title"], "goal": goal,
                "duration_weeks": duration_weeks, "weeks": weeks,
                "created_at": now.isoformat()}
    except:
        db.rollback()
        raise
    finally:
        db.close()


def list_plans(user_id=None, status=None, offset=0, limit=20):
    return plan_repository.list_plans(status=status, offset=offset, limit=limit)


def get_plan(plan_id):
    return plan_repository.get_plan(plan_id)


def delete_plan(plan_id, user_id=None):
    return plan_repository.delete_plan(plan_id)


def get_plan_stats(plan_id, user_id=None):
    return plan_repository.get_plan_stats(plan_id)


def list_tasks(user_id=None, plan_id=None, status=None, agent_type=None, offset=0, limit=20):
    return task_repository.list_tasks(plan_id=plan_id, status=status,
                                      agent_type=agent_type, offset=offset, limit=limit)


def get_task(task_id):
    return task_repository.get_task(task_id)


def update_task_status(task_id, new_status):
    return task_repository.update_task_status(task_id, new_status)
