# Summary: Conversation Context System 阶段复盘

版本：v1.0
更新时间：2026.5.25

## 1. 基本信息

- 总结名称：Conversation Context System 阶段复盘
- 日期：2026-05-25
- 负责人：why
- 覆盖周期：2026-05-25

## 2. 本阶段目标

本阶段主要目标为：

在已完成 Claude/Codex/Mock adapter message stream 接入的基础上，补齐同一个 WeAgent conversation 内的多轮上下文能力，让下一轮 agent 调用能够看到上一轮 transcript、当前用户消息，以及已记录的 file/artifact context。

本阶段明确不把 provider-native session resume、interactive choices、background lifecycle、hook/MCP/plan mode 完整展示纳入范围。

## 3. 关键进展

本阶段已经完成或明确推进的内容：

- 明确原 adapter 链路只能把最新用户输入传给 provider，属于“一轮游”。
- 建立 GSD Phase 2：`Conversation Context System`。
- 按 TDD 增加 conversation context 和 orchestrator prompt 注入测试。
- 新增 `ConversationContextService`，负责读取 bounded transcript、记录 artifact context、组装 provider-neutral prompt。
- 在 orchestrator 调用 adapter 前注入 context，不让 provider adapter 直接查询数据库。
- 修复全链路多轮验收中 `participant_ids` 需要 `agent_<agent_id>` 的使用问题。
- 完成 API 级多轮验收：同一 conversation 第二轮 agent 输入包含第一轮 marker、文件路径、conversation context 区块和当前用户消息。
- 撰写 `docs/report/conversation-context-system-debug-and-merge-report.md`，记录功能、debug、文件变更和 merge 建议。

## 4. AI 协作沉淀

本阶段沉淀出的有效协作经验：

- 先确认目标边界，再实现：why 明确本阶段只关注上下文，不追求完整本地 Claude/Codex runtime parity。
- “上下文连续”应由 WeAgent conversation 层先托底，而不是依赖 provider 原生 session。
- Adapter 保持单一职责：执行统一 `AgentRequest` 并返回 normalized stream；上下文拼装放在 orchestrator/service 层。
- TDD 验收要覆盖 prompt 内容，而不只覆盖数据库是否写入消息。
- API 验收失败时应区分业务链路问题和接口使用问题，本轮失败点是 conversation participant id 格式。

## 5. 已升级的规范

本阶段已经升级形成的内容：

- 新增 `Spec`：暂未新增独立 spec，建议后续补 `conversation-context-contract.md`。
- 新增 `Skill`：暂未新增。
- 新增 `Rules`：暂未新增独立 rules 文件，但形成候选规则：
  - 上下文连续性优先由 WeAgent conversation 管理。
  - Provider-native session resume 不是 MVP 上下文能力的前提。
  - Provider adapter 不直接查数据库。
  - 多轮验收必须检查第二轮 provider prompt 是否包含第一轮 transcript/context。

## 6. 当前问题

本阶段仍存在的问题：

- 当前实现不是 Claude/Codex 原生 session resume。
- 如果 provider raw event 不暴露文件读取路径，WeAgent 不能自动结构化记录“读过哪个文件”。
- interactive choices、后台运行、技能执行、子 agent、hook/MCP/plan mode 仍需后续阶段单独设计。
- 前端侧还需要更完整的多轮验收脚本和可视化验证。

## 7. 下一阶段建议

下一阶段建议重点推进：

- 先形成 runtime event surface / interaction continuation 的 spec。
- 明确 interactive choice 在 SSE、数据库、前端 UI 中的协议。
- 与 sandbox/workspace 层对齐 agent 调用目录、产物路径和权限边界。
- 再做 Claude/Codex 真实 provider 的前台多轮调度验收。
