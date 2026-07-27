# WeAgent 技术文档配图提示词

用途：本文件保存用于生成技术文档配图的提示词。生成图片时优先追求“一眼看懂模块关系”，不要追求把所有实现细节塞进一张图。

## 1. 系统架构总览图提示词

```text
请生成一张 16:9 横向技术架构总览图，主题是“WeAgent 系统架构”。

画面目标：
让读者一眼看懂 WeAgent 是一个多端客户端 + Flask 后端协调 + Docker Sandbox 执行 + Capability / Artifact / Service Preview 回传的系统。

视觉风格：
干净、现代、技术文档风格，浅色背景，模块清晰，留白充足。使用扁平化架构图，不要 3D，不要照片质感，不要复杂装饰。颜色控制在 4 类以内：客户端蓝色、后端绿色、沙箱橙色、数据/基础设施灰色。字体清晰，文字尽量少，每个模块只放 2 到 6 个中文字或英文术语。

画面布局：
从左到右分成 5 个大区域：

1. 用户与客户端
   - 标注“用户”
   - 三个客户端入口：Web、Desktop、Android
   - 表示它们都连接同一个后端

2. Flask 后端协调层
   - 大模块标题：“Flask Backend”
   - 内部只放 5 个小标签：Auth、Conversation、Message、Agent、Sandbox Host
   - 旁边补一个小标签：Socket.IO

3. Docker Sandbox 执行层
   - 大模块标题：“Docker Sandbox”
   - 表示“一会话一容器”
   - 内部包含：Orchestrator、Agent Runtime、Provider Runner、Tool / MCP、weagent-service

4. 数据与基础设施
   - 放在后端下方或右下角
   - 包含：MySQL、Redis、Docker Engine、Provider CLI

5. 产物与实时回传
   - 放在右侧或从 Sandbox 回到 Client 的路径上
   - 包含：Message Elements、Artifact / Workbench、Service Preview、Realtime Events

箭头关系：
- 用户任务从“用户与客户端”进入“Flask Backend”
- Flask Backend 创建会话并调度到“Docker Sandbox”
- Capability / Toolset 从后端投影到 Sandbox，箭头标注“.weagent projection”
- Sandbox 内 Agent Runtime 调用 Provider Runner、Tool / MCP、weagent-service
- 执行状态、消息元素、Artifact、Service Preview 通过 Socket.IO 回到客户端
- 数据持久化从后端连接到 MySQL / Redis

必须避免：
- 不要生成密密麻麻的小字。
- 不要画成产品宣传海报。
- 不要使用真实公司 logo。
- 不要把 Web、Desktop、Android 画成三个完全独立后端。
- 不要把模型服务画成 WeAgent 内部服务，Provider CLI 是外部执行入口。

标题：
顶部居中写“WeAgent 系统架构”

整体观感：
像一张正式技术文档里的 C4 风格系统上下文图和容器图的结合版，清晰、克制、模块边界明确。
```

## 2. Agent 执行系统图提示词

```text
请生成一张 16:9 横向技术架构图，主题是“WeAgent Agent 执行系统”。

一句话目标：
让读者一眼看懂：用户消息进入会话后，后端选择目标 Agent，并把会话级配置和工作流上下文交给 Docker Sandbox 中的 Agent Runtime；Agent Runtime 调用 Provider / Tool 执行任务，再把状态、文本和产物实时回传给用户。

视觉风格：
技术文档插图，浅色背景，模块少而清楚，线条干净。不要人物插画，不要机器人拟人化，不要复杂发光特效。每个模块只用短标签，不要大段文字。

画面布局：
从左到右画一条主执行链，分成 4 个大区域：

1. 会话输入
   - 标题：“Conversation”
   - 包含：User Message、Mentions、Workflow、Session Agent Config
   - 用小标签表示用户可以指定 Agent、选择工作流、临时调整 Agent 配置

2. 后端调度
   - 标题：“MessageService”
   - 包含三个判断/处理点：
     - target_agent_ids
     - agent_configs
     - selected_workflow
   - 输出到两条路径：
     - Single Agent
     - Multi Agent + Moderator

3. Sandbox 执行
   - 标题：“Docker Sandbox”
   - 内部画 3 张简洁 Agent 卡片：Moderator、Worker A、Worker B
   - 每张 Agent 卡片都连接到同一个结构：Agent Runtime -> Provider Runner
   - Provider Runner 下方写：Claude / Codex / OpenCode
   - 旁边有 Tool / MCP Runtime
   - 不要把每个 Agent 画得很复杂，只需要表现“每个 Agent 是一个可配置执行角色”

4. 实时回传
   - 标题：“Realtime Output”
   - 包含：Status、Text、Artifacts、Service、Workflow Plan
   - 通过 Socket.IO 箭头回到 Conversation UI

关键箭头：
- User Message -> MessageService
- Session Agent Config 和 Workflow 作为侧边输入进入 MessageService
- MessageService -> Moderator 或 Single Agent
- Moderator -> Worker A / Worker B，箭头标注“plan / delegation”
- Agent Runtime -> Provider Runner
- Agent Runtime -> Tool / MCP Runtime
- Sandbox events -> Socket.IO -> Conversation UI

重点表达：
- Agent 不是模型本身，而是会话中的可配置执行角色。
- Provider Runner 才负责调用 Claude、Codex、OpenCode 等 CLI。
- Docker Sandbox 是执行边界。
- 工作流图和会话级 Agent 配置是调度上下文，不是全局配置。
- 输出包括状态、文本、Artifact、Service Preview 和 Workflow Plan。

必须避免：
- 不要画成很多小机器人围在一起。
- 不要把 Agent 画成独立服务器。
- 不要把 Session Agent Config 画成会修改全局 Agent。
- 不要把 Socket.IO 写成数据库。
- 不要出现密集代码、表格或过多小字。

标题：
顶部居中写“WeAgent Agent 执行系统”

整体观感：
像一张清晰的系统执行链路图。读者看到后应该能马上理解：后端负责任务分配，Sandbox 负责执行，Provider / Tool 负责实际能力，Socket.IO 负责实时回传。
```

