# AI Learning Assistant

> 🎓 基于 LangGraph + DeepSeek 的智能学习助手系统  
> Multi-Agent 架构 | RAG 知识库 | 会话记忆 | Web 界面

---

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  /chat        /knowledge     /plans       /reports      │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP (REST API)
┌────────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                Service Layer                        │  │
│  │  chat_service.py  knowledge_service.py  rag_service│  │
│  └────────────────────────┬────────────────────────────┘  │
│                           │                                │
│  ┌────────────────────────▼────────────────────────────┐  │
│  │              Agent Adapter Layer                     │  │
│  │           agent_adapter.py (桥接层)                  │  │
│  └────────────────────────┬────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ Python import
┌───────────────────────────▼─────────────────────────────────┐
│              Supervisor Agent (LangGraph)                   │
│                                                             │
│  supervisor_node: 自动路由                                   │
│       ├── Code Agent (Python 编程)                          │
│       ├── English Agent (英语学习)                           │
│       ├── Career Agent (学习规划)                            │
│       ├── Search Agent (联网搜索)                            │
│       ├── Research Agent (多源研究)                          │
│       ├── RAG Agent (文档问答)                               │
│       └── Planner (复杂任务拆解)                             │
│                                                             │
│  MemorySaver: 会话记忆                                       │
│  user_profile.json: 长期记忆                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **Multi-Agent** | 7 个子 Agent 各司其职，Supervisor 自动路由 |
| **RAG 知识库** | 上传 PDF → 自动切片 → Embedding → FAISS 检索 → 引用回答 |
| **会话记忆** | MemorySaver 记录对话历史，跨消息上下文理解 |
| **长期记忆** | user_profile.json 持久化用户画像 |
| **联网搜索** | DuckDuckGo Search Agent 获取实时信息 |
| **Web 界面** | React + Tailwind 聊天界面，可视化知识库管理 |

---

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- DeepSeek API Key

### 1. 后端启动

```bash
cd web_app/backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
echo DEEPSEEK_API_KEY=your-key-here > .env

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端启动

```bash
cd web_app/frontend

# 安装依赖
npm install

# 启动开发服务器
npx vite --host 0.0.0.0 --port 5173
```

### 3. 验证

```bash
# 健康检查
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}

# 发送聊天消息
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Python 列表是什么？","session_id":"test-1"}'
```

---

## 项目目录

```
web_app/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # 应用入口
│   │   ├── core/
│   │   │   └── config.py             # 全局配置
│   │   ├── api/v1/
│   │   │   ├── chat.py               # 聊天 API
│   │   │   └── knowledge.py          # 知识库 API
│   │   ├── models/                   # 数据模型（预留）
│   │   └── services/
│   │       ├── agent_adapter.py      # Agent 桥接层
│   │       ├── chat_service.py       # 对话服务
│   │       ├── knowledge_service.py  # 知识库服务
│   │       └── rag_service.py        # RAG 检索服务
│   ├── uploads/                      # PDF 文件存储
│   ├── data/                         # 持久化数据
│   │   ├── documents.json            # 文档元数据
│   │   └── chunk_metadata.json       # 块级元数据
│   ├── rag_index/                    # FAISS 索引（来自 supervisor_agent）
│   ├── .env                          # 环境变量
│   └── requirements.txt              # Python 依赖
│
├── frontend/                         # React 前端
│   ├── src/
│   │   ├── App.tsx                   # 路由配置
│   │   ├── pages/
│   │   │   ├── Home.tsx              # 首页
│   │   │   ├── Chat.tsx             # 聊天页
│   │   │   └── Knowledge.tsx        # 知识库页
│   │   ├── components/chat/
│   │   │   ├── MessageBubble.tsx     # 消息气泡（含引用来源）
│   │   │   ├── AgentBadge.tsx        # Agent 标识
│   │   │   └── InputBox.tsx          # 输入框
│   │   ├── api/
│   │   │   ├── chat.ts              # 聊天 API
│   │   │   └── knowledge.ts         # 知识库 API
│   │   └── types/chat.ts            # TypeScript 类型
│   └── vite.config.ts               # Vite 配置（API 代理）
│
├── supervisor_agent/                 # ⚠️ 不修改（旧 CLI 项目，通过 adapter 调用）
│   ├── agent_graph.py               # LangGraph 图定义
│   ├── rag_engine.py                 # RAG 底层引擎
│   └── .env                          # DeepSeek Key
│
├── ARCHITECTURE.md                   # 架构文档
└── README.md                         # 本文件
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| **Agent 框架** | LangGraph + LangChain |
| **LLM** | DeepSeek (ChatOpenAI 兼容接口) |
| **后端** | FastAPI + Python 3.11 |
| **前端** | React 19 + Vite + Tailwind CSS |
| **向量检索** | FAISS + Sentence-Transformers |
| **PDF 处理** | PyMuPDF (fitz) |
| **记忆系统** | MemorySaver (会话) + JSON (长期) |

---

## RAG 工作流程

```
用户上传 PDF
    ↓
knowledge_service.upload_file()
    ↓
rag_service.ingest_pdf()
    ├── RAGEngine 读取 PDF → 按段落切块 (500字/块)
    ├── SentenceTransformer 计算 Embedding
    ├── 存入 FAISS 索引
    └── 记录 chunk_metadata（文档名 → 块映射）
    ↓
用户提问
    ↓
chat_service.send_message()
    ├── knowledge_service.search() 检索 FAISS
    │   ├── Embed 用户问题
    │   ├── FAISS 搜索 Top-K（L2 距离）
    │   └── 映射到 chunk_metadata 获取文档名
    ├── 构建增强 Prompt（含引用来源）
    ├── 调用 Supervisor Agent
    └── 返回 Answer + Citations
```

---

## 许可证

MIT
