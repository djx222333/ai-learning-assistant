# -*- coding: utf-8 -*-
"""聊天 API 路由"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.models import User
from app.services import chat_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/chat", tags=["chat"])

class CitationItem(BaseModel):
    document_name: str = Field("", description="来源文档名称")
    chunk_id: int = Field(0, description="文本块编号")
    chunk_text: str = Field("", description="文本块内容")
    relevance_score: float = Field(0.0, description="相关度")

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    session_id: str = Field(None, description="会话 ID")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    agent_type: str = Field("", description="Agent 类型")
    agent_name: str = Field("Assistant", description="Agent 显示名称")
    citations: list[CitationItem] = Field([], description="引用来源")

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    result = chat_service.send_message(
        message=request.message,
        session_id=request.session_id,
        user_id=current_user.id,
        username=current_user.username,
    )
    return ChatResponse(
        answer=result["answer"],
        agent_type=result["agent_type"],
        agent_name=result["agent_name"],
        citations=[CitationItem(**c) for c in result.get("citations", [])],
    )