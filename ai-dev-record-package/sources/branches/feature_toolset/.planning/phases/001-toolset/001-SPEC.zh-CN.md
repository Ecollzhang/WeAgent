# 阶段 001：工具集能力 v1 - 规格说明

**创建时间：** 2026-05-28
**分支：** `feature/toolset`
**来源流程：** `$gsd-spec-phase`
**歧义评分：** 0.11（门槛：<= 0.20）
**需求数量：** 10 项已锁定

## 目标

WeAgent 要从“Agent 表单里直接填写内联 `skill` 文本和 `tool_ids`”的模式，演进为一个能力系统。在这个系统里，Skill、Tool、MCP 和 Plugin 都是一等的、由数据库支撑的资产；它们可以绑定到 Agent，在每个 session sandbox 中投影到 `.weagent/*`，通过显式授权控制权限，并通过真实运行时记录进行审计。

## 背景

当前分支基于已经测试过的多 Agent / artifact 工作。仓库中已经有 Agent CRUD、Tools 页面、sandbox session、多 Agent 进度、消息展示和 artifact 展示。

当前实现点：

- `backend/app/models/agent.py` 在 Agent 行上把 `skill` 存为内联文本，把 `tool_ids` 存为 JSON。
- `backend/app/models/agent_tool.py` 和 `backend/app/services/tool_service.py` 支持把内置工具和自定义工具作为一个扁平工具列表。
- `frontend/src/components/AgentEditForm/index.vue` 允许用户编辑 Agent、填写 Skill 文本块并选择工具。
- `frontend/src/views/Tools.vue` 管理工具，但没有把 Skill、MCP 或 Plugin 表达为并列的能力类型。
- `backend/app/sandbox/host/manager.py` 为每个 conversation/session 创建一个 Docker 容器，容器内有 `/workspace`，没有 host volume mount。
- `backend/app/sandbox/container/orchestrator.py` 管理容器侧 Agent、内置工具、session 文件和 ClaudeRuntime 执行。
- 当前还不存在由 DB 支撑的 Skill Library、能力版本管理、Agent 能力绑定、权限快照、`.weagent/*` 投影、MCP npx manifest 导入、Plugin manifest 导入或能力调用审计。

## 需求

1. **并列能力模型**：后端必须把 Skill、Tool、MCP 和 Plugin 建模为并列的能力类型。
   - 当前：Skill 是 Agent 内联文本，Tool 是独立的 `AgentTool`，MCP/Plugin 没有一等持久化。
   - 目标：由 DB 支撑的能力库保存 `skill`、`tool`、`mcp`、`plugin` 的定义、版本、来源元数据、权限声明和类型特定元数据。
   - 验收：验证者可以为每种类型创建或 seed 一条记录，并通过统一的能力列表 API 取回它们；MCP/Plugin 不能嵌套在 Skill 下面。

2. **Agent 级默认绑定**：能力必须作为 Agent 的默认配置进行绑定，而不是在每次新建对话时临时选择。
   - 当前：Agent 直接保存 `tool_ids` 和 `skill`。
   - 目标：创建/编辑 Agent 时，可以绑定能力版本，并保存显式 enabled 状态和 granted permissions；Agent 的默认绑定保存在 DB 中。
   - 验收：创建一个带两个能力的 Agent 会持久化 `agent_capability_bindings`；用该 Agent 启动新 session 时会自动使用这些绑定。

3. **固定版本行为**：Agent 绑定默认必须指向固定能力版本。
   - 当前：现有 `skill` 和 `tool_ids` 没有版本行为。
   - 目标：每个 Agent binding 都引用一个 `capability_version_id`；`version_policy` 在 v1 支持 `pinned`，可以预留 `follow_latest`，但不能暴露自动升级行为。
   - 验收：更新 Skill 会创建新版本，但不改变现有 Agent binding；Agent 详情 API 可以报告有可升级版本。

