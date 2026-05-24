# Agent Adapter 前端测试与 GSD 实现报告

日期：2026-05-24  
负责人：why  
分支：`agent_adapter`  
文档类型：How-to + Explanation

## 1. 前端如何测试

本节用于你在浏览器里手动验收“前端能否调度 agent，并看到流式消息”。

### 1.1 启动方式

如果当前服务还在运行，可以直接访问：

- 前端：`http://127.0.0.1:8080`
- 后端健康检查：`http://127.0.0.1:5000/api/health`

如果需要重新启动，使用两个终端。

后端：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
$env:FLASK_ENV="testing"
$env:PORT="5000"
python run.py
```

前端：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
npm run serve -- --host 127.0.0.1
```

说明：

- 当前 localhost 验证建议用 `FLASK_ENV=testing`，后端会使用 SQLite 内存库，避免依赖本地 MySQL。
- testing 模式下重启后数据会消失，需要重新注册用户和创建测试 agent。
- 前端已经在 `frontend/vue.config.js` 里关闭 Vue CLI parallel worker，避免 Windows 下 `thread-loader spawn EPERM`。

### 1.2 推荐测试：Mock Adapter 快速验收

Mock adapter 是当前最适合前端验收的路径，因为它稳定、快速，不依赖真实 Claude/Codex CLI 响应时间。

步骤：

1. 打开 `http://127.0.0.1:8080/dashboard`。
2. 如果被跳转到登录页，先注册一个测试账号并登录。
3. 点击左侧导航的“我的Agent”。
4. 选择一个分类，点击“新建Agent”。
5. 填写 Agent 名称，例如 `Local Mock Adapter`。
6. 在“底层模型”中选择 `Mock`。
7. 保存 Agent。
8. 回到左侧导航的“聊天”。
9. 点击新建会话。
10. 选择刚才创建的 `Local Mock Adapter`。
11. 创建会话。
12. 在输入框发送任意消息，例如：

```text
hello localhost frontend dispatch
```

预期现象：

- 发送后，聊天窗口显示用户消息。
- 右侧聊天区出现 agent 正在响应状态。
- 前端通过 SSE 收到 `message.delta`，临时 agent 消息逐步更新。
- 收到 `message.completed` 后，临时消息完成。
- 后端最终持久化一条 agent 消息。
- 如果刷新或重新进入会话，仍能看到最终 agent 回复。

### 1.3 可选测试：Claude / Codex Adapter

真实 Claude/Codex adapter 已经在后端层完成过 smoke 验证，但前端手动验收时要注意：

- Claude/Codex 需要本机 CLI 已登录并可执行。
- Codex 在 UI 调度里可能响应较慢，不建议作为快速前端验收路径。
- 真实 CLI 当前只保证 normalized message stream，hook、MCP、plan mode、交互选择等 runtime 状态还没有完整展示。

可选步骤：

1. 在“我的Agent”中创建或选择一个 `Claude Code` / `Codex` agent。
2. 回到“聊天”，创建包含该 agent 的会话。
3. 发送一个很短的提示词，例如：

```text
Reply exactly: FRONTEND_SMOKE_OK
```

预期：

- 后端会通过 `AgentAdapterFactory` 调用对应 adapter。
- 如果 CLI 快速返回，前端能看到流式消息。
- 如果 CLI 很慢，前端会保持响应中状态，需等待真实 CLI 完成。

### 1.4 已验证的 localhost smoke

本轮已经验证过：

- `http://127.0.0.1:5000/api/health` 返回 200。
- `http://127.0.0.1:8080` 返回 200。
- Mock adapter 的 SSE 输出包含：
  - `agent.started`
  - `message.delta`
  - `message.delta`
  - `message.completed`
  - `done`
- 持久化结果包含两条消息：
  - 用户消息
  - agent 最终回复

示例最终 agent 内容：

```text
**Local Mock Adapter** received your request: persist this localhost dispatch
```

## 2. 整体实现方式

这次实现的主线是：把 Claude Code、Codex、Mock 等 provider 收敛到统一 adapter 层，再通过 orchestrator、SSE 和前端 store 打通用户可见的消息流。

