# 阶段 001：工具集能力 v1 - 实施计划

**创建时间：** 2026-05-28
**来源流程：** `$gsd-plan-phase`
**规格：** `.planning/phases/001-toolset/001-SPEC.md`
**目标：** 为 Skill、Tool、MCP 和 Plugin 构建由 DB 支撑的能力系统，包含 Agent 默认绑定、`.weagent/*` session projection、显式授权，以及最小真实 Tool/MCP 调用审计。

## 架构

DB 仍然是 capability definitions、versions、Agent bindings、authorization snapshots、call records 和 Skill drafts 的 canonical source of truth。每个 session sandbox 都会收到一个临时的 `/workspace/.weagent/*` projection，该投影从所选 Agents 的 pinned bindings 构建。Runtime code 读取该 projection，暴露每个 Agent 的能力视图，记录 Tool/MCP 调用，并把 Agent 写入的 Skill 改动同步回 draft revisions，供用户确认。

## 现有集成点

- `backend/app/models/agent.py`：现有 Agent 定义，包含 legacy `skill` 和 `tool_ids`。
- `backend/app/models/agent_tool.py`：现有内置/自定义工具模型，应桥接或 seed 到新的 capability model。
- `backend/app/services/agent_service.py`：Agent 创建/更新和默认 seed data。
- `backend/app/services/tool_service.py`：现有 Tool 列表和 seed 逻辑。
- `backend/app/controllers/agent_controller.py`：Agent CRUD API。
- `backend/app/controllers/tool_controller.py`：当前 Tool API，可能被 capability APIs 替代或包装。
- `backend/app/sandbox/host/manager.py`：host-side session 创建和 container bootstrapping。
- `backend/app/sandbox/container/orchestrator.py`：container-side Agent 管理、tool execution 和 workspace 行为。
- `backend/app/sandbox/container/tools/__init__.py`：内置工具 registry 和 execution。
- `frontend/src/components/AgentEditForm/index.vue`：Agent 创建/编辑 UI。
- `frontend/src/views/Tools.vue`：当前工具管理 UI，可演进为 Capability Library。
- `frontend/src/api/agent.js` 和 `frontend/src/api/tools.js`：现有前端 API wrappers。

## 计划文件

**新建：**

- `backend/app/models/capability.py`：能力库、版本、Agent bindings、call records 和 Skill draft models。
- `backend/app/repositories/capability_repo.py`：capabilities、versions、bindings、drafts 和 call records 的 DB access helpers。
- `backend/app/services/capability_service.py`：library CRUD、versioning、imports、binding validation、authorization snapshots 和 upgrade checks。
- `backend/app/services/capability_projection_service.py`：根据 Agent bindings 构建 session injection plan。
- `backend/app/services/capability_call_sync_service.py`：将 container-side call JSONL 和 Skill draft sync payloads 持久化为 DB records。
- `backend/app/controllers/capability_controller.py`：capability library、import、binding、draft 和 call-record APIs。
- `backend/app/schemas/capability_schema.py`：capability APIs 的请求/响应校验。
- `backend/app/sandbox/container/capabilities.py`：写入和读取 `.weagent/*`、Agent views、snapshots、call JSONL 和 Skill draft detection helpers。
- `backend/app/sandbox/container/mcp_runtime.py`：用于 install/start/list-tools/call 的最小 npx MCP runtime。
- `frontend/src/api/capabilities.js`：能力库和 bindings 的前端 API wrapper。
- `frontend/src/views/CapabilityLibrary.vue`：Skill/Tool/MCP/Plugin library view。
- `backend/tests/test_capability_models.py`：model 和 versioning tests。
- `backend/tests/test_capability_service.py`：service、import、binding 和 permission tests。
- `backend/tests/test_capability_projection.py`：`.weagent/*` projection unit tests。
- `backend/tests/test_capability_runtime_records.py`：Tool/MCP call record tests。

**修改：**

