# AgentHub 技术方案文档

本文档是 AgentHub 多 Agent 协作平台的技术方案总入口。原命题以 `AgentHub- 多Agent协作平台设计-feishu.pdf` 为最高优先级，其他研究报告和草案只作为参考材料。

AgentHub 的核心形态是一个 IM 聊天式多 Agent 协作平台。用户通过新建对话、选择 Agent、发送消息、群聊 @Agent 的方式，让 Claude Code、Codex、OpenCode 或自建 Agent 协作完成网页、Workflow、代码、文档等产物。系统需要同时支持聊天体验、Agent 调度、流式输出、产物预览、上下文连续和 AI 协作规范沉淀。

## 推荐阅读路径

1. 先读 [总规则文件](./00_agenthub_rules.md)，明确方案边界、技术栈和文档规则。
2. 再读 [原命题拆解与 MVP 范围](./01_problem_scope.md)，确认哪些是 P0，哪些是 P1/P2。
3. 然后读 [总体架构方案](./02_architecture_overview.md)，理解前端、后端、中台和 Agent 的关系。
4. 开发或答辩时使用 [模块索引](./03_module_index.md)，按模块跳转到对应方案。

## 文档结构

| 文件 | 作用 |
|---|---|
| [00_agenthub_rules.md](./00_agenthub_rules.md) | 总规则文件，约束技术选型、模块写法、AI 协作沉淀和验收口径 |
| [01_problem_scope.md](./01_problem_scope.md) | 原命题拆解、MVP 范围、P0/P1/P2 分层 |
| [02_architecture_overview.md](./02_architecture_overview.md) | 总体架构、主链路、技术栈、核心数据流 |
| [03_module_index.md](./03_module_index.md) | 全部模块功能清单、模块链接、上下游关系 |
| [modules/](./modules/) | 每个模块的详细解决方案 |
| [appendices/](./appendices/) | API、事件协议、数据库、Demo 脚本、风险兜底等附录 |

## 技术栈总览

| 层级 | 技术选择 | 说明 |
|---|---|---|
| 前端 | Vue 3 + Vite + TypeScript | 承载 IM 聊天、Agent 联系人、产物预览和可视化状态 |
| 后端 | Python + FastAPI | 承载 REST API、数据模型、持久化、文件访问和基础业务服务 |
| 中台 | Python 调度中台 | 承载 Orchestrator、Agent Adapter、事件归一化、SSE 推送和运行时管理 |
| 数据库 | SQLite 开发期，Postgres 正式化 | 先保证 12 天内可复现，后续具备迁移空间 |
| 实时通信 | SSE 优先，WebSocket 预留 | MVP 优先解决 Agent 流式输出 |
| Agent 接入 | Codex + Claude Code + Mock Adapter | 至少接入两个主流 Agent，Mock 作为 Demo 兜底 |
| 产物展示 | Monaco Editor + iframe + 文件卡片 | 支持代码、网页、文件三类核心产物 |

## 核心交付目标

- 一个可运行的 Web Demo。
- 一套可解释的技术架构。
- 一套可复现的模块接口和协议。
- 一套可答辩的风险与降级方案。
- 一套 AI 协作开发规范，包括 Spec、rules、skills、开发记录。

