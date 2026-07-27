# B. 后端 API 与实时通信层方案

> 摘要：后端 API 层使用 Python + FastAPI，负责承接前端请求、管理会话和消息、创建 run、查询 Agent 和 Artifact，并提供 SSE 事件入口。它连接前端 Web 层、数据协议层、中台 Orchestrator 和 Artifact 服务，核心接口包括 Conversation API、Message API、Run API、Agent API、Artifact API 和 Event Stream API。

## 1. 模块目标

后端 API 层是 AgentHub 的业务入口，需要把前端的操作转成可持久化、可调度、可查询的业务数据。

核心目标：

- 提供稳定的 REST API。
- 维护 Conversation、Message、AgentProfile、Run、Artifact 等数据。
- 用户发送消息后创建 run，并通知中台调度。
- 提供 SSE endpoint，让前端订阅 AgentEvent。
- 接收中台写回的消息、事件和产物。

## 2. 功能清单

| 功能 | 优先级 | 说明 |
|---|---|---|
| Conversation API | P0 | 会话创建、列表、详情、归档 |
| Message API | P0 | 发送消息、查询历史 |
| Run API | P0 | 创建 run、查询状态、查询事件流地址 |
| Event Stream API | P0 | SSE 推送 AgentEvent |
| Agent API | P0 | 内置 Agent、自建 Agent CRUD |
| Artifact API | P0 | 产物查询、预览、下载 |
| Settings API | P1 | API Key、模型、权限 |
| Deploy API | P1 | 部署状态、导出 |

## 3. 模块边界

后端 API 负责业务数据，不直接执行外部 Agent。真正的 Agent 调度由 [D Orchestrator](./D_orchestrator.md) 和 [E Agent Adapter](./E_agent_adapter.md) 执行。

后端可以调用中台，也可以被中台写回：

- 前端请求后端创建 run。
- 中台读取或订阅 run。
- 中台把事件、消息和产物写回后端。
- 后端把事件通过 SSE 推给前端。

## 4. 相连模块

| 相连模块 | 连接方式 | 说明 |
|---|---|---|
| [A 前端 Web](./A_frontend_web.md) | REST API、SSE | 前端创建会话、发送消息、订阅事件 |
| [C 数据协议](./C_data_protocol.md) | Pydantic schema、SQL model | 统一数据结构 |
| [D Orchestrator](./D_orchestrator.md) | Run service、internal API | 创建 run 后交给中台调度 |
| [G Artifact](./G_artifact_preview.md) | Artifact API | 查询和预览产物 |

## 5. 推荐目录

```text
services/api/
  app/
    main.py
    routers/
      conversations.py
      messages.py
      runs.py
      agents.py
      artifacts.py
      settings.py
    services/
      conversation_service.py
      message_service.py
      run_service.py
      event_service.py
      agent_service.py
      artifact_service.py
    schemas/
      conversation.py
      message.py
      run.py
      agent.py
      artifact.py
      event.py
    db/
      database.py
      models.py
      migrations/
```

## 6. 核心接口

### 6.1 Conversation API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/conversations` | 获取会话列表 |
| `POST` | `/api/conversations` | 创建会话 |
| `GET` | `/api/conversations/{id}` | 获取会话详情 |
| `PATCH` | `/api/conversations/{id}` | 修改标题、置顶、归档 |

### 6.2 Message API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/conversations/{id}/messages` | 查询消息历史 |
| `POST` | `/api/conversations/{id}/messages` | 发送用户消息并创建 run |

### 6.3 Run API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/runs/{runId}` | 查询 run 状态 |
| `GET` | `/api/runs/{runId}/events` | SSE 事件流 |
| `POST` | `/api/runs/{runId}/cancel` | P1，取消任务 |

### 6.4 Agent API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/agents` | Agent 列表 |
| `POST` | `/api/agents` | 创建自建 Agent |
| `PATCH` | `/api/agents/{id}` | 修改 Agent |
| `DELETE` | `/api/agents/{id}` | 禁用或删除 Agent |

### 6.5 Artifact API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/conversations/{id}/artifacts` | 查询会话产物 |
| `GET` | `/api/artifacts/{artifactId}` | 查询产物详情 |
| `GET` | `/api/artifacts/{artifactId}/content` | 读取产物内容 |
| `GET` | `/api/artifacts/{artifactId}/download` | 下载产物 |

## 7. 发送消息流程

```text
1. 前端 POST /api/conversations/{id}/messages
2. 后端写入用户消息
3. 后端创建 run，状态为 pending
4. 后端通知中台调度层
5. 后端返回 messageId、runId、eventStreamUrl
6. 前端用 eventStreamUrl 建立 EventSource
7. 中台推送事件，后端 SSE 转发给前端
8. 后端持续落库事件和最终消息
```

## 8. SSE 设计

SSE endpoint：

```http
GET /api/runs/{runId}/events
```

示例：

```text
event: message.delta
data: {"type":"message.delta","runId":"run_001","agentId":"codex","text":"正在创建项目结构"}

event: artifact.created
data: {"type":"artifact.created","runId":"run_001","agentId":"codex","artifact":{"id":"art_001","type":"code","title":"App.vue"}}
```

## 9. P0 / P1 / P2 范围

| 等级 | 内容 |
|---|---|
| P0 | Conversation、Message、Run、Agent、Artifact、SSE |
| P1 | Settings、Deploy、Cancel Run、日志查询 |
| P2 | 企业权限、多租户、审计后台 |

## 10. 风险与降级方案

| 风险 | 降级 |
|---|---|
| 后端和中台边界混乱 | 保持后端只做业务 API，中台只做调度和事件 |
| SSE 状态管理复杂 | 先用内存队列，后续再换 Redis pub/sub |
| 数据库迁移来不及 | SQLite 单库完成 Demo，文档说明 Postgres 迁移 |

## 11. 验收标准

- 前端可以创建会话并查询列表。
- 发送消息后返回 `runId` 和 `eventStreamUrl`。
- 前端可以订阅 SSE 并收到事件。
- 中台可以写回事件、消息和产物。
- 刷新后消息历史仍可查询。

## 12. 相关链接

- [A 前端 Web 层](./A_frontend_web.md)
- [C 数据与协议层](./C_data_protocol.md)
- [D Orchestrator 编排层](./D_orchestrator.md)
- [API 附录](../appendices/api_reference.md)

