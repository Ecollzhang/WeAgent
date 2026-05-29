# 沙箱 Agent 与多底层 Adapter 融合方案

更新时间：2026-05-27

## 1. 结论

队友引入的 Adapter/Context 代码不应该直接替换现有沙箱链路。

现有代码的主链路是：

- 会话对应一个 Docker sandbox container。
- container 内每个 Agent 有独立工作目录。
- Claude Code 在 container 内运行。
- Agent 通过 `claude -c` 恢复 Claude Code 自身上下文。
- `weagent-report`、stdout/stderr、文件写入事件进入后端，形成 `raw_output`、`elements`、`meta.events`。
- 前端展示实时输出、进度、结果、表格、文件、图片、代码和工作目录产物。

队友代码的主链路是：

- 用 `AgentAdapterFactory` 统一 Claude/Codex/OpenCode/Mock 的底层调用。
- 用 `AgentRequest` 统一传入 prompt、conversation_id、agent_id、workspace_path。
- 用 normalizer 把不同 provider 输出转成统一事件：`message.delta`、`message.completed`、`tool.started`、`artifact.created` 等。
- 用 `conversation_context_service` 从数据库消息中构造 WeAgent 自己的 prompt 上下文。

这两套代码的正确融合方式是：

1. 保留现有 sandbox container 作为默认运行时。
2. 保留 container 内 Claude Code 的 `claude -c` 会话恢复，不能用外部 prompt 拼接上下文替代。
3. 引入 Adapter 抽象，但把它下沉为“provider 执行层”，而不是让它绕过 sandbox。
4. `conversation_context_service` 只能作为可选补充上下文，不能默认注入到 Claude Code 的每轮 prompt。
5. 统一事件协议可以吸收，但必须映射到现有 `sandbox_event_bridge` 的 `elements/meta.events/raw_output` 存储模型。

## 2. 当前两套实现的边界

### 2.1 现有沙箱链路必须保留的能力

这些能力是当前产品核心，不允许被合并覆盖：

- 一个会话对应一个容器。
- 一个会话内多个 Agent 共享同一个 `/workspace`。
- 每个 Agent 有自己的 `/workspace/agents/<workspace_name>`。
- 支持 `/workspace/shared` 公共目录。
- 支持前端查看 Agent 工作目录、预览/下载文件、预览 HTML、访问容器内服务端口。
- 支持 `weagent-report` 上报 `progress/result/table/file/image/code`。
- 支持 Claude Code stdout/stderr 真实流式输出。
- 支持停止 Agent 时保留停止前已经产生的输出和产物。
- 支持消息刷新后从数据库恢复 `raw_output`、`result`、`elements`、产物卡片。
- 支持 Claude Code 继续上下文：container 内 `agent.py` 根据 `.weagent_claude_session` 使用 `claude -c`。

### 2.2 队友 Adapter 代码可以保留的能力

这些能力适合作为底层 provider 抽象合入：

- `AgentAdapterFactory`
- `BaseAgentAdapter.stream(request)`
- `AgentRequest`
- `MockAdapter`
- `CodexAdapter`
- `ClaudeAdapter` 的事件 normalizer 思路
- `normalize_codex_event`
- `normalize_claude_event`
- 统一事件类型：
  - `agent.started`
  - `agent.status`
  - `message.delta`
  - `message.completed`
  - `tool.started`
  - `tool.completed`
  - `artifact.created`
  - `agent.failed`

但需要调整运行位置和职责：

- 不要让 host 侧 `orchestrator_service` 直接调用本机 `claude`/`codex` 来完成会话任务。
- Provider adapter 应优先在 container 内执行，或被 container runtime 调用。
- Host 侧 adapter 只能用于开发调试、非沙箱模式或未来单独的 local runtime，不能成为默认会话执行路径。

## 3. 核心冲突点

### 3.1 上下文冲突

现有方案：

- Claude Code 自己维护会话。
- 第二轮开始使用 `claude -c` 继续上下文。
- `.weagent_claude_session` 只是 WeAgent 的继续标记。
- 这类上下文包括 Claude Code 对工具调用、文件修改、历史推理状态的内部记录。