4. **显式权限授权**：能力必须声明权限，Agent binding 必须保存授权快照。
   - 当前：sandbox 路由和 Agent 工具没有表达能力级权限。
   - 目标：能力版本从 `read_workspace`、`write_workspace`、`run_command`、`network`、`use_secret`、`modify_skill`、`start_service` 中声明权限；Agent binding 保存 granted permissions 和 authorization snapshot。
   - 验收：绑定一个要求 `run_command` 的能力时，如果请求没有授予 `run_command`，则绑定失败；未来能力版本扩大权限时，不能静默扩大已有 binding 的权限。

5. **DB 作为事实源，session 运行时投影**：能力定义必须持久化在 DB 中，并且只在 session 运行时投影到 sandbox。
   - 当前：session 容器持有临时 workspace 文件，而 Skill/Tool 数据存储在 Agent/Tool 行里。
   - 目标：DB 是 canonical source of truth；每个 session 在 `/workspace` 下得到一个临时 `.weagent/*` runtime projection。
   - 验收：销毁 session 时，`.weagent/*` 会随容器一起删除；能力库和 Agent bindings 仍可供下一次 session 使用。

6. **`.weagent/*` 运行时契约**：v1 只能生成 WeAgent 运行时文件，不能生成 Claude/Codex 原生兼容目录。
   - 当前：没有 `.weagent/*` 投影；ClaudeRuntime 使用自己的 Agent workspace 行为。
   - 目标：sandbox 写入 `/workspace/.weagent/capabilities/index.json`、`/workspace/.weagent/skills/<skill_id>/SKILL.md`，以及 `/workspace/.weagent/agents/<agent_id>/` 下的每个 Agent 视图文件；Agent runtime instructions 包含一个紧凑 bootstrap，指向该 Agent 的 `.weagent` 视图文件。
   - 验收：一个包含单个 Skill 的 Agent session 会产生共享 Skill 文件、Agent 专属 `capabilities.json`、`skill-index.json` 和 `permissions.json`，并且 runtime bootstrap 引用这些文件；v1 不生成 `.claude/skills`、`.codex/skills` 或 `.mcp.json`。

7. **Skill 生命周期和 Agent 写入草稿**：Skill 必须可在平台 UI 中编辑，也可由 session runtime 中的 Agent 修改，但不能直接覆盖用户库。
   - 当前：Skill 是 Agent 上的 textarea，不是可复用的 library asset。
   - 目标：用户可以在能力库中创建/编辑/导入 Markdown Skill；Agent 可以修改 session runtime copy；平台同步时把 Agent 改动保存为 `skill_revision_drafts`。
   - 验收：编辑投影出来的 `.weagent/skills/<skill_id>/SKILL.md` 会创建一条 DB draft，并关联 `source_skill_id`、`source_version_id`、`session_id` 和 `agent_id`；发布 draft 会创建新的 Skill version，另存为 fork 会创建新的 Skill。

8. **MCP npx manifest 路径**：MCP v1 必须要求先导入 manifest，才能绑定或执行。
   - 当前：没有 MCP model 或 runtime。
   - 目标：用户从 WeAgent 自有的 npx manifest schema 导入 MCP 定义；WeAgent 在允许 Agent 绑定前解析声明的 server command、tools 和 permissions。
   - 验收：一个 manifest-backed MCP 可以被安装，在 sandbox 内通过 npx 启动，列出至少一个 tool，执行一次真实的最小调用，并写入调用记录。

9. **Tool 和 Plugin 最小范围**：Tool 和 Plugin v1 必须是真实能力，但范围刻意收窄。
   - 当前：内置工具作为 DB 行和容器侧 Python callable 存在，但调用审计没有绑定到 Agent capability bindings。
   - 目标：Tool 至少支持一个带 `capability_call_records` 的内置 callable；Plugin 只支持 manifest 导入和安装记录，不允许任意 Plugin 执行。
   - 验收：内置 Tool 调用记录 start/completion 元数据；Plugin manifest 导入会创建 Plugin capability 和 install record，但 v1 不能执行 plugin code。

10. **平台展示和配置**：前端必须展示并配置能力库和 Agent 默认工具集。
    - 当前：用户在不同页面管理 Agents 和 Tools；Skill 是内联文本。
    - 目标：平台提供 Capability Library 视图和 Agent 创建/编辑流程，用户可以查看、创建、导入、绑定、授权并查看能力版本状态。
    - 验收：用户可以创建一个 Skill Markdown asset，导入一个 Markdown Skill，导入一个 npx manifest，在创建 Agent 时绑定能力，并看到 pinned version 和 upgrade availability。

