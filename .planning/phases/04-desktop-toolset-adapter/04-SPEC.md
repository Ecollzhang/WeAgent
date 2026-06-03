# Phase 04: Desktop Toolset Adapter - SPEC

**Created:** 2026-06-03
**Status:** Ready for planning
**Base branch:** `combine/toolset_v1.1.0`
**Target branch:** `combine/toolset_v1.1.0`
**Depends on:** Phase 03 Toolset Desktop Merge

## Purpose

让桌面端真正接入 Phase 03 已合并的 Toolset/Capability 模块。桌面端本阶段优先补齐三个目标：

- A: 桌面端提供工具集入口和 Agent 能力绑定入口。
- C: 桌面端发起的 Agent 运行时可以真实注入并使用绑定的 Skill、Tool、MCP 配置。
- B+: 桌面端复用 Web 端同源 API，提供 Markdown、zip、npx、MCP manifest 导入、权限审计展示、配置测试和启停入口。

本阶段的核心不是让 Electron 客户端直接执行工具，而是确保桌面端选择、导入、配置和保存的能力可以被后端服务处理、被后续 Agent 运行时消费，并通过 Codex/Claude 的真实调用证据证明有效。

## Current State

- Phase 03 已将 Toolset/Capability DB 模型、Web 管理 UI、Agent capability binding、`.weagent/*` runtime projection、MCP runtime、built-in Tool handler 合并到 desktop runtime base。
- Web 前端 `frontend` 已具备较完整的工具集管理能力。
- 桌面端 `clients/desktop` 当前只有 Conversations、Agents、Settings 等页面，没有独立 Tools/Capabilities 页面。
- 桌面端 `Agents.vue` 仍主要使用旧式 `tool_ids` 选择，尚未完整使用 Skill/MCP/Plugin/Tool 并行的 capability binding。
- 桌面端运行时需要补充面向 Codex/Claude 的真实 smoke 验证，证明桌面端 Agent 的能力绑定会进入 `.weagent/*`、provider 配置和调用记录。

## Locked Requirements

### REQ-27: 桌面端新增工具集入口

- Current state: 桌面端侧边栏存在禁用的工具按钮，未接入工具集页面。
- Target state: 桌面端提供可访问的工具集入口，展示用户可绑定的 Skill/MCP/Plugin/Tool，按一级类别筛选，进入后按四类能力展开。
- Acceptance criterion: 登录桌面端后可以从侧边栏进入工具集入口，至少可以查看已有类别、能力类型、能力卡片和绑定状态；不显示不可绑定/隐藏/未配置的空壳能力。

### REQ-28: 桌面端 Agent 创建和编辑支持 capability binding

- Current state: 桌面端 Agent 表单主要保存基础字段、provider/adapter 和旧式 `tool_ids`。
- Target state: 桌面端 Agent 创建和编辑时可以选择绑定 Skill/MCP/Plugin/Tool capability，默认使用固定版本；保存后刷新仍能看到绑定结果。
- Acceptance criterion: 桌面端创建/编辑 Agent 后，后端 `/api/agents/<agent_id>/capabilities` 返回相同绑定；Agent 列表或详情能展示绑定能力摘要。

### REQ-29: 工具实际由 Agent runtime 使用，Electron 客户端不直接执行

- Current state: Web 端管理能力与 sandbox runtime 已存在，桌面端需要决定执行边界。
- Target state: Electron 客户端只负责选择、保存、展示和触发对话；npx、MCP server、Docker、文件注入、权限审计、Tool handler 执行仍由后端/sandbox/provider runtime 负责。
- Acceptance criterion: 桌面端代码不新增直接执行 npx/MCP/Docker/脚本的逻辑；运行时执行仍走后端已有 API 和 sandbox provider。

### REQ-30: 桌面端运行时生成 canonical `.weagent/*` projection

- Current state: Phase 03 已实现 `.weagent/*` projection，但需要覆盖桌面端创建/运行 Agent 的路径。
- Target state: 从桌面端创建或选择 Agent 发起会话后，session/workspace 中生成该 Agent 对应的 `.weagent/*` 文件。
- Acceptance criterion: smoke 能证明存在：
  - `/workspace/.weagent/capabilities/index.json`
  - `/workspace/.weagent/agents/<agent_id>/capabilities.json`
  - `/workspace/.weagent/agents/<agent_id>/skill-index.json`
  - `/workspace/.weagent/agents/<agent_id>/tool-index.json`
  - `/workspace/.weagent/agents/<agent_id>/permissions.json`

### REQ-31: Codex 真实读取并暴露绑定 MCP/Skill/Tool 信息

- Current state: Codex provider 已修复 MCP server 写入 `config.toml` 的路径，但需要从桌面端流程做端到端验证。
- Target state: 桌面端 Agent 绑定 MCP/Skill/Tool 后，Codex provider 启动时能读取 `.weagent/*`，并将 MCP server 写入 Codex runtime config。
- Acceptance criterion: 至少一次 Codex 桌面端 Agent smoke 证明：
  - Codex session config 包含绑定 MCP server。
  - Codex prompt/context 可看到 Skill/Tool index 入口。
  - 能产生模型回复或运行记录，证明配置被加载；若外部模型不可用，需保留可复现的 provider config/log 证据。

### REQ-32: Claude 真实读取绑定 Skill/Tool/MCP 索引

