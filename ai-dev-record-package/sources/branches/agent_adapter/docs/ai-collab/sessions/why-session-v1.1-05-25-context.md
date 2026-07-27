# Session: Conversation Context System 与多轮验收

版本：v1.1  
日期：2026-05-25

## 1. 基本信息

- Session 名称：Conversation Context System 与多轮验收
- 日期：2026-05-25
- 参与人类成员：why
- 参与 AI 角色：Codex
- 对应负责人：why
- 对应任务方向：factory 兼容 Codex + Claude Code gateway
- 本次记录范围：记录从 adapter “一轮游”问题确认，到 WeAgent-owned conversation context 的 GSD Phase 2 规划、TDD 实现、debug、全链路多轮验收和文档沉淀。

## 2. 本轮背景与初始判断

本轮开始时，Claude/Codex adapter 已经能通过 factory 和 orchestrator 被调用，也能把消息流通过 SSE 送到前端。

why 进一步确认了一个核心问题：如果用户在前端同一个 conversation 中继续提问，Claude/Codex 是否能像本地对话一样记住上一轮读过什么文件、说过什么内容。

初始判断为：

- 原有 adapter 只把最新用户输入作为 `AgentRequest.prompt`。
- `AgentRequest.conversation_history` 字段虽存在，但未被填充和使用。
- 当前行为更接近每轮新开 CLI 调用，因此属于“一轮游”。
- 不应把完整 native Claude/Codex runtime parity 纳入本阶段，应聚焦 WeAgent 自己拥有的 conversation context。

## 3. 讨论过程

- 【问题】why 指出目标不是“小补丁”，而是希望前端同一个对话能持续拥有上下文。
- 【边界修正】why 进一步澄清：本阶段专注上下文，不做完整本地 Claude/Codex runtime 复刻。
- 【GSD 规划】建立 Phase 2：`Conversation Context System`，补充 ROADMAP、REQUIREMENTS、CONTEXT、PLAN。
- 【TDD】先写失败测试，覆盖：
  - bounded transcript loading
  - artifact context recording
  - orchestrator prompt assembly
  - 第二轮 prompt 包含第一轮上下文
- 【实现】新增 `ConversationContextService`，由 orchestrator 在调用 adapter 前构造 provider-neutral prompt。
- 【debug】首次 API 级多轮验收失败，原因不是上下文逻辑，而是 conversation 创建时 `participant_ids` 传了裸 agent id。
- 【修正】改为传 `agent_<agent_id>` 后，全链路多轮验收通过。
- 【文档】新增 report 记录阶段功能、debug 过程、文件变更和 merge 建议。
- 【git 策略】此前 `docs/ai-collab/` 被忽略，本轮按 why 要求准备将 ai-collab 入 git。

## 4. 当前收敛结果

本轮结束时收敛到以下结果：

- WeAgent 已具备 conversation-scoped context 注入能力。
- 同一 conversation 第二轮调用会包含上一轮 user/agent transcript。
- 默认上下文窗口为 20 条消息。
- `artifact.created` 且含 `storagePath` 的事件会被记录为 file/artifact context。
- Claude/Codex adapter 仍保持统一入口 `adapter.stream(AgentRequest)`。
- provider adapter 不直接查询数据库。
- 全链路 API 验收通过：
  - 4 条消息
  - 2 条 agent 回复
  - 第二轮包含第一轮 marker、`docs/spec.md`、context section 和当前用户消息。

## 5. 未解决问题 / 后续建议

- 当前上下文系统不是 Claude/Codex 原生 session resume。
- 如果 CLI provider 不暴露文件读取路径，WeAgent 无法结构化记录“读过哪个文件”。
- interactive choices、后台任务、hook/MCP/plan mode 仍需后续阶段设计。
- merge 回 main 时应特别注意 `docs/ai-collab/`，避免删除 zby 已有归档。

## 6. 可沉淀结果

- 是否值得升级为 `Archive`：是。本轮形成了稳定的上下文边界、debug 结论、TDD 实现方式和 merge 注意事项。
- 可升级为 `Spec`：可在后续把 conversation context contract 独立为 spec。
- 可升级为 `Skill`：暂不升级，当前更像项目能力而非 AI 角色定义。
- 可升级为 `Rules`：可沉淀规则：上下文连续性优先由 WeAgent 管理，不把 provider-native session 作为 MVP 前提。
