# WeAgent 技术文档 副本

## **1\. 项目范围**

WeAgent 是一个面向复杂任务执行的 AI Agent 工作平台，支持单 Agent 独立执行、多 Agent 协作调度、沙箱容器执行、多类型产物预览与编辑，以及 Web、桌面端、Android 多端访问。

本文档聚焦 WeAgent 的技术实现，不展开产品功能说明，重点说明：

- 系统整体架构。

- 前端、后端、沙箱容器的模块划分。

- Web / Desktop / Android 与后端的通信方式。

- Agent 执行链路、事件推送与产物上报机制。

- Codex / Claude Code / OpenCode Adapter 接入方式。

- 多类型产物预览与编辑的适配机制。

- 关键接口、数据模型、故障处理和术语定义。

不在本文档展开的内容：

- 用户操作手册。

- 产品介绍和竞赛材料。

- 详细 UI 设计稿。

- 每个接口的完整字段级 API 文档。

- 每个测试用例的执行报告。

## **2\. 相关技术栈**

### **2\.1 前端技术栈**

- Vue：Web、Desktop、Android 页面实现。

- Element UI：基础 UI 组件。

- Axios：REST API 请求。

- Socket\.IO Client：实时消息和进度事件接收。

- Markdown 渲染组件：消息内容、Raw Output、代码块展示。

- Electron：桌面端应用外壳和打包。

- Capacitor：Android WebView 应用外壳。

### **2\.2 后端技术栈**

- Python：后端主要语言。

- Flask：HTTP API 服务。

- Flask\-SocketIO：实时通信。

- SQLAlchemy：ORM。

- PyMySQL：MySQL 数据库连接。

- Marshmallow：请求和响应数据校验。

- Docker SDK / Docker CLI：沙箱容器管理。

### **2\.3 沙箱与 Agent 技术栈**

- Docker：隔离 Agent 执行环境。

- Orchestrator：容器内多 Agent 管理与消息路由。

- Claude Code CLI：Claude Code Provider。

- Codex CLI：Codex Provider。

- OpenCode CLI：OpenCode Provider。

- `weagent-report`：容器内结构化进度和产物上报工具。

- `weagent-service`：容器内服务启动与代理辅助工具。

### **2\.4 数据与基础设施**

- MySQL：用户、Agent、会话、消息、产物、工具等数据存储。

- Node\.js / npm：前端构建与桌面端构建。

- Android Studio / Gradle：Android 端构建与调试。

## **3\. 系统架构**

WeAgent 采用“多端客户端 \+ 后端服务 \+ Docker 沙箱 \+ Provider Adapter”的分层架构。

```Plain Text
Web / Desktop / Android
        |
        | REST API / Socket.IO
        v
Flask Backend
        |
        | Sandbox Host Proxy
        v
Docker Sandbox Container
        |
        | Orchestrator
        v
Provider Runner
        |
        v
Claude Code / Codex / OpenCode
```



### **3\.1 客户端层**

客户端负责用户交互、会话展示、消息渲染、产物查看编辑和配置管理。

- Web 端：核心功能入口。

- Desktop 端：Electron 桌面应用，连接外部后端。

- Android 端：Capacitor \+ WebView，承载移动端主要功能。

### **3\.2 后端服务层**

后端负责统一业务控制：

- 用户认证。

- 模型配置。

- Agent 管理。

- 会话管理。

- 消息保存。

- Agent 执行调度。

- 沙箱容器代理。

- 产物持久化。

- Socket 实时推送。

### **3\.3 沙箱容器层**

沙箱容器负责隔离执行 Agent 任务：

- 每个正式会话绑定 sandbox session。

- 容器内运行 Orchestrator。

- Orchestrator 管理多个 AgentRuntime。

- AgentRuntime 通过 Provider Runner 调用底层 CLI。

- 容器内生成文件、日志、服务和产物事件。

### **3\.4 Adapter 层**

Adapter 层负责将不同底层执行引擎统一成平台可调用的 Agent 能力：

- Claude Code

- Codex

- OpenCode

每个 Agent 可以配置底层 Adapter，从而切换不同执行引擎。

\[架构图预留：WeAgent 系统架构图\]



## **4\. 核心模块**

### **4\.1 前端模块**

主要模块：

- 登录注册模块：用户进入平台。

- 会话模块：会话列表、会话详情、消息输入、消息展示。

- 消息渲染模块：Markdown、代码块、进度、Raw Output、产物卡片、工作流卡片。

