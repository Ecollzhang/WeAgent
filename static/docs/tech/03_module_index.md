# 模块索引

本文档列出 AgentHub 的所有模块、模块职责、上下游连接和详细方案链接。每个模块都按可封装、可链接、可验收的方式撰写。

## 1. 模块总表

| 编号 | 模块 | 摘要 | 详细方案 |
|---|---|---|---|
| A | 前端 Web 层 | Vue IM 交互界面，负责会话、消息、Agent 联系人、产物卡片和实时事件展示 | [A_frontend_web.md](./modules/A_frontend_web.md) |
| B | 后端 API 与实时通信层 | Python FastAPI 服务，负责 REST API、消息落库、run 创建、SSE 入口和业务查询 | [B_backend_api_realtime.md](./modules/B_backend_api_realtime.md) |
| C | 数据与协议层 | 定义 Conversation、Message、Run、AgentEvent、Artifact 等统一数据模型 | [C_data_protocol.md](./modules/C_data_protocol.md) |
| D | Orchestrator 编排层 | 中台核心调度器，负责意图理解、任务拆分、Agent 分派、结果聚合 | [D_orchestrator.md](./modules/D_orchestrator.md) |
| E | Agent Adapter 层 | 统一接入 Codex、Claude Code、Mock，将 raw output 转成 AgentEvent | [E_agent_adapter.md](./modules/E_agent_adapter.md) |
| F | Runtime 与 Sandbox 层 | 为每个会话准备 workspace，约束 Agent 文件访问和命令执行 | [F_runtime_sandbox.md](./modules/F_runtime_sandbox.md) |
| G | Artifact 产物层 | 管理代码、网页、文件、部署状态等产物的生成、存储、预览和导出 | [G_artifact_preview.md](./modules/G_artifact_preview.md) |
| H | 交付与工程化层 | 管理测试、日志、Demo、文档、部署和 12 天交付节奏 | [H_delivery_engineering.md](./modules/H_delivery_engineering.md) |
| I | AI 协作规则层 | 沉淀 Spec、rules、skills、AI 协作开发记录，应对 30% AI 协作评分 | [I_ai_collaboration_rules.md](./modules/I_ai_collaboration_rules.md) |

## 2. 模块连接矩阵

| 模块 | 直接连接模块 | 核心接口 |
|---|---|---|
| A 前端 Web | B、C、G | REST API、SSE、Artifact URL |
| B 后端 API | A、C、D、G | REST API、service call、DB model |
| C 数据协议 | A、B、D、E、G | TypeScript types、Pydantic schemas、SQL schema |
| D Orchestrator | B、C、E、F、G | OrchestratorPlan、AgentTask、AgentEvent |
| E Agent Adapter | C、D、F | AgentAdapter interface、AsyncIterable AgentEvent |
| F Runtime Sandbox | D、E、G | Workspace API、permission policy、file ops |
| G Artifact | A、B、C、F | ArtifactRef、preview_url、artifact.created |
| H 工程化 | 全部模块 | test plan、demo script、logs、fallback checklist |
| I AI 协作 | 全部模块 | Spec template、rules template、skill template、collaboration log |

## 3. P0 模块闭环

P0 演示必须跑通以下闭环：

```text
A 前端聊天界面
 -> B 后端消息 API
 -> D 中台 Orchestrator
 -> E Codex / Claude Code / Mock Adapter
 -> C AgentEvent 协议
 -> B SSE 推送
 -> A 消息流展示
 -> G 产物卡片展示
```

## 4. 附录链接

| 附录 | 作用 |
|---|---|
| [api_reference.md](./appendices/api_reference.md) | REST API 汇总 |
| [event_protocol_reference.md](./appendices/event_protocol_reference.md) | AgentEvent 和 SSE 协议 |
| [database_schema.md](./appendices/database_schema.md) | 数据库表结构 |
| [demo_script.md](./appendices/demo_script.md) | 3 分钟 Demo 脚本 |
| [risk_and_fallback.md](./appendices/risk_and_fallback.md) | 风险与兜底方案 |