## 3. 还值得补充的配图

结论：除“系统架构总览图”和“Agent 执行系统图”外，最值得继续配图的是读者需要同时理解多个模块边界、数据方向和用户结果的部分。不是每个章节都需要 AI 生图；已经有清晰时序图的链路可以保留 Mermaid，避免技术文档被图片打散。

| 优先级 | 配图主题 | 对应章节 | 为什么值得画 | 建议形式 |
| --- | --- | --- | --- | --- |
| P1 | Capability / Toolset 能力投影 | `6.6`、`7.3` | 能力导入、审查、绑定、投影和调用记录跨越前端、后端、数据库与 Sandbox，纯文字不易一眼看懂。 | AI 架构图 |
| P1 | Artifact / Workbench 文件闭环 | `6.7`、`6.8`、`7.4`、`7.6` | 消息元素、Artifact、Workbench、Diff、文件迁移是连续闭环，需要把“产物是什么”和“产物如何继续处理”分开讲清楚。 | AI 流程图 |
| P1 | WeAgent Service 服务预览 | `6.9`、`7.7` | `weagent-service`、`ServiceManager`、`proxy_url`、token、日志和预览页面存在跨容器代理链路，适合用图降低理解成本。 | AI 链路图 |
| P2 | Docker Sandbox 内部边界 | `6.5` | Host manager、Container API、Orchestrator、workspace、Tool / MCP runtime 和 ServiceManager 都在 Sandbox 边界附近，适合补一张内部边界图。 | AI 架构图 |
| P2 | 多端客户端连接 | `6.1`、`7.8` | Web、Desktop、Android 的差异主要在连接方式和端侧能力，复杂度低于前三项。 | Mermaid 或简图 |
| P3 | 实时事件流 | `6.10`、`7.1` | 技术文档中已有时序图更利于审计事件顺序；除非做演示版文档，否则不必单独 AI 生图。 | Mermaid 优先 |

## 4. Capability / Toolset 能力投影图提示词

