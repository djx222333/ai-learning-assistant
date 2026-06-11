# -*- coding: utf-8 -*-
"""报告 API

API 清单:
  GET /api/v1/reports/overview    学习总览统计
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.models import User
from app.services import report_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/reports", tags=["reports"])


class OverviewResponse(BaseModel):
    """学习总览响应"""
    plans: int = Field(0, description="学习计划总数")
    tasks: int = Field(0, description="总任务数")
    completed_tasks: int = Field(0, description="已完成任务数")
    completion_rate: float = Field(0.0, description="完成率%")
    documents: int = Field(0, description="已上传文档数")
    conversations: int = Field(0, description="对话会话数")
    messages: int = Field(0, description="消息总数")
    agent_distribution: dict = Field(default_factory=dict, description="Agent 使用分布")
    plans_by_status: dict = Field(default_factory=dict, description="计划状态分布")

    model_config = {
        "json_schema_extra": {
            "example": {
                "plans": 3,
                "tasks": 28,
                "completed_tasks": 20,
                "completion_rate": 71.4,
                "documents": 12,
                "conversations": 56,
                "messages": 420,
                "agent_distribution": {"Code Agent": 20, "Search Agent": 15},
                "plans_by_status": {"active": 2, "completed": 1},
            }
        }
    }


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    current_user: User = Depends(get_current_user),
):
    """获取学习总览统计"""
    return report_service.get_overview(user_id=current_user.id)
