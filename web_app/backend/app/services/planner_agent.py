# -*- coding: utf-8 -*-
"""planner_agent.py - 学习计划生成 Agent

职责：
1. 接收用户学习目标 + 时间（如 "8周内学会 FastAPI"）
2. LLM 分析目标 → 拆解知识点 → 生成周计划
3. 自动写入 PostgreSQL (plans + tasks 表)
4. 返回结构化 JSON

接入 Supervisor 的方式：
  Supervisor 路由 "planner" 到 planner_node（LangGraph 内）。
  本服务是独立的 REST API 实现，直接调用 LLM + DB，
  不依赖 Supervisor 图。

数据流：
  POST /plans/generate
    → generate_plan(goal, duration_weeks, user_id)
      → LLM prompt: 学习计划生成
      → LLM response: JSON {weeks: [{week, topic, description, tasks}]}
      → DB: INSERT into plans
      → DB: INSERT into tasks (batch)
      → Return PlanResponse
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models import Plan, Task

# ---- LLM 配置 ----
# 复用 supervisor_agent 的 LLM 配置
# 从 agent_adapter 模块获取 ChatOpenAI 类
import sys, os

ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERVISOR_DIR = os.path.abspath(os.path.join(ADAPTER_DIR, "..", "..", "..", "..", "supervisor_agent"))
if SUPERVISOR_DIR not in sys.path:
    sys.path.insert(0, SUPERVISOR_DIR)

from agent_graph import get_llm


# ============================================================
# 数据模型
# ============================================================

class WeeklyTask(BaseModel):
    """周计划中的单个学习任务"""
    order: int = Field(..., description="当周任务序号")
    description: str = Field(..., description="任务描述")
    agent_type: str = Field("code", description="负责 Agent 类型")

    class Config:
        from_attributes = True


class WeeklyPlan(BaseModel):
    """一周学习计划"""
    week: int = Field(..., description="第几周")
    topic: str = Field(..., description="本周主题")
    description: str = Field(..., description="本周内容概述")
    tasks: list[WeeklyTask] = Field(default_factory=list, description="具体任务列表")

    class Config:
        from_attributes = True


class PlanRequest(BaseModel):
    """生成学习计划的请求"""
    goal: str = Field(..., description="学习目标", min_length=2, max_length=500)
    duration_weeks: int = Field(8, description="计划周数", ge=1, le=52)
    user_id: Optional[str] = Field(None, description="用户 ID（可选）")


class PlanResponse(BaseModel):
    """生成学习计划的响应"""
    id: str = Field(..., description="计划 ID")
    title: str = Field(..., description="计划标题")
    goal: str = Field(..., description="学习目标")
    duration_weeks: int = Field(..., description="计划周数")
    weeks: list[WeeklyPlan] = Field(default_factory=list, description="每周计划详情")
    created_at: str = Field(..., description="创建时间")


class PlanListItem(BaseModel):
    """计划列表项"""
    id: str
    title: str
    goal: str
    status: str
    task_count: int
    created_at: str

    class Config:
        from_attributes = True


# ============================================================
# Prompt 模板
# ============================================================

PLANNER_SYSTEM_PROMPT = """你是一个专业的学习规划师。
你的任务是：根据用户的学习目标和时间，制定详细的学习计划。

输出格式必须是 JSON，不要包含 markdown 代码块或额外文字：

{
  "title": "计划标题（一句话概括）",
  "weeks": [
    {
      "week": 1,
      "topic": "本周主题（简短）",
      "description": "本周学习内容概述（50-100字）",
      "tasks": [
        {
          "order": 1,
          "description": "具体学习任务（30-50字）",
          "agent_type": "code"
        }
      ]
    }
  ]
}

