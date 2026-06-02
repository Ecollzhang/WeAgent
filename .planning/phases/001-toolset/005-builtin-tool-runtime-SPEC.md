# 005 Built-in Tool Runtime and Markdown Contract SPEC

**Created:** 2026-06-01
**Ambiguity score:** 0.10 (gate: <= 0.20)
**Requirements:** 11 locked

## Goal

WeAgent 内置 Tool 从“工具集卡片和最小调用记录”升级为按分类可绑定、可渐进披露、可真实调用、可权限控制、可审计的 runtime capability；每个功能分类都有清晰的必要 Tool，未实现项不得伪装成可用能力。

## Background

当前系统已经把 `Skill`、`MCP`、`Plugin`、`Tool` 作为并列 `Capability` 保存到 DB，并能在工具集页面按分类展示和绑定到 Agent。`backend/app/services/tool_service.py` 中已有 `代码生成`、`代码审查`、`文件操作`、`网页搜索`、`数据库查询`、`终端执行`、`Git操作` 等内置 Tool 模板；`capability_service.seed_builtin_tool_capabilities()` 会把这些模板种为 `Capability(type="tool")`。

但真实 sandbox runtime 目前只注册了 `read_file`、`write_file`、`run_command`、`report_progress`、`list_files` 五个基础 callable。Capability resolver 只把 `file_operations` 映射到文件读写列表，把 `terminal` 映射到 `run_command`。其他内置 Tool 多数仍是展示壳，没有专属 handler、参数 schema、`TOOL.md` 说明、渐进式披露索引或可验收调用链路。Prompt 也会暴露 registry 中所有基础工具，而不是只展示当前 Agent 已绑定和授权的 Tool。

## Requirements

1. **Tool contract**: 每个 Tool capability 版本必须有机器可读 manifest 和 Agent 可读 Markdown 说明。
   - Current: 内置 Tool manifest 只有 `{"runtime": "builtin", "tool": {...}}`，没有统一 schema、handler、参数、输出、审计或 Markdown 使用说明。
   - Target: Tool 版本使用 `weagent.tool/v1` 契约，至少包含 `runtime`、`handler`、`tool_names`、`input_schema`、`output_schema`、`permissions`、`audit`、`ui.status`，并保存对应 `TOOL.md`。
   - Acceptance: 任一内置 Tool 的详情能显示 `TOOL.md` 和简化 manifest；后端测试能断言 manifest 字段完整且 `TOOL.md` 非空。

2. **Built-in immutability**: 系统内置 Tool 对用户只读。
   - Current: UI 已避免删除内置能力，但内置 Tool 没有明确的“不可编辑 TOOL.md/manifest/handler/权限”契约。
   - Target: 用户不能编辑、删除或直接覆盖内置 Tool 的 `TOOL.md`、manifest、handler、权限声明；平台升级内置 Tool 时生成新版本，Agent 绑定默认仍固定旧版本并提示可升级。
   - Acceptance: UI 不展示内置 Tool 编辑/删除入口；API 拒绝用户修改内置 Tool 内容；已有 Agent 绑定不会因平台 seed 更新而静默改变版本。

3. **Progressive disclosure**: Tool 说明采用和 Skill 类似的渐进式披露。
   - Current: `.weagent/*` 只完整投影 Skill/MCP/Plugin；Tool 没有 `.weagent/tools/<runtime_id>/TOOL.md` 或 per-Agent `tool-index.json`。
   - Target: Session projection 写入 `.weagent/tools/<runtime_id>/TOOL.md`、`.weagent/tools/<runtime_id>/manifest.json`，并为每个 Agent 写入 `.weagent/agents/<agent_id>/tool-index.json`。Agent 初始只看到摘要、权限、工具名和 `doc_path`，需要时再读取完整 `TOOL.md`。
   - Acceptance: 创建绑定 Tool 的 Agent 后，sandbox workspace 中存在 `tool-index.json` 和对应 Tool 文档；Agent prompt 不再无条件列出未绑定 Tool 的完整说明。

4. **Bound-only execution**: Agent 只能调用已绑定且授权的 Tool。
   - Current: `ToolRegistry.call_from_agent()` 在找不到 capability binding 时仍可能执行 legacy registry tool，保留了迁移期兼容路径。
   - Target: capability-aware session 中，Tool 调用必须先解析当前 Agent 的绑定和授权；未绑定或权限不足时拒绝执行并返回结构化错误。
   - Acceptance: 测试覆盖未绑定 `read_file`、权限不足 `write_file`、未实现 tool_name 三种失败；失败不会执行副作用。

5. **Call audit parity**: 所有真实内置 Tool 调用都写入统一 call record。
   - Current: 文件 Tool 的 JSONL/DB 同步已有覆盖，但其他内置 Tool 没有专属记录链路。
   - Target: 每个 implemented Tool 调用记录 `session_id`、`run_id`、`agent_id`、`capability_id`、`capability_version_id`、`tool_name`、`permissions_used`、`input_summary`、`output_summary`、`status`、`error`、开始/结束时间。
   - Acceptance: 至少每个功能分类一个 implemented Tool 有完成和失败调用记录测试；DB sync 后能查询到对应 `CapabilityCallRecord`。

