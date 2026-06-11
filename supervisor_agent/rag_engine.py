# -*- coding: utf-8 -*-
"""rag_engine.py - RAG 核心引擎"""

import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


INDEX_DIR = "rag_index"
CHUNKS_FILE = os.path.join(INDEX_DIR, "chunks.json")
FAISS_INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")


class RAGEngine:
    """RAG 引擎：PDF 读取 → 切块 → Embed → FAISS 索引 → 检索"""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print("Loading embedding model...")
        self.embedder = SentenceTransformer(model_name)
        os.makedirs(INDEX_DIR, exist_ok=True)
        self.index = None
        self.chunks = []
        self._load_existing()

    def _load_existing(self):
        """加载已有的索引和文本块"""
        if os.path.exists(FAISS_INDEX_FILE) and os.path.exists(CHUNKS_FILE):
            self.index = faiss.read_index(FAISS_INDEX_FILE)
            with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            print(f"Loaded existing index: {len(self.chunks)} chunks")

    def ingest_pdf(self, file_path: str) -> str:
        """读取 PDF → 切块 → Embed → 建索引"""
        import fitz  # PyMuPDF

        if not os.path.exists(file_path):
            return f"Error: file not found: {file_path}"

        # 1. 读取 PDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()

        if not text.strip():
            doc.close()
            return "Error: no text found in PDF"

        # 2. 切块：按段落切，每块约 500 字
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < 500:
                current += "\n\n" + p if current else p
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)

        # 3. Embedding
        embeddings = self.embedder.encode(chunks, show_progress_bar=False)

        # 4. 存入 FAISS
        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings.astype(np.float32))
        self.chunks.extend(chunks)

        page_count = len(doc)
        doc.close()

        # 5. 保存到磁盘
        faiss.write_index(self.index, FAISS_INDEX_FILE)
        with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        return f"Indexed {len(chunks)} chunks from {page_count} pages"

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """检索最相关的文本块"""
        if self.index is None or not self.chunks:
            return ["No documents indexed yet. Use ingest_pdf first."]

        # 1. Embed 问题
        q_vec = self.embedder.encode([query])

        # 2. FAISS 搜索
        distances, indices = self.index.search(q_vec.astype(np.float32), min(top_k, len(self.chunks)))

        # 3. 返回文本块
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append(f"[Chunk {i+1}] {self.chunks[idx][:300]}")
        return results if results else ["No relevant content found."]