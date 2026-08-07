# 事件协议附录

本文档定义 AgentHub 中台推送给前端、写回后端的统一事件协议。所有 Codex、Claude Code、Mock 等 Agent 输出都必须先归一化为 `AgentEvent`。

## 1. SSE 格式

```text
event: <event_type>
data: <json_payload>
```

示例：

```text
event: message.delta
data: {"schemaVersion":"v1","type":"message.delta","runId":"run_001","agentId":"codex","text":"正在创建项目结构..."}
```

## 2. 基础字段

| 字段 | 说明 |
|---|---|
| `schemaVersion` | 协议版本，MVP 默认为 `v1` |
| `type` | 事件类型 |
| `runId` | 本次执行 ID |
| `agentId` | 产生事件的 Agent ID |
| `timestamp` | 事件时间，推荐 ISO 字符串 |

## 3. 事件类型

### run.started

```json
{
  "schemaVersion": "v1",
  "type": "run.started",
  "runId": "run_001",
  "conversationId": "conv_001"
}
```

### agent.started

```json
{
  "schemaVersion": "v1",
  "type": "agent.started",
  "runId": "run_001",
  "agentId": "codex"
}
```

### message.delta

```json
{
  "schemaVersion": "v1",
  "type": "message.delta",
  "runId": "run_001",
  "agentId": "codex",
  "text": "正在创建项目结构..."
}
```

### message.completed

```json
{
  "schemaVersion": "v1",
  "type": "message.completed",
  "runId": "run_001",
  "agentId": "codex",
  "finalText": "Todo 页面已生成。"
}
```

### tool.started

```json
{
  "schemaVersion": "v1",
  "type": "tool.started",
  "runId": "run_001",
  "agentId": "codex",
  "toolName": "write_file",
  "input": {
    "path": "src/App.vue"
  }
}
```

### tool.completed

```json
{
  "schemaVersion": "v1",
  "type": "tool.completed",
  "runId": "run_001",
  "agentId": "codex",
  "toolName": "write_file",
  "output": {
    "path": "src/App.vue"
  }
}
```

### artifact.created

```json
{
  "schemaVersion": "v1",
  "type": "artifact.created",
  "runId": "run_001",
  "agentId": "codex",
  "artifact": {
    "id": "art_001",
    "type": "code",
    "title": "App.vue",
    "previewUrl": "/api/artifacts/art_001/content",
    "language": "vue"
  }
}
```

### agent.failed

```json
{
  "schemaVersion": "v1",
  "type": "agent.failed",
  "runId": "run_001",
  "agentId": "claude-code",
  "error": "Adapter unavailable"
}
```

### run.completed

```json
{
  "schemaVersion": "v1",
  "type": "run.completed",
  "runId": "run_001",
  "summary": "已完成 Todo 页面实现和检查。"
}
```

## 4. 前端消费规则

| 事件 | 前端行为 |
|---|---|
| `run.started` | 显示 run 状态 |
| `agent.started` | 标记 Agent running |
| `message.delta` | 追加到 streaming 气泡 |
| `message.completed` | 标记气泡完成 |
| `tool.started` | 显示工具调用状态 |
| `tool.completed` | 标记工具完成 |
| `artifact.created` | 添加 ArtifactCard |
| `agent.failed` | 显示错误气泡 |
| `run.completed` | 显示汇总结果 |