整体链路如下：

```text
Frontend Dashboard
  -> POST /api/messages
  -> message_service.send_message(sender_type='user')
  -> orchestrator_service.dispatch_to_agents(...)
  -> AgentAdapterFactory.create(agent.adapter_name)
  -> adapter.stream(AgentRequest)
  -> normalized AgentEvent
  -> broadcast(conversation_id, event)
  -> GET /api/messages/stream/<conversation_id>
  -> EventSource named events
  -> Vuex streaming message mutations
  -> ChatWindow / MessageBubble render
```

### 2.1 Adapter 层

核心文件：

- `backend/app/adapters/types.py`
- `backend/app/adapters/factory.py`
- `backend/app/adapters/base_adapter.py`
- `backend/app/adapters/normalizers.py`
- `backend/app/adapters/claude_adapter.py`
- `backend/app/adapters/codex_adapter.py`
- `backend/app/adapters/mock_adapter.py`

主要设计：

- `AgentRequest` 作为统一输入。
- `AgentEvent` 作为统一输出。
- `AgentAdapterFactory.create(provider)` 作为创建入口。
- `adapter.stream(request)` 是 canonical streaming method。
- `send_prompt(...)` 仍保留为兼容聚合方法。

当前 provider：

- `claude`
- `codex`
- `mock`
- `opencode`

workspace 解析顺序：

1. `AgentRequest.workspace_path`
2. `AGENT_WORKSPACE_ROOT`
3. WeAgent project root

### 2.2 Orchestrator 层

核心文件：

- `backend/app/services/orchestrator_service.py`
- `backend/app/services/message_service.py`

当前行为：

- 用户发送消息后，`message_service` 不再走旧的 `_mock_agent_response` demo 路径。
- `message_service` 会触发 `orchestrator_service.dispatch_to_agents(...)`。
- Orchestrator 根据会话 participants 找到 agent。
- 每个 agent 通过 `AgentAdapterFactory.create(agent.adapter_name)` 创建 adapter。
- Orchestrator 构造 `AgentRequest`。
- Orchestrator 消费 `adapter.stream(request)`。
- 每个 normalized event 都会通过 `broadcast(...)` 推给 SSE 队列。
- `message.delta` 会被累积。
- `message.completed` 后会保存一条最终 agent message。
- adapter 异常会广播 `agent.failed`。

本轮还修复了一个真实 smoke 中发现的问题：

- 后台 agent worker 子线程需要 Flask app context。
- 现在 `_invoke_agent_in_context(...)` 会确保子线程内可以安全访问 DB/session。

### 2.3 SSE 层

核心文件：

- `backend/app/controllers/message_controller.py`

当前设计：

- 持久化 DB message 仍走默认 SSE data event。
- normalized agent event 走 named SSE event。

示例：

```text
event: message.delta
data: {"schemaVersion":"v1","type":"message.delta",...}
```

支持的 named events：

- `agent.started`
- `message.delta`
- `message.completed`
- `agent.failed`
- `done`

这样前端可以区分：

- 已落库的历史/最终消息
- 正在流式生成的 agent event
- 调用失败事件
- 本轮 agent 响应结束事件

### 2.4 前端层

核心文件：

- `frontend/src/views/Dashboard.vue`
- `frontend/src/store/modules/message.js`
- `frontend/src/components/AgentEditForm/index.vue`
- `frontend/vue.config.js`

当前行为：

- `Dashboard.vue` 的 `EventSource` 现在监听：
  - `agent.started`
  - `message.delta`
  - `message.completed`
  - `agent.failed`
  - `done`
- Vuex message store 新增 streaming mutations：
  - `APPEND_STREAMING_DELTA`
  - `FINALIZE_STREAMING_MESSAGE`
  - `FAIL_STREAMING_MESSAGE`
  - `REMOVE_STREAMING_MESSAGES_FOR_AGENT`
