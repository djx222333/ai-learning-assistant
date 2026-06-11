# AI Learning Assistant — 生产部署文档

> 技术栈：Vercel (Frontend) + Railway (Backend) + Neon (PostgreSQL)

---

## 架构总览

```
User Browser
      │
      ▼
https://your-app.vercel.app  (Vercel - Frontend)
      │
      │  vercel.json rewrites /api/* → Railway
      │
      ▼
https://your-app.up.railway.app  (Railway - Backend)
      │
      │  Docker: uvicorn + langgraph + faiss
      │
      ▼
postgresql://...@ep-xxx.aws.neon.tech/neondb  (Neon - PostgreSQL)
```

---

## 部署步骤

### 第一步：Neon PostgreSQL

1. 打开 https://console.neon.tech
2. 点击 **Create Project**
3. 项目名称：`ai-learning-assistant`
4. 区域选择：**US East** (或离你最近的区域)
5. 创建后，点击 **Connect**
6. 复制 **Connection string (pooled)**：
   ```
   postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
7. 保存到剪贴板（下一步使用）

### 第二步：Railway Backend

1. 打开 https://railway.app
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择你的 GitHub 仓库
4. 设置 Root Directory：`/` (项目根目录)
5. Railway 会自动检测 `railway.json` 和 `Dockerfile`

**环境变量设置：**

在 Railway Dashboard → Variables 中设置：

| 变量 | 值 | 来源 |
|------|-----|------|
| `DATABASE_URL` | `postgresql://...` | Neon 连接串（含 sslmode=require）|
| `DEEPSEEK_API_KEY` | `sk-xxxx` | DeepSeek API Key |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Vercel 域名（部署后更新）|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | 生成随机字符串 |
| `LOG_LEVEL` | `info` | 保持默认 |

**验证部署：**

```bash
# 等待部署完成 (约 3-5 分钟，包含 embedding 模型下载)
# 检查日志
railway logs

# 测试 healthcheck
curl https://your-app.up.railway.app/health
# {"status":"ok","version":"0.4.0"}
```

### 第三步：Vercel Frontend

1. 打开 https://vercel.com
2. 点击 **Add New** → **Project**
3. 选择你的 GitHub 仓库
4. 设置：
   - **Framework Preset**: Vite
   - **Root Directory**: `web_app/frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. 在 **Environment Variables** 中设置：

| 变量 | 值 |
|------|-----|
| `VITE_API_URL` | Railway 部署 URL (可选，rewrites 优先) |

6. 点击 **Deploy**

**配置 Rewrites（API 代理）：**

部署完成后，更新 `vercel.json` 中的 Railway 域名：

```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://your-app.up.railway.app/api/$1"
    }
  ]
}
```

或者在 Vercel Dashboard → Project Settings → Environment Variables 设置：

| 变量 | 值 |
|------|-----|
| `RAILWAY_PUBLIC_DOMAIN` | `your-app.up.railway.app` |

### 第四步：验证完整链路

```bash
# 1. Frontend 可访问
curl -I https://your-app.vercel.app
# HTTP/2 200

# 2. API 代理正常
curl https://your-app.vercel.app/api/v1/health
# {"status":"ok","version":"0.4.0"}

# 3. Chat 功能正常
curl -X POST https://your-app.vercel.app/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","session_id":"prod-test-1"}'
# {"answer":"...","agent_type":"code","citations":[]}

# 4. Database 正常
curl -X POST https://your-app.vercel.app/api/v1/plans/generate \
  -H "Content-Type: application/json" \
  -d '{"goal":"测试计划","duration_weeks":4}'
# {"id":"uuid-xxx","title":"...","weeks":[...]}
```

---

## Railway 配置参考

### railway.json

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "web_app/backend/Dockerfile",
    "watchPatterns": ["web_app/backend/**", "supervisor_agent/**"]
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 120,
    "numReplicas": 1,
    "sleepApplication": false
  }
}
```

**重要：** Railway 的 root directory 必须是仓库根目录（包含 `supervisor_agent/` 和 `web_app/`）。

### 构建过程（约 3-5 分钟）

```
1. Railway 拉取 GitHub 代码
2. 检测 railway.json + Dockerfile
3. 执行 Docker 构建（多阶段）
   - 安装 Python 依赖（~2 分钟）
   - 编译 FAISS + sentence-transformers（~1 分钟）
   - 拷贝 supervisor_agent（~10 秒）
4. 启动容器
5. 自动运行 alembic upgrade head（~2 秒）
6. 启动 uvicorn + 加载 embedding 模型（~20 秒）
7. Healthcheck 通过 → 部署完成
```

---

## Vercel 配置参考

### vercel.json

```json
{
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://$RAILWAY_PUBLIC_DOMAIN/api/$1"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {"key": "Cache-Control", "value": "public, immutable, max-age=31536000"}
      ]
    }
  ]
}
```

**Rewrites 说明：**

| 规则 | 作用 |
|------|------|
| `/api/(.*)` → Railway | 所有 API 请求代理到后端 |
| `/(.*)` → `/index.html` | SPA 路由支持（React Router） |
| `/assets/(.*)` → 1年缓存 | 静态资源极致缓存 |

---

## 环境变量汇总

### Railway (Backend)

| 变量 | 是否必填 | 说明 | 示例 |
|------|---------|------|------|
| `DATABASE_URL` | **是** | Neon PostgreSQL 连接串 | `postgresql://...neondb?sslmode=require` |
| `DEEPSEEK_API_KEY` | **是** | DeepSeek API 密钥 | `sk-xxxxxxxx` |
| `CORS_ORIGINS` | 是 | 允许的跨域域名（逗号分隔） | `https://app.vercel.app` |
| `SECRET_KEY` | **是** | JWT 加密密钥（32位随机串） | `zK3p...9mQ=` |
| `DEEPSEEK_MODEL` | 否 | 模型名称 | `deepseek-v4-flash` |
| `DEEPSEEK_BASE_URL` | 否 | API 基础地址 | `https://api.deepseek.com/v1` |
| `LOG_LEVEL` | 否 | 日志级别 | `info` |
| `MAX_UPLOAD_SIZE` | 否 | 上传文件大小限制 | `52428800` (50MB) |

