# Summary Template

版本 ：v1.0
更新时间：2026.5.25

## 1. 基本信息

- 总结名称：Agent Adapter 阶段完成与验收口径总结
- 日期：2026-05-25
- 负责人：why
- 覆盖周期：2026-05-24 至 2026-05-25

## 2. 本阶段目标

本阶段主要目标为：

完成 factory 兼容 Codex + Claude Code gateway 的第一阶段闭环，使 WeAgent 能通过统一 adapter factory 调用 mock、Claude Code、Codex，并把 normalized message stream 经 orchestrator、SSE 和前端展示出来。

## 3. 关键进展

本阶段已经完成或明确推进的内容：

- 完成 adapter contract、factory、mock adapter、Claude adapter、Codex adapter 和 provider normalizers。
- 真实验证 Claude Code adapter 能返回标准化消息流。
- 真实验证 Codex adapter 能返回标准化消息流，并修复 Windows executable 解析和真实 JSONL 输出形态。
- 完成 backend orchestrator 接入 adapter factory。
- 完成 `message_service` 用户消息路径到 orchestrator 的切换。
- 完成 SSE named events。
- 完成前端 Dashboard + Vuex 的临时流式 agent message 展示。
- 完成 mock adapter localhost smoke。
- 完成前端测试与 GSD 实现报告。
- 完成 GSD Task 5/6/7 checkbox 和 STATE 同步。

## 4. AI 协作沉淀

本阶段沉淀出的有效协作经验：

- 需要把“实现完成”“测试通过”“GSD checkbox 完成”“git 已提交推送”分开检查。
- 前端 smoke 优先使用 mock adapter，这能快速证明 WeAgent 自身链路是否工作。
- Claude/Codex 真实 adapter 验收应单独标注，因为它们受 CLI 登录、权限、网络、运行时间和 workspace 影响。
- 对外表述要准确：当前完成的是 normalized message stream，不是完整 runtime event surface。
- 文档沉淀应分层：
  - `docs/report` 用于团队可读报告。
  - `docs/ai-collab/session` 记录协作过程。
  - `docs/ai-collab/archive` 提炼长期复用判断。
  - `docs/ai-collab/summary` 做阶段复盘。

## 5. 已升级的规范

本阶段已经升级形成的内容：

- 新增 `Spec`：已存在 `docs/ai-collab/spec/agent-adapter-message-stream-spec.md`。
- 新增 `Skill`：暂未新增。
- 新增 `Rules`：暂未新增独立 rules 文件，但形成候选规则：
  - smoke test 优先 mock adapter。
  - 真实 Claude/Codex 验收必须明确标注 provider 和运行环境。
  - message stream 完成不能等同于 runtime 完全适配。
  - GSD 完成前必须检查 checkbox、STATE、summary、verification 和 git push。

## 6. 当前问题

本阶段仍存在的问题：

- hook、MCP、plan mode、permission prompt、session id、api retry 等 runtime 状态尚未完整展示。
- Claude/Codex interactive choice 尚不能在 WeAgent 前端中暂停、选择并继续同一会话。
- sandbox/workspace 层尚未正式接入 `workspace_path` 生成与隔离策略。
- rich tool timeline 与 raw event 持久化仍未实现。

## 7. 下一阶段建议

下一阶段建议重点推进：

- 先写 runtime event surface spec。
- 明确 runtime event 在前端聊天、日志、工具调用、timeline 中的展示位置。
- 设计 interactive choice continuation 协议。
- 与 sandbox/workspace 层对齐执行目录和产物归属。
- 再进行 Claude/Codex 真实前台调度验收。