- Agent 管理模块：全局 Agent 创建、编辑、删除和配置。

- 会话级 Agent 配置模块：当前会话内临时覆盖 Agent 配置。

- 产物工作台模块：文件、图片、表格、代码、Diff、HTML、Workflow 预览与编辑。

- 收藏与历史模块：收藏会话、消息搜索、历史问题跳转。

- 设置模块：模型配置、个人信息、关于我们。

### **4\.2 后端模块**

主要模块：

- Auth：登录注册和用户认证。

- Settings：模型配置和用户资料。

- Conversation：会话创建、查询、删除、收藏、沙箱绑定。

- Message：消息保存、发送、Agent 回复落库。

- Agent：Agent 配置管理。

- AgentRun：Agent 执行状态、事件序号和错误记录。

- Artifact：产物创建、查询、更新。

- Sandbox：宿主侧容器管理和代理。

- Capability / Toolset：工具集和能力管理。

### **4\.3 沙箱模块**

主要模块：

- Host Manager：宿主侧创建、停止和查询 Docker 容器。

- Sandbox API Proxy：宿主侧 `/api/sandbox` 接口。

- Container Orchestrator：容器内 Agent 管理和消息路由。

- AgentRuntime：单个 Agent 的运行上下文。

- Provider Runner：Claude Code / Codex / OpenCode 适配。

- ServiceManager：容器内预览服务管理。

- ToolRegistry：容器内工具注册。

- MCP Runtime：容器内 MCP 工具运行。

### **4\.4 数据模块**

主要数据对象：

- User

- UserModelConfig

- Agent

- Conversation

- ConversationParticipant

- Message

- AgentRun

- Artifact

- Workflow

- Capability

- ToolProviderConfig

- ToolsetCategory

## **5\. 核心技术实现**

### **5\.1 前后端通信与实时推送**

WeAgent 使用 REST API \+ Socket\.IO 的组合通信机制。

REST API 用于确定性操作：

- 登录注册。

- 创建会话。

- 发送消息。

- 查询 Agent。

- 更新配置。

- 上传文件。

- 查询文件树。

- 读取产物内容。

Socket\.IO 用于实时状态：

- 新消息推送。

- Agent typing 状态。

- 沙箱事件。

- 进度更新。

- 执行日志。

- 产物生成。

关键实现：

- `backend/app/socket/events.py`

- `backend/app/sandbox/api/routes.py`

- `backend/app/services/sandbox_event_bridge.py`

- `frontend/src/utils/socket.js`

事件链路：

```Plain Text
容器内 Agent 执行
  -> weagent-report / push_event
  -> 宿主 /api/sandbox/events
  -> sandbox_event_bridge
  -> 保存消息、进度、产物
  -> socketio.emit("sandbox_event")
  -> 前端更新会话详情
```

设计重点：

- 前端按 `conversation_id` 加入 Socket room。

- 后端按会话隔离事件。

- 进度历史需要持久化，刷新后不能丢失。

- 用户消息和 Agent 回复必须按真实时间顺序展示。

### **5\.2 沙箱容器执行机制**

沙箱容器用于隔离 Agent 执行环境。宿主后端通过 `/api/sandbox` 代理访问容器，而不是让前端直接访问容器。

关键实现：

- `backend/app/sandbox/api/routes.py`

- `backend/app/sandbox/host/manager.py`

- `backend/app/sandbox/container/orchestrator.py`

容器生命周期：

```Plain Text
创建会话
  -> 创建 sandbox session
  -> 启动 weagent-sandbox:latest
  -> 容器内启动 Orchestrator Server
  -> 添加 Agent 到容器
  -> 发送任务
  -> 容器执行
  -> 回传进度、日志、产物
```

容器提供的能力：

- 多 Agent 工作区。

- 文件上传与读取。

- 工作区快照。

- 容器服务启动。

- HTML / Web 服务预览。

- 日志收集。

- 工具和能力投影。

### **5\.3 Adapter 适配器实现**

Adapter 用于把不同底层执行引擎统一成 WeAgent 的 Agent 执行能力。

关键实现：

- `backend/app/sandbox/container/providers/base.py`

- `backend/app/sandbox/container/providers/factory.py`

- `backend/app/sandbox/container/providers/claude_code.py`

- `backend/app/sandbox/container/providers/codex.py`

- `backend/app/sandbox/container/providers/opencode.py`

Provider 映射：

