# Phase 001: Toolset Capabilities v1 - Implementation Plan

**Created:** 2026-05-28
**Source workflow:** `$gsd-plan-phase`
**Spec:** `.planning/phases/001-toolset/001-SPEC.md`
**Goal:** Build a DB-backed capability system for Skill, Tool, MCP, and Plugin, with Agent default bindings, `.weagent/*` session projection, explicit authorization, and minimal real Tool/MCP call audit.

## Architecture

DB remains the canonical source of truth for capability definitions, versions, Agent bindings, authorization snapshots, call records, and Skill drafts. Each session sandbox receives a transient `/workspace/.weagent/*` projection built from the selected Agents' pinned bindings. Runtime code reads the projection, exposes per-Agent capability views, records Tool/MCP calls, and syncs Agent-written Skill changes back as draft revisions for user confirmation.

## Existing Integration Points

- `backend/app/models/agent.py`: existing Agent definition with legacy `skill` and `tool_ids`.
- `backend/app/models/agent_tool.py`: existing built-in/custom tool model that should be bridged or seeded into the new capability model.
- `backend/app/services/agent_service.py`: Agent creation/update and default seed data.
- `backend/app/services/tool_service.py`: existing Tool list and seed logic.
- `backend/app/controllers/agent_controller.py`: Agent CRUD API.
- `backend/app/controllers/tool_controller.py`: current Tool API, likely replaced or wrapped by capability APIs.
- `backend/app/sandbox/host/manager.py`: host-side session creation and container bootstrapping.
- `backend/app/sandbox/container/orchestrator.py`: container-side Agent management, tool execution, and workspace behavior.
- `backend/app/sandbox/container/tools/__init__.py`: built-in tool registry and execution.
- `frontend/src/components/AgentEditForm/index.vue`: Agent creation/editing UI.
- `frontend/src/views/Tools.vue`: current tool management UI, candidate to evolve into Capability Library.
- `frontend/src/api/agent.js` and `frontend/src/api/tools.js`: existing frontend API wrappers.

## Planned Files

**Create:**

- `backend/app/models/capability.py`: capability library, versions, Agent bindings, call records, and Skill draft models.
- `backend/app/repositories/capability_repo.py`: DB access helpers for capabilities, versions, bindings, drafts, and call records.
- `backend/app/services/capability_service.py`: library CRUD, versioning, imports, binding validation, authorization snapshots, and upgrade checks.
- `backend/app/services/capability_projection_service.py`: builds the session injection plan from Agent bindings.
- `backend/app/services/capability_call_sync_service.py`: persists container-side call JSONL and Skill draft sync payloads into DB records.
- `backend/app/controllers/capability_controller.py`: capability library, import, binding, draft, and call-record APIs.
- `backend/app/schemas/capability_schema.py`: request/response validation for capability APIs.
- `backend/app/sandbox/container/capabilities.py`: writes and reads `.weagent/*`, Agent views, snapshots, call JSONL, and Skill draft detection helpers.
- `backend/app/sandbox/container/mcp_runtime.py`: minimal npx MCP runtime for install/start/list-tools/call.
- `frontend/src/api/capabilities.js`: frontend API wrapper for capability library and bindings.
- `frontend/src/views/CapabilityLibrary.vue`: Skill/Tool/MCP/Plugin library view.
- `backend/tests/test_capability_models.py`: model and versioning tests.
- `backend/tests/test_capability_service.py`: service, import, binding, and permission tests.
- `backend/tests/test_capability_projection.py`: `.weagent/*` projection unit tests.
- `backend/tests/test_capability_runtime_records.py`: Tool/MCP call record tests.

**Modify:**

