# Phase 03: Toolset Desktop Merge - SPEC

**Created:** 2026-06-02
**Status:** Ready for planning
**Base branch:** `origin/feature/desktop_app_support_v1.0.6`
**Module source:** `origin/feature/toolset`
**Target branch:** `combine/toolset_v1.1.0`

## Purpose

将 `feature/toolset` 已完成的能力库/工具集模块嵌入到 `desktop_app_support` 的新版运行底座中。合并后的系统以 desktop 分支的 sandbox service/proxy、多 provider runtime、端口和运行结构为主干，同时保留 toolset 分支的 Skill/MCP/Plugin/Tool 数据模型、Web 管理界面、Agent 绑定能力和 `.weagent/*` runtime projection。

## Current State

- `desktop_app_support` 已引入新版 `backend/app/sandbox/container/providers/*`，支持 Claude Code、Codex、OpenCode provider runner，并包含 service proxy、preview token、端口 `5002`、桌面端客户端目录 `clients/desktop`。
- `desktop_app_support` 的 Web `Tools.vue` 仍偏 demo/旧工具管理形态，没有完整的 Skill/MCP/Plugin/Tool 并行能力库。
- `toolset` 已实现 Capability DB 模型、Toolset 分类、Skill Markdown/zip/npx/MCP manifest 导入、安全审查、Agent capability binding、provider config、内置 Tool runtime、`.weagent/*` 投影和 Web 前端能力库页面。
- 两个分支在 `backend/app/sandbox/*`、`backend/app/models/__init__.py`、`frontend/src/components/AgentEditForm/index.vue`、`.planning/*` 上存在真实冲突，不能简单选择一边。

## Locked Requirements

### REQ-16: 合并分支与基底

- Current state: `feature/toolset` 和 `feature/desktop_app_support_v1.0.6` 是并行功能分支。
- Target state: 新建并使用 `combine/toolset_v1.1.0`，以 `origin/feature/desktop_app_support_v1.0.6` 为基底，再合并 `origin/feature/toolset`。
- Acceptance criterion: `git log --first-parent combine/toolset_v1.1.0` 显示 desktop 分支为主线，最终合并提交包含 toolset 模块。

### REQ-17: Web 前端可用，桌面端 UI 不扩展

- Current state: desktop 分支新增 `clients/desktop`，toolset 分支主要实现 Web 前端 `frontend` 的能力库体验。
- Target state: 本阶段只保证 Web 前端 `frontend` 的工具集/能力库管理、导入、配置和 Agent 绑定可用；桌面端客户端仅继承服务端能力，不新增工具集 UI。
- Acceptance criterion: `frontend` 能打开工具集页面并完成核心 UAT；`clients/desktop` 不出现新增工具集页面或未验证 UI。

### REQ-18: Provider runtime 以 desktop 架构为准

- Current state: desktop 分支使用 `backend/app/sandbox/container/providers/*`；toolset 分支包含旧 sandbox capability runtime 和 MCP runtime。
- Target state: 保留 desktop provider runner、service manager、host proxy、agent workspace 架构，不恢复旧 `backend/app/adapters/*` 作为主运行入口；toolset 的能力投影、MCP runtime、内置 Tool handler 作为附加能力接入。
- Acceptance criterion: sandbox agent 仍通过 `ProviderRunnerFactory` 创建 provider；工具集注入不会破坏 Claude/Codex/OpenCode provider runner。

### REQ-19: Capability 数据模型和 API 完整迁入

- Current state: desktop 分支缺少 capability/toolset 相关模型、schema、controller、service。
- Target state: 迁入 `Capability`、`CapabilityVersion`、`CapabilityVersionAsset`、`AgentCapabilityBinding`、`CapabilityCallRecord`、`ToolProviderConfig`、`ToolsetCategory` 等模型，并注册 `/api/capabilities`、`/api/agents/*/capabilities`、`/api/toolsets` 等 API。
- Acceptance criterion: 后端启动后 DB 表可创建/迁移，能力列表、创建 Skill、导入预览、确认导入、绑定 Agent、provider config 创建/测试/保存 API 均返回预期结构。

### REQ-20: Agent 创建/编辑同时支持 provider 与 capability binding

- Current state: desktop 分支 Agent 编辑包含 provider/adapter 选择；toolset 分支 Agent 编辑包含 capability selector。
- Target state: `AgentEditForm` 同时保留 provider 选择和 capability 选择；保存 Agent 时不会丢失 `adapter_name`、`tool_ids` 或 capability bindings。
- Acceptance criterion: Web 前端创建/编辑 Agent 后，后端 Agent provider 配置和绑定的 Skill/MCP/Plugin/Tool 都能在刷新后保持。

### REQ-21: `.weagent/*` canonical projection 注入 sandbox

- Current state: toolset 分支可生成 `.weagent/capabilities/index.json`、`.weagent/skills/*`、`.weagent/mcp/*`、`.weagent/plugins/*`、`.weagent/tools/*`、`.weagent/agents/<agent_id>/*`；desktop 分支的 agent workspace 迁到 `/workspace/agents/<workspace_name>`。
- Target state: 创建 sandbox session 或添加 agent 时，根据 Agent 绑定能力生成 session-local runtime projection，并写入容器 `/workspace/.weagent/*`，每个 Agent 读取自己的 view。
- Acceptance criterion: sandbox 内可看到 `.weagent/capabilities/index.json`、`.weagent/agents/<agent_id>/capabilities.json`、`skill-index.json`、`tool-index.json`、`permissions.json`，Agent system prompt 或 bootstrap 中包含能力入口说明。

