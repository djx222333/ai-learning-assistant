# -*- coding: utf-8 -*-
"""知识库服务：文件上传 + 索引管理（数据库版）

职责：
1. 文件存储管理（uploads/ 目录）
2. 文档记录持久化（documents 表）
3. Chunk 元数据管理（chunks 表）
4. 委托 rag_service 处理 FAISS 索引/检索

数据库 vs JSON：
  JSON  →  SQLAlchemy
  documents.json → documents 表
  chunk_metadata.json → chunks 表
"""
import os
import uuid
from datetime import datetime, timezone
from . import rag_service as rs
from app.database import SessionLocal
from app.models import Document, Chunk


# ---- 配置 ----
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.abspath(os.path.join(ADAPTER_DIR, "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _utcnow():
    return datetime.now(timezone.utc)


def get_files(user_id: str = None) -> list[dict]:
    """返回当前用户的文档列表（按上传时间倒序）"""
    db = SessionLocal()
    try:
        query = db.query(Document)
        if user_id:
            query = query.filter(Document.user_id == user_id)
        docs = query.order_by(Document.created_at.desc()).all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "file_path": d.file_path,
                "file_size": d.file_size,
                "index_status": d.index_status,
                "chunk_count": d.chunk_count,
                "page_count": d.page_count,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]
    finally:
        db.close()


def upload_file(file_path: str, filename: str, user_id: str = None) -> dict:
    """上传：保存记录 -> 建索引 -> 更新 chunk

    Args:
        file_path: 已保存的文件路径
        filename: 原始文件名
        user_id: 当前用户 ID（自动绑定文档归属）

    Returns:
        文档记录 dict
    """
    db = SessionLocal()
    try:
        doc_id = str(uuid.uuid4())

        # 1. 创建文档记录（自动绑定 user_id）
        doc = Document(
            id=doc_id,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            index_status="processing",
        )
        db.add(doc)
        db.commit()

        # 2. 调用 rag_service 建索引
        svc = rs.get_rag_service()
        result = svc.ingest_pdf(file_path, filename, doc_id=doc_id)

        # 3. 更新文档记录
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if result["status"] == "ok":
            doc.chunk_count = result["chunk_count"]
            doc.page_count = result["page_count"]
            doc.index_status = "ready"

            # 4. 同步 chunk 元数据到数据库
            if doc.chunk_count > 0:
                _sync_chunks_to_db(db, doc_id)
        else:
            doc.index_status = "failed"
            doc.error = result.get("message", "Unknown error")

        db.commit()
        db.refresh(doc)
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_size": doc.file_size,
            "index_status": doc.index_status,
            "chunk_count": doc.chunk_count,
            "page_count": doc.page_count,
            "created_at": doc.created_at.isoformat(),
        }
    except Exception as e:
        db.rollback()
        doc = db.query(Document).filter(Document.id == doc_id).first() if "doc_id" in dir() else None
        if doc:
            doc.index_status = "failed"
            doc.error = str(e)
            db.commit()
        raise
    finally:
        db.close()


def _sync_chunks_to_db(db, doc_id: str):
    """将 rag_service 的 chunk 元数据同步到 chunks 表"""
    svc = rs.get_rag_service()
    import json
    meta_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chunk_metadata.json")
    if not os.path.exists(meta_path):
        return
    with open(meta_path, "r", encoding="utf-8") as f:
        all_meta = json.load(f)
    doc_chunks = [m for m in all_meta if m.get("doc_id") == doc_id]
    if not doc_chunks:
        return
    for m in doc_chunks:
        chunk = Chunk(
            document_id=doc_id,
            chunk_index=m.get("chunk_index", 0),
            content=m.get("text", ""),
            embedding_idx=m.get("chunk_index"),
        )
        db.add(chunk)
    db.commit()


def delete_file(doc_id: str, user_id: str = None) -> bool:
    """删除：校验所有权 -> 移除记录 -> 删除文件 -> 重建索引

    Args:
        doc_id: 文档记录的 UUID
        user_id: 当前用户 ID（校验文档归属）

    Returns:
        True 删除成功，False 未找到或无权限
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return False

        # 所有权校验：只能删除自己的文档
        if user_id and doc.user_id and doc.user_id != user_id:
            return False

        # 删除物理文件
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # 删除数据库记录（cascade 自动删除 chunks）
        db.delete(doc)
        db.commit()

        # 从 FAISS 删除对应向量
        svc = rs.get_rag_service()
        svc.delete_document(doc_id)

        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def search(query: str, top_k: int = 3, user_id: str = None) -> list[dict]:
    """检索知识库，返回结构化 citation 列表

    TODO (P2): 添加 FAISS multi-tenant filtering
    当前 FAISS 索引是全局的，所有用户共享。
    P2 阶段改为：每个用户独立 FAISS 索引，或在 chunk_metadata 中增加 user_id 过滤。

    Args:
        query: 检索关键词
        top_k: 返回条数
        user_id: 保留参数，暂未启用过滤
    """
    svc = rs.get_rag_service()
    results = svc.search(query, top_k=top_k)

    citations = []
    for r in results:
        citations.append({
            "document_name": r["document_name"],
            "chunk_id": r["chunk_id"],
            "chunk_text": r["chunk_text"],
            "relevance_score": r["relevance_score"],
        })

    return citations