- `backend/app/models/__init__.py`: import new models so SQLAlchemy registers them.
- `backend/app/__init__.py`: register capability blueprint and seed built-in capabilities.
- `backend/sql/init.sql`: add initial schema for capability tables if this repo continues to use SQL bootstrap.
- `backend/app/models/agent.py`: preserve legacy fields but expose capability bindings in `to_dict`.
- `backend/app/services/agent_service.py`: create/update Agent with default capability bindings.
- `backend/app/controllers/agent_controller.py`: accept capability binding payload on create/update.
- `backend/app/sandbox/host/manager.py`: pass capability injection plans to containers and project them before Agent startup.
- `backend/app/sandbox/container/orchestrator.py`: initialize `.weagent`, create Agent views, record snapshots, and detect Skill draft changes.
- `backend/app/sandbox/container/tools/__init__.py`: record built-in Tool calls through capability call logging.
- `frontend/src/router/index.js`: add Capability Library route.
- `frontend/src/components/Sidebar/index.vue`: add navigation item if the sidebar controls top-level routes.
- `frontend/src/components/AgentEditForm/index.vue`: replace inline-only Skill/Tool configuration with capability picker, version pin, and permission grant UI while preserving legacy display during migration.
- `frontend/src/views/Tools.vue`: either redirect to Capability Library or keep as a Tool-filtered view backed by capabilities.

## Task 1: Capability Data Model

**Objective:** Add durable DB models for capability library, versions, Agent bindings, call records, and Skill drafts.

**Actions:**

1. Create `backend/app/models/capability.py` with:
   - `Capability`: `id`, `user_id`, `type`, `name`, `slug`, `description`, `source`, `source_ref`, `is_builtin`, `latest_version_id`, `created_at`, `updated_at`.
   - `CapabilityVersion`: `id`, `capability_id`, `version`, `content`, `manifest`, `permissions`, `meta`, `checksum`, `created_by`, `created_at`.
   - `AgentCapabilityBinding`: `id`, `agent_id`, `capability_id`, `capability_version_id`, `enabled`, `version_policy`, `granted_permissions`, `authorization_snapshot`, `created_at`, `updated_at`.
   - `CapabilityCallRecord`: `id`, `session_id`, `run_id`, `agent_id`, `capability_id`, `capability_version_id`, `call_type`, `tool_name`, `permissions_used`, `input_summary`, `output_summary`, `status`, `error`, `started_at`, `completed_at`.
   - `SkillRevisionDraft`: `id`, `source_skill_id`, `source_version_id`, `session_id`, `agent_id`, `diff`, `full_markdown`, `status`, `created_at`, `reviewed_at`.
2. Register these models in `backend/app/models/__init__.py`.
3. Update `backend/sql/init.sql` with MySQL-compatible tables and indexes.
4. Keep legacy `Agent.skill` and `Agent.tool_ids` fields during v1.

**Verification:**

- Run `python -c "from app.models.capability import Capability, CapabilityVersion, AgentCapabilityBinding, CapabilityCallRecord, SkillRevisionDraft; print('ok')"` from `backend`.
- Run backend model tests for creation, version pinning, and binding relations.

## Task 2: Capability Service and Permission Policy

**Objective:** Implement library CRUD, versioning, imports, binding validation, authorization snapshots, and upgrade detection.

**Actions:**

1. Create `backend/app/repositories/capability_repo.py` with query helpers scoped by `user_id` plus built-in capabilities.
2. Create `backend/app/services/capability_service.py` with:
   - `list_capabilities(user_id, type=None)`.
   - `create_skill(user_id, markdown, meta)`.
   - `import_skill_markdown(user_id, markdown, source_ref)`.
   - `import_npx_manifest(user_id, manifest, source_ref)`.
   - `create_version(capability_id, content, manifest, permissions, meta)`.
   - `bind_to_agent(agent_id, capability_version_id, granted_permissions, version_policy='pinned')`.
   - `get_agent_bindings(agent_id)`.
   - `get_upgrade_status(agent_id)`.
3. Enforce permission declaration and grant validation:
   - Valid permission set: `read_workspace`, `write_workspace`, `run_command`, `network`, `use_secret`, `modify_skill`, `start_service`.
   - Binding fails if `granted_permissions` contains permissions not declared by the version.
   - Binding fails if a required declared permission is not granted.
   - Authorization snapshot stores capability id, version id, declared permissions, granted permissions, source, source_ref, and timestamp.
4. Seed built-in platform capabilities by translating existing built-in tool templates into `Capability(type='tool')` rows.

