# WeAgent 产品文档

更新日期：2026-06-08

## 1. 产品概览

### 1.1 评审 30 秒摘要

WeAgent 是一个 IM 式多 Agent 协作工作台。它把“配置角色、发起任务、调度多个 Agent、绑定工具能力、在 Docker sandbox 中执行、沉淀 Artifact 产物、复查历史会话”放到同一条产品链路里。

对比赛评审来说，WeAgent 的关键价值不是做一个聊天界面，而是展示一个可运行、可配置、可追踪的 AI 协作系统：用户能像开群聊一样组织多个 Agent，也能把 Skill、Tool、MCP、Plugin 等能力绑定给指定 Agent，再通过消息流、文件、diff、服务预览和历史记录看到任务如何推进。

对真实用户来说，WeAgent 的目标是把复杂任务从“和一个助手来回问答”变成“在一个任务会话里组织角色、工具和产物”。

### 1.2 WeAgent 是什么

WeAgent 是一个基于会话的多 Agent 协作平台。用户可以创建单 Agent 或多 Agent 会话，为 Agent 配置模型、提示词、技能和工具能力，让它们围绕同一个目标进行拆解、执行、反馈和产物沉淀。

它解决四个问题：

- 谁来做：通过 Agent、能力标签、系统提示词、Skill 和工具绑定定义执行角色。
- 怎么协作：通过单 Agent 或多 Agent 会话承载持续对话、任务拆解和进度反馈。
- 产出在哪：通过消息元素、Artifact、文件、表格、diff、服务预览等方式保留结果。
- 如何复用：通过会话历史、收藏、工具集、能力库和 AI 协作记录沉淀经验。

本版文档采用联合事实源：`combine/toolset_v1.1.0`、`feature/user_manual_and_product_introduction_v1.1.1`、`combine/artifact_editing_system(base_v1.08)`。某些能力已在待汇总分支实现，但尚未进入当前本地分支，本文会用状态表明确标注。

### 1.3 应该读哪份文档

| 你是谁 | 建议阅读 |
|---|---|
| 比赛评审 | 本文的产品概览、功能状态表、差异化亮点、演示界面描述；再读技术文档的架构和验证章节。 |
| 真实用户 | 本文的 10 分钟快速开始、用户流程、FAQ / 排障、术语表。 |
| 开发者 / 维护者 | `docs/TECHNICAL_DOCUMENTATION.md`；需要恢复上下文时再读 `docs/DOCUMENTATION_TODO.md`。 |

## 2. 当前功能状态

状态标签：

- 当前分支可用：当前本地分支 `combine/toolset_v1.1.0` 中已有实现证据。
- 待汇总分支：已在远端事实分支实现，最终交付前需要确认是否合并。
- 待验证：本轮文档审计未重新运行完整环境验证。

| 能力 | 用户能看到什么 | 状态 | 事实依据 |
|---|---|---|---|
| 登录 / 注册 / 个人资料 | 用户账号、登录态、个人信息入口 | 当前分支可用 | `backend/app/controllers/auth_controller.py`、`frontend/src/views/Login.vue` |
| 模型配置 | Settings 中填写 API Key、Base URL、模型名、自定义模型等 | 当前分支可用 | `backend/app/controllers/settings_controller.py`、`frontend/src/views/Settings.vue` |
| Agent 管理 | 创建、编辑、分类、选择 Agent | 当前分支可用 | `backend/app/controllers/agent_controller.py`、`frontend/src/views/AgentManager.vue` |
| 单 Agent / 多 Agent 会话 | Dashboard 中创建任务会话、添加或移除 Agent | 当前分支可用 | `backend/app/controllers/conversation_controller.py`、`frontend/src/views/Dashboard.vue` |
| 消息与实时进度 | 消息状态、Agent 输出、结构化元素、Raw Output | 当前分支可用 | `backend/app/services/message_service.py`、`backend/app/services/sandbox_event_bridge.py` |
| Docker sandbox 执行 | 每个会话对应隔离容器，Agent 在容器内运行 | 当前分支可用，最终 smoke 待验证 | `backend/app/sandbox/host/manager.py`、`backend/app/sandbox/container/server.py` |
| Toolset / Capability | 创建、导入、审计、测试、启用能力，绑定到 Agent | 当前分支可用 | `backend/app/controllers/capability_controller.py`、`frontend/src/views/Tools.vue` |
| 服务预览 | Agent 启动容器内服务后，通过 proxy URL 预览 | 当前分支可用，最终 smoke 待验证 | `backend/app/sandbox/bin/weagent-service`、`docs/report/sandbox-service-proxy-design.md` |
| Desktop 客户端 | 独立 Electron 客户端，配置外部后端地址 | 当前分支可用 | `clients/desktop/package.json`、`clients/desktop/src/router/index.js` |
| Android 客户端 | 移动端服务器配置、登录、会话、Agent、设置 | 待汇总分支 | `origin/feature/user_manual_and_product_introduction_v1.1.1:clients/android/` |
| 收藏会话 | 将重要会话加入 Favorites 并快速复查 | 待汇总分支 | `Conversation.is_favorite`、`/<conversation_id>/favorite`、`frontend/src/views/Favorites.vue` |
| Artifact Workbench | 文件树、代码编辑、HTML 预览、diff 查看、文件迁移 | 待汇总分支 | `origin/combine/artifact_editing_system(base_v1.08)` |