```Plain Text
claude / claude_code -> ClaudeCodeRunner
codex                -> CodexRunner
opencode             -> OpenCodeRunner
```

执行方式：

1. Agent 配置中保存 adapter 类型。

2. Orchestrator 创建 Agent 时读取 `adapter_name`。

3. ProviderRunnerFactory 校验并返回对应 Runner。

4. Runner 构造底层 CLI 调用命令。

5. Runner 注入模型配置、API Key、Base URL、工作目录等环境信息。

6. Runner 解析 stdout / stderr / 错误输出。

7. Orchestrator 将结果转换为统一消息、进度和产物。

适配器解决的问题：

- 不同 CLI 参数不同。

- 不同 Provider 认证方式不同。

- 不同 Provider 输出格式不同。

- 不同 Provider 对沙箱和权限的要求不同。

- 前端必须使用同一套消息和产物展示协议。

### **5\.4 Agent 执行、事件与产物上报**

单 Agent 执行：

```Plain Text
用户发送消息
  -> message_service 保存用户消息
  -> 后端确认会话与 Agent
  -> 后端确认 sandbox session
  -> 添加 Agent 到容器
  -> 发送任务给 Orchestrator
  -> Provider Runner 执行
  -> 保存 Agent 回复、执行事件、产物和错误
  -> Socket 推送前端
```

Agent 执行过程中不是只上报“进度”，而是上报一组结构化执行事件。前端消息中的当前进度、进度历史、产物卡片、Raw Output、服务入口和错误提示，都是从这些事件中解析和持久化出来的。

事件来源包括：

- Provider Runner 的 stdout / stderr。

- `weagent-report` 主动上报。

- Orchestrator 系统事件。

- workspace snapshot 文件差异。

- 容器服务状态变化。

- Adapter 运行错误。

结构化上报类型包括：

- `progress`：当前执行进度。

- `result`：阶段性或最终结果。

- `summary`：摘要信息。

- `text`：普通文本块。

- `table`：表格产物。

- `image`：图片产物。

- `code`：代码产物。

- `file`：文件产物。

- `service`：容器服务产物。

- `error`：错误事件。

事件处理链路：

```Plain Text
Provider Runner / weagent-report
  -> Orchestrator push_event
  -> /api/sandbox/events
  -> sandbox_event_bridge
  -> Message / AgentRun / Artifact 更新
  -> Socket 推送
  -> 前端消息、进度、产物同步更新
```

设计重点：

1. `AgentRun.last_seq` 用于记录事件序号，避免重复处理。

2. 结构化 result 与 Raw Output 分开处理，避免同一段内容重复展示。

3. 产物必须落库，避免刷新后只剩前端临时状态。

4. 事件处理要能容忍 Provider 输出不规范的情况。

5. 用户消息、Agent 占位消息、Agent 最终结果需要保持顺序一致。

### **5\.5 多 Agent 协作与工作流调度**

多 Agent 执行：

```Plain Text
用户发送任务
  -> 主持人 Agent 分析需求
  -> 主持人生成任务拆解
  -> 调度 worker Agent
  -> worker Agent 执行子任务
  -> 主持人汇总结果
  -> 保存工作流、消息和产物
```

多 Agent 协作的核心不是简单让多个 Agent 同时回答，而是通过主持人 Agent 建立调度层。主持人负责把用户任务转换成可执行计划，再将子任务分配给合适的 worker Agent。

调度过程包括：

1. 读取会话参与者和每个 Agent 的能力标签、Skill、系统提示词。

2. 判断用户任务适合单 Agent、串行多 Agent 还是并行多 Agent。

3. 生成任务拆解计划。

4. 将子任务分派给 worker Agent。

5. 收集 worker Agent 的执行结果和产物。

6. 必要时继续追问或安排下一轮执行。

7. 汇总最终结果。

工作流调度的实现重点：

- 主持人 Agent 生成 workflow JSON。

- workflow 不按普通 `file` 产物处理，而是作为 `workflow` 类型展示。

- 消息中展示“任务分配工作流”卡片。

- 点击预览时打开工作流图窗口。

- workflow 内容本身支持复制和查看。

- 多 Agent 的计划、执行、汇总需要与消息顺序绑定。

工作流数据流：

```Plain Text
主持人 Agent 输出任务计划
  -> 后端解析 workflow 数据
  -> Message.workflow / Artifact(workflow) 保存
  -> 前端渲染 workflow 卡片
  -> 用户点击预览
  -> 打开工作流图弹窗
```

