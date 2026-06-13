# -*- coding: utf-8 -*-
"""对话历史 API 路由

API 清单：
  GET    /api/v1/conversations           — 获取当前用户的会话列表
  GET    /api/v1/conversations/{id}      — 获取会话详情
  GET    /api/v1/conversations/{id}/messages — 获取会话消息
  DELETE /api/v1/conversations/{id}      — 删除会话

设计原则：
1. 所有接口通过 Depends(get_current_user) 保护
2. 用户隔离：只返回 current_user 的数据
3. 权限不足统一返回 404（不暴露数据存在性）
4. 删除依赖 cascade 级联（不手动删除 messages）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.models import User
from app.services import conversation_service as cs
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


# ============================================================
# Pydantic 数据模型
# ============================================================

class ConversationSummary(BaseModel):
    """会话摘要（列表用）"""
    id: str = Field(..., description="会话 UUID")
    session_id: str = Field(..., description="外部会话标识")
    title: str = Field("新对话", description="会话标题")
    message_count: int = Field(0, description="消息总数")
    last_message: str = Field("", description="最新消息摘要（前 100 字）")
    doc_count: int = Field(0, description="关联文档数")
    created_at: str = Field("", description="创建时间")
    updated_at: str = Field("", description="最后更新时间")

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    """会话详情"""
    id: str = Field(..., description="会话 UUID")
    session_id: str = Field(..., description="外部会话标识")
    title: str = Field("新对话", description="会话标题")
    message_count: int = Field(0, description="消息总数")
    created_at: str = Field("", description="创建时间")
    updated_at: str = Field("", description="最后更新时间")

    model_config = {"from_attributes": True}


class MessageItem(BaseModel):
    """消息项"""
    id: str = Field(..., description="消息 UUID")
    role: str = Field(..., description="user / assistant")
    content: str = Field(..., description="消息内容")
    agent_type: Optional[str] = Field(None, description="Agent 类型")
    agent_name: Optional[str] = Field(None, description="Agent 名称")
    citations: Optional[list] = Field(None, description="引用来源")
    created_at: str = Field("", description="发送时间")

    model_config = {"from_attributes": True}


class PaginatedConversations(BaseModel):
    """分页会话列表"""
    total: int = Field(0, description="总数")
    offset: int = Field(0, description="偏移")
    limit: int = Field(20, description="每页条数")
    items: list[ConversationSummary] = Field(default_factory=list, description="会话列表")


class PaginatedMessages(BaseModel):
    """分页消息列表"""
    total: int = Field(0, description="总数")
    offset: int = Field(0, description="偏移")
    limit: int = Field(50, description="每页条数")
    items: list[MessageItem] = Field(default_factory=list, description="消息列表")


class DeleteResponse(BaseModel):
    """删除响应"""
    message: str = Field("deleted", description="操作结果")
    id: str = Field(..., description="被删除的会话 UUID")


# ============================================================
# 获取会话列表
# ============================================================

@router.get(
    "",
    response_model=PaginatedConversations,
    summary="获取会话列表",
    description="返回当前用户的所有对话会话，按最后更新时间倒序排列",
)
def list_conversations(
    current_user: User = Depends(get_current_user),
    offset: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取当前用户的会话列表"""
    return cs.list_conversations(
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )


# ============================================================
# 获取会话详情
# ============================================================

@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="获取会话详情",
    description="返回指定会话的详细信息",
    responses={
        200: {"description": "成功返回会话详情"},
        404: {"description": "会话不存在或无权限访问"},
    },
)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取会话详情"""
    result = cs.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return result


# ============================================================
# 获取会话消息
# ============================================================

@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedMessages,
    summary="获取会话消息",
    description="返回指定会话的消息列表，按发送时间正序排列",
    responses={
        200: {"description": "成功返回消息列表"},
        404: {"description": "会话不存在或无权限访问"},
    },
)
def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    offset: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(50, ge=1, le=200, description="每页条数"),
):
    """获取会话的消息列表"""
    result = cs.get_conversation_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return result


# ============================================================
# 删除会话
# ============================================================

@router.delete(
    "/{conversation_id}",
    response_model=DeleteResponse,
    summary="删除会话",
    description="删除指定的对话会话及其所有消息（级联删除）",
    responses={
        200: {"description": "删除成功"},
        404: {"description": "会话不存在或无权限访问"},
    },
)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """删除会话（cascade 自动删除关联消息）"""
    ok = cs.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "deleted", "id": conversation_id}

class RenameRequest(BaseModel):
    """重命名请求"""
    title: str = Field(..., min_length=1, max_length=256, description="新标题")


@router.patch(
    "/{conversation_id}",
    summary="重命名会话",
    description="修改会话标题",
    responses={
        200: {"description": "重命名成功"},
        404: {"description": "会话不存在或无权限"},
    },
)
def rename_conversation(
    conversation_id: str,
    body: RenameRequest,
    current_user: User = Depends(get_current_user),
):
    """重命名会话"""
    ok = cs.update_title(
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=body.title,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "renamed", "id": conversation_id}