- `backend/app/models/__init__.py`：导入新 models，让 SQLAlchemy 注册它们。
- `backend/app/__init__.py`：注册 capability blueprint，并 seed built-in capabilities。
- `backend/sql/init.sql`：如果仓库继续使用 SQL bootstrap，则加入 capability tables 初始 schema。
- `backend/app/models/agent.py`：保留 legacy fields，但在 `to_dict` 中暴露 capability bindings。
- `backend/app/services/agent_service.py`：创建/更新 Agent 时支持默认 capability bindings。
- `backend/app/controllers/agent_controller.py`：create/update 接收 capability binding payload。
- `backend/app/sandbox/host/manager.py`：把 capability injection plans 传给 containers，并在 Agent startup 前投影。
- `backend/app/sandbox/container/orchestrator.py`：初始化 `.weagent`、创建 Agent views、记录 snapshots、检测 Skill draft changes。
- `backend/app/sandbox/container/tools/__init__.py`：通过 capability call logging 记录内置 Tool 调用。
- `frontend/src/router/index.js`：增加 Capability Library route。
- `frontend/src/components/Sidebar/index.vue`：如果 sidebar 控制顶级路由，则增加导航项。
- `frontend/src/components/AgentEditForm/index.vue`：用 capability picker、version pin 和 permission grant UI 替换 inline-only Skill/Tool 配置，同时在迁移期保留 legacy display。
- `frontend/src/views/Tools.vue`：重定向到 Capability Library，或保留为由 capabilities 支撑的 Tool-filtered view。

## 任务 1：能力数据模型

**目标：** 增加能力库、版本、Agent bindings、call records 和 Skill drafts 的持久化 DB models。

**动作：**

1. 创建 `backend/app/models/capability.py`，包含：
   - `Capability`：`id`、`user_id`、`type`、`name`、`slug`、`description`、`source`、`source_ref`、`is_builtin`、`latest_version_id`、`created_at`、`updated_at`。
   - `CapabilityVersion`：`id`、`capability_id`、`version`、`content`、`manifest`、`permissions`、`meta`、`checksum`、`created_by`、`created_at`。
   - `AgentCapabilityBinding`：`id`、`agent_id`、`capability_id`、`capability_version_id`、`enabled`、`version_policy`、`granted_permissions`、`authorization_snapshot`、`created_at`、`updated_at`。
   - `CapabilityCallRecord`：`id`、`session_id`、`run_id`、`agent_id`、`capability_id`、`capability_version_id`、`call_type`、`tool_name`、`permissions_used`、`input_summary`、`output_summary`、`status`、`error`、`started_at`、`completed_at`。
   - `SkillRevisionDraft`：`id`、`source_skill_id`、`source_version_id`、`session_id`、`agent_id`、`diff`、`full_markdown`、`status`、`created_at`、`reviewed_at`。
2. 在 `backend/app/models/__init__.py` 中注册这些 models。
3. 使用 MySQL-compatible tables 和 indexes 更新 `backend/sql/init.sql`。
4. v1 期间保留 legacy `Agent.skill` 和 `Agent.tool_ids` 字段。

**验证：**

- 在 `backend` 下运行 `python -c "from app.models.capability import Capability, CapabilityVersion, AgentCapabilityBinding, CapabilityCallRecord, SkillRevisionDraft; print('ok')"`。
- 运行后端 model tests，覆盖 creation、version pinning 和 binding relations。

## 任务 2：能力服务和权限策略

**目标：** 实现 library CRUD、versioning、imports、binding validation、authorization snapshots 和 upgrade detection。

**动作：**

1. 创建 `backend/app/repositories/capability_repo.py`，提供按 `user_id` 加 built-in capabilities 作用域查询的 helpers。
2. 创建 `backend/app/services/capability_service.py`，包含：
   - `list_capabilities(user_id, type=None)`。
   - `create_skill(user_id, markdown, meta)`。
   - `import_skill_markdown(user_id, markdown, source_ref)`。
   - `import_npx_manifest(user_id, manifest, source_ref)`。
   - `create_version(capability_id, content, manifest, permissions, meta)`。
   - `bind_to_agent(agent_id, capability_version_id, granted_permissions, version_policy='pinned')`。
   - `get_agent_bindings(agent_id)`。
   - `get_upgrade_status(agent_id)`。