6. **Category coverage**: 每个功能分类必须有明确的必要 Tool 状态。
   - Current: 代码、文件、网络、数据、图像、系统分类都有展示项，但很多项为空壳；`自定义`分类混合了承载用户能力和系统内置推荐的语义。
   - Target: 内置分类按下列口径整理：
     - `代码工具`: `code_search`、`code_review_scan`。
     - `文件与文档`: `read_file`、`write_file`、`list_files`、`document_text_extract`。
     - `网络与检索`: `http_fetch`、`api_request`；`web_search` 仅在配置搜索 provider 或 MCP 时标记可用。
     - `数据处理`: `csv_profile`、`json_query`、`sqlite_query_readonly`。
     - `图像/多媒体`: `image_info`，可选 `image_convert`；AI 图像理解不作为内置 v1。
     - `系统与终端`: `run_command_safe`、`git_status`、`git_diff`、`git_log`、`report_progress`。
     - `自定义`: 不是功能分类，不强制内置执行 Tool；只承载用户自建/导入 Tool，并提供创建入口或模板说明。
   - Acceptance: 工具集页面每个功能分类至少展示一个 `已实现` Tool；未实现或外部依赖项显示 `未实现/需要配置/建议 MCP`，不计入“可调用”验收。

7. **No fake capabilities**: 未实现内置 Tool 必须显式标记状态。
   - Current: 卡片上看不出哪些 Tool 只是定义，用户容易以为全部可调用。
   - Target: Tool manifest 和 UI 支持 `implemented`、`partial`、`requires_config`、`deferred` 四种状态；详情展示为什么不可用以及建议替代方案。
   - Acceptance: `代码生成`、`网页搜索`、`数据库查询` 等如果没有真实 handler 或配置，不展示为“已实现”；用户无法对 deferred Tool 发起 runtime call。

8. **Risk-scoped handlers**: 高风险能力必须拆分为安全子 Tool。
   - Current: `Git操作`、`终端执行`、`数据库查询` 都是大而泛的展示项，权限粒度过粗。
   - Target: Git v1 只做只读 `git_status/git_diff/git_log`；命令执行采用 `run_command_safe` 并经过 allowlist/denylist 与超时限制；数据库 v1 只支持显式配置 profile 的只读查询，未配置时标为 `requires_config`。
   - Acceptance: Git 写操作、任意 shell、数据库写入在本阶段不可用；尝试调用会返回拒绝原因并记录失败。

9. **User Tool boundary**: 用户自建 Tool 和内置 Tool 使用同一契约，但执行权限更严格。
   - Current: 用户已经能创建/导入能力，但完整用户脚本 Tool runtime 尚未定型。
   - Target: 用户 Tool 可以编辑 `TOOL.md` 和 manifest 草稿；脚本类用户 Tool 必须经过语法检查、安全审计、权限确认和发布后才能绑定执行。若本阶段不实现脚本执行，也必须在 UI/API 明确显示为后续能力。
   - Acceptance: 用户不能通过编辑 Markdown 绕过 manifest 权限；用户 Tool draft 未发布前不会进入 Agent runtime projection。

10. **Legacy migration**: 旧 `AgentTool` 模板与新 Tool capability 不得继续分叉。
    - Current: 旧 `/api/tools`、`agent_tools`、`tool_ids` 和新 `Capability(type=tool)` 并存。
    - Target: 内置 Tool 定义有单一 canonical source；旧 `AgentTool` 只作为兼容视图或迁移来源，不再产生新的空壳 Tool。
    - Acceptance: Seed 不重复创建同名内置 Tool；工具集页使用 capability-backed Tool；Agent 旧 `tool_ids` 显示不回归。

11. **Verification and UAT**: 真实调用必须能在 Docker sandbox 中验收。
    - Current: UAT 已能打开 Docker 和页面，但内置 Tool 真实调用范围不完整。
    - Target: 提供 005 UAT 指南，覆盖绑定 Tool、启动 session、调用每类代表 Tool、查看 `.weagent/tools`/`tool-index.json`、查看 call record 和失败记录。
    - Acceptance: 后端测试、前端契约测试、sandbox smoke、Docker UAT 指南均能证明“不是空壳”。

## Boundaries

**In scope:**
- 定义 `weagent.tool/v1` manifest 契约和 `TOOL.md` 说明契约。
- 内置 Tool 只读、版本化、可升级提示。
- `.weagent/tools/<runtime_id>/TOOL.md`、`manifest.json` 和 per-Agent `tool-index.json` projection。
- 已绑定/已授权 Tool 才能执行的 runtime gate。
- 每个功能分类至少一个真实 implemented Tool；自定义分类作为用户能力容器。
- Tool 状态展示：`implemented`、`partial`、`requires_config`、`deferred`。
- 文件、代码搜索、Git 只读、受限命令、HTTP fetch/API request、CSV/JSON/SQLite 只读、图像元信息、进度上报的首批 handler。
- JSONL call record 和 DB sync 回归。
- 工具集 UI 的内置 Tool 文档、状态、权限、调用边界展示。