### Vercel (Frontend)

| 变量 | 是否必填 | 说明 | 示例 |
|------|---------|------|------|
| `RAILWAY_PUBLIC_DOMAIN` | **是** | Railway 部署域名（用于 rewrites） | `your-app.up.railway.app` |

### Neon (Database)

| 变量 | 是否必填 | 说明 | 获取方式 |
|------|---------|------|---------|
| `DATABASE_URL` | **是** | PostgreSQL 连接串（含 SSL） | Neon Dashboard → Connect |

---

## 上线检查清单

### 部署前

```
□  Neon 数据库已创建
□  DATABASE_URL 已包含 ?sslmode=require
□  DEEPSEEK_API_KEY 已设置且有效
□  SECRET_KEY 已替换为随机 32 位字符串
□  CORS_ORIGINS 包含 Vercel 前端域名
□  railway.json 中的 healthcheckPath = /health
□  vercel.json 中的 rewrites 指向正确的 Railway 域名
□  Git 仓库已推送（含 supervisor_agent/ 目录）
```

### 部署中

```
□  Railway 构建成功（日志无 Error）
□  Railway healthcheck 通过（等待 ~60 秒）
$ curl https://your-app.up.railway.app/health

□  Vercel 构建成功
□  Vercel Rewrites 配置正确
$ curl https://your-app.vercel.app/api/v1/health

□  Alembic 迁移自动执行（首次启动）
$ railway logs | grep "alembic"
```

### 部署后

```
□  聊天功能正常
$ curl -X POST https://your-app.vercel.app/api/v1/chat \
  -d '{"message":"Hello"}'

□  知识库上传正常
$ curl -X POST https://your-app.vercel.app/api/v1/knowledge/upload \
  -F "file=@test.pdf"

□  计划生成正常
$ curl -X POST https://your-app.vercel.app/api/v1/plans/generate \
  -d '{"goal":"学习Python"}'

□  Reports 正常
$ curl https://your-app.vercel.app/api/v1/reports/overview

□  CORS 正常工作（浏览器打开前端，F12 → Network 无 CORS 错误）
```

---

## 回滚方案

### 方案 A：Vercel 回滚

```bash
# 1. Vercel Dashboard → Deployments
# 2. 找到上次稳定的部署
# 3. 点击 "..." → Promote to Production
# 完成时间：< 1 分钟
```

### 方案 B：Railway 回滚

```bash
# 1. Railway Dashboard → Deployments
# 2. 找到上次稳定的部署
# 3. 点击 "..." → Rollback to this deploy
# 完成时间：~ 2 分钟（容器重启）
```

### 方案 C：数据库回滚（Neon）

```bash
# 1. Neon Dashboard → Branches
# 2. 创建新的分支从回滚点
# 3. 更新 Railway DATABASE_URL 指向新分支
# 完成时间：~ 5 分钟

# 或直接执行 Alembic 降级
railway run alembic downgrade -1
```

### 回滚优先级

```
1. Vercel 回滚（前端纯静态，秒级完成）     ← 最常用
2. Railway 回滚（后端容器，分钟级完成）     ← 次常用
3. Neon 分支回滚（数据库，含数据迁移）      ← 紧急使用
```

---

## 成本估计

| 服务 | 免费额度 | 超出费用 | 说明 |
|------|---------|---------|------|
| **Vercel** | 100GB 带宽/月 | $20/100GB | 静态站点，通常免费 |
| **Railway** | $5 额度/月 | $5+/月 | 1 容器 + 512MB RAM |
| **Neon** | 0.5GB 存储/月 | $15+/月 | 包含 100h 计算 |
| **DeepSeek API** | 500万 tokens/月 | ¥1/百万 tokens | API 调用计费 |

**预估月费用：** $0-10（个人项目，低流量）

---

## 监控建议

### Railway 日志

```bash
# 查看实时日志
railway logs -f

# 搜索错误
railway logs | grep -i error

# 查看部署历史
railway deployments
```

### Neon 监控

```bash
# Dashboard → Monitor
# 查看：连接数、查询延迟、存储使用
# 告警：CPU > 80%、连接数 > 90%
```

### 自定义健康检查

```bash
# 每 5 分钟检查一次
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://your-app.vercel.app/api/v1/health)
  TIME=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$TIME] API Status: $STATUS"
  sleep 300
done
```

---

## 故障排除

### 问题：Railway 部署超时

```
症状：部署卡在 "Building" 超过 10 分钟
原因：sentence-transformers 模型下载慢（~80MB）
解决：
  1. 使用 Railway 缓存卷持久化模型
  2. 或预先在 Dockerfile 中下载模型
  优化：添加以下到 Dockerfile
  RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### 问题：CORS 错误

```
症状：浏览器控制台显示 CORS 错误
原因：CORS_ORIGINS 未包含 Vercel 域名
解决：
  railway variables set CORS_ORIGINS=https://your-app.vercel.app
  railway restart
```

### 问题：数据库连接失败

```
症状：Alembic 迁移失败 / API 返回 500
原因：DATABASE_URL 格式错误或 SSL 未启用
解决：
  1. 确认 Neon 连接串包含 ?sslmode=require
  2. 在 Railway Dashboard 检查 DATABASE_URL
  3. railway run alembic upgrade head --tag test
```