3. 强制执行权限声明和授权校验：
   - 合法权限集合：`read_workspace`、`write_workspace`、`run_command`、`network`、`use_secret`、`modify_skill`、`start_service`。
   - 如果 `granted_permissions` 包含版本未声明的权限，则 binding 失败。
   - 如果某个 required declared permission 未被授予，则 binding 失败。
   - Authorization snapshot 保存 capability id、version id、declared permissions、granted permissions、source、source_ref 和 timestamp。
4. 通过把现有内置工具模板转换为 `Capability(type='tool')` 行来 seed built-in platform capabilities。

**验证：**

- Service tests 证明：如果 capability version 需要 `run_command`，但未授予 `run_command`，则不能绑定。
- Service tests 证明：发布新的 Skill version 不会改变现有 Agent binding。
- Service tests 证明：当存在较新版本时，upgrade status 会出现。

## 任务 3：能力 API

**目标：** 暴露统一 API，用于 library、imports、Agent bindings、drafts 和 call records。

**动作：**

1. 创建 `backend/app/schemas/capability_schema.py` 做输入校验。
2. 创建 `backend/app/controllers/capability_controller.py`，包含 authenticated endpoints：
   - `GET /api/capabilities`
   - `POST /api/capabilities/skills`
   - `POST /api/capabilities/import/markdown`
   - `POST /api/capabilities/import/npx-manifest`
   - `GET /api/capabilities/<id>`
   - `GET /api/capabilities/<id>/versions`
   - `POST /api/agents/<agent_id>/capabilities`
   - `GET /api/agents/<agent_id>/capabilities`
   - `PUT /api/agents/<agent_id>/capabilities/<binding_id>`
   - `GET /api/capabilities/drafts`
   - `POST /api/capabilities/drafts/<draft_id>/publish`
   - `POST /api/capabilities/drafts/<draft_id>/fork`
   - `POST /api/capabilities/calls/sync`
   - `GET /api/capabilities/calls`
3. 在 `backend/app/__init__.py` 注册 blueprint。
4. 更新 `backend/app/controllers/agent_controller.py` 和 `backend/app/services/agent_service.py`，使 Agent create/update 可以包含 `capability_bindings`。

**验证：**

- API tests 覆盖 capability create/list、Markdown import、npx manifest import、Agent bind 和 draft publish/fork。
- 现有 Agent create/update tests 在 legacy payload 下仍然通过。

## 任务 4：前端能力库

**目标：** 增加平台 UI，用于管理 Skill、Tool、MCP 和 Plugin capabilities。

**动作：**

1. 创建 `frontend/src/api/capabilities.js`。
2. 创建 `frontend/src/views/CapabilityLibrary.vue`，用 tabs 或 filters 展示 `Skill`、`Tool`、`MCP` 和 `Plugin`。
3. 增加 Skill Markdown 编辑器，包含：
   - Name、description、tags/source metadata。
   - Markdown textarea/editor。
   - 保存新版本行为。
   - 从 Markdown 文本/文件内容导入。
4. 增加 npx manifest 导入表单，包含：
   - Package/manifest input。
   - Parsed capability preview。
   - 导入前的 permissions preview。
5. 增加 Plugin manifest 展示，显示 install record status，不提供 execution control。
6. 更新 router/sidebar，暴露 Capability Library。
7. 保持 `Tools.vue` 可用：要么链接到新的 Tool tab，要么读取 Tool capabilities。

**验证：**

- 用户可以创建 Skill、编辑 Markdown，并看到新版本。
- 用户可以粘贴 Markdown 并导入为 Skill。
- 用户可以导入 npx manifest，并看到 MCP/Plugin/Skill definitions。
- 现有 Tools route 不破坏。

