# -*- coding: utf-8 -*-
"""知识库 API 路由"""
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from app.models import User
from app.services import knowledge_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))


class FileItem(BaseModel):
    """文件项"""
    id: str
    filename: str
    file_size: int
    index_status: str
    chunk_count: int
    page_count: int
    created_at: str


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    conversation_id: str = Query(None, description="绑定到指定会话"),
):
    """上传 PDF 文件并自动建索引（自动绑定当前用户）"""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    record = knowledge_service.upload_file(
        file_path=file_path,
        filename=file.filename,
        user_id=current_user.id,
        conversation_id=conversation_id,
    )

    return FileItem(
        id=record["id"],
        filename=record["filename"],
        file_size=record["file_size"],
        index_status=record["index_status"],
        chunk_count=record["chunk_count"],
        page_count=record["page_count"],
        created_at=record["created_at"],
    )


@router.get("/files", response_model=list[FileItem])
def list_files(
    current_user: User = Depends(get_current_user),
    conversation_id: str = Query(None, description="按会话过滤"),
):
    """获取当前用户已上传的文件列表"""
    records = knowledge_service.get_files(user_id=current_user.id, conversation_id=conversation_id)
    return [
        FileItem(
            id=r["id"],
            filename=r["filename"],
            file_size=r["file_size"],
            index_status=r["index_status"],
            chunk_count=r["chunk_count"],
            page_count=r["page_count"],
            created_at=r["created_at"],
        )
        for r in records
    ]


@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """删除文件（只能删除自己的文件）"""
    ok = knowledge_service.delete_file(
        doc_id=file_id,
        user_id=current_user.id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"message": "deleted", "id": file_id}
