# -*- coding: utf-8 -*-
"""?? API

API ???
  GET    /api/v1/tasks             ????????? + ??????
  GET    /api/v1/tasks/{id}        ??????
  PATCH  /api/v1/tasks/{id}        ??????
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.models import User
from app.services import planner_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


class TaskItem(BaseModel):
    id: str
    plan_id: str
    order: int
    description: str
    agent_type: str
    status: str
    result: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TaskDetailResponse(BaseModel):
    id: str
    plan_id: str
    plan_title: str = ""
    order: int
    description: str
    agent_type: str
    status: str
    result: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaginatedTaskResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[TaskItem]

    model_config = {"from_attributes": True}


class UpdateTaskRequest(BaseModel):
    status: str = Field(..., description="???", pattern="^(pending|in_progress|completed|failed)$")

    model_config = {"json_schema_extra": {"example": {"status": "in_progress"}}}


@router.get("", response_model=PaginatedTaskResponse,
            summary="??????", description="?? + ? plan/status/agent_type ??")
def list_tasks(
    current_user: User = Depends(get_current_user),
    plan_id: Optional[str] = Query(None, description="?????"),
    status: Optional[str] = Query(None, description="?????"),
    agent_type: Optional[str] = Query(None, description="? Agent ????"),
    offset: int = Query(0, ge=0, description="????"),
    limit: int = Query(20, ge=1, le=200, description="????"),
):
    """??????"""
    return planner_service.list_tasks(
        user_id=current_user.id,
        plan_id=plan_id, status=status, agent_type=agent_type,
        offset=offset, limit=limit,
    )


@router.get("/{task_id}", response_model=TaskDetailResponse,
            summary="??????", description="???????")
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """??????"""
    task = planner_service.get_task(task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="?????")
    return task


@router.patch("/{task_id}", response_model=dict,
              summary="??????", description="pending/in_progress/completed/failed")
def update_task_status(
    task_id: str,
    request: UpdateTaskRequest,
    current_user: User = Depends(get_current_user),
):
    """??????"""
    ok = planner_service.update_task_status(task_id, request.status, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="?????")
    return {"message": "updated", "task_id": task_id, "status": request.status}