**Verification:**

- Service tests prove that a capability version with `run_command` cannot be bound without granting `run_command`.
- Service tests prove that publishing a new Skill version does not change an existing Agent binding.
- Service tests prove that upgrade status appears when a newer version exists.

## Task 3: Capability API

**Objective:** Expose a unified API for library, imports, Agent bindings, drafts, and call records.

**Actions:**

1. Create `backend/app/schemas/capability_schema.py` for input validation.
2. Create `backend/app/controllers/capability_controller.py` with authenticated endpoints:
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
3. Register the blueprint in `backend/app/__init__.py`.
4. Update `backend/app/controllers/agent_controller.py` and `backend/app/services/agent_service.py` so Agent create/update can include `capability_bindings`.

**Verification:**

- API tests cover capability create/list, Markdown import, npx manifest import, Agent bind, and draft publish/fork.
- Existing Agent create/update tests still pass with legacy payloads.

## Task 4: Frontend Capability Library

**Objective:** Add platform UI for managing Skill, Tool, MCP, and Plugin capabilities.

**Actions:**

1. Create `frontend/src/api/capabilities.js`.
2. Create `frontend/src/views/CapabilityLibrary.vue` with tabs or filters for `Skill`, `Tool`, `MCP`, and `Plugin`.
3. Add Skill Markdown editor with:
   - Name, description, tags/source metadata.
   - Markdown textarea/editor.
   - Save new version behavior.
   - Import from Markdown text/file content.
4. Add npx manifest import form with:
   - Package/manifest input.
   - Parsed capability preview.
   - Permissions preview before import.
5. Add Plugin manifest display with install record status and no execution control.
6. Update router/sidebar to expose the Capability Library.
7. Keep `Tools.vue` working by either linking to the new Tool tab or reading Tool capabilities.

**Verification:**

- User can create a Skill, edit Markdown, and see a new version.
- User can paste Markdown and import it as a Skill.
- User can import an npx manifest and see MCP/Plugin/Skill definitions.
- Existing Tools route does not break.

## Task 5: Agent Default Capability Binding UI

**Objective:** Let users configure an Agent's default toolset at Agent creation/edit time.

**Actions:**

1. Update `frontend/src/components/AgentEditForm/index.vue` to load capabilities through `frontend/src/api/capabilities.js`.
2. Replace the old Skill textarea as the primary configuration path with:
   - Capability picker grouped by Skill, Tool, MCP, Plugin.
   - Version selector defaulting to latest at bind time.
   - Permission grant checklist based on the selected version's declared permissions.
   - Pinned version display.
   - Upgrade-available indicator for existing bindings.
3. Preserve legacy `skill` and `tool_ids` values as read-only or migration hints during v1 so old Agents remain understandable.
4. Send `capability_bindings` with Agent create/update payloads.

**Verification:**

- Creating an Agent with selected capabilities writes DB bindings.
- Editing an Agent can enable/disable a binding and change granted permissions within declared permissions.
- Existing Agents without bindings can still be opened and saved.

## Task 6: Host-Side Injection Plan

**Objective:** Build a session injection plan from Agent default bindings before sandbox Agent startup.

**Actions:**

1. Create `backend/app/services/capability_projection_service.py`.
2. Given a list of Agent configs, load each Agent's enabled capability bindings and pinned versions.
3. Produce a JSON-safe projection payload containing:
   - `session_id`
   - `agents`
   - shared `capabilities`
   - `skills`
   - `mcp`
   - `plugins`
   - per-Agent views
   - authorization snapshots
4. Update `backend/app/sandbox/host/manager.py` to pass the projection payload to the container through a startup API call before Agent creation.
5. Ensure projection happens before `_create_agent_in_container` creates runtime Agents.

**Verification:**

- Unit test proves two Agents sharing one Skill produce one shared Skill in the projection and two per-Agent views.
- Unit test proves disabled bindings are excluded.
- Host manager test or service-level test proves projection is built before Agent creation.

## Task 7: `.weagent/*` Container Projection

**Objective:** Materialize the runtime contract under `/workspace/.weagent/*`.

