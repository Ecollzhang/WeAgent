# 006 Default Tool Catalog and Configurable Provider Tools SPEC

**Created:** 2026-06-02
**Ambiguity score:** 0.08 (gate: <= 0.20)
**Requirements:** 12 locked

## Goal

让默认工具集只展示真实可用或可配置后可用的 Tool：移除未完成空壳，降级代码生成，并为网页搜索、图像分析、图像生成、数据库查询提供前端配置入口、运行链路和 Docker 验收测试。

## Background

当前 `backend/app/services/builtin_tool_definitions.py` 已经把内置 Tool 统一为 `weagent.tool/v1` manifest，并在 `backend/app/sandbox/container/tools/__init__.py` 中实现了代码搜索、文件操作、HTTP 抓取、API 调用、本地数据分析、图像信息、受限命令和 Git 只读操作。

仍然存在几个产品边界问题：

- `代码生成` 当前是 `deferred`，本质属于 Agent/Skill 的模型编排能力，不适合作为确定性 Tool。
- `网页搜索`、`数据库查询` 当前是 `requires_config`，但缺少前端配置窗口和配置完成后的真实运行链路。
- `图像分析` 当前是 `deferred`，但用户希望它与网页搜索、数据库查询一样通过配置后可运行。
- `图像生成` 还没有默认能力定义，但它应属于需配置的 provider/MCP 能力，而不是未完成空壳。
- 前端不应展示无法配置、无法运行、也没有明确替代路径的未完成 Tool。

## Requirements

1. **Code generation downgraded**: `代码生成` 不再作为默认 Tool 可绑定或可调用能力出现。
   - Current: `code_generator` 作为 `deferred` Tool 存在于内置定义中，虽然不可执行，但仍可能在工具集页面造成“这是一个工具”的误解。
   - Target: `code_generator` 从工具集前端列表和 Agent 能力选择中移除；如需保留迁移兼容，仅在后端标记为 `hidden/deprecated`，并在文档中指向代码类 Skill 或 Agent workflow。
   - Acceptance: 工具集页面、Agent 创建/编辑能力选择器、分类计数均不展示 `代码生成`；已有历史绑定不会崩溃，但不能新绑定或调用。

2. **No unfinished frontend tools**: 前端不展示没有运行链路、没有配置入口、没有验收路径的未完成 Tool。
   - Current: `deferred` 和 `requires_config` 的视觉差异容易不足，用户可能把未实现能力理解为可用能力。
   - Target: `deferred/hidden` Tool 不进入工具集主列表；`requires_config` 只有在存在配置 UI 和运行计划时才允许展示。
   - Acceptance: 前端列表只包含 `implemented`、`configured`、或有配置入口的 `requires_config`；没有配置入口的 Tool 不显示也不计数。

3. **Configurable provider class**: 网页搜索、图像分析、图像生成、数据库查询被统一定义为“需配置能力”，配置完成后必须能运行。
   - Current: 这些能力要么不存在，要么只是静态状态说明。
   - Target: 四类能力均有可保存的用户级或系统级 provider/MCP 配置记录；配置通过校验后，能力状态从 `requires_config` 变为 `configured` 或可绑定状态。
   - Acceptance: 每类能力至少有一个配置 profile 可以通过 API 保存、校验、绑定到 Agent，并触发 sandbox 内真实调用。

4. **Frontend configuration window**: 工具集页面提供配置窗口和交互流程。
   - Current: Tool 详情面板能展示状态和文档，但不能配置 provider/MCP/DB profile。
   - Target: 对 `web_search`、`image_analysis`、`image_generation`、`database_query` 展示“配置”入口；右侧详情或弹窗内提供表单、校验、测试连接、保存、启用/停用、查看最近调用记录。
   - Acceptance: 用户能从前端完成新增配置、测试配置、保存配置、重新测试、删除/停用用户配置；内置 Tool 本体仍不可编辑。

5. **Bindable only after valid configuration**: 需配置能力未配置前不可绑定到 Agent，配置有效后才可绑定。
   - Current: `requires_config` 只是显示状态，绑定规则不完整。
   - Target: Agent 创建/编辑页只允许选择已实现 Tool 或已通过配置校验的 provider-backed Tool；未配置项显示在工具集页面但不出现在可勾选列表，或以禁用状态展示原因。
   - Acceptance: 未配置 `web_search/image_analysis/image_generation/database_query` 不能被绑定；配置通过后可以被绑定，并携带 pinned version 和授权快照。