### 2.1 当前可直接演示路径

如果评审或用户只想确认当前分支能跑出什么，应优先走下面这条路径。它只依赖当前本地分支中已有的核心能力；Android、Favorites 和完整 Artifact Workbench 可以作为后续汇总能力补充说明。

| 顺序 | 操作 | 成功后应该看到 | 状态 |
|---:|---|---|---|
| 1 | 启动后端并访问 `/api/health` | 返回健康检查响应，后端端口可访问 | 当前分支可用 |
| 2 | 启动 Web 前端并注册 / 登录 | 进入 Dashboard，而不是停留在登录页 | 当前分支可用 |
| 3 | 进入 Settings 保存模型配置 | API Key 脱敏显示，模型名 / Base URL 被保存 | 当前分支可用 |
| 4 | 进入 Agent 管理页选择或创建 Agent | Agent 列表出现可选角色，编辑后能保存 | 当前分支可用 |
| 5 | 在 Dashboard 新建单 Agent 或多 Agent 会话 | 会话列表出现新任务，会话页显示参与 Agent | 当前分支可用 |
| 6 | 发送一个小任务 | 消息流出现用户消息、Agent 状态和执行输出 | 当前分支可用 |
| 7 | 查看 Raw Output / 结构化元素 | 能看到执行过程、结果、文件或 service 类型元素 | 当前分支可用 |
| 8 | 如任务启动了服务，打开 service artifact / proxy URL | 通过后端 proxy 访问 sandbox 内服务 | 当前分支可用，最终 smoke 待验证 |

建议演示任务保持很小，例如“生成一个产品 FAQ 草稿”或“创建一个最小 HTML 页面并尝试预览”。这样可以同时展示会话、Agent、执行进度、产物沉淀和服务预览，而不会把演示风险集中到长任务上。

## 3. 核心价值



| 用户痛点 | WeAgent 的做法 | 技术支撑 | 演示界面 | 状态 |
|---|---|---|---|---|
| 复杂任务只靠一个助手，角色边界不清 | 用多个 Agent 作为会话参与者，每个 Agent 有自己的配置和能力 | `ConversationParticipant`、`Agent`、`message_service` | Dashboard / ChatWindow / AgentManager | 当前分支可用 |
| 工具能力散在提示词里，难以复用和审计 | 用 Toolset / Capability 统一管理 Skill、Tool、MCP、Plugin | `Capability`、`AgentCapabilityBinding`、`capability_projection_service` | Tools / Capability Library | 当前分支可用 |
| AI 执行过程看不见，只能等最终回答 | 实时推送消息状态、进度、结构化元素和 Raw Output | Flask-SocketIO、`SandboxEventBridge` | 会话消息流 / Raw Output 面板 | 当前分支可用 |
| 生成内容留在聊天文本里，不像可交付产物 | 将文件、表格、diff、service 等沉淀为消息元素和 Artifact | `Artifact`、message elements、Artifact Workbench | Artifact 预览 / 文件树 / diff | 基础能力当前可用，Workbench 待汇总 |
| 前端或服务类产物无法真实预览 | Agent 在 sandbox 内启动服务，后端提供带 token 的 proxy URL | `weagent-service`、`ServiceManager`、sandbox proxy | service artifact / preview link | 当前分支可用，最终 smoke 待验证 |
| 长期任务难以回看和复用 | 会话历史、收藏、AI 协作记录沉淀上下文 | conversation APIs、Favorites 分支、`docs/ai-collab/` | 会话列表 / Favorites | 历史当前可用，收藏待汇总 |

