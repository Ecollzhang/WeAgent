# C. 数据与协议层方案

> 摘要：数据与协议层定义 AgentHub 的统一语言。它连接前端、后端、中台、Orchestrator、Adapter 和 Artifact 模块，核心接口是 TypeScript 类型、Pydantic Schema、数据库表结构和 `AgentEvent` 事件协议。该模块的目标是避免每个模块各写一套字段，保证系统可联调、可落库、可答辩。

## 1. 模块目标

数据与协议层需要统一四类结构：

- 业务实体：Conversation、Message、AgentProfile、Run、Artifact。
- 流式事件：AgentEvent。
- 产物引用：ArtifactRef。
- 存储结构：数据库表和 JSON metadata。

## 2. 核心实体

| 实体 | 说明 |
|---|---|
| User | 用户，MVP 可先单用户 |
| Conversation | 会话，包含 single 或 group 模式 |
| Message | 聊天消息，包含用户消息、Agent 消息、系统消息 |
| AgentProfile | Agent 联系人，包括内置 Agent 和自建 Agent |
| Run | 一次用户消息触发的 Agent 调度执行 |
| AgentEvent | 中台推送给前端的统一流式事件 |
| Artifact | 代码、网页、文件、部署等产物 |
| Workspace | 会话级工作区 |
| Deployment | P1，部署或导出记录 |

## 3. 相连模块

| 相连模块 | 使用方式 |
|---|---|
| [A 前端 Web](./A_frontend_web.md) | 使用 TypeScript 类型渲染 UI |
| [B 后端 API](./B_backend_api_realtime.md) | 使用 Pydantic Schema 和 SQL model |
| [D Orchestrator](./D_orchestrator.md) | 使用 Run、OrchestratorPlan、AgentTask |
| [E Agent Adapter](./E_agent_adapter.md) | 输出 AgentEvent |
| [G Artifact](./G_artifact_preview.md) | 使用 ArtifactRef 和 Artifact 表 |

## 4. Conversation

```ts
type Conversation = {
  id: string;
  title: string;
  mode: 'single' | 'group';
  agentIds: string[];
  pinnedMessageIds?: string[];
  createdAt: string;
  updatedAt: string;
  archivedAt?: string | null;
};
```

## 5. Message

```ts
type Message = {
  id: string;
  conversationId: string;
  runId?: string;
  senderType: 'user' | 'agent' | 'system' | 'tool';
  senderId: string;
  content: string;
  status: 'pending' | 'streaming' | 'completed' | 'failed';
  artifacts?: ArtifactRef[];
  metadata?: Record<string, unknown>;
  createdAt: string;
};
```

## 6. AgentProfile

```ts
type AgentProfile = {
  id: string;
  name: string;
  provider: 'codex' | 'claude-code' | 'opencode' | 'mock' | 'custom';
  description: string;
  avatar?: string;
  capabilities: string[];
  systemPrompt: string;
  tools: string[];
  permissions: {
    canReadWorkspace: boolean;
    canWriteWorkspace: boolean;
    canRunShell: boolean;
    canDeploy: boolean;
  };
  enabled: boolean;
};
```

## 7. Run

```ts
type Run = {
  id: string;
  conversationId: string;
  userMessageId: string;
  status: 'pending' | 'planning' | 'running' | 'completed' | 'failed' | 'cancelled';
  orchestratorPlan?: OrchestratorPlan;
  startedAt?: string;
  completedAt?: string;
  error?: string;
};
```

## 8. AgentEvent

`AgentEvent` 是中台、后端和前端之间最重要的协议。

```ts
type AgentEvent =
  | { type: 'run.started'; runId: string; conversationId: string }
  | { type: 'agent.started'; runId: string; agentId: string }
  | { type: 'message.delta'; runId: string; agentId: string; text: string }
  | { type: 'message.completed'; runId: string; agentId: string; finalText: string }
  | { type: 'tool.started'; runId: string; agentId: string; toolName: string; input?: unknown }
  | { type: 'tool.completed'; runId: string; agentId: string; toolName: string; output?: unknown }
  | { type: 'artifact.created'; runId: string; agentId: string; artifact: ArtifactRef }
  | { type: 'agent.failed'; runId: string; agentId: string; error: string }
  | { type: 'run.completed'; runId: string; summary: string }
  | { type: 'run.failed'; runId: string; error: string };
```

## 9. ArtifactRef

```ts
type ArtifactRef = {
  id: string;
  type: 'code' | 'web_preview' | 'file' | 'diff' | 'deployment' | 'text_document';
  title: string;
  url?: string;
  previewUrl?: string;
  language?: string;
  storagePath?: string;
  metadata?: Record<string, unknown>;
};
```

## 10. 数据库表

P0 表：

- `users`
- `conversations`
- `conversation_agents`
- `messages`
- `agent_profiles`
- `runs`
- `agent_events`
- `artifacts`
- `workspaces`

P1 表：

- `deployments`
- `settings`
- `run_logs`

完整表结构见 [数据库附录](../appendices/database_schema.md)。

## 11. 协议版本规则

每个事件 payload 允许带 `schemaVersion`：

```json
{
  "schemaVersion": "v1",
  "type": "message.delta",
  "runId": "run_001",
  "agentId": "codex",
  "text": "正在生成..."
}
```

MVP 可以默认 v1，不做复杂迁移。

## 12. 风险与降级方案

| 风险 | 降级 |
|---|---|
| 字段过多影响开发 | P0 只实现必需字段，metadata_json 容纳扩展 |
| 前后端类型不一致 | 从协议文件生成或复制 TypeScript + Pydantic 双份定义 |
| AgentEvent 类型太多 | P0 限制为 6 类核心事件 |

## 13. 验收标准

- 前端、后端、中台都使用同名字段。
- SSE 事件能被前端无歧义解析。
- 每条 Agent 输出都能追溯到 run、conversation、agent。
- 每个产物都能通过 ArtifactRef 打开或下载。

## 14. 相关链接

- [事件协议附录](../appendices/event_protocol_reference.md)
- [数据库附录](../appendices/database_schema.md)
- [B 后端 API 与实时通信层](./B_backend_api_realtime.md)
- [E Agent Adapter 层](./E_agent_adapter.md)