6. **Runtime gate and call records**: 配置型 Tool 调用必须经过绑定、权限、配置解析和审计记录。
   - Current: 已实现内置 Tool 有 call record，但 provider-backed Tool 还没有统一运行链路。
   - Target: sandbox 调用时解析 Agent 绑定、provider profile、权限、secret alias、MCP runtime 或 provider adapter；成功和失败均写入 `.weagent/runs/<run_id>/calls.jsonl` 并可同步到 DB。
   - Acceptance: 四类配置型 Tool 的成功调用和失败调用都能查到 `CapabilityCallRecord`，包含 tool name、profile id/alias、权限摘要、输入摘要、输出摘要、错误原因和时间戳。

7. **Web search configurable runtime**: 网页搜索配置后必须能执行一次搜索。
   - Current: `web_search` 没有 provider/MCP 配置入口，建议替代为 `http_fetch`。
   - Target: 支持至少一种可测试配置路径：MCP search server 或 HTTP search provider profile。配置中声明 tool name、endpoint/command、权限和 secret alias。
   - Acceptance: Docker smoke 使用 fixture MCP 或本地 HTTP fixture 完成一次 search 调用，返回结构化结果列表，并写入 call record。

8. **Image analysis configurable runtime**: 图像分析配置后必须能对 workspace 图像执行一次分析。
   - Current: 只有 `image_info` 是确定性内置 Tool；`image_analysis` 被标为 deferred。
   - Target: `image_analysis` 改为 `requires_config`，支持 MCP vision tool 或 model/provider profile；输入为 workspace 图像路径和问题/任务。
   - Acceptance: Docker smoke 使用 fixture vision MCP/provider 对样例图像返回结构化分析文本；真实 provider UAT 在存在凭证时可以运行同一路径。

9. **Image generation configurable runtime**: 新增图像生成作为需配置能力，生成结果必须落地为 workspace 文件。
   - Current: 没有默认 `image_generation` Tool 定义。
   - Target: 新增 `image_generation` 或 `image_generate` Tool，状态为 `requires_config`；配置后调用 provider/MCP 生成 PNG/JPEG/WebP 文件，并作为 image artifact 上报。
   - Acceptance: Docker smoke 使用 fixture image generator 生成一个有效图片文件；调用记录包含输出文件路径，前端消息/工件展示能打开该图片。

10. **Database query configurable runtime**: 数据库查询配置后必须以只读方式运行。
    - Current: `sqlite_query_readonly` 可读取 workspace SQLite 文件；`database_query` 作为外部 DB 查询需要 profile 但没有配置和运行链路。
    - Target: `database_query` 支持 DB profile，包括驱动类型、连接 alias、只读策略、允许 schema/table、查询超时和最大行数；secret 不直接投影到 `.weagent/*`。
    - Acceptance: 测试 profile 能执行 `SELECT` 并拒绝 `INSERT/UPDATE/DELETE/DDL`；Docker smoke 至少覆盖 SQLite fixture，环境存在 MySQL/Postgres 测试 URL 时覆盖外部 DB。

11. **Permission and secret boundary**: 配置型 Tool 的权限和密钥必须显式。
    - Current: `network/use_secret/read_workspace/write_workspace` 已存在，但配置型能力还没有细分授权说明。
    - Target: 每类配置型 Tool 声明 required/optional permissions；secret 只以 alias/profile 引用进入 runtime projection，不把明文写入 `.weagent/*` 或 call record。
    - Acceptance: `.weagent/tools/*/manifest.json` 和 Agent permission view 不含明文 secret；缺少 `network/use_secret/read_workspace/write_workspace` 时调用被拒绝并记录失败。

12. **Verification and migration safety**: 新目录规则不能破坏现有已实现 Tool、MCP 导入、Skill 导入和 Agent 绑定。
    - Current: 005 已经覆盖默认 Tool runtime，但 006 会改变可见性、绑定规则和配置型能力。
    - Target: 保留现有 implemented Tool 行为；迁移旧 `code_generator` 或 deferred 绑定时显示兼容提示而不是报错；现有 UI 合同测试和 Docker smoke 更新后通过。
    - Acceptance: 后端 focused tests、前端 contract tests、Docker fixture smoke 均通过；旧数据中隐藏 Tool 不导致列表、详情、Agent 编辑页崩溃。

## Boundaries

**In scope:**

- 调整默认 Tool 目录和前端可见性规则。
- 降级/隐藏 `代码生成`，并从 Agent 可绑定列表移除。
- 新增或调整 `web_search`、`image_analysis`、`image_generation`、`database_query` 为需配置能力。
- 前端配置窗口：创建、编辑、测试、保存、启用/停用配置。
- 后端配置 profile/API/schema/service。
- sandbox/provider/MCP 调用链路和 call record。
- Docker fixture tests 证明配置后可运行。
- 文档和 UAT 指南说明哪些是内置确定性 Tool，哪些是配置型 Tool。

