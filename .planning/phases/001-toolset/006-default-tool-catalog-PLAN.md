# 006 Default Tool Catalog and Configurable Provider Tools PLAN

## Purpose

执行 `006-default-tool-catalog-SPEC.md`：清理默认 Tool 目录，隐藏未完成空壳，降级代码生成，并让网页搜索、图像分析、图像生成、数据库查询从“状态说明”升级为可配置、可绑定、可运行、可审计的 provider/MCP-backed Tools。

## Current Baseline

- `backend/app/services/builtin_tool_definitions.py` 是内置 Tool canonical source。
- `backend/app/sandbox/container/tools/__init__.py` 已实现确定性 Tool runtime。
- `frontend/src/views/Tools.vue` 已有工具集分类、类型 tab、详情面板、状态标签和文件视图。
- `frontend/src/components/AgentEditForm/index.vue` 已有能力选择区域，但需确认是否只展示 bindable/configured 能力。
- `backend/app/controllers/capability_controller.py` 已有 capability list、import、draft、call sync 等 API。
- 005 已经要求 `.weagent/tools/<runtime_id>/TOOL.md`、manifest、per-Agent `tool-index.json`、runtime gate 和 call record。

## Guiding Decisions

- `代码生成` 不再是 Tool；它属于 Skill 或 Agent workflow。
- `deferred/hidden` Tool 不在前端展示，不计入分类数字，不进入 Agent 选择器。
- `requires_config` 只有在存在配置窗口和可运行适配器时才能展示。
- `web_search`、`image_analysis`、`image_generation`、`database_query` 是配置型 Tool，不是未完成 Tool。
- 配置通过前不可绑定；配置通过后必须能在 sandbox 中真实调用并写入 call record。
- 内置 Tool 本体不可编辑；用户只能创建/编辑自己的 provider profile 或 MCP/DB 配置。

## Checkpoint A: Catalog Visibility Contract

**Goal:** 先用测试锁住“哪些该显示，哪些不该显示，哪些可绑定”。

Tasks:

1. 后端新增/扩展目录状态测试：
   - `code_generator` 不出现在默认 visible catalog。
   - `deferred/hidden` 不进入 list/count/bindable。
   - 有配置入口的 `requires_config` 可以展示为“需配置”。
   - 未配置 `requires_config` 不可绑定。
   - configured profile 存在后可绑定。
2. 前端契约测试：
   - 工具集主列表不展示 `代码生成`。
   - 分类计数不统计 hidden/deferred。
   - Agent 选择器不展示未配置配置型 Tool。
   - 配置型 Tool 卡片展示“配置”入口，而不是编辑内置 Tool。
3. 迁移安全测试：
   - 历史 Agent 若绑定旧 hidden Tool，详情页不崩溃。
   - 调用旧 hidden Tool 返回结构化拒绝。

Verification:

```powershell
python -m pytest tests\test_default_tool_catalog.py tests\test_capability_api.py -q
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
```

## Checkpoint B: Canonical Tool Catalog Cleanup

**Goal:** 调整 canonical definitions，删除或降级误导性 Tool。

Tasks:

1. 更新 `backend/app/services/builtin_tool_definitions.py`：
   - `code_generator` 标记为 `hidden/deprecated`，或从 seed list 中移出。
   - `web_search` 保留为 `requires_config`，但增加 `configurable=true`、`config_schema`、`provider_types`。
   - `image_analysis` 从 `deferred` 改为 `requires_config`。
   - 新增 `image_generation` 或 `image_generate`，状态 `requires_config`。
   - `database_query` 保留为 `requires_config` 并增加 DB profile schema。
2. 更新 `capability_service.seed_builtin_tool_capabilities()`：
   - 不为 hidden Tool 创建新的可见版本。
   - 已存在 hidden capability 更新状态但不破坏历史绑定。
   - configured state 不直接写进内置 definition，而由用户 profile 决定。
3. 更新 list serialization：
   - 返回 `visibility`、`bindable`、`configurable`、`configured_profiles_count`、`configuration_required_reason`。
   - category counts 默认只统计 visible capabilities。

Verification:

```powershell
python -m pytest tests\test_default_tool_catalog.py tests\test_toolset_categories.py -q
```

## Checkpoint C: Provider Profile Data Model and API

**Goal:** 提供可保存、可测试、可启用的配置记录。

Likely files:

- `backend/app/models/tool_provider_config.py`
- `backend/app/schemas/tool_provider_config_schema.py`
- `backend/app/services/tool_provider_config_service.py`
- `backend/app/controllers/tool_provider_config_controller.py`
- `backend/sql/init.sql`

Tasks:

1. 新增 provider profile 模型，字段至少包括：
   - `id`
   - `user_id`
   - `capability_id`
   - `profile_name`
   - `provider_type`: `mcp`、`http`、`model`、`database`
   - `config`: 非敏感配置
   - `secret_refs`: secret alias 列表，不存明文
   - `status`: `draft`、`valid`、`invalid`、`disabled`
   - `last_test_status`
   - `last_test_error`
   - `created_at/updated_at`