### REQ-22: MCP/Skill/Tool 调用记录真实存在

- Current state: toolset 分支已有 MCP stdio runtime 和 built-in Tool call audit；desktop 分支有 tool registry 和 service proxy。
- Target state: 至少保留 Skill runtime projection、一个 npx/manifest MCP server 的安装启动/列工具/调用记录链路，以及内置 Tool 调用记录；调用记录写入 DB 或 `.weagent` run records 后可同步。
- Acceptance criterion: UAT 能完成一次 MCP tool list/call 或最小 smoke，并能看到对应 call record；内置 implemented/configured tool 调用被记录。

### REQ-23: 需配置 Tool 必须有配置窗口

- Current state: toolset 分支把 Web Search、Image Analysis、Image Generation、Database Query 等定义为需配置能力。
- Target state: Web 前端对需配置 Tool 提供创建、测试、保存、启用/停用配置窗口；配置保存到 DB 并可进入 sandbox projection。
- Acceptance criterion: 用户可在工具集页面打开配置窗口，保存后刷新仍存在；绑定到 Agent 后 projection 中出现 provider config 快照。

### REQ-24: 内置 Tool 展示必须只显示可用或可配置项

- Current state: toolset 分支曾处理 hidden/deferred tool 与 tab count 不一致问题；desktop 分支旧 Tools 页面可能展示空壳。
- Target state: 未实现且不可配置的内置 Tool 不在 Web 前端展示或计数；需要配置但可运行的 Tool 显示为需配置能力；已实现 Tool 显示为已实现。
- Acceptance criterion: Tool tab 数量与实际列表一致，不显示空分类/空壳 tool；代码生成类 deferred tool 不作为可绑定 Tool 展示。

### REQ-25: `.planning` 以 desktop 顶层为主，toolset 作为 Phase 03

- Current state: desktop 分支已有 Phase 01/02；toolset 分支原本使用 `001-toolset`。
- Target state: 合并后保留 desktop 顶层 `.planning` 语境，新增 `03-toolset`；toolset 旧规划资料如需保留，应归档到 `03-toolset` 下或以合并说明引用，不覆盖 01/02 顶层状态。
- Acceptance criterion: `.planning/phases` 至少包含 `01-agent-adapter-streaming-factory`、`02-conversation-context-system`、`03-toolset`，且顶层 `ROADMAP.md`/`REQUIREMENTS.md` 能索引 Phase 03。

### REQ-26: 验证以真实功能可用优先

- Current state: 两个分支各自测试覆盖不同，合并后旧测试可能因运行架构变化失效。
- Target state: 修复测试时优先保证真实业务路径可用，而不是机械保留旧测试断言；被移除或调整的旧测试必须有等价的新断言覆盖。
- Acceptance criterion: 后端核心 pytest、前端 build、工具集 API/UI contract、sandbox smoke 至少形成一组可复现验证清单。

## In Scope

- 创建 `combine/toolset_v1.1.0` 合并工作分支。
- 解决 desktop 与 toolset 的 Git 冲突。
- 迁入 capability/toolset 模型、API、服务、schema、前端页面和 Agent binding。
- 将 toolset runtime projection、MCP runtime、内置 Tool handler 接到 desktop sandbox provider runtime。
- 保留 Web 前端工具集管理、provider config、Agent 创建/编辑绑定能力。
- 保留 desktop 端口、sandbox service/proxy、多 provider runner 和桌面端目录。
- 更新 `.planning` 为 Phase 03 toolset。
- 运行并记录合并后的后端、前端、sandbox 验证。

## Out of Scope

- 不新增桌面端工具集 UI。
- 不把旧 `backend/app/adapters/*` 恢复为主运行时。
- 不实现任意用户脚本 Tool 的完整执行沙盒。
- 不把 deferred/不可配置 Tool 伪装成可运行能力。
- 不解决与本合并无关的产品功能扩展，例如新的内置工具清单大扩容。
- 不改变 desktop 分支已确定的后端端口和 service proxy 行为。

## Acceptance Criteria

- [ ] 分支 `combine/toolset_v1.1.0` 基于 `origin/feature/desktop_app_support_v1.0.6`。
- [ ] `origin/feature/toolset` 合并后无未解决冲突。
- [ ] Web `frontend` 可打开工具集页面并显示分类下 Skill/MCP/Plugin/Tool 四类。
- [ ] 用户可创建/导入 Skill，保存到 DB，并在 Agent 创建/编辑时绑定。
- [ ] 需配置 Tool 可创建、测试、保存、启用/停用配置。
- [ ] Agent 绑定能力后创建 sandbox session，容器内生成 `.weagent/*` projection。
- [ ] sandbox provider runner 仍支持 Claude/Codex/OpenCode，不被 toolset 旧 adapter 覆盖。
- [ ] 至少一个 MCP manifest/npx 路径能被安装、启动、列工具并记录一次调用，或保留明确 smoke fixture。
- [ ] implemented/configured Tool 调用有审计记录。
- [ ] 后端核心 pytest 和前端 build 通过，Docker smoke 若环境可用则通过。
- [ ] `.planning/phases/03-toolset` 存在并包含本 SPEC/PLAN。

## Ambiguity Report

After user decisions on 2026-06-02:

- Goal Clarity: 0.93
- Boundary Clarity: 0.90
- Constraint Clarity: 0.86
- Acceptance Criteria: 0.84
- Ambiguity: 0.10

Gate status: passed. The remaining ambiguity is implementation-level conflict detail, which belongs in PLAN and merge execution rather than SPEC.
