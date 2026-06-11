# AI Learning Assistant — 架构文档

> 系统架构图、数据流、状态流、Memory 流

---

## 1. 整体架构图

```mermaid
graph TB
    subgraph Frontend["Frontend (React + Vite :5173)"]
        CHAT["/chat 聊天页"]
        KNOW["/knowledge 知识库页"]
    end

    subgraph Backend["Backend (FastAPI :8000)"]
        API["API 路由层<br/>chat.py / knowledge.py"]
        CS["chat_service.py<br/>对话服务 + RAG 注入"]
        KS["knowledge_service.py<br/>文档管理 + 检索入口"]
        RS["rag_service.py<br/>FAISS 检索 + 元数据管理"]
        AA["agent_adapter.py<br/>桥接层"]
    end

    subgraph Agent["supervisor_agent/ (LangGraph)"]
        SV["Supervisor<br/>问题分类路由"]
        CA["Code Agent<br/>Python 编程"]
        EA["English Agent<br/>英语学习"]
        CR["Career Agent<br/>学习规划"]
        SA["Search Agent<br/>联网搜索"]
        RA["Research Agent<br/>多源研究"]
        RAG["RAG Agent<br/>文档问答"]
        PL["Planner<br/>任务拆解"]
        MEM["MemorySaver<br/>会话记忆"]
        LTM["user_profile.json<br/>长期记忆"]
    end

    subgraph Storage["数据存储"]
        FAISS[("FAISS 向量索引<br/>rag_index/")]
        META[("chunk_metadata.json<br/>块级元数据")]
        DOCS[("documents.json<br/>文档记录")]
        UPLOADS[("uploads/<br/>PDF 文件")]
    end

    %% 前端 → 后端
    CHAT -->|POST /api/v1/chat| API
    KNOW -->|POST/GET/DELETE /api/v1/knowledge| API

    %% 后端内部
    API --> CS
    API --> KS
    CS --> KS
    CS --> AA
    KS --> RS
    RS --> FAISS
    RS --> META
    KS --> DOCS
    KS --> UPLOADS

    %% 后端 → Agent
    AA -->|graph.invoke()| SV
    SV --> CA
    SV --> EA
    SV --> CR
    SV --> SA
    SV --> RA
    SV --> RAG
    SV --> PL
    CA --> MEM
    EA --> MEM
    CR --> MEM
    SA --> MEM
    RA --> MEM
    RAG --> MEM
    PL --> MEM
    CA --> LTM
    EA --> LTM
    CR --> LTM
    SA --> LTM
    RA --> LTM
    RAG --> LTM
    PL --> LTM
```

---

## 2. RAG 数据流

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as React 前端
    participant API as FastAPI
    participant CS as chat_service
    participant KS as knowledge_service
    participant RS as rag_service
    participant FAISS as FAISS Index
    participant AA as agent_adapter
    participant Agent as Supervisor Agent

    Note over User,Agent: === 上传 PDF 阶段 ===
    User->>Frontend: 上传 Python基础.pdf
    Frontend->>API: POST /api/v1/knowledge/upload
    API->>KS: upload_file()
    KS->>RS: ingest_pdf(file_path, filename)
    RS->>RS: 读取 PDF → 切块
    RS->>RS: SentenceTransformer Embedding
    RS->>FAISS: 存入索引
    RS->>RS: 记录 chunk_metadata
    RS-->>KS: {status:"ok", chunk_count:45}
    KS-->>API: {id, filename, index_status:"ready"}
    API-->>Frontend: 上传成功
    Frontend-->>User: ✓ 已索引

    Note over User,Agent: === 提问阶段 ===
    User->>Frontend: "Python 列表是什么？"
    Frontend->>API: POST /api/v1/chat
    API->>CS: send_message("Python 列表是什么？")
    CS->>KS: search("Python 列表是什么？", top_k=3)
    KS->>RS: search(query)
    RS->>FAISS: embed(query) → Top-K 搜索
    FAISS-->>RS: [indices, distances]
    RS->>RS: 映射到 chunk_metadata
    RS-->>KS: [{document_name, chunk_id, chunk_text, score}]
    KS-->>CS: [{文档名, 块号, 文本, 相关度}]
    CS->>CS: 构建增强 Prompt
    CS->>AA: chat(augmented_message)
    AA->>Agent: graph.invoke()
    Agent-->>AA: {answer, agent_type}
    AA-->>CS: {answer, agent_type, agent_name}
    CS-->>API: {answer, agent_type, citations}
    API-->>Frontend: {answer, citations}
    Frontend-->>User: 回答 + 引用来源