## 4. 10 分钟快速开始

本节面向本地自部署体验。更完整的命令、环境变量和验证说明见 `docs/TECHNICAL_DOCUMENTATION.md`。

### 4.1 准备依赖

确认本机具备：

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- Redis 服务，建议 Redis 7.x
- Docker Desktop

### 4.2 准备最小后端配置

后端配置来自 `backend/.env` 或等效环境变量。最小本地配置可以从 `backend/.env.example` 开始：

```env
FLASK_ENV=development
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DB=weagent
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
JWT_SECRET_KEY=change-this-to-a-random-secret-key
SECRET_KEY=change-this-to-another-random-key
```

成功标志：MySQL 中存在 `weagent` 数据库，Redis 服务可连接，后端启动时不会因为数据库或缓存配置报错。

### 4.3 启动后端

1. 进入 `backend/`。
2. 创建并激活 Python 虚拟环境。
3. 安装 `requirements.txt`。
4. 准备 `.env`，确保 MySQL、Redis、JWT、上传目录等配置可用。
5. 运行 `python run.py`。
6. 打开 `http://localhost:5002/api/health`，确认后端健康检查可访问。

成功标志：终端显示 Flask 服务正在监听，浏览器或接口工具访问 `/api/health` 有响应。

### 4.4 构建 sandbox 镜像

在 `backend/` 下构建 `weagent-sandbox:latest`。如果镜像不存在，Agent 会话无法进入真实 sandbox 执行链路。

成功标志：`docker image ls weagent-sandbox` 能看到 `latest` 镜像。

### 4.5 启动 Web

1. 进入 `frontend/`。
2. 安装 npm 依赖。
3. 运行 `npm run serve`。
4. 打开 Vue CLI dev server，通常是 `http://localhost:8080`。

成功标志：浏览器能打开 Web 工作台；登录后能进入 Dashboard。

### 4.6 完成第一条任务

1. 注册或登录账号。
2. 进入 Settings，填写模型配置。
3. 进入 Agent 管理页，选择默认 Agent 或创建新 Agent。
4. 回到 Dashboard，新建会话并添加 Agent。
5. 输入一个小任务，例如“生成一个产品 FAQ 草稿”。
6. 观察消息状态、Agent 输出和结构化元素。
7. 如果任务产生文件、diff 或服务预览，从消息中的产物入口查看。

## 5. 模型配置

模型配置入口在 Settings。用户需要填写：

| 字段 | 用途 | 用户注意点 |
|---|---|---|
| API Key | 供 provider runner 调用模型或 CLI 适配层使用 | 保存后前端只显示脱敏值。 |
| Base URL | 自定义模型服务或兼容接口地址 | Codex / OpenCode 可能使用从该地址推导出的 OpenAI-compatible endpoint。 |
| 模型名 / 自定义模型 | 指定默认模型 | 选择 custom 时必须填写自定义模型名。 |
| Temperature | 保存到用户模型配置 | 当前文档不把它写成已投影给 provider runner 的环境变量。 |
| 最大 token | 保存到用户模型配置 | 当前文档不把它写成已投影给 provider runner 的环境变量。 |

当前后端创建或更新 sandbox 会话时，容器环境变量投影主要覆盖 API key、Base URL、模型名和 Codex 相关变量。Claude Code、Codex、OpenCode CLI 的本机可用性、认证状态和网络环境仍会影响真实执行。

### 5.1 常见 provider 配置方式

| 场景 | 建议填写 | 成功标志 |
|---|---|---|
| 使用默认 Claude / Anthropic 兼容服务 | 填写 API Key，模型选择默认项或自定义模型名，Base URL 可留空或填兼容服务地址 | 发送任务后 provider runner 能返回输出，而不是认证错误 |
| 使用 OpenAI-compatible 中转 | 填写中转服务的 API Key、Base URL 和模型名 | Raw Output 中不出现 base URL / model 解析错误 |
| 使用 Codex / OpenCode 等 CLI runner | Settings 保存 key/base/model；同时确认宿主机或 sandbox 内对应 CLI 已安装并完成认证 | Agent 执行时不因 CLI 不存在或未登录失败 |
| 自定义模型 | 选择 custom 并填写自定义模型名 | 保存后 Settings 中能看到有效模型名 |