多 Agent 调度需要处理的边界：

- worker Agent 不存在或配置缺失。

- 某个 worker 执行失败后是否继续。

- 并行任务的结果顺序与消息展示顺序。

- 主持人总结中不能丢失 worker 产物。

- workflow JSON 不能被错误渲染成普通 Raw Output。

### **5\.6 多类型产物预览与编辑适配**

WeAgent 的产物系统不是简单展示文件列表，而是把不同类型产物适配到统一的产物抽屉和工作台中。

产物来源：

- Agent 结构化上报。

- 容器工作区文件扫描。

- workspace snapshot 差异检测。

- 消息内 workflow / table / file 数据。

- 容器服务生成的页面地址。

产物持久化：

- 使用 Artifact 模型独立存储。

- 产物与 Message 关联。

- 刷新页面后仍可恢复。

- 编辑后可更新产物内容或写回容器文件。

不同产物的适配方式：

- 文件产物：通过 sandbox file raw API 读取内容。

- HTML 产物：通过 workspace proxy 预览，并处理相对资源路径。

- 表格产物：优先使用内置 columns / rows 渲染，不要求文件存在于容器目录。

- 图片产物：展示图片并进入图片工作台编辑。

- 代码产物：进入代码编辑器，保留缩进、换行和语法结构。

- Diff 产物：展示修改前后差异，用于复查 Agent 改动。

- Workflow 产物：打开工作流图预览，而不是按普通文件展示。

- Service 产物：展示容器服务地址、日志和运行状态。

- Raw Output：作为执行原始输出展示，避免和结构化 result 重复渲染。

关键设计点：

1. 产物展示协议统一，前端根据 artifact type 分发到不同工作台。

2. 表格和 workflow 可脱离容器文件系统存在。

3. 文件路径必须处理中文、空格、URL 编码和路径安全。

4. HTML 预览必须保证 CSS、JS、图片资源能通过代理访问。

5. 产物编辑需要区分“编辑内置数据”和“写回容器文件”。

### **5\.7 会话级配置合并**

会话级 Agent 配置是 WeAgent 的关键扩展能力。它允许用户在某个会话中临时调整 Agent 行为，但不修改全局 Agent。

配置来源：

- 全局 Agent 配置。

- 当前会话的 Agent override。

- 用户模型配置。

- 工具集和能力投影。

- Adapter 配置。

合并原则：

1. 会话级配置优先于全局配置。

2. 未覆盖字段继续使用全局 Agent 配置。

3. Adapter、Skill、系统提示词、能力标签和工具都可以参与合并。

4. 合并后的配置只用于当前会话执行。

5. 不把会话级配置写回全局 Agent。

技术价值：

- 同一个 Agent 可以在不同会话中承担不同职责。

- 用户可以临时切换底层 Adapter。

- 多 Agent 协作时，主持人读取的是当前会话有效配置。

- 避免实验性调整污染全局配置。

### **5\.8 安全、隔离与错误处理**

沙箱隔离：

- Agent 在 Docker 容器内运行。

- 宿主后端只通过受控 API 代理容器。

- 容器工作区与宿主环境隔离。

文件安全：

- 保留文件名和后缀。

- 防止路径穿越。

- 处理中文路径和 URL 编码。

- 用户头像等大文件不直接以 base64 写入数据库字段。

Adapter 错误：

- Provider 不存在。

- CLI 未安装。

- API Key 缺失。

- 模型配置错误。

- 执行超时。

容器错误：

- 镜像不存在。

- 容器启动失败。

- 宿主访问容器 404。

- 文件路径不存在。

- 服务代理失败。

处理原则：

- Runner 统一转换底层错误。

- Orchestrator 推送 error 事件。

- 后端保存运行失败状态。

- 前端在对应消息或产物区域展示错误原因。

## **6\. 关键数据流**



### **6\.1 发送消息数据流**

```Plain Text
Client 输入消息
  -> POST /api/messages 或 Socket send_message
  -> message_service 保存用户消息
  -> conversation_service 获取会话参与者
  -> 创建 / 复用 sandbox session
  -> /api/sandbox/sessions/<sid>/send
  -> container Orchestrator
  -> Provider Runner
  -> 返回 Agent 回复
  -> 保存 Message / AgentRun / Artifact
  -> Socket 推送前端
```



### **6\.2 多 Agent 协作数据流**