注意事项：
1. 每周 3-5 个具体任务
2. 知识点由浅入深，前后有依赖关系
3. agent_type 可选：code / english / career / search / research
4. 确保计划可执行，每周工作量适中
5. 每周主题要清晰，任务描述要具体
"""


# ============================================================
# 核心函数
# ============================================================

def _llm_generate_plan(goal: str, duration_weeks: int) -> dict:
    """调用 LLM 生成学习计划 JSON

    Args:
        goal: 学习目标（如 "学会 FastAPI"）
        duration_weeks: 计划周数

    Returns:
        {"title": "...", "weeks": [...]}

    异常:
        ValueError: LLM 返回内容无法解析为 JSON
    """
    llm = get_llm()
    if llm is None:
        return {"error": "LLM not available - check API key"}

    user_prompt = (
        f"学习目标：{goal}\n"
        f"计划周数：{duration_weeks}周\n\n"
        f"请生成一个详细的学习计划。"
    )

    response = llm.invoke([
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    content = response.content.strip()

    # 移除可能的 markdown 代码块
    if content.startswith("```"):
        # 找到第一个 ``` 之后的第一个换行，然后找到最后一个 ```
        content = content.split("\n", 1)[1] if "\n" in content else content
        if "```" in content:
            content = content.rsplit("```", 1)[0]
    content = content.strip()

    # 解析 JSON
    try:
        plan_data = json.loads(content)
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            content = content[start:end]
            plan_data = json.loads(content)
        else:
            raise ValueError(f"LLM 返回内容无法解析为 JSON:\n{content[:500]}")

    # 校验必要字段
    if "title" not in plan_data:
        plan_data["title"] = f"{goal} 学习计划"
    if "weeks" not in plan_data or not plan_data["weeks"]:
        raise ValueError("LLM 返回的周计划为空")

    # 确保每周有任务
    for w in plan_data["weeks"]:
        if "tasks" not in w or not w["tasks"]:
            w["tasks"] = [
                {"order": 1, "description": f"学习 {w['topic']} 基础知识", "agent_type": "code"}
            ]

    return plan_data


def generate_plan(
    goal: str,
    duration_weeks: int = 8,
    user_id: Optional[str] = None,
) -> dict:
    """生成学习计划并持久化到数据库

    完整流程：
    1. LLM 分析目标 + 时间 → JSON 计划
    2. 写入 plans 表
    3. 批量写入 tasks 表
    4. 返回结构化响应

    Args:
        goal: 学习目标
        duration_weeks: 计划周数（默认 8 周）
        user_id: 用户 ID（可选）

    Returns:
        PlanResponse dict
    """
    # Step 1: LLM 生成计划
    plan_data = _llm_generate_plan(goal, duration_weeks)

    # Step 2: 持久化到 DB
    db = SessionLocal()
    try:
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # 创建 Plan 记录
        plan = Plan(
            id=plan_id,
            user_id=user_id,
            title=plan_data["title"],
            goal=goal,
            status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(plan)
        db.flush()  # 获取 ID

        # 创建 Task 记录（批量）
        task_global_order = 0
        for week_data in plan_data["weeks"]:
            week_num = week_data.get("week", 1)
            for task_data in week_data.get("tasks", []):
                task_global_order += 1
                task = Task(
                    plan_id=plan_id,
                    order=task_global_order,
                    agent_type=task_data.get("agent_type", "code"),
                    description=f"Week{week_num}: {task_data['description']}",
                    status="pending",
                    created_at=now,
                    updated_at=now,
                )
                db.add(task)

        db.commit()

        # Step 3: 构造响应
        weeks = []
        for w in plan_data["weeks"]:
            weeks.append({
                "week": w["week"],
                "topic": w["topic"],
                "description": w.get("description", ""),
                "tasks": [
                    {
                        "order": t.get("order", i + 1),
                        "description": t["description"],
                        "agent_type": t.get("agent_type", "code"),
                    }
                    for i, t in enumerate(w.get("tasks", []))
                ],
            })

        return {
            "id": plan_id,
            "title": plan_data["title"],
            "goal": goal,
            "duration_weeks": duration_weeks,
            "weeks": weeks,
            "created_at": now.isoformat(),
        }

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_plans(user_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    """获取学习计划列表"""
    db = SessionLocal()
    try:
        query = db.query(Plan)
        if user_id:
            query = query.filter(Plan.user_id == user_id)
        plans = query.order_by(Plan.created_at.desc()).limit(limit).all()

        results = []
        for p in plans:
            task_count = db.query(Task).filter(Task.plan_id == p.id).count()
            results.append({
                "id": p.id,
                "title": p.title,
                "goal": p.goal,
                "status": p.status,
                "task_count": task_count,
                "created_at": p.created_at.isoformat(),
            })
        return results
    finally:
        db.close()


def get_plan(plan_id: str) -> Optional[dict]:
    """获取单个计划详情（含所有 task）"""
    db = SessionLocal()
    try:
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            return None

        tasks = (
            db.query(Task)
            .filter(Task.plan_id == plan_id)
            .order_by(Task.order)
            .all()
        )

        # 按周分组
        weeks_map = {}
        for t in tasks:
            # 从描述中提取 Week 编号
            week_num = 1
            desc = t.description
            if desc.startswith("Week"):
                try:
                    week_num = int(desc.split(":")[0].replace("Week", ""))
                except (ValueError, IndexError):
                    pass

            if week_num not in weeks_map:
                weeks_map[week_num] = {
                    "week": week_num,
                    "topic": f"第 {week_num} 周",
                    "description": "",
                    "tasks": [],
                }
            weeks_map[week_num]["tasks"].append({
                "order": t.order,
                "description": desc,
                "agent_type": t.agent_type,
                "status": t.status,
            })

        return {
            "id": plan.id,
            "title": plan.title,
            "goal": plan.goal,
            "status": plan.status,
            "duration_weeks": len(weeks_map),
            "weeks": sorted(weeks_map.values(), key=lambda w: w["week"]),
            "created_at": plan.created_at.isoformat(),
        }
    finally:
        db.close()


def update_task_status(task_id: str, status: str) -> bool:
    """更新任务状态

    Args:
        task_id: 任务 ID
        status: pending / in_progress / completed / failed

    Returns:
        True 成功，False 任务不存在
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