排查顺序：先确认 Settings 保存成功，再看 Raw Output / provider error，最后检查 CLI 登录状态和网络连通性。

## 6. 核心使用流程

### 6.0 UI 级成功标志

| 流程 | 必填 / 必选内容 | 成功后看到什么 |
|---|---|---|
| 创建 Agent | 名称、provider / adapter、系统提示词；能力标签和 Capability 可按需配置 | Agent 出现在列表中，进入会话时可被选择 |
| 发起单 Agent 会话 | 会话标题、会话类型、一个目标 Agent | ChatWindow 只有一个 Agent 参与，消息发送后出现该 Agent 的执行状态 |
| 发起多 Agent 会话 | 会话标题、多个参与 Agent | 会话参与者区域显示多个 Agent，消息可指向一个或多个 Agent |
| 绑定 Capability | 选择 Capability，再绑定到目标 Agent | Agent 编辑页或能力列表能看到绑定关系 |
| 查看产物 | 打开消息中的文件、表格、service、diff 或 Artifact 入口 | 能看到结构化内容，而不是只有纯文本回答 |

### 6.1 创建 Agent

1. 打开 Agent 管理页。
2. 新建 Agent 或复制默认 Agent。
3. 填写名称、头像颜色、分类、能力标签、provider / adapter、系统提示词。
4. 根据任务需要绑定 Skill 或 Capability。
5. 保存后在会话中选择该 Agent。

适合的 Agent 设计方式：

- 文档 Agent：擅长总结、写作、结构化输出。
- 前端 Agent：擅长页面实现、样式检查、服务预览。
- 后端 Agent：擅长接口、数据库、服务联调。
- 测试 Agent：擅长验收清单、回归测试和风险发现。

### 6.2 发起单 Agent 会话

1. 打开 Dashboard。
2. 新建会话，选择单 Agent。
3. 输入明确目标和约束。
4. 观察 Agent 的进度、输出和结果。
5. 对结果继续追问、要求修改或保存产物。

单 Agent 适合边界清楚、目标直接的任务，例如写一份 FAQ、解释一段代码、生成一个小组件草稿。

### 6.3 发起多 Agent 会话

1. 新建多 Agent 会话。
2. 添加主持 Agent 和多个 worker Agent。
3. 先让主持 Agent 输出计划和分工。
4. 根据计划让不同 Agent 执行对应部分。
5. 在同一会话中复查每个 Agent 的输出、文件、diff 和服务预览。

多 Agent 适合跨角色任务，例如“产品需求 -> 前端页面 -> 后端接口 -> 测试验收 -> 文档总结”。

### 6.4 绑定 Toolset / Capability

1. 进入 Tools / Capability 管理入口。
2. 新建 Skill，或从 Markdown、zip bundle、npx manifest、MCP manifest 导入能力。
3. 查看系统生成的安全审计和权限推断。
4. 为 Tool 配置 provider profile，执行测试并启用。
5. 将能力绑定到指定 Agent。
6. 在会话中验证 Agent 是否能按能力边界工作。

### 6.5 查看和复用产物

用户可在消息流或 Artifact 入口查看：

- 执行进度
- 最终结果
- 表格
- 文件
- 图片
- Raw Output
- diff
- 服务预览

Artifact Workbench、文件树、HTML 预览、diff 查看和文件迁移来自待汇总分支。最终交付前需要确认这些能力是否已进入统一分支。

## 7. 使用场景

### 7.1 文档生成

用户说明读者、目标和章节边界，让文档 Agent 先列目录，再生成正文。适合 README、产品介绍、技术方案、阶段总结、FAQ。

### 7.2 前端开发和服务预览

前端 Agent 在 sandbox workspace 中生成页面或原型，必要时启动本地服务。用户通过 service artifact 的预览地址查看效果，并通过 diff 或文件入口复查修改。

### 7.3 多角色任务协作

产品 Agent 负责需求拆解，前端 Agent 负责页面，后端 Agent 负责接口，测试 Agent 负责验收。用户在一个会话里看见角色分工、执行过程和最终产物。

### 7.4 长期任务复查

用户从会话历史回到之前任务。收藏能力来自待汇总分支，可用于把重要会话加入 Favorites 并按标题、参与者、类型和更新时间复查。

## 8. 演示界面描述