2. 新增 API：
   - `GET /api/capabilities/<id>/provider-configs`
   - `POST /api/capabilities/<id>/provider-configs`
   - `PUT /api/capabilities/<id>/provider-configs/<config_id>`
   - `POST /api/capabilities/<id>/provider-configs/<config_id>/test`
   - `POST /api/capabilities/<id>/provider-configs/<config_id>/enable`
   - `POST /api/capabilities/<id>/provider-configs/<config_id>/disable`
   - `DELETE /api/capabilities/<id>/provider-configs/<config_id>`
3. 权限边界：
   - 用户只能管理自己的 profile。
   - 系统内置 profile 只读。
   - 删除/停用 profile 后，新 Agent 不可绑定；旧 Agent 运行时返回配置不可用。
4. secret 边界：
   - v1 可先存 alias，不负责完整 secret vault。
   - 明文 secret 不返回前端，不进入 `.weagent/*`。

Verification:

```powershell
python -m pytest tests\test_tool_provider_config_service.py tests\test_tool_provider_config_api.py -q
```

## Checkpoint D: Frontend Configuration UI

**Goal:** 在工具集页面给用户明确的配置窗口和交互。

Likely files:

- `frontend/src/views/Tools.vue`
- `frontend/src/api/toolProviderConfigs.js`
- `frontend/src/components/toolset/ProviderConfigDialog.vue`
- `frontend/tests/tool-provider-config-ui-contract.test.js`

Tasks:

1. 工具详情面板新增配置区：
   - 未配置：显示“需要配置”状态、原因、配置按钮。
   - 已配置：显示 profile 列表、状态、最近测试结果、启用状态。
   - 配置失败：显示错误摘要和重新测试入口。
2. 配置窗口按能力类型展示不同表单：
   - `web_search`: MCP command/tool name 或 HTTP endpoint/search params。
   - `image_analysis`: MCP/model provider、tool/model id、输入图片字段。
   - `image_generation`: MCP/model provider、输出格式、默认尺寸、输出目录。
   - `database_query`: driver/profile alias、readonly policy、allowed schemas/tables、max rows、timeout。
3. 交互动作：
   - 新建 profile。
   - 测试配置。
   - 保存。
   - 启用/停用。
   - 删除用户 profile。
4. Agent 选择器更新：
   - 未配置能力禁用或不显示。
   - 配置有效后可选择具体 profile 或默认 valid profile。

Verification:

```powershell
node tests\tool-provider-config-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
npm run build
```

## Checkpoint E: Runtime Projection and Binding for Configured Tools

**Goal:** 配置通过后，Agent 绑定能带上 profile，并投影到 sandbox。

Tasks:

1. 扩展 Agent capability binding：
   - 支持绑定 `provider_config_id` 或 profile alias。
   - pinned capability version 仍然固定。
   - profile 可以禁用，运行时必须重新校验状态。
2. 扩展 projection：
   - `.weagent/tools/<runtime_id>/manifest.json` 包含 `provider_profile_alias`，不包含明文 secret。
   - `.weagent/agents/<agent_id>/tool-index.json` 展示配置型 Tool 的 tool name、doc path、profile label、权限摘要。
   - `.weagent/agents/<agent_id>/capabilities.json` 包含 profile id/alias 和 configured state。
3. Runtime gate：
   - 未绑定拒绝。
   - 未授权拒绝。
   - profile 不存在/禁用/测试失败拒绝。
   - 缺少 secret alias 拒绝。
4. Audit：
   - call record 中记录 `provider_config_id` 或 alias。
   - input/output summary 脱敏。

Verification:

```powershell
python -m pytest tests\test_capability_projection.py tests\test_configured_tool_runtime_gate.py -q
```

## Checkpoint F: Configured Tool Runtime Adapters

**Goal:** 四类配置型 Tool 都能在 Docker fixture 中跑通。

### Web Search

Tasks:

- 支持 MCP-backed search profile 或 HTTP fixture provider。
- 输入：query、max_results。
- 输出：results array，包含 title/url/snippet/source。
- 失败路径：无 network 权限、provider 失败、超时。

### Image Analysis

Tasks:

- 支持 MCP/model-backed vision profile。
- 输入：workspace image path、prompt/task。
- 输出：analysis text、metadata。
- 失败路径：无 read_workspace、文件不存在、provider 失败。

### Image Generation

Tasks:

- 新增 runtime tool name，例如 `image_generate`。
- 输入：prompt、size、format、output_path。
- 输出：workspace image path、format、size。
- fixture provider 生成一个有效 PNG，用于无外部密钥的 Docker smoke。
- 失败路径：无 write_workspace、非法输出路径、provider 失败。

### Database Query

Tasks:

- 支持 readonly DB profile。
- v1 测试至少支持 SQLite fixture；如果 `WEAGENT_TEST_DB_URL` 存在，则额外测试外部 DB。
- 输入：query、max_rows。
- 输出：columns、rows、row_count。
- 失败路径：写入 SQL、DDL、多语句、超时、无 secret/use_secret 权限。

