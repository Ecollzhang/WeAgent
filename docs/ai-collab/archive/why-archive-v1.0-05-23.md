# Archive

版本：v1.0
更新时间：2026-05-23

## 1. 归档信息

- 归档名称：Agent Adapter Factory 规划与 GSD 执行入口
- 归档日期：2026-05-23
- 归档人：why
- 对应 session：why-session-v1.0-05-23.md
- 对应 session 记录范围：Claude Code / Codex adapter factory 方案调研、GSD 分支与规划建立、计划审阅、下一步 TDD 执行准备

## 2. 归档原因

本轮对话已经形成可复用的阶段性结果：

- 明确了 WeAgent 接入 Claude Code 与 Codex 的 adapter/factory 方向。
- 建立了远程分支 `agent_adapter`。
- 将规划收敛到 GSD 单主体，不再混用 Superpowers。
- 修正了 GSD phase 命名、PLAN 命名和 decision coverage。
- 明确了下一步执行方式：TDD、增量、模块化。

## 3. 对话主题

本轮主题为：

- Factory 模式统一接入 Claude Code 与 Codex。
- Adapter 输出统一为 `AgentEvent` 流。
- GSD 方式建立 requirements、roadmap、context、plan。
- 审阅 Phase 1 PLAN 是否可执行、是否覆盖上下文决策。
- 规划下一步以 TDD 方式进入实现。

## 4. 归档提炼

关键可复用结论：

- MVP 接入策略：
  - Codex：优先使用 `codex exec --json` JSONL 输出。
  - Claude Code：优先使用 `claude -p --output-format stream-json --include-partial-messages`。
  - SDK 接入作为后续增强，不阻塞 MVP。
- Adapter 统一出口：
  - adapter 暴露 `stream(request) -> Iterator[AgentEvent]`。
  - 上层 Orchestrator 和 SSE 不直接消费 provider raw event。
- GSD 主体原则：
  - 本阶段规划文件统一落在 `WeAgent/.planning`。
  - Phase 1 路径为 `.planning/phases/01-agent-adapter-streaming-factory/`。
  - PLAN 文件为 `01-01-PLAN.md`。
- Workspace policy：
  - 优先读取 `AGENT_WORKSPACE_ROOT`。
  - 未配置时回退到当前 `WeAgent` 项目根。
- 审阅发现并补充的关键缺口：
  - 原计划缺少显式 `mock` adapter。
  - 原计划只考虑 Orchestrator，未覆盖 REST `send_message` + SSE 主链路。
  - 前端当前只处理完整消息，必须支持 `message.delta`、`message.completed`、`agent.failed`。
- GSD coverage：
  - `check.decision-coverage-plan` 已通过。
  - 13/13 个 CONTEXT 决策被 PLAN 覆盖。

## 5. 已形成成果

已形成并推送到 `agent_adapter` 的成果：

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/todos/pending/2026-05-23-agent-adapter-streaming-factory.md`
- `.planning/phases/01-agent-adapter-streaming-factory/01-CONTEXT.md`
- `.planning/phases/01-agent-adapter-streaming-factory/01-01-PLAN.md`

对应提交：

- `38b6241 docs: plan agent adapter streaming factory`
- `96f211b docs: align agent adapter plan with gsd`

## 6. 后续去向

下一步应落入：

- GSD execute / TDD 实现流程
  - 从 `.planning/phases/01-agent-adapter-streaming-factory/01-01-PLAN.md` Task 1 开始。
  - 严格遵循 TDD：先写测试，再写最小实现，再验证。
  - 保持增量和模块化，不一次性大改。
- 可考虑后续补充到 `rules/`
  - 本项目规划阶段以 GSD 为主体。
  - 每轮压缩上下文前应写 `session`，有长期复用价值时写 `archive`。

## 7. 备注

压缩上下文后恢复工作时，应优先读取：

1. `.planning/phases/01-agent-adapter-streaming-factory/01-01-PLAN.md`
2. `.planning/phases/01-agent-adapter-streaming-factory/01-CONTEXT.md`
3. `.planning/REQUIREMENTS.md`
4. 本归档文件

恢复后的首要工作不是重新设计，而是进入 TDD 执行：测试优先、模块化实现、小步提交。