本轮不伪造截图或演示链接。后续补充真实材料时，建议至少提供以下界面截图或视频片段：

| 界面 | 截图应展示什么 | 证明的能力 |
|---|---|---|
| 登录 / 注册 | 登录成功后进入主工作台 | 用户账号体系可用 |
| Settings 模型配置 | API Key 脱敏、Base URL、模型、自定义模型字段 | 模型配置入口清晰 |
| Agent 管理 | Agent 列表、新建 / 编辑弹窗、能力标签 | 角色配置和复用 |
| Dashboard 会话列表 | 单 Agent / 多 Agent 会话入口和会话历史 | 会话式任务容器 |
| ChatWindow 多 Agent 会话 | 多个 Agent 参与者、消息流、状态变化 | 多 Agent 协作形态 |
| Tools / Capability | Skill / Tool / MCP / Plugin 分类、导入、审计、启用 | 能力管理和绑定 |
| 消息进度与 Raw Output | Agent 执行中状态、进度、原始输出 | 过程可见而非黑盒 |
| Artifact / 文件 / diff | 文件树、代码编辑、diff 或 Artifact 卡片 | 产物沉淀 |
| 服务预览 | service artifact、proxy URL、预览页面 | sandbox 内服务可访问 |
| Desktop Server Setup | 配置外部后端地址并通过健康检查 | 桌面端多端连接 |
| Android Server Setup | 手机端填写局域网 / 公网后端地址 | 移动端连接边界 |
| Favorites | 收藏会话列表和筛选 | 待汇总分支的复查能力 |

建议后续截图命名按演示顺序组织，例如 `01-login.png`、`02-settings-model-config.png`、`03-agent-manager.png`、`04-multi-agent-chat.png`、`05-tools-capability.png`、`06-raw-output.png`、`07-artifact-preview.png`、`08-service-preview.png`。每张图应能回答一个问题：这个能力在哪里、当前状态是什么、评审如何判断它不是空描述。

## 9. 差异化亮点

### 9.1 IM 式多 Agent 产品形态

用户不需要理解复杂调度系统，也能通过“谁在会话里、谁负责什么、现在做到哪一步”理解任务进展。评审可通过多 Agent 会话界面直接看到这一点。

### 9.2 可配置、可审计的 Agent 能力

Agent 的能力不只藏在提示词里，而是通过 Toolset / Capability 管理：

- 能力有类型。
- 能力有版本。
- 能力有资源文件。
- 能力有权限推断。
- 能力有导入审计。
- 能力绑定到具体 Agent。
- 能力调用有记录。

评审可通过 Tools / Capability 页面和 Agent 绑定关系看到这一点。

### 9.3 Docker sandbox 承载真实执行

后端会创建 Docker 容器，容器内运行 Orchestrator Server 和 provider runner。Agent 在隔离 workspace 中执行，而不是只在前端展示模拟消息。评审可通过技术文档、sandbox API、service preview 和历史 smoke 记录看到支撑。

### 9.4 产物从过程里自然沉淀

Agent 在执行过程中上报进度、文件、服务和结果。平台把这些内容组织成可读、可复查的产物，而不是把所有东西堆进一段聊天文本。

### 9.5 AI 协作过程可展示

仓库包含 `.planning/`、`docs/ai-collab/`、`docs/report/` 和 `ai-dev-record-package/`，用于展示项目如何通过 AI 协作逐步规划、实现、验证和沉淀。

## 10. 当前限制和路线图

### 10.1 当前限制

| 限制 | 影响 | 当前处理 |
|---|---|---|
| 三条事实分支尚未全部汇总到单一远端分支 | 某些能力不能简单写成当前分支全部可用 | 用功能状态表标注来源和状态 |
| Android 来自待汇总分支 | 当前本地分支不含 `clients/android/` | 文档标注来源，最终合并后再更新 |
| 收藏和 Artifact Workbench 来自待汇总分支 | 当前本地分支可能无法直接演示完整体验 | 演示前确认合并状态 |
| Docker Desktop 和 `weagent-sandbox:latest` 是 sandbox 执行前提 | Docker 不可用时 Agent 执行链路受限 | 快速开始和 FAQ 中提示 |
| provider CLI 和模型网络依赖外部环境 | API key、Base URL、CLI 认证错误会导致任务失败 | Settings 与排障部分说明 |
| 手机端不能用自身 `localhost` 访问电脑后端 | Android 真机连接会失败 | 使用局域网 IP 或公网 HTTPS |