- Current state: Claude provider 需要与桌面端 capability projection 做端到端验证。
- Target state: 桌面端 Agent 绑定能力后，Claude provider 的启动上下文或系统说明中包含 `.weagent/*` 能力入口。
- Acceptance criterion: 至少一次 Claude 桌面端 Agent smoke 证明：
  - Claude runtime prompt/context 包含 agent capability view 或 skill index 路径。
  - Claude 对话输出能反映已绑定测试 Skill，或 provider 日志证明上下文已注入。
  - 若 Claude 外部调用不可用，需保留 prompt/config 注入证据并标记为环境限制。

### REQ-33: 调用和注入证据必须可审查

- Current state: Phase 03 已有 call record 和 projection smoke，但桌面端路径未形成固定验收报告。
- Target state: Phase 04 必须产出三层证据：投影证据、运行证据、行为证据。
- Acceptance criterion: 验收报告中记录：
  - 投影证据：`.weagent/*` 文件截图/日志/读取结果。
  - 运行证据：Codex/Claude provider config、prompt/context、MCP config 或启动日志。
  - 行为证据：测试 Skill/MCP/Tool 的一次输出或调用记录。

### REQ-34: 桌面端复用同源 API 提供核心工具集管理能力

- Current state: Web 端已有创建、导入、配置、测试、删除等管理能力。
- Target state: 桌面端提供核心工具集管理入口，包括新建/编辑 Skill Markdown、Markdown 导入、zip bundle 导入、npx 导入、MCP manifest 导入、权限审计预览和记录展示、provider config 创建/测试/保存/启用/停用。
- Acceptance criterion: 桌面端能通过后端同源 API 完成上述管理动作；所有 npx/MCP/Docker/审计执行仍由后端和 sandbox 完成，Electron 不直接执行外部命令。

## In Scope

- 桌面端工具集入口：查看类别和 Skill/MCP/Plugin/Tool 列表。
- 桌面端 Agent 创建/编辑：选择并保存 capability binding。
- 桌面端 Agent 列表/详情：展示已绑定能力摘要。
- 桌面端工具集管理：新建 Skill、编辑 Skill Markdown、Markdown/zip/npx/MCP manifest 导入、删除用户能力。
- 桌面端安全审计：导入预览审计、详情页审计记录展示、高风险专家确认。
- 桌面端 provider config：创建、测试、保存、启用、停用、删除配置。
- 桌面端 API wrapper：复用后端 `/api/capabilities`、`/api/toolsets`、`/api/agents/<id>/capabilities`。
- Codex/Claude provider 的桌面端端到端 smoke。
- `.weagent/*` projection 的桌面端路径验证。
- MCP config、Skill index、Tool index、permissions 的注入证据。
- 调用记录或行为证据的验收报告。

## Out of Scope

- 桌面端直接执行 npx、MCP server、Docker、用户脚本或内置 Tool。
- 任意用户脚本 Tool 的完整执行沙盒。
- 新增大量内置 Tool 的业务实现。
- 重构 Web 端 Tools 页面。
- 改变 Phase 03 已确定的 provider runtime 架构。

## Acceptance Criteria

- [ ] 桌面端侧边栏工具入口可用。
- [ ] 桌面端工具集入口按类别和 Skill/MCP/Plugin/Tool 展示能力。
- [ ] 桌面端 Agent 创建时可以绑定 capability，默认固定版本。
- [ ] 桌面端 Agent 编辑时可以加载、增加、移除并保存 capability binding。
- [ ] 桌面端可以新建 Skill，并编辑用户 Skill Markdown 版本。
- [ ] 桌面端可以从 Markdown、zip bundle、npx、MCP manifest 生成导入预览并确认入库。
- [ ] 桌面端导入预览和详情页可以展示安全审计，且高风险导入需要专家确认原因。
- [ ] 桌面端可以对需配置 Tool 创建、测试、保存、启用、停用 provider config。
- [ ] 桌面端可以删除用户创建/导入的能力，并展示删除影响。
- [ ] 旧式 `tool_ids` 与新 capability binding 的关系明确，不再让用户误以为空壳 Tool 可直接运行。
- [ ] 桌面端发起会话后生成 `.weagent/*` runtime projection。
- [ ] Codex smoke 证明绑定 MCP/Skill/Tool 信息被 provider runtime 读取。
- [ ] Claude smoke 证明绑定 Skill/Tool/MCP 索引进入 provider context。
- [ ] 至少一个 Skill 测试能力能在 Agent 回复或运行记录中体现。
- [ ] 至少一个 MCP 配置能在 Codex/Claude runtime 配置或日志中被审查。
- [ ] 至少一个 built-in Tool 绑定能进入 `tool-index.json`/permissions，并在可执行路径中留下调用记录；若不触发真实执行，需说明限制。
- [ ] 桌面端不直接执行 npx/MCP/Docker/脚本。
- [ ] 生成 Phase 04 验收报告，包含投影证据、运行证据、行为证据。

## Follow-up Scope

Phase 05 或后续阶段可以考虑：

- 桌面端更完整的调用记录和工具时间线。
- 桌面端任意脚本 Tool 编辑、执行和更强的沙盒策略。
- 桌面端对 provider secret vault 的专用管理界面。

## Ambiguity Report

After user decisions on 2026-06-03:

- Goal Clarity: 0.91
- Boundary Clarity: 0.88
- Constraint Clarity: 0.86
- Acceptance Criteria: 0.84
- Ambiguity: 0.12

Gate status: passed. Remaining ambiguity is implementation-level UI composition and exact provider smoke fixture selection, which belongs in PLAN and execution.
