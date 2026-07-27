# Summary Template

版本 ：v1.0
更新时间：2026.5.24

## 1. 基本信息

- 总结名称：Claude Code 与 Codex Adapter 接入阶段总结
- 日期：2026-05-24
- 负责人：why
- 覆盖周期：2026-05-23 至 2026-05-24

## 2. 本阶段目标

本阶段主要目标为：

在 WeAgent 中以 factory + adapter 的方式统一接入 Claude Code 与 Codex，先完成可验证的消息流发送/接收闭环，并明确当前能力边界，为后续 sandbox、orchestrator 和前端流式展示做准备。

## 3. 关键进展

本阶段已经完成或明确推进的内容：

- 确认以 GSD 作为本轮主要工作方式，不混用其他流程。
- 确认所有项目内文档、计划、归档都必须写在 `WeAgent` 目录内。
- 确认 why 负责方向为 factory 兼容 Codex + Claude Code gateway。
- 建立并推送 `agent_adapter` 分支。
- 采用 TDD 和最小模块修改方式完成 adapter 层初版。
- 完成 `AgentAdapterFactory`、统一 request/event 类型、Mock adapter、Claude Code adapter、Codex adapter 和 provider normalizer。
- 真实调用 Claude Code adapter，验证可以收到标准化流式消息。
- 真实调用 Codex adapter，修复 Windows 可执行文件解析和真实 JSONL 输出映射后，验证可以收到标准化消息。
- 明确当前 adapter 可以称为“消息流兼容”，但不能称为“完整 runtime 功能适配”。
- 将 `docs/ai-collab/` 设置为本地 ignored 目录，用于保存 AI 协作沉淀，不进入 git。
- 明确 `.pycache_verify` 是 Python 缓存目录，不应进入 git。

## 4. AI 协作沉淀

本阶段沉淀出的有效协作经验：

- 当用户要求使用 GSD 时，应把 GSD 作为主流程，避免把多个规划体系混在一起。
- 工程实现前先明确 scope，尤其要区分“消息流可用”和“完整 runtime 可用”。
- 真实 provider 验证必须通过 adapter 完成，直接 CLI 只能作为诊断，不能替代 adapter smoke test。
- 对 Claude Code/Codex 这类外部 CLI，要把 provider 差异收敛在 adapter 和 normalizer 内，避免泄漏到上层业务接口。
- Windows 环境下需要特别验证真实 CLI 行为，包括 executable 解析、编码、非 JSON 输出和退出尾部噪声。
- AI 协作内容应在每轮结束后先写 session，再按复用价值升级为 archive/spec/summary/rules。

## 5. 已升级的规范

本阶段已经升级形成的内容：

- 新增 `Spec`：`docs/ai-collab/spec/agent-adapter-message-stream-spec.md`
- 新增 `Skill`：暂未新增。本阶段还不是稳定 AI 角色职责，而是工程 adapter 接入规范。
- 新增 `Rules`：暂未单独新增 rules 文件，但已形成候选规则：
  - 真实能力验证优先走 adapter。
  - raw CLI 调用只作为诊断。
  - 不把消息流兼容描述为完整 runtime 兼容。
  - ai-collab 归档只保留本地，不进入 git。

## 6. 当前问题

本阶段仍存在的问题：

- hook、MCP 错误、plan mode、permission prompt、session id、api retry 等 Claude/Codex runtime 事件还没有完整向上层暴露。
- 交互式选项目前只能作为文本消息读到，还不能在同一 adapter 会话中暂停、等待用户选择并继续。
- adapter 与 sandbox/workspace 层尚未正式合并，只是通过 `workspace_path` 预留执行目录控制入口。
- orchestrator、SSE、前端消息展示还没有接入本轮 adapter。
- `.pycache_verify` 虽然可以删除且已被忽略，但当前 Windows 权限拒绝导致仍保留在本地。

## 7. 下一阶段建议

下一阶段建议重点推进：

- 先设计 runtime event surface，明确普通消息、状态提示、hook、MCP、plan mode、permission、工具调用、错误、交互请求等事件类型。
- 再设计 adapter 的交互式 continuation 机制，使 Claude/Codex 要求用户选择时，上层能接住并继续同一任务。
- 与 sandbox/workspace 方向对齐，确定 `workspace_path` 的来源、隔离策略和文件产物归属。
- 在不改动前端的前提下，先完成 backend/orchestrator 层的 adapter 调用集成测试。
- 阶段稳定后，再补充 rules 文件，把本轮已经验证有效的协作规范固化下来。