## 边界

**范围内：**

- `Capability`、`CapabilityVersion`、`AgentCapabilityBinding`、`CapabilityCallRecord` 和 `SkillRevisionDraft` 的后端数据模型。
- MySQL 兼容持久化所需的 migration 或初始化更新。
- 能力记录的列表、创建、导入、版本管理、绑定、授权和检索后端 API。
- 前端能力库 UI 和 Agent 创建/编辑集成。
- 将 session sandbox 容器运行时投影到 `/workspace/.weagent/*`。
- `/workspace/.weagent/agents/<agent_id>/` 下的 Agent 专属能力视图文件。
- Skill Markdown 生命周期、Markdown 文本/文件导入、Agent 写入 draft 同步、发布为新版本、另存为 fork。
- 平台能力的内置 capability seed。
- 一个最小平台内置 Tool 调用记录。
- 一个最小 npx MCP manifest 导入、sandbox start、tool list、call 和 audit record。
- Plugin 仅做 manifest 导入和 install record。
- 核心 model/service/projection/authorization 行为测试。

**范围外：**

- 解决其他分支带来的无关 merge conflicts。
- 在设计/spec 工作中为用户机器安装 Docker。
- 远程 marketplace 浏览、GitHub marketplace 导入、zip 包安装或任意本地路径包导入。
- 在 host backend 执行 npx/MCP/Plugin 代码。
- 完整 Plugin runtime execution、hooks、自定义 UI extension runtime 或任意 plugin command execution。
- 自动生成 `.claude/*`、`.codex/*` 或 `.mcp.json` 兼容目录。
- 按单条消息安装能力。
- 自动将现有 Agent bindings 升级到最新能力版本。
- 对现有未认证 sandbox 路由进行完整安全加固，除非 capability API 和 runtime records 需要认证与权限检查。

## 约束

- DB 是 Agent 定义、Skill 内容、能力版本、绑定、权限、导入和草稿的 canonical source of truth。
- `/workspace/.weagent/*` 是临时 session runtime projection，不能被当成长久存储。
- 当前架构中的 workspace 是 session-scoped；Skill/Plugin/MCP/Tool library 内容保存在 DB 中，以便未来 session 复用。
- Workspace root 拥有共享 `.weagent` 投影；每个 Agent 只接收 `.weagent/agents/<agent_id>/` 下自己的视图。
- Skill 内容通过轻量 index 和 path 加载，默认不把全文注入到每次 prompt 中。
- npx/MCP 执行发生在 sandbox container 内，不发生在 host backend。
- 能力绑定授权属于 Agent；workspace/session 管理 Agents，并可在未来阶段加入策略上限。
- v1 默认支持 `pinned` version policy；`follow_latest` 可以作为保留模型值存在，但不能静默改变运行行为。
- 实现必须保留现有多 Agent 消息、进度展示和 artifact 展示行为。
- 迁移期间可以保留现有 legacy `Agent.skill` 和 `Agent.tool_ids` 行为以兼容旧数据，但新的功能开发必须使用 capability bindings。

## 验收标准

- [ ] 后端暴露统一 capability list，包含 Skill、Tool、MCP 和 Plugin records。
- [ ] 用户可以在 DB 中创建和编辑 Skill Markdown capability。
- [ ] 用户可以从 Markdown 文本或 Markdown 文件内容导入 Skill。
- [ ] 用户可以导入 npx manifest，并由此生成 MCP/Plugin/Skill capability definitions。
- [ ] 用户可以创建 Agent，并以显式 granted permissions 绑定 pinned capability versions。
- [ ] 发布较新的 Skill version 时，现有 Agent bindings 不改变。
- [ ] 用 Agent 启动 session 时，会在 `/workspace` 下写入 `.weagent/*` runtime files。
- [ ] Session projection 包含共享 capability files 和 per-Agent view files。
- [ ] Agent 修改 runtime Skill 会创建 DB draft revision，不会自动发布。
- [ ] 用户确认后，可以将 draft 发布为新的 Skill version，或另存为 fork。
- [ ] 内置 Tool 可被调用，并写入包含 Agent、session、capability version、permissions、status、input summary 和 output summary 的 call record。
- [ ] 从 npx manifest 导入的 MCP server 可以在 sandbox 内启动、list tools、执行一次最小调用，并写入 call record。
- [ ] Plugin manifest 可以被导入，并作为 record 安装，但不执行 plugin code。
- [ ] v1 runtime projection 不创建 `.claude/skills`、`.codex/skills` 或 `.mcp.json`。
- [ ] 加入 capability projection 后，现有多 Agent message display、progress display 和 artifact display 继续工作。