Verification:

```powershell
python -m pytest tests\test_configured_web_search_tool.py tests\test_configured_image_tools.py tests\test_configured_database_query_tool.py -q
```

## Checkpoint G: Docker Smoke and Real UAT Guide

**Goal:** 证明“配置好了就能运行”，不是只靠单元测试。

Tasks:

1. 新增 Docker smoke 脚本：
   - `.planning/phases/001-toolset/006-default-tool-catalog/docker-smoke/smoke_configured_tools.py`
2. Smoke 场景：
   - 创建/使用 fixture profile。
   - 创建 Agent 并绑定四类配置型 Tool。
   - 启动 sandbox session。
   - 验证 `.weagent/tools/*`、`tool-index.json`、profile alias projection。
   - 调用 web search。
   - 调用 image analysis。
   - 调用 image generation 并检查图片文件。
   - 调用 database query SELECT。
   - 调用失败路径并检查失败 call record。
3. 新增 UAT 文档：
   - `.planning/phases/001-toolset/006-default-tool-catalog/CONFIGURED-TOOLS-UAT-GUIDE.zh-CN.md`
4. 文档说明：
   - 未配置时如何看。
   - 如何配置。
   - 如何测试配置。
   - 如何绑定 Agent。
   - 如何查看 call record。
   - 哪些真实 provider 需要用户自备凭证。

Verification:

```powershell
docker info
python .planning\phases\001-toolset\006-default-tool-catalog\docker-smoke\smoke_configured_tools.py
```

## Checkpoint H: Regression, Cleanup, and Push Readiness

**Goal:** 收束目录行为、配置行为和既有工具行为。

Tasks:

1. 回归测试：
   - 005 implemented Tools 仍可运行。
   - Skill 导入/编辑仍可用。
   - MCP npx 导入仍可用。
   - Plugin manifest 仍不执行。
   - Agent 创建/编辑 capability selection 不回归。
2. 前端检查：
   - 工具集分类计数正确。
   - hidden/deferred 不显示。
   - configured/requires_config 状态清楚。
   - 右侧详情面板可收起。
   - 配置弹窗误点外部不丢失输入。
3. 文档更新：
   - 更新 006 checkpoint 报告。
   - 如需要，更新 `.planning/STATE.md` 和 roadmap extension artifacts。
4. Git hygiene：
   - 不提交 `.planning/tmp/`、`.planning/*.lock`、`.claude/logs/`。
   - 006 单独提交。

Verification:

```powershell
python -m pytest tests\test_capability_models.py tests\test_capability_service.py tests\test_capability_api.py tests\test_capability_projection.py tests\test_capability_tool_audit.py tests\test_default_tool_catalog.py tests\test_tool_provider_config_api.py tests\test_configured_tool_runtime_gate.py -q
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
node tests\tool-provider-config-ui-contract.test.js
npm run build
```

## Add / Remove Summary

### Add

- Configurable Tool profile model/API/service.
- Frontend provider configuration dialog.
- `image_generation` configurable Tool.
- Configured runtime adapters for:
  - `web_search`
  - `image_analysis`
  - `image_generate`
  - `database_query`
- Docker fixture smoke for configured Tools.
- UAT guide for configured Tools.

### Remove or Hide

- Hide/downgrade `code_generator` from frontend catalog and Agent binding.
- Hide any `deferred` Tool without configuration UI.
- Exclude hidden/deferred Tool from category counts.
- Disable binding for unconfigured `requires_config` Tool.

### Keep

- Existing implemented deterministic Tools from 005.
- `http_fetch` and `api_request` as deterministic network Tools.
- `image_info` as deterministic image metadata Tool.
- `sqlite_query_readonly` as local data Tool.
- Plugin manifest-only boundary.
- `.weagent/*` as canonical runtime projection.

## Risks and Mitigations

- **Secret leakage risk**: profile must store aliases only; tests scan `.weagent/*` and call records for known test secrets.
- **Fake configured state risk**: `configured` only after test endpoint succeeds; disabled/invalid profile is not bindable.
- **Provider flakiness risk**: Docker smoke uses local fixture providers; real provider UAT is optional and credential-gated.
- **Database write risk**: readonly parser rejects writes before provider execution; DB user should also be readonly where possible.
- **UI confusion risk**: `requires_config` uses explicit configuration CTA; hidden/deferred does not appear.

## Success Criteria

- `code_generator` is no longer visible or bindable as a default Tool.
- Unfinished Tools are absent from frontend lists unless they are real configurable capabilities.
- Search, image analysis, image generation, and database query all have frontend configuration workflows.
- Configured profiles can be tested, saved, enabled, bound to Agent, projected, called, and audited.
- Docker fixture smoke proves all four configured Tools run successfully and fail safely.
- Existing 005 runtime Tool coverage remains passing.

---

*Phase: 006-default-tool-catalog*
*Plan created: 2026-06-02*
*Recommended next step: review this plan, then implement Checkpoint A first.*
