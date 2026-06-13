# AI Learning Assistant - Project User Guide

> 帮助从零上手并在面试中流畅演示

## 1. 项目概述

AI Learning Assistant 是一个基于 LangGraph Multi-Agent 的智能学习助手。
用户发一条消息 -> Supervisor 判断问题类型 -> 路由到对应 Agent -> 返回答案

### 6 个 Agent

| Agent | 触发场景 | 工具 |
|---|---|---|
| Code Agent | Python/编程问题 | calculator, read_file |
| Search Agent | 联网搜索 | web_search (DuckDuckGo) |
| Career Agent | 学习规划 | calculator, user_profile |
| Research Agent | 深度调研 | web_search, calculator |
| RAG Agent | 基于 PDF 问答 | ingest_pdf, rag_search |
| English Agent | 英语学习 | calculator |

## 2. 启动方式

### Docker
`ash
cp web_app/.env.example .env
docker compose up -d
# http://localhost
`

### 本地开发
`ash
# 后端
cd web_app/backend && pip install -r requirements.txt
alembic upgrade head && uvicorn app.main:app --reload --port 8000
# 前端
cd web_app/frontend && npm install && npm run dev
`

## 3. 执行流程

User -> POST /v1/chat
  -> chat_service.send_message()
    -> agent_adapter.chat()
      -> supervisor_node (LLM 分类)
      -> route_to_agent (Conditional Edge)
      -> 对应 Agent (ReAct: LLM + Tool)
      -> END
    -> 保存到 PostgreSQL
  -> 返回 {answer, agent_type, citations}

## 4. 面试演示脚本 (5 分钟)

1. 打开页面: '这个项目是 AI 学习助手, 后端 FastAPI+LangGraph, 前端 React'
2. 注册登录: 'JWT + bcrypt, 所有 API 有 Depends(get_current_user)'
3. Code Agent: 输入'写快速排序', 'Supervisor 路由到 Code Agent, ReAct 模式'
4. Search Agent: 输入'Python 3.13 新特性', '调用 DuckDuckGo 搜索'
5. RAG: 上传 PDF -> 提问, 'FAISS 检索 + LLM 生成, 带引用来源'
6. 历史会话: 刷新页面, 'PostgreSQL 持久化, MemorySaver 上下文记忆'
7. 总结: '20 API / 7 张表 / 57 测试 / Docker 部署'

## 5. 面试预备问题

Q: RAG 用户隔离了吗?
A: FAISS 索引是全局共享的, 已知 P2 问题, rag_service.py 中有 TODO

Q: 删除文档后索引重建?
A: 会重建但空索引有边界问题, 需要修复

Q: Plans 页面在哪?
A: API 已完成, Planner Agent 可生成计划, 缺前端页面
