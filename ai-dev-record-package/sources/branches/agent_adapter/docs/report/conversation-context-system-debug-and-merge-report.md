# Conversation Context System Debug and Merge Report

日期：2026-05-25  
负责人：why  
分支：`agent_adapter`  
实现提交：`11ab486 feat: add conversation context system`  
文档类型：Explanation + How-to

## 1. 阶段目标

本阶段目标是让 WeAgent 的同一个 conversation 具备可持续上下文能力。

用户期望是：

- 第 1 轮让 agent 读某个文件或讨论某个主题。
- 第 2 轮继续在同一个前端对话里提问。
- Claude/Codex/Mock adapter 在下一轮调用时能看到上一轮 conversation transcript 和已记录的 file/artifact context。

本阶段刻意不做以下内容：

- Claude/Codex provider-native session resume。
- interactive choices continuation。
- background agent lifecycle。
- hook、MCP、plan mode 的完整 UI 展示。

也就是说，本阶段实现的是 WeAgent-owned conversation context，不是完整复制本地 Claude Code/Codex 的运行时。

## 2. 当前实现方式

新增的核心链路如下：

```text
/api/messages
  -> message_service.send_message(sender_type='user')
  -> orchestrator_service.dispatch_to_agents(...)
  -> conversation_context_service.build_context(...)
  -> conversation_context_service.format_prompt(...)
  -> AgentAdapterFactory.create(...)
  -> adapter.stream(AgentRequest)
  -> normalized events
  -> SSE broadcast + final message persistence
```

上下文 prompt 会包含固定区块：

```text
## Agent Instructions
## Conversation Context
## File and Artifact Context
## Current User Message
```

默认上下文窗口：

- 最近 20 条同 conversation 消息。
- `artifact.created` 且带 `storagePath` 的事件会记录为 file/artifact context。
- 如果 Claude/Codex CLI 没有吐出文件读取路径，WeAgent 目前不会凭空知道它读了哪个文件。

## 3. Debug 过程与结论

### 3.1 Codex 调用失败

一开始 Codex 在前端和 adapter 手测中失败。直接运行 `codex exec` 也失败，说明问题不在 WeAgent 前端。

关键错误包括：

```text
attempt to write a readonly database
Codex cannot access session files at C:\Users\rt do believe\.codex\sessions
failed to clean up stale arg0 temp dirs: 拒绝访问。 (os error 5)
```

结论：

- 默认 `C:\Users\rt do believe\.codex` 对 Codex sandbox runtime 写权限不稳定。
- 直接 CLI 都失败时，WeAgent adapter 只能透传失败。

修复：

- 支持 `WEAGENT_CODEX_HOME` 指向 E 盘隔离 runtime home。
- Codex adapter 使用 `codex exec --json --ephemeral`。
- Codex adapter 后台读取 stderr，避免 warning 堵塞 stdout JSONL。
- Codex 的可恢复 reconnect 事件映射为 `agent.status`，不再误报 `agent.failed`。

### 3.2 多轮上下文不是 provider native session

确认后发现，原始实现里 `AgentRequest.conversation_history` 虽然存在，但没有填充，也没有被用于 Claude/Codex prompt。

原始行为：

```text
第 1 轮用户消息 -> 新 CLI 调用，只看第 1 句
第 2 轮用户消息 -> 新 CLI 调用，只看第 2 句
```

本阶段修复：

- 在 orchestrator 构造 `AgentRequest` 前加载 conversation context。
- 把 transcript 和 file/artifact context 拼入 provider-neutral prompt。
- adapter 仍只负责执行 `adapter.stream(request)`，不直接查询数据库。

### 3.3 全链路多轮验收

API 级验收流程：

```text
POST /api/auth/register
POST /api/auth/login
POST /api/agents
POST /api/conversations
POST /api/messages  第一轮
GET  /api/messages/conversation/<id>
POST /api/messages  第二轮
GET  /api/messages/conversation/<id>
```

第一次验收脚本失败，原因是创建 conversation 时传了裸 agent id。

实际接口要求：

```text
participant_ids: ["agent_<agent_id>"]
```

修正后验收通过：

```text
message_count: 4
agent_message_count: 2
has_agent_instructions: true
has_conversation_context: true
has_file_context_section: true
has_current_user_section: true
has_first_turn_marker: true
has_first_turn_file_path: true
has_second_turn_message: true
```

## 4. 从原始代码到当前产物改了什么