```

---

## 3. Chunk Metadata 架构

```mermaid
graph LR
    subgraph RAGEngine["RAGEngine (supervisor_agent/rag_engine.py)"]
        CHUNKS["chunks: list[str]<br/>['chunk1', 'chunk2', ...]"]
        FAISS_I["FAISS Index<br/>[vec1, vec2, ...]"]
    end

    subgraph RAGService["rag_service.py (web_app)"]
        META["chunk_metadata.json<br/>[{text, document_name, doc_id, chunk_index}]"]
    end

    CHUNKS -- "索引对齐" --> META
    FAISS_I -- "搜索返回 indices" --> META
    META -- "映射到文档名" --> CITATION["Citation<br/>{document_name, score}"]

    style META fill:#f9f,stroke:#333,stroke-width:2px
    style CITATION fill:#9f9,stroke:#333,stroke-width:2px
```

---

## 4. Memory 架构

```mermaid
graph TB
    subgraph SessionMemory["会话记忆 (MemorySaver)"]
        THREAD1["thread_id: session-abc<br/>消息历史"]
        THREAD2["thread_id: session-xyz<br/>消息历史"]
    end

    subgraph LongTermMemory["长期记忆 (user_profile.json)"]
        PROFILE["{<br/>  background: '计算机大一',<br/>  skill_level: 'beginner',<br/>  learning_goal: 'Python',<br/>  last_active: '2026-06-11',<br/>  conversation_count: 5<br/>}"]
    end

    subgraph KnowledgeMemory["知识记忆 (chunk_metadata.json)"]
        CMETA["[{<br/>  text: '...',<br/>  document_name: 'Python基础.pdf',<br/>  doc_id: 'uuid',<br/>  chunk_index: 0<br/>}]"]
    end

    Agent["Supervisor"] --> SessionMemory
    Agent --> LongTermMemory
    LongTermMemory -->|read_profile / update_profile tools| Agent
    KnowledgeMemory -->|search()| RAGService
    RAGService --> chat_service

    style SessionMemory fill:#eef,stroke:#333
    style LongTermMemory fill:#efe,stroke:#333
    style KnowledgeMemory fill:#ffe,stroke:#333
```

---

## 5. Component 关系图

```mermaid
classDiagram
    class RAGService {
        +RAGEngine _engine
        +list _metadata
        +ingest_pdf(file_path, filename) dict
        +search(query, top_k) list
        +delete_document(doc_id) bool
        +get_stats() dict
    }

    class RAGEngine {
        +SentenceTransformer embedder
        +FAISS index
        +list chunks
        +ingest_pdf(file_path) str
        +search(query, top_k) list
    }

    class KnowledgeService {
        +get_files() list
        +upload_file(file_path, filename) dict
        +delete_file(doc_id) bool
        +search(query, top_k) list
    }

    class ChatService {
        +send_message(message, session_id) dict
    }

    class AgentAdapter {
        +chat(message, session_id) dict
        +graph
    }

    RAGService --> RAGEngine : wraps
    KnowledgeService --> RAGService : calls
    ChatService --> KnowledgeService : calls for citations
    ChatService --> AgentAdapter : calls for LLM
```

---

## 6. 异常处理流程

```mermaid
graph TD
    START["用户提问"] --> TRY["RAG 检索"]
    TRY -->|成功且有结果| BUILD["构建增强 Prompt"]
    TRY -->|成功但无结果| FALLBACK["使用原始消息"]
    TRY -->|异常| FALLBACK
    BUILD --> CALL["调用 Agent"]
    FALLBACK --> CALL
    CALL -->|成功| RETURN["返回 Answer + Citations"]
    CALL -->|超时/失败| ERROR["返回错误信息"]
    RETURN --> DONE["前端渲染"]
    ERROR --> DONE

    style FALLBACK fill:#ff9,stroke:#333
    style ERROR fill:#f99,stroke:#333
```