**Actions:**

1. Create `backend/app/sandbox/container/capabilities.py`.
2. Implement projection writer that creates:
   - `/workspace/.weagent/capabilities/index.json`
   - `/workspace/.weagent/skills/<skill_id>/SKILL.md`
   - `/workspace/.weagent/skills/<skill_id>/manifest.json`
   - `/workspace/.weagent/mcp/<mcp_id>/manifest.json`
   - `/workspace/.weagent/plugins/<plugin_id>/manifest.json`
   - `/workspace/.weagent/agents/<agent_id>/capabilities.json`
   - `/workspace/.weagent/agents/<agent_id>/skill-index.json`
   - `/workspace/.weagent/agents/<agent_id>/permissions.json`
3. Add run snapshot writer:
   - `/workspace/.weagent/runs/<run_id>/capability-snapshot.json`
   - `/workspace/.weagent/runs/<run_id>/calls.jsonl`
4. Update `backend/app/sandbox/container/orchestrator.py` to initialize projection before Agent startup and write a run snapshot for each Agent task.
5. Update Agent runtime instruction creation so each Agent receives a compact bootstrap pointing to `/workspace/.weagent/agents/<agent_id>/skill-index.json`, `capabilities.json`, and `permissions.json`.
6. Ensure v1 does not write `.claude/skills`, `.codex/skills`, or `.mcp.json`.

**Verification:**

- Container-side unit test writes a sample projection into a temporary workspace and compares expected files.
- Test proves only `.weagent/*` files are created.
- Test proves per-Agent `skill-index.json` excludes unbound Skills.

## Task 8: Tool Call Recording

**Objective:** Tie built-in Tool calls to capability call records.

**Actions:**

1. Update `backend/app/sandbox/container/tools/__init__.py` so `call_from_agent` writes a call record to `.weagent/runs/<run_id>/calls.jsonl`.
2. Include `agent_id`, `session_id`, `run_id`, `capability_id`, `capability_version_id`, `tool_name`, `permissions_used`, `input_summary`, `output_summary`, `status`, and timing.
3. Add `backend/app/services/capability_call_sync_service.py` to persist JSONL call records into `CapabilityCallRecord`.
4. Use at least one existing built-in tool as the v1 verification target.

**Verification:**

- Calling the selected built-in Tool writes a JSONL call record.
- Persisted DB call record contains the same Agent, session, capability version, and status.
- Failed Tool call records `status='failed'` and includes an error summary.

## Task 9: Minimal MCP npx Runtime

**Objective:** Support one manifest-backed npx MCP server from import to one audited call.

**Actions:**

1. Create `backend/app/sandbox/container/mcp_runtime.py`.
2. Implement minimal operations using the manifest schema in `.planning/phases/001-toolset/001-CONTEXT.md`:
   - install/start from manifest command.
   - list tools from MCP server.
   - call one tool with JSON input.
   - stop server.
3. Require the MCP capability to declare `run_command`; require `network` only if manifest declares it.
4. Record MCP tool calls through the same call record path used by built-in Tools.
5. Keep npx execution inside the sandbox container.

**Verification:**

- A fixture manifest imports as an MCP capability.
- Binding fails without `run_command`.
- Starting the server lists at least one tool.
- Calling the tool writes success or failure call records with MCP metadata.

## Task 10: Plugin Manifest Import

**Objective:** Represent Plugin as a first-class installable source without executing Plugin code in v1.

**Actions:**

1. Extend `import_npx_manifest` to create `Capability(type='plugin')` when manifest contains plugin metadata.
2. Store Plugin manifest, source package, version, included capability references, and install status.
3. Surface Plugin records in the Capability Library.
4. Do not add runtime execution, hooks, UI extension execution, or arbitrary command execution.

**Verification:**

- Plugin manifest import creates a Plugin capability and version.
- Plugin detail API returns manifest and install record.
- No Plugin execute endpoint exists in v1.

## Task 11: Skill Draft Sync

**Objective:** Convert Agent-written runtime Skill changes into DB drafts for user review.

**Actions:**