- 前端会按 `runId` 创建临时消息。
- `message.delta` 会增量拼接到临时消息。
- `message.completed` 会 finalize 临时消息。
- 后端最终 DB message 到达后，会移除同 agent 的临时完成消息，避免重复显示。
- Agent 创建表单现在支持选择 `Mock`。

### 2.5 当前边界

已经完成：

- Claude/Codex/Mock adapter factory。
- Claude/Codex 本地真实 CLI smoke。
- Backend orchestrator 集成。
- SSE named events。
- Frontend temporary streaming message render。
- Mock adapter 前台 localhost smoke。

尚未完成：

- hook 提示展示。
- MCP 错误展示。
- plan mode 状态展示。
- permission prompt 展示。
- Claude/Codex interactive choice 的继续会话协议。
- 后台任务生命周期。
- 子 agent 状态。
- rich tool timeline。
- raw event 持久化审计表。

当前一句话结论：

> 现在已经完成 normalized message stream 的端到端链路；还没有完成完整 runtime event surface。

## 3. 本轮 GSD 链路

本轮采用 GSD 作为主流程，避免混用其他规划体系。

### 3.1 讨论与定界

关键定界：

- 目标是 factory 兼容 Claude Code + Codex gateway。
- 先做 adapter 和消息流。
- 前期不动前端，先保持最小模块修改。
- 后续在本地 Claude/Codex 都能调用后，再进入 orchestrator/SSE/frontend 集成。
- `docs/ai-collab` 保留本地，不进入 git。
- 归档命名使用 why。

### 3.2 计划

Phase：

- `01-agent-adapter-streaming-factory`

主要任务：

- Task 1：定义 shared adapter contract。
- Task 2：添加 factory registry。
- Task 3：添加 provider normalizers。
- Task 4：实现 Claude/Codex CLI streaming adapters。
- Task 5：集成 backend orchestrator。
- Task 6：集成 SSE/frontend streaming。
- Task 7：verification、docs、GSD sync、commit。

### 3.3 执行顺序

实际执行顺序：

1. 创建并推送 `agent_adapter` 分支。
2. 编写 adapter 类型、factory、mock adapter。
3. 编写 Claude/Codex normalizer。
4. 编写 Claude/Codex CLI adapter。
5. 用测试 fake subprocess 覆盖 provider adapter。
6. 真实调用 Claude Code，修正 `--verbose` 要求。
7. 真实调用 Codex，修正 Windows executable 解析和 `item.completed` 输出形状。
8. 更新 adapter 技术文档。
9. 归档 ai-collab session/archive/spec/summary。
10. 将 backend user-message path 接入 orchestrator。
11. 将 SSE 改为 named events。
12. 将前端 Dashboard 和 Vuex 接入 streaming events。
13. 用 mock adapter 完成 localhost smoke。
14. 更新 GSD plan/summary/state。
15. 提交并推送。

### 3.4 验证

后端：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python -m unittest discover tests
```

结果：

```text
19 tests passing
```

编译检查：

```powershell
python -m compileall app\adapters app\services app\controllers app\schemas
```

前端：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
npm run build -- --no-clean
```

结果：

- build 通过。
- 存在 asset size warning，属于当前已有体积提示，不阻塞本轮功能。

localhost：

- backend health：200
- frontend：200
- SSE stream：收到 named events
- DB messages：用户消息和 agent 消息均存在

### 3.5 已推送提交

关键提交：

- `4dd020d feat: add streaming agent adapters`
- `8f0ca8c fix: harden cli streaming adapters`
- `034ea0c fix: support real codex streaming output`
- `d17a1bf feat: route orchestrator through agent adapters`
- `0dddf76 feat: stream adapter events to frontend`

### 3.6 后续建议

下一阶段建议先写 runtime event surface spec，再继续实现：

- 统一 hook/MCP/plan mode/permission/session/background/sub-agent/interactive choice 事件。
- 明确哪些事件展示在聊天气泡，哪些展示在日志/工具调用面板。
- 设计 Claude/Codex interactive choice 的 continuation 协议。
- 与 sandbox/workspace 层对齐 `workspace_path` 的来源和隔离策略。
- 再决定是否把 raw event 持久化到数据库，用于审计和复盘。
