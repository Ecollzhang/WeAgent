# D. Orchestrator 编排层方案

> 摘要：Orchestrator 是中台调度层的核心，负责理解用户消息、识别 @Agent、拆解任务、选择 Agent、调度 Adapter、收集结果并汇总回复。它连接后端 Run、数据协议、Agent Adapter、Runtime 和 Artifact 服务，核心接口是 `OrchestratorPlan`、`AgentTask` 和标准 `AgentEvent`。

## 1. 模块目标

Orchestrator 解决群聊模式下“多个 Agent 如何协作”的问题。它本身不直接写代码，而是作为主 Agent 或调度器安排子 Agent 执行任务。

核心目标：

- 判断用户是否显式 @ 了 Agent。
- 如果用户没有指定 Agent，则根据能力标签自动选择。
- 将复杂任务拆成可执行步骤。
- 调用一个或多个 Agent Adapter。
- 收集各 Agent 输出和产物。
- 汇总成最终回复。
- 处理失败、超时和降级。

## 2. 功能清单

| 功能 | 优先级 | 说明 |
|---|---|---|
| @Agent 识别 | P0 | 从用户消息中提取 mentionedAgentIds |
| 任务计划 | P0 | 生成 OrchestratorPlan |
| 顺序调度 | P0 | 按计划依次调用 Agent |
| 结果聚合 | P0 | 汇总各 Agent 输出 |
| 失败降级 | P0 | 单个 Agent 失败时使用 Mock 或跳过 |
| 有限并发 | P1 | 多 Agent 并发执行 |
| 人工确认 | P1 | 危险操作前请求用户确认 |
| LangGraph 升级 | P2 | 正式工作流编排 |

## 3. 模块边界

Orchestrator 不直接处理 UI，不直接写数据库表，不直接解析 Codex 或 Claude 的原始输出。

它只做：

- 规划。
- 调度。
- 聚合。
- 生成标准事件。

Adapter 原始事件解析属于 [E Agent Adapter](./E_agent_adapter.md)。文件隔离属于 [F Runtime](./F_runtime_sandbox.md)。产物识别和预览属于 [G Artifact](./G_artifact_preview.md)。

## 4. 相连模块

| 相连模块 | 连接方式 | 说明 |
|---|---|---|
| [B 后端 API](./B_backend_api_realtime.md) | Run service | 获取 run，写回状态 |
| [C 数据协议](./C_data_protocol.md) | OrchestratorPlan、AgentEvent | 使用统一结构 |
| [E Agent Adapter](./E_agent_adapter.md) | AgentAdapter | 调用 Codex、Claude Code、Mock |
| [F Runtime](./F_runtime_sandbox.md) | Workspace API | 为 Agent 提供工作区 |
| [G Artifact](./G_artifact_preview.md) | Artifact service | 收集产物 |

## 5. 核心流程

```text
run.created
 -> load_conversation_context
 -> analyze_intent
 -> build_plan
 -> route_agents
 -> execute_agent_tasks
 -> collect_artifacts
 -> summarize_result
 -> run.completed
```

## 6. OrchestratorPlan

```ts
type OrchestratorPlan = {
  id: string;
  runId: string;
  userGoal: string;
  mode: 'direct_mention' | 'auto_plan';
  steps: AgentTask[];
};

type AgentTask = {
  id: string;
  title: string;
  assignedAgentId: string;
  input: string;
  dependsOn?: string[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
};
```

## 7. 调度策略

### 7.1 direct_mention

用户显式 @Agent 时，优先尊重用户选择。

示例：

```text
@codex @claude-code 帮我做一个 Todo 页面，一个负责实现，一个负责检查
```

计划：

```text
1. codex 实现 Todo 页面
2. claude-code 审查结构和可运行性
3. orchestrator 汇总结果
```

### 7.2 auto_plan

用户没有 @Agent 时，根据能力标签选择 Agent。

示例：

```text
帮我做一个带筛选功能的 Todo 网页
```

默认选择：

- `codex`：代码生成。
- `claude-code`：方案检查和修复建议。
- `mock`：当真实 Agent 不可用时兜底。

## 8. 实现方案

MVP 使用手写轻量状态机：

```text
PlanningState
 -> RoutingState
 -> RunningState
 -> CollectingState
 -> SummarizingState
 -> CompletedState
```

这样做的原因：

- 实现快。
- Debug 简单。
- 答辩容易解释。
- 失败点可控。

LangGraph 作为 P2 升级路线，不影响 MVP。

## 9. P0 / P1 / P2 范围

| 等级 | 内容 |
|---|---|
| P0 | @Agent 识别、顺序调度、结果聚合、失败降级 |
| P1 | 有限并发、人工确认、取消任务 |
| P2 | LangGraph、复杂依赖图、长期记忆、代码冲突合并 |

## 10. 风险与降级方案

| 风险 | 降级 |
|---|---|
| 多 Agent 并发导致调试复杂 | P0 使用顺序调度 |
| Agent 输出质量不稳定 | Orchestrator 最后生成汇总说明和下一步建议 |
| 真实 Agent 不可用 | 使用 Mock Adapter 撑住演示 |
| 拆任务质量不足 | direct_mention 优先，让用户显式指定 Agent |

## 11. 验收标准

- 用户 @ 两个 Agent 后，Orchestrator 能生成两个 AgentTask。
- 能按顺序调用两个 Adapter。
- 每个 Agent 的输出都能变成前端可见事件。
- 一个 Agent 失败时，run 不直接崩溃，而是给出降级说明。
- 最终有一条汇总回复。

## 12. 相关链接

- [E Agent Adapter 层](./E_agent_adapter.md)
- [F Runtime 与 Sandbox 层](./F_runtime_sandbox.md)
- [事件协议附录](../appendices/event_protocol_reference.md)