```Plain Text
用户任务
  -> 主持人 Agent
  -> 读取会话级有效 Agent 配置
  -> 任务拆解 JSON / workflow
  -> worker Agent 执行
  -> worker 产物和结果
  -> 主持人汇总
  -> Message + Artifact + Workflow 保存
  -> 前端展示
```



### **6\.3 执行事件上报数据流**

```Plain Text
Agent 执行
  -> Provider Runner 输出
  -> weagent-report 上报结构化事件
  -> Orchestrator 记录事件序号
  -> /api/sandbox/events
  -> sandbox_event_bridge 去重和转换
  -> 更新 AgentRun / Message / Artifact
  -> Socket 推送给会话 room
```



### **6\.4 产物生成数据流**

```Plain Text
Agent 执行
  -> weagent-report 上报 table/file/image/code/service/workflow
  -> 或容器工作区生成文件
  -> Orchestrator 收集产物
  -> /api/sandbox/events 回传宿主
  -> sandbox_event_bridge 解析
  -> artifact_service 保存
  -> 前端产物抽屉展示
```

### **6\.5 文件预览数据流**

```Plain Text
用户点击文件产物
  -> 前端根据 session_id + path 请求后端
  -> /api/sandbox/sessions/<sid>/files/raw
  -> 宿主代理到容器
  -> 返回文件内容
  -> 前端按文件类型渲染
```

### **6\.6 工作流预览数据流**

```Plain Text
用户点击工作流产物
  -> 前端读取 Message.workflow 或 Artifact(workflow)
  -> 打开工作流全屏弹窗
  -> 解析节点、边、Agent 分配关系
  -> 渲染任务分配工作流图
```

### **6\.7 HTML 预览数据流**

```Plain Text
用户点击 HTML 产物
  -> 前端打开 workspace proxy URL
  -> 后端代理容器文件
  -> 重写 base href / 相对资源路径
  -> 浏览器加载 HTML、CSS、JS、图片
```



## **7\. 关键接口与数据模型**

### **7\.1 关键接口**

认证：

- `POST /api/auth/login`

- `POST /api/auth/register`

会话：

- `GET /api/conversations`

- `POST /api/conversations`

- `DELETE /api/conversations/<id>`

- `PUT /api/conversations/<id>/favorite`

消息：

- `GET /api/messages`

- `POST /api/messages`

Agent：

- `GET /api/agents`

- `POST /api/agents`

- `PUT /api/agents/<id>`

- `DELETE /api/agents/<id>`

产物：

- `POST /api/artifacts`

- `GET /api/artifacts/<id>`

- `GET /api/artifacts/message/<message_id>`

- `PUT /api/artifacts/<id>`

沙箱：

- `POST /api/sandbox/sessions`

- `POST /api/sandbox/sessions/<session_id>/agents`

- `POST /api/sandbox/sessions/<session_id>/send`

- `GET /api/sandbox/sessions/<session_id>/files/tree`

- `GET /api/sandbox/sessions/<session_id>/files/raw`

- `PUT /api/sandbox/sessions/<session_id>/files/write`

- `GET /api/sandbox/sessions/<session_id>/workspace/<path>`

- `POST /api/sandbox/sessions/<session_id>/services/start`

- `GET /api/sandbox/sessions/<session_id>/services/<service_id>/logs`

- `POST /api/sandbox/events`

### **7\.2 关键数据模型**

Conversation：

- `id`

- `title`

- `type`

- `is_favorite`

- `sandbox_session_id`

- `sandbox_container_id`

- `sandbox_host_port`

- `sandbox_status`

Message：

- `id`

- `conversation_id`

- `sender_type`

- `sender_id`

- `content`

- `message_type`

- `artifact_id`

- `workflow`

- `created_at`

Agent：

- `id`

- `name`

- `avatar`

- `color`

- `capabilities`

- `system_prompt`

- `skill`

- `adapter`

- `tools`

AgentRun：

- `conversation_id`

- `round_id`

- `message_id`

- `agent_id`

- `sandbox_session_id`

- `status`

- `last_seq`

- `started_at`

- `finished_at`

- `error`

Artifact：

- `id`

- `message_id`

- `artifact_type`

- `title`

- `path`

- `content`

- `metadata`

- `version`

ToolProviderConfig：

- `capability_id`

- `provider_type`

- `config_text`

- `enabled`

## **8\. 部署与运行结构**

### **8\.1 后端**

后端需要：

