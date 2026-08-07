# Archive: WeAgent Conversation Context System 归档

版本：v1.0  
日期：2026-05-25

## 1. 归档信息

- 归档名称：WeAgent Conversation Context System 归档
- 归档日期：2026-05-25
- 归档人：why
- 对应 session：`docs/ai-collab/sessions/why-session-v1.1-05-25-context.md`
- 对应 session 记录范围：从“一轮游”问题确认，到 conversation context system 的规划、TDD 实现、debug、多轮验收和 merge 文档沉淀。

## 2. 归档原因

本次对话触发归档的原因：

- 解决了 Claude/Codex adapter 接入后的关键体验问题：同一前端 conversation 的下一轮是否有上下文。
- 明确了上下文能力边界：WeAgent-owned context，不等同 provider-native session resume。
- 形成了可复用的 debug 经验：API 验收失败时先确认 conversation participants 格式。
- 形成了 merge 风险判断：`docs/ai-collab/` 从本地忽略改为入库时，不能删除其他成员既有归档。

## 3. 对话主题

本轮对话主要主题为：

> 在 WeAgent 中实现 conversation-scoped context，让 Claude/Codex/Mock adapters 在同一个对话的下一轮调用中接收到上一轮 transcript 和 file/artifact context。

## 4. 归档提炼

从原始对话中提炼出的有效内容：

- 原始 adapter 系统只完成了 message stream 接入，并不自动具备多轮上下文。
- `AgentRequest.conversation_history` 需要由 orchestrator/context service 填充。
- provider adapter 不应直接查数据库，数据库上下文应在 orchestrator 层之前组装。
- prompt assembly 应该 provider-neutral，避免 Claude/Codex 分别实现一套上下文逻辑。
- 默认上下文窗口定为 20 条消息，避免无限增长。
- file/artifact context 的结构化记录依赖 normalized event 中暴露路径。
- 全链路验收时，conversation API 的 agent participant 需要使用 `agent_<agent_id>` 格式。

## 5. 已形成成果

本次归档已经形成的成果包括：

- `ConversationContextService`
- Orchestrator prompt context injection
- Artifact context recording extension point
- Conversation context TDD tests
- API 级多轮验收记录
- `docs/report/conversation-context-system-debug-and-merge-report.md`
- GSD Phase 2:
  - `.planning/phases/02-conversation-context-system/02-CONTEXT.md`
  - `.planning/phases/02-conversation-context-system/02-01-PLAN.md`
  - `.planning/phases/02-conversation-context-system/02-01-SUMMARY.md`

## 6. 后续去向

本次归档内容后续应落入：

- `spec/`：建议后续形成 `conversation-context-contract.md`。
- `rules/`：建议沉淀“上下文由 WeAgent 管理，不把 provider-native session 当作 MVP 前提”。
- `summaries/`：本轮已补阶段 summary。
- 仅保留在归档记录中：Codex 本机权限 debug 的细节可留在 report/archive，不必升级为通用规则。

## 7. 备注

本轮成果已经能支持“同一 WeAgent conversation 下一轮带上下文”的体验，但仍不代表完整 Claude/Codex runtime event surface。后续若要接近本地 Claude Code/Codex 的强体验，需要继续设计 provider-native resume、interactive choices、tool timeline 和 sandbox/workspace 事件记录。