```text
请生成一张 16:9 横向技术架构图，主题是“WeAgent Capability / Toolset 能力投影”。

一句话目标：
让读者一眼看懂：用户在 Tools / Capability 页面导入或管理能力，后端完成预览、审查、版本化和 Agent 绑定，再把能力投影到 Docker Sandbox 的 `.weagent` 目录，Agent 执行时从这里读取 Skill、Tool、MCP 和 Plugin。

视觉风格：
干净、克制、技术文档风格。浅色背景，模块边界清楚，箭头少而明确。不要使用产品宣传海报风格，不要使用真实公司 logo，不要出现大段代码。

画面布局：
从左到右分成 4 个区域：

1. Tools / Capability UI
   - 标题：“Tools UI”
   - 包含：Import、Preview、Audit Result、Agent Binding
   - 表示用户可以导入能力、查看审查结果、绑定到 Agent

2. Flask Backend
   - 标题：“Capability API”
   - 内部小标签：Import Preview、Security Audit、Version / Asset、Binding、Call Record
   - 表示后端负责能力数据、版本、资产、绑定和调用记录

3. Database
   - 标题：“MySQL”
   - 包含：Capability、Version、Asset、Binding、Audit、CallRecord
   - 作为后端下方的持久化区域，不要画得过大

4. Docker Sandbox
   - 标题：“Sandbox .weagent”
   - 内部小标签：skills、tools、mcp、plugins、permissions
   - 旁边放一个简洁的“Agent Runtime”模块，表示 Agent 从 `.weagent` 读取能力

关键箭头：
- Tools UI -> Capability API，标注“import / manage”
- Capability API -> MySQL，标注“save metadata”
- Capability API -> Sandbox .weagent，标注“projection”
- Agent Runtime -> Sandbox .weagent，标注“read capabilities”
- Agent Runtime -> Tool / MCP，标注“call”
- Tool / MCP -> Call Record，标注“audit log”

重点表达：
- Toolset 是产品层的能力组织方式。
- Capability 是 Skill、Tool、MCP、Plugin 的统一抽象。
- Agent 绑定能力后，真正执行时通过 Sandbox 内的 `.weagent` 投影读取。
- 调用记录和安全审查是能力系统的一部分。

必须避免：
- 不要把 Toolset 画成独立模型服务。
- 不要把 Skill、Tool、MCP、Plugin 画成四套完全不同系统。
- 不要让图像看起来像流程审批系统。
- 不要出现密集表格或无法阅读的小字。

标题：
顶部居中写“WeAgent Capability / Toolset 能力投影”
```

## 5. Artifact / Workbench 文件闭环图提示词

```text
请生成一张 16:9 横向技术流程图，主题是“WeAgent Artifact / Workbench 文件闭环”。

一句话目标：
让读者一眼看懂：Agent 输出不会只停留在聊天文本里，而是被后端拆成 Message Elements 和 Artifact；前端按类型展示后，用户可以进入 Workbench 查看、编辑、比较 diff，必要时把文件迁移到其他会话。

视觉风格：
技术文档流程图，浅色背景，模块分组清晰。用文件、卡片、编辑器、diff 的简单图标辅助理解，但不要做成花哨 UI 截图。文字必须短，每个模块 2 到 6 个字或短英文术语。

画面布局：
从左到右画一条“产物生命周期”主链路：

1. Sandbox Output
   - 标题：“Sandbox Output”
   - 包含：Provider Text、weagent-report、Service Event、File Change

2. Backend Builder
   - 标题：“Message Element Builder”
   - 包含：code、file、image、table、workflow、service、diff
   - 下方连接到“Artifact Model”

3. Conversation UI
   - 标题：“MessageBubble”
   - 展示几张简洁卡片：Code Card、File Card、Workflow Card、Service Card、Diff Card

4. Artifact Workbench
   - 标题：“Workbench”
   - 包含：CodeEditor、HtmlPageEditor、ImageCropper、DiffView
   - 表示用户可以打开产物继续查看和编辑

5. File Loop
   - 标题：“File Loop”
   - 包含：File API、WorkspaceDiff、FileMigration
   - 表示写回、比较和迁移

关键箭头：
- Sandbox Output -> Message Element Builder
- Message Element Builder -> MessageBubble
- Message Element Builder -> Artifact Model
- MessageBubble -> Workbench，标注“open”
- Workbench -> File API，标注“read / write”
- File API -> WorkspaceDiff，标注“diff”
- FileMigration -> target session，标注“copy files”

重点表达：
- Message Elements 负责把 Agent 输出变成前端可识别的结构化卡片。
- Artifact Model 负责保存代码、网页、文档、PPT、diff 等产物。
- Workbench 负责进一步查看、编辑、比较和迁移。
- workflow 和 service 可以作为消息卡片展示，但它们不是普通静态文件。

必须避免：
- 不要把 Workbench 画成一个普通文件夹。
- 不要把 Artifact 和 Message Element 混成一个概念。
- 不要画成传统网盘或 CMS。
- 不要出现大量伪代码或虚构 UI 文案。

标题：
顶部居中写“WeAgent Artifact / Workbench 文件闭环”
```

## 6. WeAgent Service 服务预览图提示词

