# AgentHub 总规则文件

本文件定义 AgentHub 技术方案的统一规则。后续所有模块设计、接口定义、开发实现和答辩说明，都以本文件为约束。

## 1. 原命题优先级规则

最高优先级材料是 `AgentHub- 多Agent协作平台设计-feishu.pdf`。如果草案、研究报告或后续讨论与原命题冲突，以原命题为准。

原命题中的必答项包括：

| 必答项 | 方案响应 |
|---|---|
| IM 聊天式交互 | 前端必须以会话列表、聊天窗口、消息流、联系人式 Agent 为核心 |
| 单聊与群聊 | 支持单 Agent 对话，也支持群聊 @ 多 Agent |
| Orchestrator | 群聊模式下必须有主 Agent 协调、拆任务、聚合结果 |
| 多 Agent 接入 | 至少接入两个主流 Agent，默认 Codex + Claude Code |
| 用户自建 Agent | 支持最小版自建 Agent，包含名称、Prompt、工具集、能力标签 |
| 产物内联 | 支持代码、网页预览、文件等产物卡片 |
| 上下文连续 | 会话历史作为 Agent 输入上下文，支持关键消息 pin 作为增强 |
| AI 协作能力 | 沉淀 Spec、skill、rules、AI 协作开发记录 |

## 2. 技术栈规则

本项目技术栈固定为：

```text
前端：Vue 3 + Vite + TypeScript
后端：Python + FastAPI
中台：Python 调度中台，负责调度、推送、归一化和写回
```

三层职责不可混淆：

| 层级 | 核心职责 | 不负责 |
|---|---|---|
| 前端 Vue | 展示聊天体验、Agent 状态、产物预览，消费实时事件 | 不直接调用外部 Agent，不直接写数据库 |
| 后端 Python | 提供 REST API、数据存储、用户会话、产物查询 | 不承载复杂 Agent 调度策略 |
| 中台调度 | Orchestrator、Adapter、事件流、运行时、向前端推送、向后端写回 | 不做复杂 UI，不绕过后端数据模型 |

## 3. MVP 边界规则

12 天内优先完成 P0。P1 可以作为增强，P2 只做方案预留。

| 等级 | 定义 |
|---|---|
| P0 | 不做就无法体现原命题核心能力 |
| P1 | 做了会提升演示效果，但不影响主链路成立 |
| P2 | 正式产品需要，但比赛 MVP 不强求 |

P0 必须包含：

- 会话列表、新建会话、聊天窗口。
- 单聊模式。
- 群聊 @Agent 模式。
- Orchestrator 拆分和聚合。
- Codex Adapter、Claude Code Adapter、Mock Adapter。
- SSE 流式消息展示。
- 代码、网页、文件三类产物卡片。
- 自建 Agent 最小闭环。
- 技术文档、产品文档、AI 协作开发记录、Demo 脚本。

## 4. 默认技术决策规则

除非出现无法实现或严重影响演示的风险，否则默认采用以下决策：

| 方向 | 默认方案 | 原因 |
|---|---|---|
| UI 框架 | Vue 3 + Vite + TypeScript | 开发快，团队已确定 Vue |
| UI 组件库 | Naive UI | Vue 适配好，表单、弹窗、布局完整 |
| 状态管理 | Pinia | 会话、消息、Agent、产物状态边界清晰 |
| 后端框架 | FastAPI | Python 生态好，适合流式接口和 AI SDK |
| 实时推送 | SSE 优先 | 最适合服务端持续推送 Agent token / event |
| 编排方式 | 手写轻量状态机 | 12 天内更可控，便于答辩解释 |
| Agent 接入 | Codex + Claude Code + Mock | 满足双 Agent 接入，保留兜底演示 |
| 存储 | SQLite 开发期，Postgres 正式化 | 开发轻，迁移路径清楚 |
| 工作区 | 会话级本地 workspace | 简单可复现，避免多会话互相污染 |
| 产物 | 本地 artifacts 目录 + 元数据入库 | 便于预览、导出和 Demo |

## 5. 模块文档规则

每个模块文档必须使用同一结构，保证评审和开发都能快速阅读：

```markdown
# 模块名称

> 摘要：说明这个模块做什么、连接哪些模块、主要接口是什么。

## 1. 模块目标
## 2. 功能清单
## 3. 模块边界
## 4. 相连模块
## 5. 核心流程
## 6. 接口与数据结构
## 7. 实现方案
## 8. P0 / P1 / P2 范围
## 9. 风险与降级方案
## 10. 验收标准
## 11. 相关链接
```

模块之间必须通过链接显式连接，不能只写“见上文”。

## 6. 接口规则

前端、后端、中台之间只通过明确协议交互：

| 方向 | 协议 |
|---|---|
| 前端请求后端 | REST API |
| 后端返回结果 | JSON |
| 中台向前端推送 | SSE event stream |
| 中台写回后端 | 内部 Python service 调用或 HTTP API |
| 中台调用 Agent | Adapter 统一接口 |
| Agent 输出到平台 | AgentEvent 统一事件 |

所有流式事件必须归一化为 `AgentEvent`，详见 [事件协议附录](./appendices/event_protocol_reference.md)。

## 7. AI 协作沉淀规则

原命题中“AI 协作能力”权重最高，因此必须显式沉淀：

- `specs/`：功能 Spec、接口 Spec、验收 Spec。
- `rules/`：开发规则、提交规则、Agent 使用规则。
- `skills/`：可复用的 Agent 技能，例如前端生成、Adapter 调试、Demo 脚本生成。
- `docs/ai-collaboration/`：AI 协作开发记录，记录每次让 AI 做了什么、产出什么、人工如何审核。

## 8. 答辩规则

每个技术选择都要能回答四个问题：

1. 为什么这么做。
2. 为什么不选更复杂的方案。
3. 风险是什么。
4. 如果失败如何降级。

答辩中优先讲主链路：

```text
用户发消息
 -> 后端创建 message/run
 -> 中台 Orchestrator 规划任务
 -> Adapter 调用 Agent
 -> AgentEvent 归一化
 -> SSE 推送前端
 -> 产物入库并生成卡片
```

