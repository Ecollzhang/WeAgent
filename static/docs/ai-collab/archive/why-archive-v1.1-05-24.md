# Archive Template

版本 ：v1.0
更新时间：2026.5.24

## 1. 归档信息

- 归档名称：Claude Code 与 Codex Adapter 消息流兼容边界归档
- 归档日期：2026-05-24
- 归档人：why
- 对应 session：`docs/ai-collab/sessions/why-session-v1.1-05-24.md`
- 对应 session 记录范围：Claude Code 与 Codex adapter 的最小模块实现、真实流式消息验证、workspace 调用位置说明，以及当前尚未覆盖的 runtime 能力边界。

## 2. 归档原因

本次对话触发归档的原因：

- 本轮已经形成可复用的工程判断：WeAgent 可以先通过 factory + adapter 的方式统一 Claude Code 与 Codex 的消息流出口。
- 本轮也明确了一个重要边界：当前完成的是“接收消息流兼容”，不是 hook、MCP、plan mode、后台运行、技能运行、子 agent、交互选择等完整 runtime 能力适配。
- 这些判断会影响后续 sandbox、orchestrator、SSE、前端消息展示和报告撰写，因此需要从 session 中提炼为 archive。

## 3. 对话主题

本轮对话主要主题为：

Claude Code 与 Codex 如何通过统一 adapter factory 接入 WeAgent，并以最小模块方式实现流式消息发送/接收，同时确认当前能力边界和后续扩展方向。

## 4. 归档提炼

从原始对话中提炼出的有效内容：

- Adapter MVP 的正确定位是统一消息出口，而不是直接替代 Claude Code/Codex 的完整交互运行时。
- 统一调用模型应以 `AgentAdapterFactory.create(provider)` 获取 provider adapter，再通过 `adapter.stream(AgentRequest)` 获取标准化事件。
- `AgentRequest.workspace_path` 是当前控制 Claude/Codex 执行位置的主要入口，可用于后续和 sandbox/workspace 隔离层对接。
- workspace 解析顺序当前为：
  - 优先使用 `AgentRequest.workspace_path`
  - 其次使用 `AGENT_WORKSPACE_ROOT`
  - 最后回退到 WeAgent 项目根目录
- Claude Code 真实调用需要注意：
  - `stream-json` 输出需要配合 `--verbose`
  - Windows 下输出需要按 UTF-8 解码，并容忍非法字节
  - 当前 adapter 能映射文本消息为 `message.delta` / `message.completed`
  - raw stream 中实际存在 hook、system init、MCP、permission、session id、api retry 等事件，但当前 normalizer 尚未向上层完整暴露
- Codex 真实调用需要注意：
  - Windows 下直接执行 `codex` 可能触发权限问题，应优先解析 `codex.cmd` 或 `codex.exe`
  - Codex `exec --json` 的真实输出可能是 `item.completed`，其中 `item.type=agent_message`，文本在 `item.text`
  - Windows 进程结束时可能出现非 JSON 的 `SUCCESS: The process with PID...` 行，normalizer 应忽略这类已知尾部噪声
- 真实验证结论：
  - Claude Code adapter 可以收到标准化消息事件
  - Codex adapter 可以收到标准化消息事件
  - 二者当前可以称为“消息接收兼容”
  - 不能称为“各种功能完美适配”
- 与前端相关的 SSE、消息卡片、运行时提示展示不在本轮范围内，后续应单独规划。
- `.pycache_verify` 是 Python 编译/验证产生的缓存目录，不属于源码或协作归档；它已经被 `.gitignore` 忽略，不应该提交。

## 5. 已形成成果

本次归档已经形成的成果包括：

- `agent_adapter` 远程分支已经推送。
- backend adapter 模块完成最小可用接入。
- Claude Code 和 Codex 均已完成真实 adapter smoke 测试。
- backend 测试为 17 个通过。
- `docs/tech/modules/E_agent_adapter.md` 已记录 adapter 调用位置、workspace 控制和真实 smoke 结论。
- GSD phase summary 已记录本轮执行结果和当前限制。
- `docs/ai-collab/` 已被设置为本地忽略目录，用于后续持续沉淀 AI 协作资产。

## 6. 后续去向

本次归档内容后续应落入：

- `spec/`：建议后续创建 runtime event surface spec，定义 hook/MCP/plan mode/permission/session/background/sub-agent/interactive choice 等事件如何标准化。
- `skills/`：暂不升级。当前不是稳定角色职责，而是工程接入方案。
- `rules/`：建议后续沉淀规则：真实能力验证必须通过 adapter；直接 CLI 只能作为诊断；不得把消息流兼容描述为完整 runtime 兼容。
- `summaries/`：阶段结束后可整理为 why 的 adapter 接入阶段总结。
- 仅保留在归档记录中：`.pycache_verify` 这类本地运行产物处理说明可保留在 archive 中，不必升级为 spec。

## 7. 备注

当前 adapter 的价值已经成立：Claude Code 与 Codex 可以通过同一层 factory/adapter 被调用，并接收标准化消息。

但当前 adapter 的边界也必须继续保留在报告中：它仍然只是读取消息流，还没有完整展示 hook 提示、MCP 出错、plan mode、后台运行、技能运行、子 agent 和交互选择等运行时状态。
