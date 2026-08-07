# 3 分钟 Demo 脚本

本文档用于录制和现场答辩。目标是在 3 分钟内证明 AgentHub 的 IM 体验、多 Agent 协作、产物预览和 AI 协作沉淀。

## 0:00 - 0:20 开场

说明：

```text
AgentHub 是一个 IM 聊天式多 Agent 协作平台。用户像使用飞书或微信一样创建会话、选择 Agent、发送消息，让多个 AI Agent 协作生成网页、代码和文档产物。
```

展示：

- 左侧会话列表。
- 中间聊天窗口。
- 右侧产物面板。
- Agent 联系人入口。

## 0:20 - 0:50 创建群聊

操作：

1. 点击新建会话。
2. 选择群聊模式。
3. 添加 Codex 和 Claude Code。
4. 创建会话。

讲解：

```text
每个 Agent 都像一个聊天联系人，有名称、头像、能力标签和工具权限。群聊模式下，Orchestrator 会负责协调它们的分工。
```

## 0:50 - 1:30 多 Agent 协作

输入：

```text
@codex @claude-code 帮我做一个 Todo 网页。Codex 负责实现，Claude Code 负责检查结构和可运行性。
```

展示：

- Orchestrator 生成任务计划。
- Codex 开始流式回复。
- Claude Code 接着检查。
- Agent 状态从 running 到 completed。

讲解：

```text
用户消息进入后端后会创建 run，中台 Orchestrator 识别 @Agent 并生成计划，再通过 Adapter Gateway 调用不同 Agent。所有输出都会被归一化为 AgentEvent，通过 SSE 实时推给前端。
```

## 1:30 - 2:10 产物预览

展示：

- 代码卡片。
- 网页预览卡片。
- 文件卡片。

操作：

1. 点击代码卡片，打开 Monaco 预览。
2. 点击网页卡片，打开 iframe 预览。
3. 点击文件卡片，展示下载入口。

讲解：

```text
Agent 的输出不只是文字，还会变成 Artifact。Artifact 与 conversation、run、agent 关联，用户可以直接在聊天流中预览和操作。
```

## 2:10 - 2:35 自建 Agent

操作：

1. 打开 Agent 联系人页。
2. 点击创建 Agent。
3. 展示名称、System Prompt、能力标签、工具权限。

讲解：

```text
除了内置 Codex 和 Claude Code，用户也可以创建自己的 Agent。MVP 中先支持 Prompt、标签和工具权限配置。
```

## 2:35 - 3:00 AI 协作沉淀

展示：

- `specs/`
- `rules/`
- `skills/`
- `docs/ai-collaboration/`

讲解：

```text
本项目不只是用 AI 写代码，还沉淀了 Spec、rules、skills 和协作日志。每个模块都有清晰的目标、接口、验收标准和人工审核记录，用于保证 AI 协作过程可复盘、可解释。
```

## 兜底演示

如果真实 Codex 或 Claude Code 调用失败：

1. 切换 Mock Adapter。
2. 使用同一条用户消息。
3. 展示 Mock 仍可输出流式消息和产物卡片。
4. 说明真实 Adapter 和 Mock 使用同一个 AgentEvent 协议。

