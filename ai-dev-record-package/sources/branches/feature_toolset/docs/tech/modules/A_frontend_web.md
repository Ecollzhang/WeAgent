# A. 前端 Web 层方案

> 摘要：前端 Web 层负责把 AgentHub 呈现为一个 IM 聊天产品。它连接后端 API、SSE 事件流和 Artifact 产物服务，核心接口包括 `POST /api/conversations`、`POST /api/conversations/{id}/messages`、`GET /api/runs/{runId}/events` 和 `GET /api/artifacts/{id}`。该模块的重点不是普通管理台，而是会话列表、聊天窗口、@Agent、流式回复、Agent 状态和产物卡片。

## 1. 模块目标

前端需要让用户像使用飞书或微信一样使用 AgentHub：

- 在左侧看到会话列表。
- 新建单聊或群聊会话。
- 在聊天窗口中发送消息。
- 在群聊中 @ 一个或多个 Agent。
- 实时看到 Agent 的流式回复。
- 看到每个 Agent 的运行状态。
- 在聊天流中看到代码、网页、文件等产物卡片。
- 点击产物卡片进入右侧或全屏预览。
- 创建自定义 Agent。

## 2. 功能清单

| 功能 | 优先级 | 说明 |
|---|---|---|
| 会话列表 | P0 | 新建、搜索、置顶、归档、最近活跃排序 |
| 聊天窗口 | P0 | 消息流、用户消息、Agent 消息、系统消息 |
| @Agent 输入 | P0 | 识别 `@codex`、`@claude-code` 等 Agent |
| SSE 消费 | P0 | 接收 `message.delta`、`message.completed`、`artifact.created` |
| Agent 状态 | P0 | 展示 waiting、running、completed、failed |
| 产物卡片 | P0 | 展示 code、web_preview、file |
| Agent 联系人页 | P0 | 展示内置 Agent 和自建 Agent |
| 自建 Agent 表单 | P0 | 名称、描述、Prompt、能力标签、工具权限 |
| 设置页 | P1 | API Key、模型、权限、运行参数 |
| Demo 页面 | P1 | 固定演示会话和演示按钮 |

## 3. 模块边界

前端只负责展示和交互，不直接调用外部 Agent，不直接写数据库，不绕过后端读取 workspace 文件。

前端输入：

- 用户点击和输入。
- 后端 REST API 返回的 JSON。
- 中台通过 SSE 推送的事件。

前端输出：

- REST API 请求。
- 用户选择的 Agent、消息内容、产物操作。
- 前端状态更新和 UI 渲染。

## 4. 相连模块

| 相连模块 | 连接方式 | 说明 |
|---|---|---|
| [B 后端 API](./B_backend_api_realtime.md) | REST API、SSE | 创建会话、发送消息、查询历史、监听事件 |
| [C 数据协议](./C_data_protocol.md) | TypeScript 类型 | 使用 Conversation、Message、AgentEvent、ArtifactRef |
| [G Artifact 产物层](./G_artifact_preview.md) | Artifact API、preview_url | 展示代码、网页、文件卡片 |
| [I AI 协作规则](./I_ai_collaboration_rules.md) | 前端 Spec | 记录前端组件生成和 AI 协作过程 |

## 5. 核心页面

| 页面 | 路由 | 说明 |
|---|---|---|
| 会话主页面 | `/chat/:conversationId` | 核心聊天界面 |
| Agent 联系人页 | `/agents` | 内置 Agent、自建 Agent 列表 |
| 自建 Agent 页 | `/agents/new` | 创建 Agent |
| 产物预览页 | `/artifacts/:artifactId` | 展开代码、网页、文件 |
| 设置页 | `/settings` | P1，模型、权限和 API Key |
| Demo 页 | `/demo` | P1，固定演示路径 |

## 6. 组件结构

