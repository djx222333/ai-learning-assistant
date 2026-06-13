# -*- coding: utf-8 -*-
"""Chat API Router"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.models import User
from app.services import chat_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/chat", tags=["chat"])

class CitationItem(BaseModel):
    document_name: str = Field("", description="Source document name")
    chunk_id: int = Field(0, description="Chunk number")
    chunk_text: str = Field("", description="Chunk content text")
    relevance_score: float = Field(0.0, description="Relevance score 0-1")

class ChatRequest(BaseModel):
    conversation_id: str = Field(None, description="会话 UUID（用于知识库隔离）")
    message: str = Field(..., description="User message", min_length=1, max_length=10000)
    session_id: str = Field(None, description="Session ID")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI answer")
    source: str = Field("llm", description="Answer source: rag=RAG, llm=direct LLM")
    agent_type: str = Field("", description="Agent type")
    agent_name: str = Field("Assistant", description="Agent display name")
    citations: list[CitationItem] = Field([], description="Citation sources")

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
        source=result.get("source", "llm"),
        agent_type=result["agent_type"],
        agent_name=result["agent_name"],
        citations=[CitationItem(**c) for c in result.get("citations", [])],
    )