### 4.1 GSD 与规划文件

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/config.json`
- `.planning/phases/01-agent-adapter-streaming-factory/*`
- `.planning/phases/02-conversation-context-system/*`
- `.planning/todos/pending/2026-05-23-agent-adapter-streaming-factory.md`

作用：

- 建立 GSD 主线。
- Phase 1 记录 adapter streaming factory。
- Phase 2 记录 conversation context system。

### 4.2 Backend adapter 层

- `backend/app/adapters/types.py`
- `backend/app/adapters/factory.py`
- `backend/app/adapters/normalizers.py`
- `backend/app/adapters/mock_adapter.py`
- `backend/app/adapters/claude_adapter.py`
- `backend/app/adapters/codex_adapter.py`
- `backend/app/adapters/base_adapter.py`
- `backend/app/adapters/__init__.py`
- `backend/app/adapters/opencode_adapter.py`

作用：

- 统一 `AgentRequest` / `AgentEvent`。
- 提供 `AgentAdapterFactory`。
- 实现 Claude/Codex/Mock streaming adapter。
- 处理 Codex Windows executable、stderr、`WEAGENT_CODEX_HOME`、`--ephemeral`。
- 将 raw events 归一化为 `message.delta`、`message.completed`、`artifact.created`、`agent.status`、`agent.failed`。

### 4.3 Backend orchestration 和 SSE

- `backend/app/services/message_service.py`
- `backend/app/services/orchestrator_service.py`
- `backend/app/services/conversation_context_service.py`
- `backend/app/controllers/message_controller.py`
- `backend/app/schemas/agent_schema.py`

作用：

- 用户消息触发 orchestrator。
- Orchestrator 通过 factory 调 adapter。
- SSE 支持 named events。
- 新增 conversation context build/format/record。
- `mock` adapter 可通过 API schema 创建。

### 4.4 Frontend streaming 展示

- `frontend/src/views/Dashboard.vue`
- `frontend/src/store/modules/message.js`
- `frontend/src/components/AgentEditForm/index.vue`
- `frontend/vue.config.js`

作用：

- 前端 EventSource 接收 `agent.started`、`message.delta`、`message.completed`、`agent.failed`。
- Vuex 维护 streaming temporary message。
- Agent 表单支持选择 `Mock`。
- Windows 下关闭 Vue CLI parallel worker，避免 `thread-loader spawn EPERM`。

### 4.5 Tests

- `backend/tests/test_adapter_factory.py`
- `backend/tests/test_adapter_normalizers.py`
- `backend/tests/test_cli_streaming_adapters.py`
- `backend/tests/test_mock_streaming_adapter.py`
- `backend/tests/test_orchestrator_adapter_stream.py`
- `backend/tests/test_conversation_context_service.py`
- `backend/tests/test_support.py`

作用：

- 覆盖 factory、normalizer、CLI adapter、mock adapter、orchestrator streaming、conversation context。
- Phase 2 按 TDD 完成，先写失败测试，再实现服务和 orchestration 注入。

### 4.6 Docs

- `docs/report/agent-adapter-frontend-test-and-gsd-report.md`
- `docs/report/conversation-context-system-debug-and-merge-report.md`
- `docs/tech/modules/E_agent_adapter.md`
- `docs/ai-collab/**`

作用：

- 记录前端测试方法。
- 记录 adapter/context 实现方式、debug 结论、验收结果和 merge 建议。
- 记录 AI collaboration session/archive/summary。

### 4.7 Ignore 规则

- `.gitignore`

变化：

- 之前 `docs/ai-collab/` 被忽略，仅本地保存。
- 本阶段按要求移除该 ignore，使 ai-collab 文档进入 git。

## 5. Verification

已执行：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python -m unittest discover tests
```

结果：

```text
Ran 26 tests in 0.433s
OK
```

compile 检查：

- 普通 `compileall` 在 `app/services/__pycache__` 覆盖旧 `.pyc` 时遇到 Windows `PermissionError`。
- 使用隔离 `PYTHONPYCACHEPREFIX` 后通过。
- 验证后已删除临时 `.pycache_verify_phase2`。

后端健康检查：

```text
http://127.0.0.1:5000/api/health -> 200
```

全链路多轮 API 验收：

- 4 条消息。
- 2 条 agent 回复。
- 第二轮 agent 输入包含第一轮 marker、`docs/spec.md`、conversation context 区块和当前用户消息。

## 6. Merge 建议

推荐走 PR 或手动 merge，但不要直接静默 fast-forward 后就结束。

建议步骤：

```powershell
git checkout main
git pull origin main
git merge --no-ff agent_adapter
```

merge 后重点检查：

1. `docs/ai-collab/`
   - 不要删除 zby 已有归档。
   - 保留 why 本轮新增 session/archive/summary。
   - 如果冲突，优先 union merge，不要二选一覆盖。
2. `.gitignore`
   - 确认 `docs/ai-collab/` 不再被忽略。
   - `docs/archive-registry.md` 是否继续忽略，需要团队决定。
3. Backend
   - 运行 `python -m unittest discover tests`。
   - 使用隔离 `PYTHONPYCACHEPREFIX` 跑 compileall，避免旧 pycache 权限问题干扰判断。
4. Frontend
   - 运行 `npm run build -- --no-clean`。
   - 如果 Windows 出现 worker EPERM，确认 `frontend/vue.config.js` 保留 `parallel: false`。
5. Manual smoke
   - 用 Mock adapter 做两轮 conversation context 验收。
   - 再选做 Claude/Codex adapter smoke。

建议 merge 前先保留当前分支最新提交：

```text
11ab486 feat: add conversation context system
```

本次补文档后应再有一个 docs commit，作为 merge 前的最后记录点。

## 7. 仍需注意

- 现在的上下文系统能解决同一 conversation 的 transcript/context continuity。
- 它不等价于 Claude/Codex 原生 session。
- file read context 依赖 provider raw event 暴露路径。
- 当前 testing 后端使用 SQLite memory，重启会清空前端测试数据。