## 任务 5：Agent 默认能力绑定 UI

**目标：** 让用户在创建/编辑 Agent 时配置 Agent 的默认工具集。

**动作：**

1. 更新 `frontend/src/components/AgentEditForm/index.vue`，通过 `frontend/src/api/capabilities.js` 加载 capabilities。
2. 将旧 Skill textarea 从主配置路径替换为：
   - 按 Skill、Tool、MCP、Plugin 分组的 capability picker。
   - 绑定时默认选择 latest 的 version selector。
   - 基于所选版本 declared permissions 的 permission grant checklist。
   - Pinned version display。
   - 现有 bindings 的 upgrade-available indicator。
3. v1 期间，把 legacy `skill` 和 `tool_ids` 值保留为只读或迁移提示，让旧 Agents 仍可理解。
4. 在 Agent create/update payload 中发送 `capability_bindings`。

**验证：**

- 创建带有 selected capabilities 的 Agent 会写入 DB bindings。
- 编辑 Agent 可以启用/禁用 binding，并在 declared permissions 范围内修改 granted permissions。
- 没有 bindings 的现有 Agents 仍可打开并保存。

## 任务 6：Host-Side 注入计划

**目标：** 在 sandbox Agent startup 前，根据 Agent 默认 bindings 构建 session injection plan。

**动作：**

1. 创建 `backend/app/services/capability_projection_service.py`。
2. 给定 Agent configs 列表，加载每个 Agent 的 enabled capability bindings 和 pinned versions。
3. 生成 JSON-safe projection payload，包含：
   - `session_id`
   - `agents`
   - shared `capabilities`
   - `skills`
   - `mcp`
   - `plugins`
   - per-Agent views
   - authorization snapshots
4. 更新 `backend/app/sandbox/host/manager.py`，在 Agent 创建前通过 startup API call 把 projection payload 传给 container。
5. 确保 projection 发生在 `_create_agent_in_container` 创建 runtime Agents 之前。

**验证：**

- Unit test 证明两个 Agents 共享一个 Skill 时，projection 中只有一个 shared Skill，并且有两个 per-Agent views。
- Unit test 证明 disabled bindings 被排除。
- Host manager test 或 service-level test 证明 projection 在 Agent creation 前构建。

## 任务 7：`.weagent/*` 容器投影

**目标：** 在 `/workspace/.weagent/*` 下物化 runtime contract。

**动作：**

1. 创建 `backend/app/sandbox/container/capabilities.py`。
2. 实现 projection writer，创建：
   - `/workspace/.weagent/capabilities/index.json`
   - `/workspace/.weagent/skills/<skill_id>/SKILL.md`
   - `/workspace/.weagent/skills/<skill_id>/manifest.json`
   - `/workspace/.weagent/mcp/<mcp_id>/manifest.json`
   - `/workspace/.weagent/plugins/<plugin_id>/manifest.json`
   - `/workspace/.weagent/agents/<agent_id>/capabilities.json`
   - `/workspace/.weagent/agents/<agent_id>/skill-index.json`
   - `/workspace/.weagent/agents/<agent_id>/permissions.json`
3. 增加 run snapshot writer：
   - `/workspace/.weagent/runs/<run_id>/capability-snapshot.json`
   - `/workspace/.weagent/runs/<run_id>/calls.jsonl`
4. 更新 `backend/app/sandbox/container/orchestrator.py`，在 Agent startup 前初始化 projection，并为每次 Agent task 写 run snapshot。
5. 更新 Agent runtime instruction creation，让每个 Agent 收到紧凑 bootstrap，指向 `/workspace/.weagent/agents/<agent_id>/skill-index.json`、`capabilities.json` 和 `permissions.json`。
6. 确保 v1 不写 `.claude/skills`、`.codex/skills` 或 `.mcp.json`。

**验证：**

- Container-side unit test 将 sample projection 写入临时 workspace，并对比 expected files。
- Test 证明只创建 `.weagent/*` 文件。
- Test 证明 per-Agent `skill-index.json` 排除未绑定 Skills。

