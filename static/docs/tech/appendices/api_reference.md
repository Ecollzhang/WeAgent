# API 附录

本文档汇总 AgentHub MVP 的 REST API 和 SSE 接口。详细业务说明见 [B 后端 API 与实时通信层](../modules/B_backend_api_realtime.md)。

## 1. Conversation API

### 获取会话列表

```http
GET /api/conversations
```

返回：

```json
{
  "items": [
    {
      "id": "conv_001",
      "title": "Todo 网页开发",
      "mode": "group",
      "agentIds": ["codex", "claude-code"],
      "updatedAt": "2026-05-22T10:00:00Z"
    }
  ]
}
```

### 创建会话

```http
POST /api/conversations
```

请求：

```json
{
  "title": "Todo 网页开发",
  "mode": "group",
  "agentIds": ["codex", "claude-code"]
}
```

返回：

```json
{
  "id": "conv_001",
  "title": "Todo 网页开发",
  "mode": "group",
  "agentIds": ["codex", "claude-code"]
}
```

## 2. Message API

### 查询消息历史

```http
GET /api/conversations/{conversationId}/messages
```

### 发送消息

```http
POST /api/conversations/{conversationId}/messages
```

请求：

```json
{
  "content": "@codex @claude-code 帮我做一个 Todo 网页",
  "mentionedAgentIds": ["codex", "claude-code"]
}
```

返回：

```json
{
  "messageId": "msg_001",
  "runId": "run_001",
  "eventStreamUrl": "/api/runs/run_001/events"
}
```

## 3. Run API

### 查询 Run

```http
GET /api/runs/{runId}
```

返回：

```json
{
  "id": "run_001",
  "conversationId": "conv_001",
  "status": "running",
  "startedAt": "2026-05-22T10:01:00Z"
}
```

### 监听 Run 事件

```http
GET /api/runs/{runId}/events
```

返回类型：`text/event-stream`。

## 4. Agent API

### 获取 Agent 列表

```http
GET /api/agents
```

### 创建自建 Agent

```http
POST /api/agents
```

请求：

```json
{
  "name": "前端检查员",
  "provider": "custom",
  "description": "检查 Vue 组件结构和样式问题",
  "capabilities": ["frontend", "review"],
  "systemPrompt": "你是一个前端代码审查 Agent。",
  "tools": ["read_file"],
  "permissions": {
    "canReadWorkspace": true,
    "canWriteWorkspace": false,
    "canRunShell": false,
    "canDeploy": false
  }
}
```

## 5. Artifact API

### 查询会话产物

```http
GET /api/conversations/{conversationId}/artifacts
```

### 查询产物详情

```http
GET /api/artifacts/{artifactId}
```

### 读取产物内容

```http
GET /api/artifacts/{artifactId}/content
```

### 下载产物

```http
GET /api/artifacts/{artifactId}/download
```

## 6. 错误格式

统一错误响应：

```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Run does not exist",
    "details": {}
  }
}
```

常见错误码：

| 错误码 | 说明 |
|---|---|
| `CONVERSATION_NOT_FOUND` | 会话不存在 |
| `AGENT_NOT_FOUND` | Agent 不存在 |
| `RUN_NOT_FOUND` | Run 不存在 |
| `ARTIFACT_NOT_FOUND` | 产物不存在 |
| `ADAPTER_UNAVAILABLE` | Agent Adapter 不可用 |
| `WORKSPACE_ACCESS_DENIED` | workspace 访问被拒绝 |

