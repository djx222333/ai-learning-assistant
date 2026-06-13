# Screenshot Checklist

> 拍摄前准备：启动项目
> ```bash
> # 终端 1
> cd web_app/backend && uvicorn app.main:app --reload --port 8000
> # 终端 2
> cd web_app/frontend && npm run dev
> ```
> 浏览器打开 http://localhost:5173，使用 Chrome 无痕模式，1920×1080 全屏

---

## 拍摄顺序（推荐）

```
 1. home.png        ─ 首页
 2. register.png    ─ 注册
 3. login.png       ─ 登录
 4. chat.png        ─ 对话
 5. knowledge_upload.png  ─ 上传 PDF
 6. knowledge_list.png    ─ 文件列表
 7. chat_citation.png     ─ 引用回答（需要先上传 PDF）
 8. history_sidebar.png   ─ 历史会话
 9. swagger.png     ─ API 文档（最后切到 8000 端口）
```

---

## ① home.png — 首页

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/ |
| **操作步骤** | 启动后直接访问首页，无需登录 |
| **推荐展示** | 项目名称、导航菜单（登录/注册按钮） |
| **检查项** | [ ] 页面正常渲染 [ ] 导航可见 [ ] 布局整洁 |

---

## ② register.png — 注册页

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/register |
| **操作步骤** | 1. 点击"注册"进入注册页<br>2. 填写：用户名（如 `demo_user`）、邮箱、密码、确认密码<br>3. **先不提交**，截图表单本身<br>4. 然后提交，截注册成功后的跳转 |
| **推荐展示** | 完整注册表单 + 密码输入框 |
| **检查项** | [ ] 表单完整 [ ] 密码可见性 [ ] 跳转逻辑正常 |

---

## ③ login.png — 登录页

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/login |
| **操作步骤** | 1. 使用刚注册的账号填写<br>2. 先截图：填写好用户名/密码后的表单状态<br>3. 再点击登录，确认跳转到 /chat |
| **推荐展示** | 已填写用户名密码的表单 + 登录按钮 |
| **检查项** | [ ] 表单完整 [ ] 登录成功后跳转 [ ] 错误提示正常 |

---

## ④ chat.png — 聊天对话

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/chat |
| **操作步骤** | 1. 登录后自动进入聊天页<br>2. 在输入框发送：**"什么是 Python 的列表？"**<br>3. 等待 AI 回复完成<br>4. 确保消息气泡中包含 Agent 名称/标签 |
| **推荐展示** | 用户消息 + AI 回复 + Agent Badge（如 "Code Agent"） |
| **检查项** | [ ] 消息正常发送 [ ] AI 回复完整 [ ] Agent Badge 可见 [ ] 侧边栏可见 |

---

## ⑤ knowledge_upload.png — 知识库上传

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/knowledge |
| **操作步骤** | 1. 点击导航进入 Knowledge 页面<br>2. 准备一个 PDF 文件（建议 2-3 页，内容清晰）<br>3. 点击上传按钮，选择 PDF<br>4. 上传后立刻截图：显示 Processing 状态 |
| **推荐展示** | 上传按钮 + 正在处理中的文件行 + 文件名 |
| **检查项** | [ ] 上传按钮正常 [ ] 文件显示 Processing [ ] 无报错 |

---

## ⑥ knowledge_list.png — 知识库文件列表

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/knowledge |
| **操作步骤** | 1. 等待上一步 Processing 变为 **Ready**<br>2. 截图完整文件列表 |
| **推荐展示** | 文件列表（文件名 + Ready 状态 + 大小 + 删除按钮） |
| **检查项** | [ ] 状态变为 Ready [ ] 删除按钮可见 [ ] 文件名完整 |

---

## ⑦ chat_citation.png — 引用回答

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/chat |
| **操作步骤** | 1. 回到聊天页<br>2. 发送关于已上传 PDF **内容**的问题<br>   - 例如：PDF 内容是 Python 教程，则问 **"Python 列表支持哪些操作？"**<br>3. 等待回答<br>4. 截图包含：回答文本 + **引用来源区域**（文件名、页码） |
| **推荐展示** | AI 回答 + 引用来源卡片（可折叠区域，显示文件名 + chunk_id + page） |
| **检查项** | [ ] 回答引用 PDF 内容 [ ] 来源卡片可见 [ ] 文件名和页码正确 |

---

## ⑧ history_sidebar.png — 历史会话

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:5173/chat |
| **操作步骤** | 1. 进行至少 2 轮对话（不同 session）<br>2. 确保侧边栏显示多个会话<br>3. 当前会话高亮<br>4. 截图包含整个页面（侧边栏 + 聊天窗口） |
| **推荐展示** | 左侧历史列表（2+ 会话）+ 右侧当前对话 + 当前会话高亮 |
| **检查项** | [ ] 侧边栏显示多个会话 [ ] 当前高亮 [ ] 会话标题可见 |

---

## ⑨ swagger.png — API 文档

| 项目 | 内容 |
|------|------|
| **页面地址** | http://localhost:8000/docs |
| **操作步骤** | 1. 浏览器打开 Swagger UI<br>2. 展开 2-3 个 API 分组（如 Auth、Chat、Knowledge）<br>3. 截图展示多个展开的 API |
| **推荐展示** | Swagger 页面 + 多个展开的 API 端点 + 请求/响应示例 |
| **检查项** | [ ] Swagger 正常加载 [ ] API 分组可见 [ ] 端点描述完整 |

---

## 截图质量检查

| 项目 | 要求 | 检查 |
|------|------|------|
| 分辨率 | 1920×1080 | [ ] |
| 格式 | PNG | [ ] |
| 浏览器 | 无痕模式 | [ ] |
| 背景 | 干净整洁 | [ ] |
| 文件名 | 全小写 + 下划线 | [ ] |
| 文件大小 | 每张 < 500KB | [ ] |

---

## README 引用路径

截图放入 `docs/screenshots/` 后，README 中通过以下路径引用：

```markdown
![Chat](docs/screenshots/chat.png)
![Knowledge](docs/screenshots/knowledge_upload.png)
![API Docs](docs/screenshots/swagger.png)
```

README 中已有的截图表格在 **📸 Screenshots** 区块，三栏布局：

```markdown
| Chat | Knowledge Base | API Docs |
|:---:|:---:|:---:|
| ![Chat](docs/screenshots/chat.png) | ![Knowledge](docs/screenshots/knowledge_upload.png) | ![Swagger](docs/screenshots/swagger.png) |
```

---

## Git 提交（截图完成后）

```bash
git add docs/screenshots/
git commit -m "docs: add project screenshots for README"
git push origin main
```
