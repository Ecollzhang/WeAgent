# E. Agent Adapter 层方案

> 摘要：Agent Adapter 层负责把 Codex、Claude Code、OpenCode 或 Mock 等不同 Agent 平台接入 AgentHub，并把它们各自的 raw output 归一化成统一的 `AgentEvent`。它连接 Orchestrator、Runtime、数据协议和外部 Agent，核心接口是 `AgentAdapter.sendMessage()`、`AsyncIterable<AgentEvent>` 和 Event Normalizer。

## 1. 模块目标

Adapter 层的目标不是简单调用外部工具，而是屏蔽不同 Agent 的 API 和输出差异，让上层 Orchestrator 只面对统一接口。

核心目标：

- 至少接入 Codex 和 Claude Code。
- 提供 Mock Adapter 作为演示兜底。
- 支持流式读取 Agent 输出。
- 将 raw output 转成 AgentEvent。
- 识别工具调用、文本增量、错误和产物。
- 支持健康检查和失败降级。

## 2. 功能清单

| 功能 | 优先级 | 说明 |
|---|---|---|
| Adapter Gateway | P0 | 统一管理不同 Agent Adapter |
| Codex Adapter | P0 | 通过 Codex CLI 或可用执行方式接入 |
| Claude Code Adapter | P0 | 通过 SDK 或 CLI stream-json 接入 |
| Mock Adapter | P0 | 本地模拟流式事件，保证 Demo |
| Event Normalizer | P0 | raw output 转 AgentEvent |
| Artifact Collector | P0 | 识别 workspace 中的产物 |
| Health Check | P1 | 检查外部 Agent 是否可用 |
| OpenCode Adapter | P2 | 作为扩展 Agent |

## 3. 模块边界

Adapter 只负责“接入和归一化”，不负责聊天 UI、不负责数据库持久化、不负责复杂任务拆分。

输入：

- Orchestrator 下发的 AgentTask。
- Runtime 提供的 workspace path。
- 会话上下文和用户目标。

输出：

- 标准 AgentEvent 流。
- Agent 退出状态。
- 产物引用或产物扫描结果。

## 4. 相连模块

| 相连模块 | 连接方式 | 说明 |
|---|---|---|
| [D Orchestrator](./D_orchestrator.md) | Adapter Gateway | 接收 AgentTask，返回事件流 |
| [C 数据协议](./C_data_protocol.md) | AgentEvent、ArtifactRef | 输出统一协议 |
| [F Runtime](./F_runtime_sandbox.md) | workspace path | 在隔离目录中运行 Agent |
| [G Artifact](./G_artifact_preview.md) | Artifact Collector | 收集代码、网页、文件 |

## 5. 统一接口

```ts
interface AgentAdapter {
  id: string;
  provider: 'codex' | 'claude-code' | 'mock' | 'opencode';

  startSession(input: StartSessionInput): Promise<AgentSession>;

  sendMessage(input: SendMessageInput): AsyncIterable<AgentEvent>;

  cancel(sessionId: string): Promise<void>;

  collectArtifacts(sessionId: string): Promise<ArtifactRef[]>;

  healthCheck(): Promise<AdapterHealth>;
}
```

## 6. Codex Adapter

推荐思路：

```bash
codex exec \
  --cd <workspace_path> \
  --json \
  --sandbox workspace-write \
  "<user_prompt>"
```

Python 读取方式：

```py
process = subprocess.Popen(
    [
        "codex",
        "exec",
        "--cd",
        workspace_path,
        "--json",
        "--sandbox",
        "workspace-write",
        prompt,
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

for line in process.stdout:
    raw_event = parse_json_or_raw_log(line)
    yield normalize_codex_event(raw_event)
```

需要处理：

- CLI 不存在。
- JSONL 格式变化。
- stderr 输出。
- exit code 非 0。
- 文件产物识别。

## 7. Claude Code Adapter

优先路线：SDK 流式读取。

备用路线：CLI stream-json。

```bash
claude -p \
  --output-format stream-json \
  --verbose \
  --include-partial-messages \
  --permission-mode plan \
  "<user_prompt>"
```

需要处理：

- SDK 不可用时切换 CLI。
- CLI 不可用时切换 Mock。
- partial message 转 `message.delta`。
- tool use 转 `tool.started` 和 `tool.completed`。

## 8. Mock Adapter

Mock Adapter 必须保留，因为它是演示兜底。

Mock 行为：

```text
1. 发送 agent.started
2. 分段发送 message.delta
3. 在 workspace 写入一个示例文件
4. 发送 artifact.created
5. 发送 message.completed
```

Mock 不只是测试用，它也是 Demo 风险控制。

## 9. Event Normalizer

归一化规则：

| 原始事件 | AgentEvent |
|---|---|
| 文本增量 | `message.delta` |
| 完整回复 | `message.completed` |
| 工具开始 | `tool.started` |
| 工具完成 | `tool.completed` |
| 文件创建 | `artifact.created` |
| 进程失败 | `agent.failed` |

## 10. P0 / P1 / P2 范围

| 等级 | 内容 |
|---|---|
| P0 | Codex、Claude Code、Mock、Event Normalizer、基础产物识别 |
| P1 | Adapter 健康检查、取消任务、stderr 展示 |
| P2 | OpenCode、更多 Agent、可配置 Adapter 插件 |

## 11. 风险与降级方案

| 风险 | 降级 |
|---|---|
| Codex CLI 参数变化 | 包装在 adapter 内，失败时切 Mock |
| Claude SDK 不稳定 | 备用 CLI stream-json |
| 流式事件格式难统一 | 先统一文本、工具、产物、错误四类 |
| Agent 调用慢 | 前端展示运行状态和日志事件 |

## 12. 验收标准

- Orchestrator 可以用同一接口调用 Codex、Claude Code、Mock。
- 至少一个真实 Agent 能产生流式输出。
- Mock Adapter 能完整跑通 Demo 主链路。
- Adapter 输出的事件都符合 AgentEvent。
- Agent 失败时前端能看到错误消息，而不是无响应。

## 13. 相关链接

- [D Orchestrator 编排层](./D_orchestrator.md)
- [F Runtime 与 Sandbox 层](./F_runtime_sandbox.md)
- [事件协议附录](../appendices/event_protocol_reference.md)