**Out of scope:**

- 直接实现通用 LLM 代码生成 Tool。代码生成属于 Skill/Agent workflow。
- 默认赠送真实商业搜索、视觉、图像生成 provider 凭证。凭证由用户配置或测试环境提供。
- 允许用户编辑系统内置 Tool 的 handler/manifest/permissions。
- 实现任意数据库写入、DDL、长期连接池管理或生产级数据库管理后台。
- 实现任意图像模型市场。只做 provider/MCP 配置与调用边界。
- 将配置兼容映射写入 `.claude/*`、`.codex/*` 或 `.mcp.json`。本阶段仍以 `.weagent/*` 为 canonical projection。

## Constraints

- 所有配置型 Tool 执行仍发生在 sandbox/container 内。
- DB 是能力、配置、绑定和审计记录的 canonical source。
- `.weagent/*` 只能包含 profile alias、manifest、tool index、权限视图和非敏感运行说明。
- `requires_config` 能力必须有配置入口，否则不能显示在前端。
- 配置测试必须有超时、输出截断、错误原因和审计记录。
- 前端不能把 raw manifest 作为主要用户说明；manifest 只在开发者详情中查看。
- Agent 能力选择器必须使用后端返回的 bindable/configured 状态，不能只靠前端过滤。

## Acceptance Criteria

- [ ] `代码生成` 不再出现在工具集主列表、分类计数和 Agent 可绑定能力选择器中。
- [ ] 没有配置入口的 `deferred/hidden` Tool 不在前端展示。
- [ ] `web_search`、`image_analysis`、`image_generation`、`database_query` 在工具集页面有配置入口和状态说明。
- [ ] 未配置的配置型 Tool 不可绑定；配置校验通过后可绑定。
- [ ] 四类配置型 Tool 都能通过 fixture 配置在 Docker sandbox 中完成一次成功调用。
- [ ] 四类配置型 Tool 都有至少一个失败路径测试，并写入失败 call record。
- [ ] 明文 secret 不出现在 `.weagent/*`、前端详情、日志和 call record 中。
- [ ] 数据库查询只允许只读 SQL，并验证写入/DDL 被拒绝。
- [ ] 图像生成输出有效图片文件，并能作为 image artifact 展示。
- [ ] 现有 implemented Tool 的后端测试、前端合同测试和 Docker smoke 继续通过。

## Ambiguity Report

| Dimension | Score | Min | Status | Notes |
|---|---:|---:|---|---|
| Goal Clarity | 0.94 | 0.75 | met | 目标明确为清理默认目录，并让需配置能力配置后可运行。 |
| Boundary Clarity | 0.93 | 0.70 | met | 明确隐藏代码生成、未完成不展示、配置型能力保留。 |
| Constraint Clarity | 0.88 | 0.65 | met | secret、sandbox、DB canonical、前端可见性和绑定约束明确。 |
| Acceptance Criteria | 0.90 | 0.70 | met | 覆盖 UI、API、runtime、Docker smoke、失败路径和迁移安全。 |
| **Ambiguity** | **0.08** | **<= 0.20** | met | 可进入计划阶段。 |

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|---|---|---|---|
| 1 | Researcher | 当前默认 Tool 哪些是真实现，哪些是空壳？ | implemented Tool 保留；`code_generator`、`image_analysis`、`web_search`、`database_query` 需要重新定边界。 |
| 2 | Simplifier | 代码生成是否应该作为 Tool？ | 代码生成降级为 Skill/Agent workflow，不作为默认可绑定 Tool。 |
| 3 | Boundary Keeper | 未完成能力是否还显示在前端？ | 未完成且无配置入口的能力不显示；配置型能力可以显示但必须有配置窗口。 |
| 4 | Failure Analyst | 配置型能力如何避免继续成为空壳？ | `web_search`、`image_analysis`、`image_generation`、`database_query` 必须配置后能运行，并有 Docker fixture 测试。 |
| 5 | Seed Closer | Provider/MCP 边界如何锁定？ | 搜索、图像分析、图像生成、数据库查询统一为 provider/MCP-backed configurable Tools。 |

---

*Phase: 006-default-tool-catalog*
*Spec created: 2026-06-02*
*Next step: implement from `006-default-tool-catalog-PLAN.md` after review.*