```text
请生成一张 16:9 横向技术链路图，主题是“WeAgent Service 服务预览链路”。

一句话目标：
让读者一眼看懂：Agent 在 Docker Sandbox 内启动本地开发服务，`weagent-service` 和 `ServiceManager` 登记服务信息，后端生成带 token 的 `proxy_url`，用户通过前端 Service Card 打开预览页面，并能查看日志、停止或重启服务。

视觉风格：
清晰的链路图，浅色背景，模块边界明确。使用少量端口、日志、浏览器窗口图标。不要画成云平台拓扑，不要出现复杂网络设备。

画面布局：
从左到右分成 5 个区域：

1. Agent Task
   - 标题：“Agent”
   - 包含：start dev server、report service

2. Docker Sandbox
   - 标题：“Docker Sandbox”
   - 内部包含：
     - weagent-service
     - ServiceManager
     - App Process
     - localhost:port
   - 表示服务进程运行在容器内部

3. Container API
   - 标题：“Container API”
   - 包含：start、stop、restart、logs、status

4. Flask Backend Proxy
   - 标题：“Backend Proxy”
   - 包含：proxy_url、token、port mapping
   - 表示后端负责把用户访问代理到容器内部服务

5. Client Preview
   - 标题：“Service Card”
   - 包含：Open Preview、Logs、Restart、Stop
   - 旁边画一个简洁浏览器预览窗口

关键箭头：
- Agent -> weagent-service，标注“register service”
- weagent-service -> ServiceManager，标注“service_id / port / command”
- ServiceManager -> Container API，标注“status / logs”
- Container API -> Backend Proxy，标注“service metadata”
- Backend Proxy -> Service Card，标注“proxy_url”
- Service Card -> Backend Proxy -> localhost:port，标注“preview”
- Logs / status 通过 Socket.IO 或 API 回到 Service Card

重点表达：
- 服务进程运行在 Sandbox 内部，不直接暴露为宿主机长期服务。
- 用户看到的是后端生成的预览链接。
- token 和代理链路用于控制访问边界。
- 日志、停止、重启属于服务管理能力。

必须避免：
- 不要画成用户直接访问容器端口。
- 不要把 `weagent-service` 画成外部 SaaS。
- 不要把 Service Preview 画成 Artifact Workbench 的一部分。
- 不要出现密集端口列表。

标题：
顶部居中写“WeAgent Service 服务预览链路”
```

## 7. Docker Sandbox 内部边界图提示词

```text
请生成一张 16:9 横向技术架构图，主题是“WeAgent Docker Sandbox 内部边界”。

一句话目标：
让读者一眼看懂：Flask 后端在宿主机侧创建和恢复会话容器；容器内部提供 Container API、Orchestrator、Agent Runtime、Tool / MCP runtime、ServiceManager 和 workspace；文件、能力投影、服务和事件都在这个边界内发生。

视觉风格：
正式技术文档架构图，浅色背景。用一条清晰的边界线把“Host Backend”和“Docker Container”分开。模块少而准确，不要塞满函数名。

画面布局：
左侧是宿主机，右侧是容器，中间用粗边界表示 Docker 隔离。

1. Host Backend
   - 标题：“Flask Backend”
   - 包含：ConversationService、MessageService、DockerContainerManager、Socket.IO
   - 表示后端负责会话、消息调度、容器管理和实时推送

2. Docker Boundary
   - 用醒目的容器边框标注：“one conversation = one container”

3. Container API
   - 标题：“Container Server”
   - 包含：health、agents、files、tools、mcp、services、events
   - 表示后端通过 API 调用容器能力

4. Execution Runtime
   - 标题：“Execution Runtime”
   - 包含：Orchestrator、AgentRuntime、Provider Runner、Tool / MCP Runtime
   - 表示 Agent 执行和工具调用发生在容器内

5. Workspace
   - 标题：“Workspace”
   - 包含：
     - `/workspace/agents`
     - `/workspace/.weagent`
     - `/workspace/.session`
   - 表示 Agent 文件、能力投影和会话状态的存放位置

6. Service Runtime
   - 标题：“ServiceManager”
   - 包含：process、logs、port、proxy metadata

关键箭头：
- ConversationService -> DockerContainerManager，标注“create / recover”
- DockerContainerManager -> Container Server，标注“container API”
- MessageService -> AgentRuntime，标注“run task”
- Capability Projection -> `/workspace/.weagent`
- Workbench / File API -> Workspace
- ServiceManager -> Backend Proxy，标注“service preview”
- Container Events -> Socket.IO，标注“realtime events”

重点表达：
- Sandbox 是执行边界，不是普通后台任务目录。
- 每个 Agent 会话对应一个容器。
- Container API 提供健康检查、Agent 执行、文件访问、工具、MCP 和服务管理入口。
- Workspace 保存 Agent 文件、能力投影和会话状态。
- ServiceManager 管理容器内长运行服务。

必须避免：
- 不要把容器画成数据库。
- 不要把 workspace 画成宿主机共享目录。
- 不要把 Provider CLI 画成 WeAgent 自研模型服务。
- 不要出现旧技术栈或历史规划内容。

标题：
顶部居中写“WeAgent Docker Sandbox 内部边界”
```