**Out of scope:**
- 任意用户脚本 Tool 的完整执行平台 - 需要更完整 sandbox、安全审计和资源限制，可在后续阶段实现。
- 内置 AI 代码生成、AI 图像理解、通用网页搜索 - 需要模型/provider/MCP 配置，不应伪装成确定性内置 Tool。
- Git 写操作、commit、push、branch mutation - 风险高，后续单独授权和确认。
- 数据库写入和任意生产数据库连接 - 需要 DB profile、secret 管理和只读/写入隔离。
- 远程 marketplace/插件商店浏览 - 与 003 导入能力不同，不属于本阶段。
- `.claude/*`、`.codex/*` 兼容映射 - 仍按既定边界只写 `.weagent/*`。

## Constraints

- DB 仍是 Tool definition、version、binding、authorization、call record 的 canonical source。
- Session workspace 仍是临时投影；`.weagent/*` 可以由每次 session 重建。
- 内置 Tool 不能通过用户编辑改变平台 handler 或权限。
- 所有执行发生在 sandbox/container 内，不在 host backend 执行任意 Tool 代码。
- 对外网络 Tool 必须显式声明 `network` 权限；涉及 secret 的 API request 必须声明 `use_secret`。
- `run_command_safe` 必须有 timeout、cwd 限制、命令 allowlist/denylist、输出截断。
- UI 不能把 raw manifest 当成主要用户说明；manifest 可在开发者详情中查看。

## Acceptance Criteria

- [ ] 任一内置 Tool version 都有 `weagent.tool/v1` manifest 和 `TOOL.md`。
- [ ] 内置 Tool 在 UI/API 中不可编辑、不可删除。
- [ ] Sandbox projection 写入 `.weagent/tools/<runtime_id>/TOOL.md`、`manifest.json` 和 `.weagent/agents/<agent_id>/tool-index.json`。
- [ ] Agent 只能调用已绑定且授权的 Tool；未绑定和权限不足会拒绝执行。
- [ ] 每个功能分类至少有一个 `implemented` Tool；自定义分类只作为用户 Tool 容器。
- [ ] `代码生成`、`网页搜索`、`数据库查询` 等未完成项不会显示为可直接调用。
- [ ] Git v1 只支持只读 Tool；shell 执行使用受限 `run_command_safe`。
- [ ] 每类代表 Tool 的成功/失败调用写入 JSONL，并能同步为 DB `CapabilityCallRecord`。
- [ ] 工具集详情展示 Tool 状态、权限、参数说明、`TOOL.md` 文件视图和建议替代方案。
- [ ] Docker UAT 指南覆盖真实调用和 call record 验收。

## Ambiguity Report

| Dimension | Score | Min | Status | Notes |
|---|---:|---:|---|---|
| Goal Clarity | 0.93 | 0.75 | met | 目标明确为内置 Tool 从展示壳升级为真实 runtime capability。 |
| Boundary Clarity | 0.91 | 0.70 | met | 明确排除任意用户脚本、AI 生成/视觉、Git 写操作、DB 写入和兼容映射。 |
| Constraint Clarity | 0.86 | 0.65 | met | 约束覆盖 DB canonical、sandbox-only、权限、网络、secret、命令限制。 |
| Acceptance Criteria | 0.89 | 0.70 | met | 验收覆盖 manifest、Markdown、projection、runtime gate、分类、审计和 UAT。 |
| **Ambiguity** | **0.10** | **<= 0.20** | met | 满足 spec gate。 |

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|---|---|---|---|
| 1 | Researcher | 当前内置 Tools 是不是空壳？ | 多数是展示壳；真实 runtime 只有少数基础 callable。 |
| 2 | Simplifier | Tool 应做成 Markdown、脚本还是其他？ | 采用 manifest + handler + `TOOL.md`，Markdown 必要但不承担执行契约。 |
| 3 | Boundary Keeper | 内置 Tool 是否允许用户编辑？ | 内置 Tool 只读；用户自建 Tool 可编辑但必须走审计和发布。 |
| 4 | Failure Analyst | 分类里是否可以继续放空工具？ | 不可以；每个功能分类要有必要 Tool，未实现项必须标状态，不可伪装可用。 |
| 5 | Seed Closer | 自定义分类是否需要系统内置 Tool？ | 自定义不是功能分类，只承载用户自建/导入 Tool，不强制内置执行项。 |

---

*Phase: 005-builtin-tool-runtime*
*Spec created: 2026-06-01*
*Next step: implement from `005-builtin-tool-runtime-PLAN.md` after user approval.*