## 任务 8：Tool 调用记录

**目标：** 将内置 Tool 调用绑定到 capability call records。

**动作：**

1. 更新 `backend/app/sandbox/container/tools/__init__.py`，使 `call_from_agent` 向 `.weagent/runs/<run_id>/calls.jsonl` 写 call record。
2. 包含 `agent_id`、`session_id`、`run_id`、`capability_id`、`capability_version_id`、`tool_name`、`permissions_used`、`input_summary`、`output_summary`、`status` 和 timing。
3. 增加 `backend/app/services/capability_call_sync_service.py`，把 JSONL call records 持久化为 `CapabilityCallRecord`。
4. 选用至少一个现有内置 tool 作为 v1 验证目标。

**验证：**

- 调用选中的内置 Tool 会写入 JSONL call record。
- 持久化后的 DB call record 包含同一 Agent、session、capability version 和 status。
- 失败的 Tool call 记录 `status='failed'`，并包含 error summary。

## 任务 9：最小 MCP npx Runtime

**目标：** 支持一个 manifest-backed npx MCP server，从导入到一次审计调用。

**动作：**

1. 创建 `backend/app/sandbox/container/mcp_runtime.py`。
2. 使用 `.planning/phases/001-toolset/001-CONTEXT.md` 中的 manifest schema，实现最小操作：
   - 从 manifest command install/start。
   - 从 MCP server list tools。
   - 用 JSON input 调用一个 tool。
   - 停止 server。
3. 要求 MCP capability 声明 `run_command`；只有 manifest 声明时才要求 `network`。
4. MCP tool calls 通过和内置 Tools 相同的 call record path 记录。
5. 保持 npx execution 在 sandbox container 内部。

**验证：**

- Fixture manifest 导入为 MCP capability。
- 缺少 `run_command` 时 binding 失败。
- 启动 server 后至少列出一个 tool。
- 调用 tool 会写入带 MCP metadata 的 success 或 failure call records。

## 任务 10：Plugin Manifest 导入

**目标：** 将 Plugin 表示为一等 installable source，但 v1 不执行 Plugin code。

**动作：**

1. 扩展 `import_npx_manifest`，当 manifest 包含 plugin metadata 时创建 `Capability(type='plugin')`。
2. 存储 Plugin manifest、source package、version、included capability references 和 install status。
3. 在 Capability Library 中展示 Plugin records。
4. 不增加 runtime execution、hooks、UI extension execution 或 arbitrary command execution。

**验证：**

- Plugin manifest import 创建 Plugin capability 和 version。
- Plugin detail API 返回 manifest 和 install record。
- v1 中不存在 Plugin execute endpoint。

## 任务 11：Skill Draft 同步

**目标：** 将 Agent 写入的 runtime Skill 改动转换为 DB drafts，供用户 review。

**动作：**

1. 增加 container helper，在 session start 时 snapshot projected Skill checksums。
2. Agent task 完成后，将 `/workspace/.weagent/skills/<skill_id>/SKILL.md` 与 baseline 对比。
3. 通过现有 callback 或新的 authenticated sandbox sync route，把变更后的 Skill content 和 metadata 发送给 host。
4. 将改动持久化为 `SkillRevisionDraft(status='pending_review')`。
5. 实现 draft actions：
   - 发布为原 Skill 的新版本。
   - 另存为新的 Skill identity。
   - 拒绝，并可选择保留 session runtime 不变。

**验证：**

- 编辑 runtime Skill Markdown 会生成一个 draft，并关联原 Skill version 和 Agent。
- 发布会创建新的 Skill version，但不移动现有 Agent bindings。
- 另存为 fork 会创建不同的 Skill capability。

## 任务 12：端到端验证

**目标：** 证明 v1 能工作，并且不回归当前多 Agent 行为。

**动作：**