队友方案：

- `conversation_context_service` 从数据库取最近消息。
- 拼成文本 prompt：
  - `## Agent Instructions`
  - `## Conversation Context`
  - `## File and Artifact Context`
  - `## Current User Message`

冲突风险：

- 如果每次都把数据库历史完整塞给 Claude Code，同时又使用 `claude -c`，会造成重复上下文。
- Agent 可能反复看到旧任务，导致重复生成、重复上报、重复产物。
- Claude Code 的真实 session 记忆和 WeAgent 拼接记忆可能不一致。
- 上下文变长后更容易超时、跑偏、覆盖已有文件。

融合原则：

- 默认：sandbox Claude Agent 使用 `claude -c`，不使用 `conversation_context_service.format_prompt()`。
- 可选：只在以下情况注入 WeAgent 上下文：
  - 新 Agent 刚加入会话，没有 Claude Code session。
  - `claude -c` 失败并降级为新会话。
  - 用户明确要求“参考某个 Agent 的产物/公共目录文件”。
  - 非 Claude provider，例如 Codex/OpenCode 没有等价的 session continuation。
- 注入时必须是“摘要级上下文”，不能把完整历史 raw output 全塞进去。

建议新增策略字段：

```python
context_policy = "provider_session" | "weagent_summary" | "hybrid_on_resume_failure" | "none"
```

默认值：

- Claude sandbox：`provider_session`
- Codex sandbox：`weagent_summary`
- Mock：`none`
- 非沙箱 local adapter：`weagent_summary`

### 3.2 运行时冲突

现有方案：

- `message_service` 通过 `get_manager().send_message(session_id, agent_id, message)` 调 container。
- container 内 `server.py -> orchestrator.py -> agent.py` 执行 Claude Code。

队友方案：

- `orchestrator_service` 通过 `AgentAdapterFactory.create(agent.adapter_name)` 在后端进程里直接启动 adapter。
- `ClaudeAdapter`/`CodexAdapter` 在 host 上用 subprocess 调 CLI。

冲突风险：

- 绕过容器后，Agent 工作目录、公共目录、文件预览、端口服务都失效。
- Host 上 CLI 配置和 container 内 CLI 配置不一致。
- 产物不会进入 `/workspace`，前端看不到。
- `sandbox_event_bridge` 收不到完整事件，消息持久化链路断掉。

融合原则：

- 当前产品默认入口仍然是 `message_service -> sandbox manager -> container`。
- `orchestrator_service` 不能替代 `message_service` 的 sandbox dispatch。
- Adapter 抽象应该下沉到 container 内，作为 `agent.py` 的 provider 执行器。

目标结构：

```text
frontend
  -> backend message_service
    -> sandbox host manager/client
      -> container server/orchestrator
        -> AgentRuntime
          -> ProviderAdapter(claude/codex/opencode/mock)
            -> CLI/API
```

### 3.3 事件协议冲突

现有方案：

- container 推事件：
  - `claude_output_delta`
  - `claude_error_delta`
  - `claude_output`
  - `agent_progress`
  - `agent_report_element`
  - `file_write`
  - `agent_task_completed`
  - `claude_stopped`
  - `error`
- `sandbox_event_bridge` 映射成：
  - `raw_output`
  - `elements`
  - `meta.events`
  - socket events

队友方案：

- Adapter 推标准事件：
  - `message.delta`
  - `message.completed`
  - `tool.started`
  - `tool.completed`
  - `artifact.created`
  - `agent.failed`

融合原则：

- 可以采纳 `schemaVersion=v1` 事件命名，但必须在后端保留一个兼容映射层。
- 前端不应该同时消费两套实时入口，避免重复消息。
- 短期内以现有 socket 事件为主，SSE `/messages/stream/<conversation_id>` 不作为主路径。

建议映射表：