- Python 虚拟环境。

- MySQL 数据库。

- 环境变量配置。

- Docker 可用。

- `weagent-sandbox:latest` 镜像存在。

### **8\.2 Web 前端**

Web 前端通过 npm 安装依赖并构建：

```Plain Text
npm install
npm run build
```

### **8\.3 桌面端**

桌面端基于 Electron：

- 配置后端地址。

- 构建桌面端前端。

- Electron 打包生成安装程序。

- 应用名称为 WeAgent。

### **8\.4 Android 端**

Android 端基于 Capacitor：

- 构建 Android 前端资源。

- 执行 Capacitor sync。

- 使用 Android Studio 打开工程。

- 配置 SDK、Gradle、真机或模拟器。

- 配置局域网后端地址和 HTTP 访问策略。

### **8\.5 沙箱镜像**

沙箱镜像必须包含：

- Orchestrator Server。

- Claude Code CLI。

- Codex CLI。

- OpenCode CLI。

- `weagent-report`。

- `weagent-service`。

- 工具和能力运行依赖。

## **9\. 常见故障**

### **9\.1 创建容器失败**

典型错误：

```Plain Text
Docker image 'weagent-sandbox:latest' not found
```

原因：

- 沙箱镜像未构建。

- 镜像名不正确。

- Docker 服务未启动。

处理：

- 检查 Docker 是否运行。

- 构建或加载 `weagent-sandbox:latest`。

- 检查后端是否能访问 Docker。

### **9\.2 宿主访问容器 404**

原因：

- 容器内 Orchestrator 服务未启动。

- 宿主代理路由与容器路由不一致。

- 使用了旧版沙箱镜像。

处理：

- 重建沙箱镜像。

- 检查 `/api/sandbox` 路由。

- 查看容器日志。

### **9\.3 Agent 执行失败**

原因：

- Adapter 配置错误。

- API Key 缺失。

- Provider CLI 未安装。

- 模型 Base URL 错误。

- 执行超时。

处理：

- 检查 Agent adapter。

- 检查模型配置。

- 检查容器内 Provider CLI。

- 查看 AgentRun error 和容器日志。

### **9\.4 产物刷新后丢失**

原因：

- 产物只存在前端临时状态。

- 后端未保存 Artifact。

- 消息中结构化数据未被 sandbox\_event\_bridge 转换。

处理：

- 检查 Artifact 是否落库。

- 检查 message 与 artifact 关联。

- 检查刷新后产物查询接口。

### **9\.5 文件或 HTML 预览没有样式**

原因：

- HTML 相对资源路径未经过代理重写。

- CSS/JS 文件不在对应目录。

- workspace proxy URL 不正确。

处理：

- 使用 `/api/sandbox/sessions/<sid>/workspace/<path>`。

- 检查 base href。

- 检查浏览器网络请求。

### **9\.6 Android 图片或后端访问失败**

原因：

- Android WebView HTTPS 页面请求 HTTP 图片被拦截。

- 局域网 IP 配置错误。

- Android 未允许明文 HTTP。

- 手机与后端不在同一网络。

处理：

- 配置 Android network security。

- 使用正确局域网 IP。

- 确认手机能访问后端端口。

## **10\. 关键术语表**

Agent：

平台中的任务执行角色，可以是前端开发专家、README 生成器等。

主持人 Agent：

多 Agent 会话中的调度角色，负责理解需求、拆解任务、安排执行顺序和汇总结果。

Worker Agent：

多 Agent 会话中执行具体子任务的 Agent。

Adapter：

底层执行引擎适配层，用于接入 Claude Code、Codex、OpenCode 等 Provider。

Provider Runner：

容器内实际调用某个底层执行引擎的运行器。

Sandbox：

Docker 沙箱环境，用于隔离 Agent 执行过程。

Orchestrator：

容器内多 Agent 管理器，负责创建 Agent、路由消息、调用 Provider、采集产物和上报事件。

Artifact：

Agent 执行过程中产生的产物，例如文件、表格、代码、图片、Diff、HTML、Workflow。

Workflow：

任务分配和执行流程图，用于展示多 Agent 协作计划。

Raw Output：

底层 Provider 的原始输出，主要用于排查执行过程和错误。

Session：

沙箱会话，一个正式会话通常绑定一个 sandbox session。

Workspace：

容器中的工作区目录，用于存放 Agent 生成或修改的文件。



> (注：内容由 AI 生成，请谨慎参考）
