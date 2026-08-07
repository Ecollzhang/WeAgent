# Spec Template

版本 ：v1.0
更新时间：2026.5.24

## 1. 基本信息

- 名称：Agent Adapter 消息流接入规范
- 日期：2026-05-24
- 负责人：why

## 2. 本轮目标

本轮希望解决的问题或达成的目标：

WeAgent 需要通过一个统一的 adapter/factory 层接入 Claude Code 与 Codex，使上层在不关心具体 provider CLI 差异的情况下，可以发送任务并接收标准化的流式消息事件。

本轮目标不是实现完整 agent runtime，而是先建立一个最小、可测试、可扩展的消息流接入规范，为后续 sandbox、orchestrator、SSE 和前端展示打基础。

## 3. 范围

本轮明确包含：

- 提供统一的 `AgentAdapterFactory`，通过 provider 名称创建 Claude Code、Codex、Mock 等 adapter。
- 提供统一的 `AgentRequest` 输入结构，至少包含 prompt、workspace path、metadata 等后续可扩展字段。
- 提供统一的流式事件输出结构，将不同 provider 的 CLI stream 映射为 WeAgent 内部可消费的事件。
- 支持 Claude Code adapter 通过真实 CLI 调用读取消息流。
- 支持 Codex adapter 通过真实 CLI 调用读取消息流。
- 支持调用方通过 `workspace_path` 指定 adapter 执行目录，为后续 sandbox/workspace 隔离预留接口。
- 通过 backend 单元测试与真实 smoke test 验证 Claude Code 和 Codex 都能返回消息。
- 保持最小模块修改，不主动改动前端和现有业务接口。

本轮明确不包含：

- 不实现前端消息展示。
- 不接入 SSE 或完整 WebSocket 推流。
- 不实现 orchestrator 的任务拆解和分派。
- 不实现 sandbox/workspace 隔离本身，只保留执行路径入口。
- 不承诺完整支持 hook、MCP 错误、plan mode、permission prompt、后台任务、技能运行、子 agent、交互选项等 runtime 状态。
- 不把直接 CLI 诊断结果等同于 adapter 行为；正式验证应以 adapter 调用为准。

## 4. 输入条件

当前已知输入包括：

- provider 类型：`claude`、`codex`、`mock`，以及未来可扩展的 provider。
- 用户或 orchestrator 生成的 prompt。
- 可选的 `workspace_path`，用于指定 Claude/Codex 在哪个工作目录执行。
- provider CLI 的真实 JSON/JSONL stream 输出。
- 当前 WeAgent backend 的测试环境和 adapter 模块结构。

## 5. 期望输出

本轮完成后期望产出：

- 上层可以通过统一 factory 创建 Claude Code 或 Codex adapter。
- 上层可以通过同一个 `stream(request)` 出口读取标准化消息事件。
- Claude Code 的文本输出可以映射为统一消息事件。
- Codex 的真实 `item.completed` / `agent_message` 输出可以映射为统一消息事件。
- provider CLI 失败时可以转换为标准化失败事件，而不是直接破坏上层调用。
- adapter 的执行目录可控，后续能够与 sandbox 层结合。

## 6. 验收标准

满足以下条件可认为本轮目标基本完成：

- backend adapter 单元测试通过。
- Claude Code adapter 真实调用可以返回标准化消息事件。
- Codex adapter 真实调用可以返回标准化消息事件。
- Windows 下 Claude/Codex CLI 的实际差异已被处理，包括 Claude `--verbose` 要求、Codex executable 解析、Codex JSONL 真实结构、非 JSON 尾部噪声。
- 文档中明确说明 adapter 的调用位置、workspace 控制方式和当前能力边界。
- 代码保持模块化，不把 provider-specific 逻辑泄漏到上层调用方。
- 不对前端做额外改动。

## 7. 风险与限制

当前已知风险、依赖或限制：

- 当前 adapter 只完成消息流兼容，不能代表完整 runtime 兼容。
- Claude Code 和 Codex CLI 的输出格式可能随版本变化，需要后续保留 normalizer 测试。
- 交互选择、permission、plan mode、MCP、hook、后台任务等事件如果不标准化，后续前端无法准确显示 agent 当前状态。
- workspace path 目前只是执行目录控制，真正的文件隔离、权限边界和产物归属仍依赖后续 sandbox 层。
- 直接 CLI 调试容易和 adapter 行为混淆，后续验证需要明确记录调用路径。

## 8. 下一步

本轮结束后建议继续推进：

- 为 runtime event surface 写单独 spec，定义 hook、MCP、plan mode、permission、session、background、sub-agent、interactive choice 等事件如何向上层暴露。
- 与 sandbox/workspace 层对齐 adapter 的执行目录、权限模式和文件产物策略。
- 在 orchestrator 层接入 adapter factory，但仍保持 provider-specific 逻辑只停留在 adapter 内。
- 设计前端/SSE 消息流展示协议，区分普通文本、运行时状态、错误、工具调用和用户交互请求。
