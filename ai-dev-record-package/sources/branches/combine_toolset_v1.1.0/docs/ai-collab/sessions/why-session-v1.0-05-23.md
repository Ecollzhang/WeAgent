# Session

版本：v1.0
更新时间：2026-05-23

## 1. 基本信息

- Session 名称：Agent Adapter Factory 与 GSD 规划收敛
- 日期：2026-05-23
- 参与人类成员：why
- 参与 AI 角色：Codex / Planning Assistant
- 对应负责人：why
- 对应任务方向：factory 兼容 Codex + Claude Code gateway
- 本次记录范围：从方案调研、分支建立、GSD 计划创建，到进入 TDD 实现前的上下文交接

## 2. 本轮背景与初始判断

- 本轮目标是为 WeAgent 统一接入 Claude Code 与 Codex，采用 factory + adapter 的方式支持流式消息发送。
- 仓库已有 `backend/app/adapters` 雏形，但当前接口仍是 `send_prompt() -> str`，不支持统一事件流。
- 需要先建立远端分支 `agent_adapter`，再按 GSD 方式沉淀 todo、requirements、roadmap、context、plan。
- 中途确认 `docs/ai-collab` 不作为本次规划主体；本轮以 GSD 为主体。

## 3. 讨论过程

- 【调研】确认本机已有 `codex-cli 0.128.0` 与 `Claude Code 2.1.148`，因此 MVP 优先采用 CLI 流式接入。
- 【分支】从远端 `main` 快进同步后，创建并推送远程分支 `agent_adapter`。
- 【规划】在 `WeAgent/.planning` 下建立 GSD 结构，包括 PROJECT、REQUIREMENTS、ROADMAP、STATE、todo、Phase 1 CONTEXT 与 PLAN。
- 【纠偏】曾误将文件写入父目录 `agentshub`，随后清理并确认所有规划文件均位于 `WeAgent` 内。
- 【主体选择】确认 GSD 为本阶段唯一主体，不混用 Superpowers。
- 【审阅】使用 GSD review/discuss 思路检查 Phase 1 PLAN，修正 GSD 目录与计划命名：
  - phase 目录：`.planning/phases/01-agent-adapter-streaming-factory/`
  - plan 文件：`01-01-PLAN.md`
- 【补充】发现原计划未覆盖 Mock Adapter、REST/SSE 主链路和前端 `message.delta` 消费，已补入 REQUIREMENTS、ROADMAP、CONTEXT 和 PLAN。
- 【决策】workspace policy 采用：优先读取 `AGENT_WORKSPACE_ROOT`，未配置则回退到当前 `WeAgent` 项目根。
- 【验证】`gsd-sdk query check.decision-coverage-plan` 通过，13/13 个 CONTEXT 决策均被 PLAN 覆盖。

## 4. 当前收敛结果

- 已建立并推送分支：`agent_adapter`
- 最新规划提交：
  - `38b6241 docs: plan agent adapter streaming factory`
  - `96f211b docs: align agent adapter plan with gsd`
- GSD 审阅入口：
  - `.planning/ROADMAP.md`
  - `.planning/REQUIREMENTS.md`
  - `.planning/phases/01-agent-adapter-streaming-factory/01-CONTEXT.md`
  - `.planning/phases/01-agent-adapter-streaming-factory/01-01-PLAN.md`
- 当前未跟踪但不处理的本地文件：`.claude/logs/`
- 当前对话归档要求：按 `docs/ai-collab/archive-schema.md` 进行归档，使用 `why-*` 命名。

## 5. 未解决问题 / 后续建议

- 下一步进入 TDD 模式实现 Phase 1。
- 实现必须保持增量和模块化：先写测试，再写最小实现，每个模块独立验证。
- 推荐执行顺序：
  1. 从 `01-01-PLAN.md` Task 1 开始。
  2. 先为 adapter types / factory / mock stream 写测试。
  3. 再实现 normalizer 与 CLI adapter。
  4. 最后接入 Orchestrator、REST/SSE 和前端 EventSource。
- 每个任务完成后更新 PLAN checkbox，并进行小提交。

## 6. 可沉淀结果

- 是否值得升级为 `Archive`：是
- 可升级为 `Spec`：已有 GSD REQUIREMENTS/CONTEXT/PLAN，暂不另建 spec
- 可升级为 `Skill`：否
- 可升级为 `Rules`：可考虑补充“本项目规划阶段以 GSD 为主体，不混用 Superpowers”的规则

