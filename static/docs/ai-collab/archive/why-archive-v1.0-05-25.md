# Archive Template

版本 ：v1.0
更新时间：2026.5.25

## 1. 归档信息

- 归档名称：Adapter 阶段完成状态与 Mock/真实 Adapter 边界归档
- 归档日期：2026-05-25
- 归档人：why
- 对应 session：`docs/ai-collab/sessions/why-session-v1.1-05-25.md`
- 对应 session 记录范围：Task 5/6/7 完成确认、GSD 状态同步、前端测试报告保存，以及 mock adapter 与 Claude/Codex adapter 的区别。

## 2. 归档原因

本次对话触发归档的原因：

- 本轮完成了 adapter phase 的状态收口，需要留下可追溯记录。
- why 明确发现 GSD checkbox 与实际实现状态不一致，因此本轮修复具有流程层面的复用价值。
- mock adapter 与真实 Claude/Codex adapter 的区别会影响后续测试、demo、报告和验收口径，需要长期保留。

## 3. 对话主题

本轮对话主要主题为：

完成 adapter-only verification、docs/GSD sync、commit 的最终确认，并沉淀 mock adapter 与 Claude/Codex adapter 的职责边界。

## 4. 归档提炼

从原始对话中提炼出的有效内容：

- Task 完成不能只看代码和测试，也必须检查 GSD plan checkbox、STATE、summary 和 git 状态是否一致。
- Task 5 的完成定义：
  - backend 用户消息路径已经进入 orchestrator。
  - orchestrator 通过 `AgentAdapterFactory.create(agent.adapter_name)` 创建 adapter。
  - adapter stream events 会被 broadcast。
  - `message.delta` 被累积。
  - `message.completed` 后保存最终 agent message。
- Task 6 的完成定义：
  - SSE 对 normalized agent events 使用 named events。
  - 前端 EventSource 监听 `agent.started`、`message.delta`、`message.completed`、`agent.failed`。
  - Vuex 能创建和更新临时流式 agent message。
  - persisted DB message 到达后能避免重复显示。
- Task 7 的完成定义：
  - 后端测试通过。
  - 后端 compileall 通过。
  - 前端 build 通过。
  - docs/GSD sync 完成。
  - commit/push 完成。
- Mock adapter 的定位：
  - 本地假 agent。
  - 稳定、快速、确定性输出。
  - 用于前端联调、SSE 验证、demo 和 smoke。
  - 不代表真实模型能力。
- Claude/Codex adapter 的定位：
  - 真实启动本机 Claude Code / Codex CLI。
  - 会在 `workspace_path` 指定目录执行。
  - 读取真实 JSON/JSONL stream 并 normalizer 成 `AgentEvent`。
  - 受 CLI 登录、权限、网络、MCP/hook 配置和运行时间影响。
- 当前能力边界：
  - normalized message stream 已经端到端完成。
  - runtime event surface 尚未完成。
  - hook、MCP、plan mode、permission、interactive choice、background/sub-agent 等状态还需要后续设计。

## 5. 已形成成果

本次归档已经形成的成果包括：

- GSD phase state 已同步为 completed。
- `01-01-PLAN.md` 中 Task 5/6/7 均已勾选。
- `01-01-SUMMARY.md` 补充了 Task 5/6/7 completion status。
- `docs/report/agent-adapter-frontend-test-and-gsd-report.md` 已形成前端测试与实现链路报告。
- 最新阶段提交已推送：
  - `0dddf76 feat: stream adapter events to frontend`
  - `07b6e90 docs: add adapter frontend test report`
  - `b645e35 docs: mark adapter phase complete`

## 6. 后续去向

本次归档内容后续应落入：

- `spec/`：runtime event surface spec。
- `skills/`：暂不升级。
- `rules/`：建议后续补充“前端 smoke 优先 mock，真实能力验收单独标注 provider”的规则。
- `summaries/`：本轮可作为 05-25 阶段收口总结的来源。
- 仅保留在归档记录中：具体提交列表和本轮 GSD checkbox 修正过程。

## 7. 备注

本阶段的准确表述应为：

> WeAgent 已完成 Claude/Codex/Mock normalized message stream 的 adapter、orchestrator、SSE、frontend 端到端链路；尚未完成完整 runtime event surface。

这句话后续用于报告、演示和对外说明时应保持一致，避免把当前能力夸大为“完全适配 Claude/Codex 所有运行时功能”。
