# Screenshot Guide — AI Learning Assistant

> 运行项目后截取以下页面，保存到 `docs/screenshots/` 目录

## 截图清单

| # | 文件名 | 页面 | 路由 | 需要展示 |
|---|--------|------|------|---------|
| 1 | `login.png` | 登录页 | /login | 用户名/密码表单 + 登录按钮 + 注册链接 |
| 2 | `register.png` | 注册页 | /register | 注册表单 + 密码确认 + 注册成功后自动跳转 |
| 3 | `chat.png` | 聊天页 | /chat | 发送"什么是 Python" + AI 回答 + Agent Badge |
| 4 | `chat_citation.png` | 引用回答 | /chat | 上传 PDF 后提问，展示引用来源（文件名+页码） |
| 5 | `knowledge_upload.png` | 知识库上传 | /knowledge | 上传 PDF 对话框 + Processing → Ready 状态 |
| 6 | `knowledge_list.png` | 知识库列表 | /knowledge | 已上传文件列表 + 删除按钮 |
| 7 | `history_sidebar.png` | 历史会话 | /chat | 侧边栏展开，显示多个历史会话 + 高亮当前会话 |
| 8 | `swagger.png` | API 文档 | /docs | FastAPI Swagger 页面，展示所有 API 端点 |
| 9 | `home.png` | 首页 | / | 项目欢迎页面或导航 |

## 拍摄要求

| 项目 | 要求 |
|------|------|
| 分辨率 | 1920×1080（全屏） |
| 格式 | PNG |
| 浏览器 | Chrome/Edge 无痕模式 |
| 背景 | 干净，无书签栏 |
| 命名 | 全小写英文字母，下划线分隔 |

## 拍摄步骤

### Step 1: 启动项目
```bash
cd web_app/backend
uvicorn app.main:app --reload --port 8000
# 新终端
cd web_app/frontend
npm run dev
```

### Step 2: 注册账号
1. 打开 http://localhost:5173
2. 点击注册 → 填写信息 → 提交
3. 截图：`register.png`

### Step 3: 登录
1. 使用刚注册的账号登录
2. 截图：`login.png`

### Step 4: 聊天测试
1. 进入聊天页面
2. 发送"什么是 Python 的列表？"
3. 等待 AI 回复
4. 截图：`chat.png`（包含 Agent 名称标签）

### Step 5: 知识库
1. 进入 Knowledge 页面
2. 上传一个 PDF 文件
3. 等待状态变为 Ready
4. 截图：`knowledge_upload.png` 和 `knowledge_list.png`

### Step 6: 引用回答
1. 回到聊天页，发送关于 PDF 内容的问题
2. 查看回答是否包含引用来源
3. 截图：`chat_citation.png`

### Step 7: Swagger
1. 打开 http://localhost:8000/docs
2. 截图：`swagger.png`

## 最终目录结构

```
docs/screenshots/
├── login.png
├── register.png
├── chat.png
├── chat_citation.png
├── knowledge_upload.png
├── knowledge_list.png
├── history_sidebar.png
├── swagger.png
└── home.png
```
