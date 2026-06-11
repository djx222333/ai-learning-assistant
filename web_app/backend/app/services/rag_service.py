import sys
import os
import json
import numpy as np
import faiss

# ---- 复用 supervisor_agent 的导入路径 ----
ADAPTER_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERVISOR_DIR = os.path.abspath(os.path.join(ADAPTER_DIR, "..", "..", "..", "..", "supervisor_agent"))
if SUPERVISOR_DIR not in sys.path:
    sys.path.insert(0, SUPERVISOR_DIR)


# ---- 配置 ----
DATA_DIR = os.path.abspath(os.path.join(ADAPTER_DIR, "..", "..", "data"))
CHUNK_METADATA_FILE = os.path.join(DATA_DIR, "chunk_metadata.json")
os.makedirs(DATA_DIR, exist_ok=True)

# supervisor_agent/rag_index/ 是 RAGEngine 使用的索引目录
RAG_INDEX_DIR = os.path.abspath(os.path.join(SUPERVISOR_DIR, "rag_index"))
FAISS_INDEX_FILE = os.path.join(RAG_INDEX_DIR, "index.faiss")
CHUNKS_FILE = os.path.join(RAG_INDEX_DIR, "chunks.json")


class RAGService:
    """文档感知的 RAG 服务

    解决三个核心问题：
    1. Chunk 不知道属于哪个文档 → 维护 chunk_metadata
    2. Citation 用假数据 → 从 FAISS 拿真实距离分数
    3. 无法按文档删除 → 支持按 doc_id 删除 chunk

    数据流：
      chunk_metadata.json: [{text, document_name, doc_id (UUID), chunk_index}]
                                     │
      FAISS index / chunks.json --------- 按索引位置对应
                                     │
      search() → 映射到 metadata → 返回 {document_name, chunk_id, score}
    """

    def __init__(self):
        # 必须在 supervisor_agent 目录下创建 RAGEngine
        # 因为 RAGEngine 使用相对路径 "rag_index/"
        _original_cwd = os.getcwd()
        os.chdir(SUPERVISOR_DIR)
        try:
            from rag_engine import RAGEngine
            self._engine = RAGEngine()
        finally:
            os.chdir(_original_cwd)

        self._metadata = []
        self._load_metadata()

    def _load_metadata(self):
        """加载 chunk 元数据，与 engine.chunks 对齐"""
        if os.path.exists(CHUNK_METADATA_FILE):
            with open(CHUNK_METADATA_FILE, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)

        # 兼容旧数据：有 chunks 但无 metadata
        if not self._metadata and self._engine.chunks:
            print("Migrating: generating metadata from existing chunks...")
            self._metadata = [
                {
                    "text": chunk,
                    "document_name": "unknown.pdf",
                    "doc_id": "legacy",
                    "chunk_index": i,
                }
                for i, chunk in enumerate(self._engine.chunks)
            ]
            self._save_metadata()

        # 校验长度
        if self._metadata and self._engine.chunks and len(self._metadata) != len(self._engine.chunks):
            print(f"Fixing: metadata({len(self._metadata)}) != chunks({len(self._engine.chunks)})")
            # 以 chunks 为准重建
            self._metadata = [
                {
                    "text": chunk,
                    "document_name": self._metadata[i].get("document_name", "unknown.pdf") if i < len(self._metadata) else "unknown.pdf",
                    "doc_id": self._metadata[i].get("doc_id", "legacy") if i < len(self._metadata) else "legacy",
                    "chunk_index": i,
                }
                for i, chunk in enumerate(self._engine.chunks)
            ]
            self._save_metadata()

    def _save_metadata(self):
        with open(CHUNK_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    # ---------- Public API ----------

    def ingest_pdf(self, file_path: str, filename: str, doc_id: str = "") -> dict:
        """PDF → 切块 → Embed → 建索引 → 记录元数据

        Args:
            file_path: PDF 文件绝对路径
            filename: 原始文件名（用于 citation 展示）
            doc_id: 文档 UUID（用于 delete 时匹配）

        Returns:
        TODO (P2): Add FAISS multi-tenant filtering - filter by user_id
            {"status": "ok/error", "chunk_count": N, "page_count": N}
        """
        old_count = len(self._engine.chunks)

        # RAGEngine.ingest_pdf 需要 CWD = supervisor_agent 目录
        _original_cwd = os.getcwd()
        os.chdir(SUPERVISOR_DIR)
        try:
            result_str = self._engine.ingest_pdf(file_path)
        finally:
            os.chdir(_original_cwd)

        new_count = len(self._engine.chunks)
        added_count = new_count - old_count

        if added_count <= 0:
            return {"status": "error", "chunk_count": 0, "page_count": 0, "message": result_str}

        # 为新 chunk 创建元数据（使用 UUID 作为 doc_id）
        for i in range(old_count, new_count):
            self._metadata.append({
                "text": self._engine.chunks[i],
                "document_name": filename,
                "doc_id": doc_id,  # UUID，用于 delete 匹配
                "chunk_index": i,
            })

        self._save_metadata()

        page_count = 0
        parts = result_str.split()
        if len(parts) > 4 and parts[4].isdigit():
            page_count = int(parts[4])

        return {"status": "ok", "chunk_count": added_count, "page_count": page_count}

    def search(self, query: str, top_k: int = 3, user_id: str = None) -> list[dict]:
        """检索，返回结构化结果

        分数归一化: score = 1 / (1 + l2_distance)
        L2 越小 -> score 越接近 1
        """
        if self._engine.index is None or not self._engine.chunks or not self._metadata:
            return []

        # 1. Embed 问题
        q_vec = self._engine.embedder.encode([query])

        # 2. FAISS 搜索
        k = min(top_k, len(self._engine.chunks))
        distances, indices = self._engine.index.search(q_vec.astype(np.float32), k)

        # 3. 映射到元数据
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue

            meta = self._metadata[idx]
            l2_distance = float(distances[0][i])
            score = round(1.0 / (1.0 + l2_distance), 4)

            results.append({
                "document_name": meta["document_name"],
                "doc_id": meta.get("doc_id", ""),
                "chunk_id": int(idx),
                "chunk_text": meta["text"][:500],
                "relevance_score": score,
                "l2_distance": round(l2_distance, 4),
            })

        results.sort(key=lambda r: r["relevance_score"], reverse=True)
        return results

    def delete_document(self, doc_id: str) -> bool:
        """删除指定文档的所有 chunk，重建索引

        Args:
            doc_id: 文档 UUID（与 documents.json 中的 id 一致）

        Returns:
        TODO (P2): Add FAISS multi-tenant filtering - filter by user_id
            True 删除成功，False 未找到
        """
        if not self._metadata:
            return False

        # 用 UUID 匹配
        to_delete = [i for i, m in enumerate(self._metadata) if m.get("doc_id") == doc_id]

        if not to_delete:
            return False

        # 分离要保留的
        remaining_chunks = []
        remaining_metadata = []
        for i, (chunk, meta) in enumerate(zip(self._engine.chunks, self._metadata)):
            if i in to_delete:
                continue
            remaining_chunks.append(chunk)
            remaining_metadata.append(meta)

        if not remaining_chunks:
            # 全部删除 → 清空
            self._engine.index = None
            self._engine.chunks = []
            self._metadata = []
            self._save_empty()
            return True

        # 重建 FAISS 索引
        print(f"Rebuilding index: {len(remaining_chunks)} chunks...")
        embeddings = self._engine.embedder.encode(remaining_chunks, show_progress_bar=False)
        dim = embeddings.shape[1]
        new_index = faiss.IndexFlatL2(dim)
        new_index.add(embeddings.astype(np.float32))

        # 保存（CWD 必须是 supervisor_agent）
        _original_cwd = os.getcwd()
        os.chdir(SUPERVISOR_DIR)
        try:
            os.makedirs(RAG_INDEX_DIR, exist_ok=True)
            faiss.write_index(new_index, FAISS_INDEX_FILE)
            self._engine.index = new_index
            self._engine.chunks = remaining_chunks
            with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
                json.dump(remaining_chunks, f, ensure_ascii=False, indent=2)
        finally:
            os.chdir(_original_cwd)

        # 更新 chunk_index
        for i, m in enumerate(remaining_metadata):
            m["chunk_index"] = i

        self._metadata = remaining_metadata
        self._save_metadata()
        return True

    def _save_empty(self):
        """清空所有索引文件"""
        _original_cwd = os.getcwd()
        os.chdir(SUPERVISOR_DIR)
        try:
            for p in [FAISS_INDEX_FILE, CHUNKS_FILE]:
                if os.path.exists(p):
                    os.remove(p)
        finally:
            os.chdir(_original_cwd)
        with open(CHUNK_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    def get_stats(self) -> dict:
        return {
            "total_chunks": len(self._engine.chunks) if self._engine.chunks else 0,
            "total_documents": len(set(m.get("doc_id", "") for m in self._metadata if m.get("doc_id"))) if self._metadata else 0,
            "index_loaded": self._engine.index is not None,
        }


# ---- 全局单例 ----
_service = None


def get_rag_service() -> "RAGService":
    global _service
    if _service is None:
        _service = RAGService()
    return _service
