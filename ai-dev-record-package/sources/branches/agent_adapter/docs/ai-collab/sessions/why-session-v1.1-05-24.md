# Session Template

版本 ：v1.1
更新时间：2026.5.24

## 1. 基本信息

- Session 名称：Claude Code 与 Codex Adapter 流式消息接入验证
- 日期：2026-05-24
- 参与人类成员：why
- 参与 AI 角色：Codex、Claude Code、GSD 执行助手
- 对应负责人：why
- 对应任务方向：factory 兼容 Codex + Claude Code gateway
- 本次记录范围：从 GSD 计划进入最小模块实现后，对 Claude Code 与 Codex adapter 的流式消息接入、真实 CLI 验证、边界确认和后续限制进行记录。

## 2. 本轮背景与初始判断

为什么会有这轮对话，以及开始时的初步理解：

- WeAgent 需要以 factory 模式统一接入 Claude Code 和 Codex，使后续 orchestrator 或 sandbox 层可以通过同一个出口发送任务并接收流式消息。
- why 明确要求本轮按 GSD 方式推进，采用模块化和 TDD，先不要修改前端，尽量不影响当前接口。
- 初始判断是先完成 backend adapter 的最小可用闭环：统一请求结构、统一事件结构、adapter factory、Claude/Codex CLI 适配、测试和真实 smoke 验证。
- `docs/ai-collab` 被定位为本地 AI 协作归档资产，不进入 git；归档文件必须使用 why 命名。

## 3. 讨论过程

按过程记录关键讨论节点，可使用【进展】【问题】【错误探索】【修正】【补充】【收敛】【结论】等标签：

- 【进展】先建立 `agent_adapter` 分支，并基于 GSD 路线创建 adapter 方案和执行计划。
- 【修正】why 指出不应混用 GSD 与 superpower，本轮改为以 GSD 为主体推进。
- 【修正】why 指出所有内容必须创建在 WeAgent 目录中，后续规划、文档、归档均落在 `E:\code for project\seedance-competition\agentshub\WeAgent` 内。
- 【修正】why 指出归档命名应使用 `why-`，不是其他成员名；随后将 ai-collab 归档命名修正为 why。
- 【进展】将 `docs/ai-collab/` 加入 `.gitignore`，保留本地迭代，不再提交到远程。
- 【进展】按 TDD 增量实现 adapter 层：统一 `AgentRequest`、流式事件模型、`AgentAdapterFactory`、`MockAdapter`、Claude/Codex adapter 和 normalizer。
- 【问题】Claude Code 真实调用中发现 `--output-format stream-json` 需要配合 `--verbose`，否则 CLI 会拒绝执行。
- 【修正】Claude adapter 增加 `--verbose`，并使用 UTF-8 decode with replacement 处理 Windows 输出乱码风险。
- 【进展】通过 adapter 调用 Claude Code，成功收到 `message.delta` 和 `message.completed`，证明 Claude 消息流可被统一出口读取。
- 【补充】Claude Code 被要求列举 skills，返回了可读消息；其中出现 `No skills needed` 被确认是正常现象。
- 【问题】why 追问 adapter 是否已经能处理后台运行、技能运行、子 agent、hook 提示、plan mode、MCP 错误等完整功能。
- 【收敛】当前 scope 明确为“读取消息流”，不是完整 runtime 事件兼容；hook、MCP、plan mode、交互选择等提示尚未向上层完整暴露。
- 【进展】文档中补充 adapter 调用位置和 workspace 控制方式：调用方可通过 `AgentRequest.workspace_path` 指定 Claude/Codex 在哪个隔离目录执行。
- 【问题】Codex 真实调用在 Windows 上直接执行 `codex` 出现 `WinError 5`，判断为 shim/可执行文件解析问题。
- 【修正】Codex adapter 在 Windows 上优先解析 `codex.cmd`、`codex.exe`，再退回 `codex`。
- 【问题】Codex 真实 JSONL 输出与预设不完全一致，实际返回 `item.completed` + `item.type=agent_message` + `text`。
- 【修正】Codex normalizer 增加真实输出形态支持，将其映射为统一的 `message.completed`。
- 【结论】Claude Code 与 Codex 当前已经可以通过统一 adapter 接收消息；但只能称为“消息流兼容”，不能称为“所有运行时能力完全适配”。

## 4. 当前收敛结果

本轮结束时暂时收敛到的结果：

- `agent_adapter` 分支已推送到远程。
- adapter 最小模块已完成并推送，主要提交包括：
  - `4dd020d feat: add streaming agent adapters`
  - `8f0ca8c fix: harden cli streaming adapters`
  - `034ea0c fix: support real codex streaming output`
- backend 测试当前为 17 个通过。
- Claude Code adapter 真实调用已验证：可以通过统一 `stream()` 收到流式消息事件。
- Codex adapter 真实调用已验证：可以通过统一 `stream()` 收到 `message.completed`。
- adapter 的执行位置可以由 `AgentRequest.workspace_path` 控制；若不提供，则按 `AGENT_WORKSPACE_ROOT` 和项目根目录兜底。
- 前端和当前业务接口没有在本轮被改动，仍保持最小模块接入。
- `.pycache_verify` 是 Python bytecode/compile cache 类运行产物，已被 `.gitignore` 忽略，不应进入 git。

## 5. 未解决问题 / 后续建议

- 需要设计 runtime event surface，将 Claude/Codex 的 hook、MCP、plan mode、permission、session id、后台任务状态等信息从 raw stream 中映射出来。
- 需要设计可持续交互协议，支持 Claude/Codex 要求用户选择选项时，前端或调用方能接住选项并继续同一轮会话。
- 需要与 zsw 的 sandbox/workspace 层对接，明确 adapter 执行目录、权限模式、隔离策略和文件产物归属。
- 需要后续再接 orchestrator / SSE / 前端消息流，本轮只完成 adapter 层，不做 UI 集成。
- 需要避免把“直接 CLI 诊断结果”和“adapter 调用结果”混为一谈；行为验证应优先通过 adapter。

## 6. 可沉淀结果

本轮是否产生以下内容：

- 是否值得升级为 `Archive`：是。Claude/Codex adapter 的真实接入边界、workspace 控制和未覆盖能力具有后续复用价值。
- 可升级为 `Spec`：部分可升级。后续建议为 runtime event surface、交互选择协议、sandbox 调用协议单独写 spec。
- 可升级为 `Skill`：暂不升级。本轮还不是稳定 AI 角色职责，而是 adapter 工程实现与验证过程。
- 可升级为 `Rules`：部分可升级。建议后续形成规则：真实验证必须走 adapter；raw CLI 只能作为诊断；不能把消息流兼容宣称为完整 runtime 兼容。