| Adapter 标准事件 | 沙箱事件 | 消息存储 |
|---|---|---|
| `agent.started` | `claude_started` / `agent_started` | progress element |
| `message.delta` | `claude_output_delta` | append `raw_output` |
| `message.completed` | `claude_output` / `agent_task_completed` | result/text element |
| `tool.started` | `agent_progress` | progress element |
| `tool.completed` | `agent_progress` | progress element |
| `artifact.created` | `file_write` 或 `agent_report_element(file/image/code)` | artifact element |
| `agent.failed` | `error` | error status + error element |
| `agent.status` | `agent_progress` | replaceable progress |

### 3.4 前端冲突

现有前端已经围绕这些 socket 事件工作：

- `conversation_message_created`
- `conversation_message_delta`
- `conversation_message_element_stream`
- `conversation_message_step`
- `conversation_message_status`

队友代码里 `message_controller.py` 提供 SSE stream，并支持 `schemaVersion=v1` 的 named SSE event。

融合原则：

- 短期不要启用第二套 SSE 消费。
- 前端主路径继续使用 socket。
- 如果未来改 SSE，必须先完成一次整体替换：
  - created/status/delta/element/step 都走 SSE；
  - socket 停止推消息；
  - store 层保留同一套 mutation。

## 4. 推荐合并步骤

### 阶段 1：只合入低风险基础结构

可以合入：

- `backend/app/adapters/factory.py`
- `backend/app/adapters/types.py`
- `backend/app/adapters/normalizers.py`
- `backend/app/adapters/mock_adapter.py`
- adapter 单元测试
- `agent_schema.py` 中 `adapter_name` 支持 `claude/codex/opencode/mock`
- `AgentEditForm` 中底层模型选择 UI

暂缓合入或禁用：

- `orchestrator_service.py` 直接调用 host adapter 的逻辑。
- `message_controller.py` SSE 主链路。
- `conversation_context_service.format_prompt()` 默认接入现有 sandbox Claude 流程。

验收：

- 现有创建 sandbox 会话、发送消息、Claude Code 输出、产物展示不变。
- Agent 配置里能保存 `adapter_name`。
- 不启动 host 侧 Claude/Codex subprocess。

### 阶段 2：定义统一 Runtime 接口，但不改变默认行为

新增内部接口：

```python
class AgentRuntime:
    def stream(self, request):
        yield event
```

实现两个 runtime：

- `SandboxRuntime`：默认，调用现有 sandbox manager。
- `LocalAdapterRuntime`：开发/测试用，调用队友的 `AgentAdapterFactory`。

路由策略：

```text
conversation.sandbox_session_id 存在 -> SandboxRuntime
conversation.sandbox_session_id 不存在且显式 local 模式 -> LocalAdapterRuntime
```

注意：

- 不允许因为 `agent.adapter_name == "claude"` 就绕过 sandbox。
- `adapter_name` 表示 provider，不表示运行位置。

### 阶段 3：把 provider adapter 下沉到 container

目标：

- container 内 Agent 根据 `adapter_name` 选择 Claude/Codex/OpenCode。
- Claude provider 继续使用当前 `claude -c` 机制。
- Codex provider 使用 Codex 自己的连续上下文方案；如果没有，则使用 `weagent_summary`。

建议 container 内抽象：

```text
container/agent.py
  Agent
    -> ProviderRunner
      -> ClaudeCodeRunner
      -> CodexRunner
      -> MockRunner
```

保留现有 `weagent-report`、事件推送、文件监听、工作目录策略。

### 阶段 4：统一事件模型

新增一个事件转换模块：

```text
provider event -> sandbox event -> message element
```

或者：

```text
provider event -> canonical event -> sandbox_event_bridge
```

但数据库最终仍然保存：

- `raw_output`
- `elements`
- `meta.events`
- `status`
- `agent_run`

不要只保存 `raw_output`，否则刷新后表格/文件/结果会丢。

### 阶段 5：谨慎引入 WeAgent 上下文服务

`conversation_context_service` 的最终定位：

- 为没有 provider session 的 adapter 提供上下文。
- 为新加入 Agent 提供摘要。
- 为主持 Agent 分派任务提供团队和历史摘要。
- 为跨 Agent 协作提供“其他 Agent 产物摘要”。

