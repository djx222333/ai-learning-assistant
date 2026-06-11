# Production Deployment Plan

## Architecture

`
  User Browser
       |
       v
  Vercel (React SPA)
       |  /api/* rewrite
       v
  Railway (FastAPI + LangGraph)
       |
  +----+----+
  |         |
  v         v
  Neon      DeepSeek
  (PG16)    (LLM)
`

## 部署顺序

1. Neon 创建免费 PostgreSQL 数据库
2. Railway 部署后端（连接 GitHub，设环境变量）
3. Vercel 部署前端（root = web_app/frontend）
4. 配置 CORS（指向 Vercel 域名）
5. 验证端到端流程

## 环境变量

Railway: DEEPSEEK_API_KEY, DATABASE_URL, SECRET_KEY, CORS_ORIGINS
Vercel:  RAILWAY_PUBLIC_DOMAIN

## 费用估算

Vercel  + Railway  + Neon  + DeepSeek ~-5 = ~-10/mo
