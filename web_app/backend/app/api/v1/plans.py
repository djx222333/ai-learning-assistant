# -*- coding: utf-8 -*-
"""???? API?Repository + Service ???

API ???
  POST   /api/v1/plans/generate    ??????
  GET    /api/v1/plans              ????????? + ???
  GET    /api/v1/plans/{id}         ???????? task ?? + ????
  GET    /api/v1/plans/{id}/stats   ??????
  DELETE /api/v1/plans/{id}         ????
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.models import User
from app.services import planner_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/plans", tags=["plans"])


class GeneratePlanRequest(BaseModel):
    goal: str = Field(..., description="????", min_length=2, max_length=500,
                      examples=["?8???? FastAPI"])
    duration_weeks: int = Field(8, description="????", ge=1, le=52)

    model_config = {"json_schema_extra": {"example": {"goal": "8???? FastAPI", "duration_weeks": 8}}}


class WeeklyTaskItem(BaseModel):
    order: int = Field(..., description="????")
    description: str = Field(..., description="????")
    agent_type: str = Field(..., description="?? Agent")

    model_config = {"from_attributes": True}


class WeeklyPlanItem(BaseModel):
    week: int = Field(..., description="???")
    topic: str = Field(..., description="????")
    description: str = Field(..., description="????")
    tasks: list[WeeklyTaskItem] = Field(default_factory=list)


class GeneratePlanResponse(BaseModel):
    id: str = Field(..., description="?? ID")
    title: str = Field(..., description="????")
    goal: str = Field(..., description="????")
    duration_weeks: int = Field(..., description="????")
    weeks: list[WeeklyPlanItem] = Field(default_factory=list, description="????")
    created_at: str = Field(..., description="????")

    model_config = {"from_attributes": True}


class TaskDetail(BaseModel):
    id: str
    order: int
    description: str
    agent_type: str
    status: str
    result: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PlanDetailResponse(BaseModel):
    id: str = Field(..., description="?? ID")
    title: str = Field(..., description="????")
    goal: str = Field(..., description="????")
    status: str = Field(..., description="????")
    task_count: int = Field(..., description="????")
    completed_count: int = Field(..., description="????")
    completion_rate: float = Field(..., description="??? %")
    tasks: list[TaskDetail] = Field(default_factory=list, description="????")
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PlanListItem(BaseModel):
    id: str
    title: str
    goal: str
    status: str
    task_count: int
    completed_count: int
    created_at: str

    model_config = {"from_attributes": True}


class PaginatedPlanResponse(BaseModel):
    total: int = Field(..., description="????")
    offset: int = Field(..., description="????")
    limit: int = Field(..., description="????")
    items: list[PlanListItem] = Field(default_factory=list, description="????")

    model_config = {"from_attributes": True}


class PlanStatsResponse(BaseModel):
    plan_id: str
    title: str
    total: int
    pending: int
    in_progress: int
    completed: int
    failed: int
    completion_rate: float


@router.post("/generate", response_model=GeneratePlanResponse,
             summary="??????", description="LLM ???????????????")
def generate_plan(
    request: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
):
    """??????

    - LLM ?????????
    - ???????????
    - ???? PostgreSQL (plans + tasks ?)
    """
    try:
        return planner_service.generate_plan(
            goal=request.goal,
            duration_weeks=request.duration_weeks,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"LLM ????: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"??????: {e}")


@router.get("", response_model=PaginatedPlanResponse,
            summary="??????", description="?? + ?????")
def list_plans(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="????"),
    offset: int = Query(0, ge=0, description="????"),
    limit: int = Query(20, ge=1, le=100, description="????"),
):
    """??????????? + ???"""
    return planner_service.list_plans(
        user_id=current_user.id,status=status, offset=offset, limit=limit)


@router.get("/{plan_id}", response_model=PlanDetailResponse,
            summary="??????", description="????? + ???")
def get_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
):
    """??????"""
    plan = planner_service.get_plan(plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="?????")
    return plan


@router.get("/{plan_id}/stats", response_model=PlanStatsResponse,
            summary="??????", description="???????????")
def get_plan_stats(
    plan_id: str,
    current_user: User = Depends(get_current_user),
):
    """??????"""
    stats = planner_service.get_plan_stats(plan_id, user_id=current_user.id)
    if not stats:
        raise HTTPException(status_code=404, detail="?????")
    return stats


@router.delete("/{plan_id}", summary="????", description="???????????")
def delete_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
):
    """??????????? task?"""
    ok = planner_service.delete_plan(plan_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="?????")
    return {"message": "deleted", "id": plan_id}