它不应该：

- 默认替换 Claude `-c`。
- 每轮把完整 raw output 注入给 Claude。
- 把所有历史文件内容塞进 prompt。

## 5. 具体文件处理建议

### 5.1 建议直接保留

- `backend/app/adapters/factory.py`
- `backend/app/adapters/types.py`
- `backend/app/adapters/normalizers.py`
- `backend/app/adapters/mock_adapter.py`
- `backend/tests/test_adapter_factory.py`
- `backend/tests/test_adapter_normalizers.py`
- `backend/tests/test_mock_streaming_adapter.py`

### 5.2 建议保留但改造

- `backend/app/adapters/claude_adapter.py`
  - 保留 normalizer 和 stream-json 解析。
  - 标注为 local/dev adapter。
  - 不作为 sandbox 会话默认 Claude 执行器。

- `backend/app/adapters/codex_adapter.py`
  - 保留 Codex JSONL 解析能力。
  - 后续迁移到 container 内 Codex runner。

- `backend/app/services/conversation_context_service.py`
  - 保留，但新增 context policy。
  - 默认不接入 Claude sandbox。

- `backend/app/services/orchestrator_service.py`
  - 不能直接替换现有 `message_service`。
  - 可以拆出“provider runtime 实验路径”。
  - 如果保留，必须避免后台线程直接调用 host CLI 影响生产会话。

- `backend/app/controllers/message_controller.py`
  - SSE 可保留为实验接口。
  - 前端主路径仍走 socket，避免双推。

- `frontend/src/store/modules/message.js`
  - 可以保留 element 去重和 streaming 临时消息逻辑。
  - 但要避免 socket 消息和 SSE 消息同时写入同一会话。

### 5.3 合并时必须人工检查

- `backend/app/services/message_service.py`
  - 当前文件已有多 Agent sandbox 分派逻辑。
  - 不要被 `orchestrator_service.dispatch_to_agents()` 替代。
  - 检查是否存在重复定义的 `_dispatch_multi_agent_round`，需要保留最终正确版本。

- `backend/app/sandbox/container/agent.py`
  - 必须保留 `claude -c` 逻辑。
  - 必须保留 stdout/stderr chunk 推送。
  - 必须保留 `.weagent_claude_session` 标记和失败降级重试。

- `backend/app/services/sandbox_event_bridge.py`
  - 必须保留 `flag_modified(message, "elements")` 和 `flag_modified(message, "meta")`。
  - 否则 JSON 字段更新不会可靠落库。

- `frontend/src/views/Dashboard.vue`
  - 必须保留工作目录、HTML 预览、文件下载、服务预览入口。
  - 不要引入第二套重复消息刷新/流式消费。

## 6. 最小可行融合方案

第一版建议只做这些：

1. 合入 Adapter 基础文件和测试。
2. Agent 模型保留 `adapter_name`。
3. 创建 sandbox session 时，把每个 Agent 的 `adapter_name` 传进 container agent config。
4. container 里暂时只支持 `adapter_name == "claude"`，其他 provider 返回明确错误：

```text
当前 sandbox runtime 暂未启用 codex/opencode provider，请切换 Claude 或等待 provider runner 接入。
```

5. 不接入 `conversation_context_service` 到 Claude sandbox。
6. 保留前端适配器选择 UI，但对未支持 provider 做禁用或提示。

这样可以先把数据结构打通，不破坏现有功能。

## 7. 后续完整融合方案

完整融合后，推荐架构是：

```text
Agent 配置
  - adapter_name: claude | codex | opencode | mock
  - runtime: sandbox | local
  - context_policy: provider_session | weagent_summary | hybrid_on_resume_failure | none

MessageService
  - 负责创建 Message / AgentRun
  - 负责选择 Runtime
  - 默认选择 SandboxRuntime

SandboxRuntime
  - 调用 sandbox manager
  - 保证产物在 /workspace
  - 保证事件进入 sandbox_event_bridge

Container Agent
  - 根据 adapter_name 选择 ProviderRunner
  - ClaudeCodeRunner 使用 claude -c
  - CodexRunner 使用 codex CLI/API
  - 所有 runner 输出统一事件

SandboxEventBridge
  - 统一落库 raw_output/elements/meta.events
  - 统一推送 socket

Frontend
  - 只消费一种实时协议
  - 展示 progress/result/raw/artifacts
```

