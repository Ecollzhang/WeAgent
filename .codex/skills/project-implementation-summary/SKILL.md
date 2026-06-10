---
name: project-implementation-summary
description: Use when starting a new feature, major module, iteration, refactor, bugfix wave, or continuation task in this repository; requires Codex to first read the project implementation summary file, understand current module completion status, dependencies, tests, risks, and update that summary after completing any substantial module or iteration.
---

# Project Implementation Summary Maintenance

Use this skill to keep long-running project work continuous across sessions. The goal is to make every new task start from the current implementation reality, not from memory or scattered conversation history.

## Summary File

Default summary file:

```text
项目实现总结.md
```

If the file does not exist, create it before or during the first substantial task using the structure in this skill.

## When To Use

Use this skill when:

- Starting a new feature or user requirement.
- Continuing after a large module was completed.
- Beginning a new iteration after tests and fixes.
- Investigating regressions across modules.
- Planning work that depends on existing Web, Desktop, Android, backend, sandbox, Agent, artifact, workflow, capability, or provider-adapter behavior.
- The user asks “先看看当前实现情况”, “继续下一个需求”, “根据已有实现继续”, “更新总结”, or similar.

## Required Workflow

### 1. Before Starting Work

Before proposing a plan or modifying code:

1. Open `项目实现总结.md`.
2. Read only the sections relevant to the current request first.
3. Identify:
   - Current implementation status of affected modules.
   - Related files and services.
   - Known dependencies between modules.
   - Existing tests or manual verification records.
   - Known risks, unfinished items, or regressions.
4. If the summary is missing, outdated, or conflicts with code, state that and verify against the repository.
5. Use the summary to shape the plan, affected scope, testing strategy, and regression checklist.

Do not rely only on conversation memory when the summary file exists.

### 2. During Implementation

While implementing:

- Keep changes scoped to the active requirement.
- Track any discovered module relationship not recorded in the summary.
- Track tests run, tests skipped, and reasons.
- Track new risks or follow-up tasks.
- If implementation changes an existing contract, note impacted modules for the final summary update.

### 3. After Completing A Major Module Or Iteration

Update `项目实现总结.md` when any of the following happens:

- A feature module is completed.
- A major bugfix changes behavior across modules.
- A new interface, data model, socket event, sandbox route, provider adapter, workflow behavior, or artifact type is added or changed.
- Web / Desktop / Android behavior diverges or becomes aligned.
- A regression test pass completes.
- A known risk is resolved or newly discovered.

The update must happen before final handoff unless the user explicitly asks not to update documentation.

## Summary File Structure

Use this structure for `项目实现总结.md`.

```markdown
# 项目实现总结

更新日期：YYYY-MM-DD

## 1. 当前总体状态

- 项目阶段：
- 当前稳定范围：
- 最近完成的大模块 / 迭代：
- 当前主要风险：

## 2. 模块实现状态

| 模块 | 实现程度 | 关键文件 | 依赖模块 | 测试状态 | 风险 / 待办 |
|---|---|---|---|---|---|
| Web 前端 |  |  |  |  |  |
| Desktop 客户端 |  |  |  |  |  |
| Android 客户端 |  |  |  |  |  |
| 后端会话与消息 |  |  |  |  |  |
| Agent 与多 Agent 协作 |  |  |  |  |  |
| Sandbox / Docker |  |  |  |  |  |
| Provider Adapter |  |  |  |  |  |
| 多类型产物与工作台 |  |  |  |  |  |
| Workflow |  |  |  |  |  |
| Capability / Tool / MCP |  |  |  |  |  |
| 文件、服务与代理 |  |  |  |  |  |
| 文档体系 |  |  |  |  |  |

## 3. 关键功能清单

| 功能 | 当前状态 | 覆盖端 | 关联模块 | 验证方式 | 备注 |
|---|---|---|---|---|---|

## 4. 跨模块关联

- 会话创建 ->
- 消息发送 ->
- Sandbox event ->
- 产物展示与恢复 ->
- 工作流复用 ->
- 能力投影 ->
- 多端后端连接 ->

## 5. 接口、事件与数据模型变更

| 类型 | 名称 / 路径 | 当前状态 | 影响范围 | 备注 |
|---|---|---|---|---|
| API |  |  |  |  |
| Socket Event |  |  |  |  |
| Model Field |  |  |  |  |
| Sandbox Route |  |  |  |  |

## 6. 测试与验证记录

| 日期 | 范围 | 命令 / 手动步骤 | 结果 | 未覆盖项 |
|---|---|---|---|---|

## 7. 已知风险与待办

| 风险 / 待办 | 影响范围 | 优先级 | 当前处理建议 |
|---|---|---|---|

## 8. 最近一次迭代总结

- 本次完成：
- 修改文件：
- 验证结果：
- 遗留问题：
- 建议下次开始前先读的章节：
```

## Update Rules

When updating `项目实现总结.md`:

- Be factual. Do not mark unverified behavior as complete.
- Prefer concise tables over long prose.
- Include key file paths for future navigation.
- Record tests and manual checks exactly enough to repeat them.
- Distinguish “implemented”, “partially implemented”, “needs verification”, and “not implemented”.
- If a feature exists only on Web or Desktop but not Android, state the platform scope.
- If a module depends on backend, sandbox, Provider CLI, Docker, or external network, state the dependency.
- If no tests were run, write “未运行” and the reason.
- Preserve useful historical notes, but remove stale contradictions when code proves them wrong.

## Final Response Requirement

After completing a substantial module or iteration, final response must include:

- Whether `项目实现总结.md` was updated.
- Which summary sections were changed.
- Tests or verification performed.
- Known remaining risks.

If the summary was not updated, explicitly explain why.