```text
apps/web/src/
  layouts/
    AppShell.vue
  pages/
    ChatPage.vue
    AgentListPage.vue
    AgentCreatePage.vue
    ArtifactPreviewPage.vue
    SettingsPage.vue
    DemoPage.vue
  components/
    sidebar/
      ConversationList.vue
      ConversationListItem.vue
    chat/
      ChatWindow.vue
      MessageBubble.vue
      AgentMentionInput.vue
      AgentRunStatus.vue
    artifact/
      ArtifactCard.vue
      ArtifactPanel.vue
      CodeArtifactViewer.vue
      WebPreviewFrame.vue
      FileArtifactViewer.vue
    agent/
      AgentCard.vue
      AgentCreateForm.vue
  stores/
    conversationStore.ts
    messageStore.ts
    agentStore.ts
    artifactStore.ts
  api/
    client.ts
    conversations.ts
    messages.ts
    agents.ts
    artifacts.ts
    events.ts
  types/
    protocol.ts
```

## 7. 状态管理

| Store | 职责 |
|---|---|
| `conversationStore` | 会话列表、当前会话、会话 Agent 成员 |
| `messageStore` | 当前消息列表、流式消息缓冲、runId 到 messageId 映射 |
| `agentStore` | Agent 列表、能力标签、运行状态 |
| `artifactStore` | 当前会话产物、当前展开产物、预览状态 |

流式消息处理规则：

```text
收到 message.delta：
  如果 runId + agentId 已有临时消息，则追加 text
  如果没有，则创建一条 streaming 状态的 Agent 消息

收到 message.completed：
  将对应 streaming 消息标记为 completed

收到 artifact.created：
  添加 ArtifactCard，并关联到当前 run 或 message
```

## 8. 接口与数据结构

### 8.1 创建会话

```http
POST /api/conversations
```

```json
{
  "title": "Todo 网页开发",
  "mode": "group",
  "agentIds": ["codex", "claude-code"]
}
```

### 8.2 发送消息

```http
POST /api/conversations/{conversationId}/messages
```

```json
{
  "content": "@codex @claude-code 帮我做一个 Todo 网页",
  "mentionedAgentIds": ["codex", "claude-code"]
}
```

### 8.3 监听事件

```http
GET /api/runs/{runId}/events
```

前端使用 `EventSource` 消费 SSE。

## 9. 实现方案

1. 使用三栏布局：左侧会话，中间聊天，右侧产物。
2. 使用 Pinia 管理业务状态。
3. API 层封装所有 REST 请求。
4. SSE 层封装 EventSource，并把事件派发到 store。
5. 聊天气泡支持 user、agent、system、tool、artifact、error 六类消息。
6. 产物卡片根据 `ArtifactRef.type` 选择 Monaco、iframe 或文件展示。

## 10. P0 / P1 / P2 范围

| 等级 | 内容 |
|---|---|
| P0 | 会话、聊天、@Agent、SSE、Agent 状态、三类产物卡片、自建 Agent |
| P1 | 设置页、Demo 页、部署状态卡片、任务取消按钮 |
| P2 | 移动端、多人协同、复杂 Diff 操作 |

## 11. 风险与降级方案

| 风险 | 降级 |
|---|---|
| SSE 事件类型太多 | P0 只支持 message.delta、message.completed、artifact.created、agent.failed |
| 产物预览时间不够 | 代码用 Monaco，网页用 iframe，文件只做下载卡片 |
| @Agent 输入复杂 | 先用简单文本解析和下拉选择，不做富文本编辑器 |

## 12. 验收标准

- 可以创建一个新会话。
- 可以选择一个 Agent 单聊。
- 可以在群聊中 @ 两个 Agent。
- 可以看到流式回复逐字或分段出现。
- 可以看到 Agent 运行状态变化。
- 可以点击代码、网页、文件产物卡片。
- 刷新页面后能重新加载会话历史。

## 13. 相关链接

- [B 后端 API 与实时通信层](./B_backend_api_realtime.md)
- [C 数据与协议层](./C_data_protocol.md)
- [G Artifact 产物层](./G_artifact_preview.md)
- [事件协议附录](../appendices/event_protocol_reference.md)