## 8. 验收测试清单

合并后必须逐项测：

### 8.1 不破坏现有 Claude sandbox

- 创建单 Agent 会话成功。
- 创建多 Agent 会话成功。
- 发送“你好”，Claude 有真实回复。
- 连续问两轮，第二轮能基于第一轮回答继续，不丢上下文。
- 查看 container 日志，第二轮使用了 `claude -c`。
- 停止 Agent 后，停止前 raw output 和产物仍展示。

### 8.2 不破坏多 Agent 分派

- 给主持 Agent 发任务。
- 主持 Agent 返回分派说明。
- worker 只做自己分配的任务。
- 文档 Agent 不写前端代码，前端 Agent 不写文档主体。
- 私有目录和 shared 目录不重复生成同一份产物，除非 prompt 明确要求共享。

### 8.3 不破坏产物持久化

- `weagent-report` 上报 table，前端实时显示。
- 刷新页面后 table 仍显示为卡片。
- `file/image/code/result` 刷新后仍显示。
- 数据库消息返回的 `elements` 包含产物，不只依赖 `meta.events`。

### 8.4 不破坏文件预览

- Agent 目录入口可打开。
- shared 目录入口可打开。
- HTML 文件可以预览，CSS/JS 正常加载。
- 图片可预览和下载。
- 文本/代码文件可预览。

### 8.5 Adapter 基础测试

- `MockAdapter` 单元测试通过。
- `normalize_claude_event` 测试通过。
- `normalize_codex_event` 测试通过。
- `AgentAdapterFactory` 注册和创建测试通过。

### 8.6 禁止双通道重复消息

- 前端不要同时启用 socket 和 SSE 消费同一轮消息。
- 切换会话再回来，raw output 不重复追加。
- 刷新页面，result/artifacts 不丢。

## 9. 推荐合并顺序

1. 先提交或暂存当前你自己的沙箱修复，确保有回滚点。
2. 合入 Adapter 基础结构，不接管执行链路。
3. 跑 adapter 单元测试。
4. 跑现有 sandbox 创建会话和 Claude 任务测试。
5. 把 `adapter_name` 传入 sandbox agent config，但 container 内仍默认 Claude。
6. 增加 provider 不支持提示，避免 Codex/OpenCode 被误选后静默失败。
7. 再做 Codex container runner。
8. 最后再考虑统一 SSE/socket，不能提前混用。

## 10. 明确禁止的合并方式

不要这样合并：

- 不要让 `orchestrator_service` 直接替代 `message_service` 的 sandbox dispatch。
- 不要让 host 侧 `ClaudeAdapter` 直接处理正常会话。
- 不要默认用 `conversation_context_service` 替代 `claude -c`。
- 不要把完整历史 raw output 每轮拼进 Claude prompt。
- 不要同时让 socket 和 SSE 给前端推同一轮消息。
- 不要只保存 `raw_output` 而不保存 `elements`。
- 不要绕过 `/workspace` 生成产物。

## 11. 最终建议

这次合并应该采用“先承认两层架构”的方式：

- 你现有代码是 runtime/sandbox 层，负责真实执行、隔离、产物、预览、上下文恢复。
- 队友代码是 provider adapter 层，负责统一 Claude/Codex/OpenCode 的底层事件格式。

正确方向不是二选一，而是：

```text
sandbox runtime 保持不变
provider adapter 被 sandbox runtime 调用
conversation context 作为补充策略
message elements/meta/raw_output 继续作为唯一持久化展示模型
```

这样合并后，既不会破坏现有 Claude Code `-c` 记忆和产物展示，也能为后续接入 Codex/OpenCode 留出清晰扩展点。
