# Module Boundary

> 本文件定义各模块的职责边界。AI 在修改代码前应先确认自己改的是哪个模块，以及哪些模块不能直接耦合。

---

## 后端模块

### Controller 层 — API 路由

每个 Controller 对应一个 Blueprint，只做三件事：解析请求、调用 Service、返回响应。

| Controller | 路径前缀 | 核心接口 |
|-----------|---------|---------|
| `auth_controller` | `/api/auth` | 注册、登录、更新用户 |
| `conversation_controller` | `/api/conversations` | 创建/查询/删除会话、参与者管理、附件上传、Agent stop |
| `message_controller` | `/api/messages` | 发送消息、查询历史、流式接口、置顶 |
| `agent_controller` | `/api/agents` | 列表、创建自定义 Agent、分类 |
| `artifact_controller` | `/api/artifacts` | 产物详情 |
| `settings_controller` | `/api/settings` | 用户设置 |
| `tool_controller` | `/api/tools` | 工具管理 |
| `upload_controller` | `/api/upload` | 文件上传 |

### Service 层 — 业务逻辑

| Service | 职责 | 不负责 |
|---------|------|--------|
| `orchestrator_service` | 任务拆解、Agent 分派、结果聚合 | 不直接调用 Agent CLI |
| `message_service` | 消息创建、流式推送、消息查询 | — |
| `artifact_service` | 产物登记、查询、预览 URL 生成 | 不生成产物内容 |
| `conversation_service` | 会话 CRUD、参与者管理、附件 | — |
| `agent_run_service` | Agent 运行生命周期 | — |
| `workspace_diff_service` | 工作区差异计算 | — |
| `sandbox_event_bridge` | 沙箱事件桥接 | — |

### Model 层 — 数据库模型

| Model | 表名 | 核心字段 |
|-------|------|---------|
| `User` | `users` | username, email, password_hash |
| `UserModelConfig` | `user_model_configs` | user_id, provider, model, api_key(已mask) |
| `Agent` | `agents` | name, agent_type(external/custom), adapter_name, system_prompt |
| `AgentCategory` | `agent_categories` | name, icon, color |
| `AgentRun` | `agent_runs` | agent_id, conversation_id, status |
| `AgentTool` | `agent_tools` | agent_id, tool_name, config |
| `Conversation` | `conversations` | title, type(single/group), owner_id, sandbox_status |
| `ConversationParticipant` | `conversation_participants` | participant_type(user/agent), participant_id |
| `Message` | `messages` | sender_type, message_type, content, elements(JSON), status |
| `Artifact` | `artifacts` | artifact_type(code/webpage/document/ppt/diff), title, preview_url |

> Adapter 层（`adapters/`）当前未独立目录，Adapter 逻辑分布在 `services/orchestrator_service.py` 及各自 provider 的 CLI 调用中。后续二期工程再拆分。

### Socket 层 — 实时通信

```
前端 join conversation room
  → 后端接收 send_message
  → 后端推送 conversation_message_created / stream / step / status
```

### Sandbox 层 — Agent 运行环境

- 每个对话对应一个 Docker 容器
- 镜像名：`weagent-sandbox:latest`
- 容器内工作目录：`/workspace`
- 单 Agent 在 `/workspace/agents/{agent_name}/` 下工作

---

## 前端模块

### 页面（View）

| 路由 | View | 功能 |
|------|------|------|
| `/dashboard` | Dashboard.vue | 主聊天页（会话列表 + 聊天窗口） |
| `/login` | Login.vue | 登录 |
| `/register` | Register.vue | 注册 |
| `/agents` | AgentManager.vue | Agent 管理 |
| `/settings` | Settings.vue | 设置 |
| `/tools` | Tools.vue | 工具 |
| `/favorites` | Favorites.vue | 收藏 |

### 组件（Component）

| 组件目录 | 职责 |
|---------|------|
| `ChatWindow/` | 聊天消息展示、输入、流式渲染 |
| `MessageBubble/` | 单条消息气泡渲染 |
| `ConversationList/` | 左侧会话列表 |
| `Sidebar/` | 侧边栏 |
| `ArtifactPreview/` | 产物预览卡片 |
| `ArtifactWorkbench/` | 产物工作台 |
| `CodeEditor/` | 代码编辑器 |
| `DiffViewCard/` | Diff 视图 |
| `AgentAvatar/` | Agent 头像 |
| `AgentEditForm/` | Agent 编辑表单 |
| `HtmlPageEditor/` | HTML 页面编辑器 |
| `ImageCropper/` | 图片裁剪 |
| `FileMigrationDialog/` | 文件迁移弹窗 |

### 状态管理（Vuex Store）

| Module | 管理内容 |
|--------|---------|
| `user` | 用户认证、信息 |
| `conversation` | 会话列表、当前会话 |
| `message` | 消息列表、流式消息 |
| `agent` | Agent 列表、分类 |
| `settings` | 用户设置 |

### API 层

| 文件 | 对应后端 Controller |
|------|-------------------|
| `auth.js` | auth_controller |
| `conversation.js` | conversation_controller |
| `message.js` | message_controller |
| `agent.js` | agent_controller |
| `artifact.js` | artifact_controller |
| `settings.js` | settings_controller |
| `tools.js` | tool_controller |
| `upload.js` | upload_controller |
| `sandbox.js` | sandbox |

---

## 不允许的跨层耦合

- Controller 不能直接调用 Repository
- Service 不能直接返回 HTTP 响应
- Model 不包含业务逻辑
- 前端 Component 不能直接调用 API（应通过 Vuex 或 api/ 模块）
- Adapter 不直接写数据库

---

## 实时通信边界

| 方向 | 协议 | 说明 |
|------|------|------|
| 前端 → 后端 | SocketIO | 发送消息、加入/离开会话 |
| 后端 → 前端 | SocketIO | 消息创建、流式元素、步骤、状态变化 |
| 前端 → 后端 | REST | 登录、查询、创建资源 |

---

## 自我迭代

> 版本：v1.0 | 最后更新：2026-06-08 | 更新人：zby

### 修改流程

1. 模块职责或边界发生变更时，同步更新本文件
2. 在文件头部更新版本号和日期
3. 修改需至少一人 review 确认
4. 涉及跨层耦合变更时，需在 `sessions/` 中记录决策背景

### 触发条件

- 新增/合并/拆分 Controller 或 Service
- 模块职责边界调整
- 数据模型新增或修改
- 新增不允许的跨层耦合规则