1. Add container helper to snapshot projected Skill checksums at session start.
2. After Agent task completion, compare `/workspace/.weagent/skills/<skill_id>/SKILL.md` against baseline.
3. Send changed Skill content and metadata to host through existing callback or new authenticated sandbox sync route.
4. Persist changes as `SkillRevisionDraft(status='pending_review')`.
5. Implement draft actions:
   - Publish as new version of original Skill.
   - Save as fork with a new Skill identity.
   - Reject and optionally leave session runtime unchanged.

**Verification:**

- Editing runtime Skill Markdown produces a draft tied to the original Skill version and Agent.
- Publishing creates a new Skill version without moving existing Agent bindings.
- Saving as fork creates a distinct Skill capability.

## Task 12: End-to-End Verification

**Objective:** Prove v1 works without regressing current multi-agent behavior.

**Actions:**

1. Add backend tests for model, service, projection, permission validation, and call records.
2. Add frontend smoke path for Capability Library and Agent binding UI if the project has an established frontend test runner; otherwise document manual smoke checks.
3. Run backend syntax and unit tests.
4. Run frontend build or lint command used by the repo.
5. Manual sandbox smoke:
   - Create Skill Markdown.
   - Create Agent with Skill and built-in Tool.
   - Start session.
   - Verify `.weagent/*` projection.
   - Invoke built-in Tool and verify call record.
   - Modify projected Skill and verify draft.
   - Import npx MCP manifest and verify one call record.
   - Import Plugin manifest and verify no execution is exposed.

**Verification:**

- All automated tests pass.
- Manual smoke checklist passes.
- Existing message stream, Agent progress, and artifact display continue to render.

## Milestone Order

1. Data model and service foundation.
2. Capability API and built-in seed migration.
3. Frontend library and Agent binding UI.
4. Host-side projection and `.weagent/*` container projection.
5. Built-in Tool call audit.
6. Minimal MCP npx runtime.
7. Plugin manifest import.
8. Skill draft sync.
9. End-to-end verification and regression checks.

## Risks and Mitigations

- **Risk:** Existing `Agent.skill` and `tool_ids` conflict with new capability bindings.
  - **Mitigation:** Keep legacy fields during v1, add capability bindings as the new path, and display legacy values as migration context.

- **Risk:** MCP npx execution can expand permissions unexpectedly.
  - **Mitigation:** Require manifest import, declared permissions, explicit Agent grant, and sandbox-only execution.

- **Risk:** `.weagent/*` runtime projection becomes a second source of truth.
  - **Mitigation:** Treat `.weagent/*` as disposable session projection; sync only approved Skill drafts back to DB.

- **Risk:** Plugin scope grows into arbitrary execution.
  - **Mitigation:** v1 Plugin stores manifest/import/install record only and exposes no execution endpoint.

- **Risk:** Sandbox route security remains broad.
  - **Mitigation:** Capability APIs must be authenticated and permission checked; broader sandbox hardening remains a separate phase unless it blocks capability correctness.

## Success Criteria

- Capability library supports all four types as peer records.
- Agent default bindings are persisted with pinned versions and authorization snapshots.
- Session startup writes `.weagent/*` runtime projection and Agent-specific views.
- Skill lifecycle supports create, edit, import, runtime modification, draft, publish, and fork.
- Built-in Tool and minimal MCP calls produce DB-persisted call records.
- Plugin import/install record exists without Plugin execution.
- Existing multi-agent messaging, progress, and artifact flows are not broken.

## Verification Commands

Run from `E:\code for project\seedance-competition\agentshub\WeAgent` after implementation:

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

## Plan Self-Review

- Spec coverage: all 10 requirements from `001-SPEC.md` map to Tasks 1 through 12.
- Empty-slot scan: no unresolved sections are left for future interpretation.
- Scope check: this is one feature phase because all tasks support the same capability runtime contract; full marketplace, Claude/Codex compatibility mapping, and Plugin execution remain out of scope.
- Gate: plan is ready for review before implementation.

---

*Phase: 001-toolset*
*Plan created: 2026-05-28*
*Next step after user approval: execute Task 1 first, with tests before implementation where feasible.*