## 歧义报告

| 维度 | 分数 | 最小值 | 状态 | 说明 |
|---|---:|---:|---|---|
| 目标清晰度 | 0.93 | 0.75 | 已满足 | 工具集能力目标明确，并映射到 DB、UI、sandbox 和 audit 行为。 |
| 边界清晰度 | 0.90 | 0.70 | 已满足 | v1 明确包含 Skill 完整生命周期、最小 Tool/MCP 真实调用，以及 Plugin manifest-only 范围。 |
| 约束清晰度 | 0.86 | 0.65 | 已满足 | DB 事实源、session-scoped sandbox、只写 `.weagent/*`、显式权限和 pinned versions 均已锁定。 |
| 验收标准 | 0.82 | 0.70 | 已满足 | Pass/fail 检查覆盖 model、UI、projection、Skill drafts、Tool/MCP calls 和 Plugin import。 |
| **歧义** | **0.11** | **<= 0.20** | 已满足 | 可以进入计划阶段。 |

## 访谈记录

| 轮次 | 视角 | 问题摘要 | 锁定决策 |
|---|---|---|---|
| 1 | Researcher | 工具集工作应使用哪个分支和基线？ | 工作从 `feature/toolset` 开始，基于 `origin/feature/multi-agent-and-artifact-v1`。 |
| 1 | Researcher | 当前分支是否已经隔离 workspace 并接入 Claude？ | 已有 session sandbox 和 Claude Code CLI 路径，但没有 capability library 或 `.weagent` 注入。 |
| 2 | Simplifier | Skill 是否只是渲染进 prompt 的 Markdown？ | 不是。Skill 是由 DB 支撑的 Markdown asset，并有 workspace runtime projection。 |
| 2 | Simplifier | 工具集是否只有 Skill？ | 不是。Skill、MCP、Plugin 和 Tool 是并列能力类型。 |
| 3 | Boundary Keeper | 各能力类型的 v1 范围是什么？ | Skill 完整生命周期；Tool/MCP 最小真实 call records；Plugin 仅 manifest import/install record。 |
| 3 | Boundary Keeper | 执行应该发生在哪里？ | npx/MCP/Plugin/Tool runtime 行为运行在 workspace sandbox 中，不运行在 host backend。 |
| 4 | Failure Analyst | 哪种权限策略能防止静默越权？ | 能力声明权限；Agent bindings 保存显式 authorization snapshots。 |
| 4 | Failure Analyst | 注入方式应如何参考 Claude/Codex？ | 使用轻量 index 和按需读取；不要把全部内容注入 prompt。 |
| 5 | Seed Closer | Runtime files 写在哪里？ | v1 只写 `.weagent/*`；不写 `.claude/*`、`.codex/*` 或 `.mcp.json`。 |
| 5 | Seed Closer | 谁拥有 binding 和默认注入？ | Agent 拥有默认 capability bindings；workspace/session 管理 Agents 并投影 runtime files。 |
| 6 | Seed Closer | 版本如何行为？ | Bindings 默认使用 pinned capability versions；UI 可以显示 upgrade availability。 |
| 6 | Seed Closer | Agent 写入的 Skill 改动如何持久化？ | Session runtime changes 变成 DB draft revisions；用户确认发布为新版本或另存为 fork。 |
| 6 | Seed Closer | MCP npx import 应如何工作？ | Manifest 必须先导入并解析，之后才能绑定或执行。 |

---

*阶段：001-toolset*
*规格创建时间：2026-05-28*
*下一步：`$gsd-plan-phase 001` 实施计划。*