### 10.2 路线图

| 阶段 | 目标 |
|---|---|
| 分支汇总 | 将 toolset、artifact editing、多端和产品介绍分支合并到统一交付分支 |
| 演示完善 | 补充真实截图、演示视频、demo 数据和评审演示脚本 |
| 产品增强 | 优化收藏、搜索、历史、工作流和产物复用体验 |
| 技术增强 | 提升 provider runner 稳定性、MCP runtime、权限边界和测试覆盖 |
| 部署增强 | 提供公网 HTTPS、多端默认后端地址和生产配置建议 |

## 11. FAQ / 排障

### Q1：WeAgent 和普通 AI 聊天工具有什么区别？

普通聊天工具通常围绕一个助手和一段对话。WeAgent 围绕任务会话组织多个 Agent、工具能力、sandbox 执行和产物沉淀，更像一个 AI 协作工作台。

### Q2：什么时候用单 Agent，什么时候用多 Agent？

目标简单、边界明确时用单 Agent。任务需要产品、前端、后端、测试、文档等多个视角时，用多 Agent 更合适。

### Q3：模型配置填错会怎样？

常见表现是 Agent 执行失败、provider runner 报错、没有有效输出。先检查 Settings 中 API Key、Base URL、模型名是否正确，再检查对应 CLI 是否已认证、网络是否可访问。

### Q4：Docker 没启动会怎样？

Agent sandbox 无法创建，任务无法进入真实执行链路。先启动 Docker Desktop，再确认 `weagent-sandbox:latest` 镜像已构建。

### Q5：`weagent-sandbox:latest` 不存在怎么办？

在 `backend/` 下构建 sandbox 镜像。技术文档的部署章节给出了对应命令。

### Q6：MySQL 或 Redis 连不上怎么办？

检查 `.env` 或环境变量中的主机、端口、用户名、密码和库名；确认 MySQL / Redis 服务正在运行。后端启动失败时优先看终端错误。

### Q7：桌面端是否自带后端？

不自带。Desktop 是独立 Electron 客户端，启动后需要配置外部后端地址，例如 `http://localhost:5002` 或服务器地址。

### Q8：Android 为什么不能连 `localhost`？

手机里的 `localhost` 指手机自身，不是电脑后端。真机测试时应填写电脑的局域网 IP，例如 `http://192.168.1.100:5002`，或使用公网 HTTPS 地址。

### Q9：收藏按钮或 Favorites 页面为什么在当前分支看不到？

收藏能力来自 `feature/user_manual_and_product_introduction_v1.1.1`，当前本地分支尚未统一汇总时可能不可见。

### Q10：Artifact Workbench 为什么要标注待汇总？

完整文件树、代码编辑、HTML 预览、diff 查看和文件迁移主要来自 `combine/artifact_editing_system(base_v1.08)` 及其后续汇总分支。最终提交前需要确认是否已合并到交付分支。

## 12. 术语表

| 术语 | 含义 |
|---|---|
| Agent | 执行任务的 AI 角色，拥有名称、提示词、provider、技能和工具能力。 |
| 会话 | 承载任务上下文、参与者、消息和 sandbox 生命周期的任务容器。 |
| 多 Agent | 一个会话中有多个 Agent 参与，适合跨角色任务。 |
| Provider runner | 在 sandbox 内调用 Claude Code、Codex、OpenCode 等执行器的适配层。 |
| Skill | 可复用的工作方法或指令包，可作为 Capability 管理。 |
| Tool | 可被 Agent 调用的工具能力。 |
| Toolset | 面向用户的工具和能力管理入口。 |
| Capability | Skill、Tool、MCP、Plugin 的统一能力模型。 |
| MCP | Model Context Protocol，用于连接外部工具或上下文服务。 |
| Plugin | 可安装或接入的扩展能力。 |
| Artifact | 从 Agent 执行过程中沉淀出的文件、代码、网页、diff、服务等产物。 |
| Sandbox | Docker 容器中的隔离执行环境。 |
| 服务预览 | 将 sandbox 内服务通过后端 proxy 暴露给用户预览。 |
| Raw Output | provider runner 的原始输出，便于排查执行过程。 |
| 待汇总分支 | 已有代码事实，但尚未合并到当前本地交付分支的远端分支。 |
