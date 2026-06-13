# GitHub Showcase Guide — AI Learning Assistant

## 🎯 面试官视角的 5 个核心卖点

| # | 卖点 | 技术深度 | 面试价值 |
|---|------|---------|---------|
| 1 | **Multi-Agent 架构** | LangGraph Supervisor + 6 个专用 Agent，非简单 ChatBot | ⭐⭐⭐⭐⭐ |
| 2 | **RAG 全链路** | PDF → Chunk → Embedding → FAISS → Citation，生产级实现 | ⭐⭐⭐⭐⭐ |
| 3 | **JWT 用户隔离** | 7 张表全部 user_id 过滤，bcrypt 加密，Token 过期管理 | ⭐⭐⭐⭐ |
| 4 | **生产化部署** | Docker + Railway + Vercel + Neon，CI/CD 就绪 | ⭐⭐⭐⭐ |
| 5 | **FastAPI 设计** | 25 个 RESTful API，SQLAlchemy 2.0 + Alembic 迁移 | ⭐⭐⭐⭐ |

---

## 📝 简历描述模板

### English Version

```
AI Learning Assistant | FastAPI · LangGraph · RAG · React

• Architected a multi-agent AI platform with LangGraph Supervisor routing queries to 
  6 specialized agents (Code, English, Career, Search, Research, RAG)
• Built production RAG pipeline: PDF upload → text chunking → Sentence Transformer 
  embedding → FAISS vector search → citation-grounded answers
• Implemented JWT authentication with bcrypt, enforcing user isolation across all 
  7 database tables (conversations, documents, plans, tasks, etc.)
• Designed PostgreSQL schema (SQLAlchemy 2.0 + Alembic migrations) with FK constraints
• Deployed to production via Docker → Railway (backend) + Vercel (frontend) + Neon DB
• Developed 25 RESTful endpoints with FastAPI, 72% JWT-protected
• Built AI-powered learning plan generator with task breakdown and progress tracking
• Integrated Session + Long-Term Memory for persistent multi-turn conversations
```

### 中文版本

```
AI Learning Assistant | FastAPI · LangGraph · RAG · React

• 基于 LangGraph Supervisor 构建多智能体架构，6 个专业 Agent 智能路由
• 实现完整 RAG 流水线：PDF 上传→文本切块→向量化→FAISS 检索→引用回答
• 使用 JWT + bcrypt 实现用户认证，7 张数据库表全部 user_id 隔离
• PostgreSQL 数据库设计（SQLAlchemy 2.0 + Alembic 迁移），含外键约束
• Docker 容器化 + Railway 部署后端 + Vercel 部署前端 + Neon 数据库
• FastAPI 设计 25 个 RESTful 接口，Swagger 自动文档生成
• AI 学习计划生成器，支持任务分解、状态追踪和完成率统计
• 集成会话记忆和长期记忆，支持多轮对话上下文保持
```

---

## 💬 面试问答

### Q1: "LangGraph Supervisor 如何工作？"
> 我实现了一个状态机架构。Supervisor 接收用户消息 → 用 LLM 分类到 6 个类别之一（code/english/career/search/research/rag）→ 返回 next_agent → 对应 Agent 执行任务 → 返回结果到 Supervisor 汇总。每个 Agent 是独立的 LangGraph 子图，通过 add_node 注册到主图。

### Q2: "RAG 如何保证答案准确？"
> 我用了三步策略：1) 重叠 Chunk（overlap=100 字符）避免内容截断 2) Top-K=3 检索 + 相似度阈值 0.4 3) 引用原文 chunk_id + page_number。如果相关度低于阈值，自动降级到 LLM 自身知识回答，不会拒绝回答。

### Q3: "用户隔离怎么做的？"
> 所有 7 张表（users/conversations/messages/documents/chunks/plans/tasks）都有 user_id 外键。每次 API 请求通过 Depends(get_current_user) 获取当前用户，所有查询 WHERE user_id = current_user.id。A 用户无法访问 B 用户的任何数据。

### Q4: "为什么选择 FastAPI？"
> 相比 Flask，FastAPI 提供异步支持、Pydantic 自动校验、OpenAPI 文档生成、性能接近 Node.js/Go。对于多 Agent 并发调用 LLM 的场景，异步支持显著提升吞吐量。

### Q5: "最大的技术挑战是什么？"
> 首次部署 Railway 时遇到 11 个阻塞问题：psycopg2 缺失 → module-level agent 初始化阻塞启动 → API Key 缺失导致崩溃 → CMD 链式命令阻塞 uvicorn → Health Check 依赖数据库。每个问题都需要修改部署策略而非业务代码，最终总结成 43 页诊断文档。

---

## 📸 截图拍摄指南

| 截什么 | 怎么拍 | 效果 |
|--------|--------|------|
| **登录页** | localhost:5173/login | 展示 JWT 认证 |
| **聊天界面** | 发送"什么是 Python List" | 展示 Agent 路由 |
| **知识库上传** | 上传 PDF → 查看状态 Ready | 展示 RAG 流程 |
| **引用回答** | 提问 PDF 内容 → 看引用来源 | 展示 Citation |
| **Swagger** | /docs 页面截图 | 展示 25 个 API |
| **Docker** | docker ps 命令截图 | 展示容器化 |

> 截图保存到 `docs/screenshots/`，命名如 `chat.png`、`knowledge.png`

---

## ✅ GitHub Profile 检查清单

- [ ] **仓库名称**: `ai-learning-assistant`
- [ ] **描述**: Multi-agent AI learning platform | LangGraph · FastAPI · RAG · React
- [ ] **Topics**: `ai`, `fastapi`, `langgraph`, `rag`, `faiss`, `react`, `docker`, `deepseek`, `agent`, `python`
- [ ] **Website**: 指向 Railway URL
- [ ] **README**: ✅ 已优化（含 Mermaid 架构图 + 徽章）
- [ ] **LICENSE**: ✅ MIT
- [ ] **截图**: 📸 待补充到 docs/screenshots/
- [ ] **社交**: LinkedIn / 牛客 / BOSS 直聘添加项目链接

---

## 🎯 适合投递的岗位

| 岗位 | 匹配度 | 原因 |
|------|--------|------|
| **AI 应用开发实习生** | ⭐⭐⭐⭐⭐ | Multi-Agent + RAG + LLM 调用 |
| **Python 后端实习生** | ⭐⭐⭐⭐⭐ | FastAPI + SQLAlchemy + Docker |
| **全栈开发实习生** | ⭐⭐⭐⭐ | React + FastAPI + 部署 |
| **Agent 工程师** | ⭐⭐⭐⭐⭐ | LangGraph Supervisor 架构 |
| **大模型应用开发** | ⭐⭐⭐⭐ | RAG + Prompt Engineering |

---

## 📦 目录结构（展示用）

```
ai-learning-assistant/
├── docs/
│   ├── screenshots/       ← 截图放这里
│   └── diagrams/          ← 架构图放这里
├── supervisor_agent/      ← Agent 核心（面试重点）
├── web_app/backend/       ← API 后端
├── web_app/frontend/      ← React 前端
├── README.md              ← 项目首页
├── GITHUB_SHOWCASE.md     ← 本文件
└── docker-compose.yml     ← 一键部署
```