1. 增加后端 tests，覆盖 model、service、projection、permission validation 和 call records。
2. 如果项目已有前端 test runner，则增加 Capability Library 和 Agent binding UI 的前端 smoke path；否则记录 manual smoke checks。
3. 运行后端 syntax 和 unit tests。
4. 运行仓库使用的 frontend build 或 lint command。
5. 手动 sandbox smoke：
   - 创建 Skill Markdown。
   - 创建带 Skill 和内置 Tool 的 Agent。
   - 启动 session。
   - 验证 `.weagent/*` projection。
   - 调用内置 Tool，并验证 call record。
   - 修改 projected Skill，并验证 draft。
   - 导入 npx MCP manifest，并验证一条 call record。
   - 导入 Plugin manifest，并验证不会暴露 execution。

**验证：**

- 所有自动化 tests 通过。
- Manual smoke checklist 通过。
- 现有 message stream、Agent progress 和 artifact display 继续渲染。

## 里程碑顺序

1. Data model and service foundation。
2. Capability API and built-in seed migration。
3. Frontend library and Agent binding UI。
4. Host-side projection and `.weagent/*` container projection。
5. Built-in Tool call audit。
6. Minimal MCP npx runtime。
7. Plugin manifest import。
8. Skill draft sync。
9. End-to-end verification and regression checks。

## 风险与缓解

- **风险：** 现有 `Agent.skill` 和 `tool_ids` 与新的 capability bindings 冲突。
  - **缓解：** v1 期间保留 legacy fields，把 capability bindings 作为新路径，并将 legacy values 作为迁移上下文展示。

- **风险：** MCP npx execution 可能意外扩大权限。
  - **缓解：** 要求 manifest import、declared permissions、显式 Agent grant 和 sandbox-only execution。

- **风险：** `.weagent/*` runtime projection 变成第二事实源。
  - **缓解：** 将 `.weagent/*` 视为 disposable session projection；只把已批准的 Skill drafts 同步回 DB。

- **风险：** Plugin 范围膨胀为任意执行。
  - **缓解：** v1 Plugin 只保存 manifest/import/install record，不暴露 execution endpoint。

- **风险：** Sandbox route security 仍然较宽。
  - **缓解：** Capability APIs 必须经过认证和权限检查；更广泛的 sandbox hardening 保持为独立阶段，除非它阻塞 capability correctness。

## 成功标准

- Capability library 支持四种并列记录类型。
- Agent 默认 bindings 以 pinned versions 和 authorization snapshots 持久化。
- Session startup 写入 `.weagent/*` runtime projection 和 Agent-specific views。
- Skill 生命周期支持 create、edit、import、runtime modification、draft、publish 和 fork。
- 内置 Tool 和最小 MCP calls 产生 DB-persisted call records。
- Plugin import/install record 存在，但不执行 Plugin。
- 现有多 Agent messaging、progress 和 artifact flows 不被破坏。

## 验证命令

实现后从 `E:\code for project\seedance-competition\agentshub\WeAgent` 运行：

```powershell
cd backend
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_projection.py tests/test_capability_runtime_records.py -v
```

```powershell
cd frontend
npm run build
```

```powershell
cd backend
python -m py_compile app\models\capability.py app\services\capability_service.py app\services\capability_projection_service.py app\services\capability_call_sync_service.py app\controllers\capability_controller.py app\sandbox\container\capabilities.py app\sandbox\container\mcp_runtime.py
```

## 计划自检

- Spec 覆盖：`001-SPEC.md` 中所有 10 项需求都映射到任务 1 到任务 12。
- 空缺扫描：没有留下需要未来解释的未解决章节。
- 范围检查：这是一个功能阶段，因为所有任务都服务于同一个 capability runtime contract；完整 marketplace、Claude/Codex compatibility mapping 和 Plugin execution 保持在范围外。
- Gate：该计划已准备好在实施前 review。

---

*阶段：001-toolset*
*计划创建时间：2026-05-28*
*用户批准后的下一步：优先执行任务 1，并在可行时先写测试再实现。*
