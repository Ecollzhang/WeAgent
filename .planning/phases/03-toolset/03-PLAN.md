---
phase: 03-toolset
plan: "03"
type: merge
wave: 1
depends_on:
  - 01-agent-adapter-streaming-factory
  - 02-conversation-context-system
files_modified:
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/STATE.md
  - .gitignore
  - backend/app/__init__.py
  - backend/app/models/__init__.py
  - backend/app/models/capability.py
  - backend/app/models/tool_provider_config.py
  - backend/app/models/toolset_category.py
  - backend/app/controllers/capability_controller.py
  - backend/app/controllers/toolset_controller.py
  - backend/app/schemas/capability_schema.py
  - backend/app/services/capability_service.py
  - backend/app/services/capability_projection_service.py
  - backend/app/services/tool_provider_config_service.py
  - backend/app/services/builtin_tool_definitions.py
  - backend/app/services/toolset_category_service.py
  - backend/app/sandbox/api/routes.py
  - backend/app/sandbox/container/agent.py
  - backend/app/sandbox/container/capabilities.py
  - backend/app/sandbox/container/mcp_runtime.py
  - backend/app/sandbox/container/tools/__init__.py
  - backend/app/sandbox/container/providers/*
  - backend/app/sandbox/host/client.py
  - backend/app/sandbox/host/manager.py
  - frontend/src/api/capabilities.js
  - frontend/src/api/toolsets.js
  - frontend/src/components/AgentEditForm/index.vue
  - frontend/src/views/Tools.vue
autonomous: false
requirements:
  - REQ-16
  - REQ-17
  - REQ-18
  - REQ-19
  - REQ-20
  - REQ-21
  - REQ-22
  - REQ-23
  - REQ-24
  - REQ-25
  - REQ-26
must_haves:
  truths:
    - D-01: `desktop_app_support` is the merge base; `toolset` is a module to embed.
    - D-02: Web frontend is in scope; desktop client UI is out of scope.
    - D-03: Backend port and sandbox service/proxy behavior follow desktop branch.
    - D-04: Keep desktop provider runtime under `backend/app/sandbox/container/providers/*`.
    - D-05: Do not restore old `backend/app/adapters/*` as the main runtime.
    - D-06: Capability projection writes canonical `/workspace/.weagent/*`.
    - D-07: Each Agent reads only its own `.weagent/agents/<agent_id>` view.
    - D-08: Tool/MCP calls must leave audit records.
    - D-09: Hidden/deferred Tools are not shown or counted in Web toolset UI.
    - D-10: `.planning` keeps desktop Phase 01/02 and adds toolset as Phase 03.
  artifacts:
    - path: .planning/phases/03-toolset/03-SPEC.md
      provides: Locked merge requirements and boundaries.
    - path: .planning/phases/03-toolset/03-PLAN.md
      provides: Merge execution checklist.
    - path: .planning/phases/03-toolset/03-VERIFY.md
      provides: Merge verification and sandbox smoke results.
---

# Phase 03 Plan: Toolset Desktop Merge

Status: verified on 2026-06-02. See `03-VERIFY.md` for test, build, and
Docker sandbox smoke results.

## Objective

Create `combine/toolset_v1.1.0` by merging `origin/feature/toolset` into a branch based on `origin/feature/desktop_app_support_v1.0.6`, then make the Toolset module work on the desktop branch runtime architecture.

## Strategy

This is not a mechanical merge. The desktop branch owns runtime architecture; the toolset branch owns capability data, UI, imports, security checks, provider config, and `.weagent/*` projection. Conflict resolution must preserve both responsibilities.

## Checkpoints

### Checkpoint A: Pre-flight and Merge Entry

- Confirm clean working tree.
- Confirm current branch is `combine/toolset_v1.1.0`.
- Confirm branch is based on `origin/feature/desktop_app_support_v1.0.6`.
- Run `git merge origin/feature/toolset --no-ff --no-commit`.
- Record actual conflicts before editing.

Verification:

- `git status --short --branch` shows merge in progress only after merge command.
- Conflict file list is captured in the final merge report.

### Checkpoint B: Planning Conflict Resolution

- Keep desktop top-level `.planning` files as the primary planning system.
- Keep `01-agent-adapter-streaming-factory` and `02-conversation-context-system`.
- Convert toolset planning into Phase 03 by keeping this `03-toolset` directory.
- Move or archive old `001-toolset` artifacts only if they are needed for review; do not let them overwrite top-level Phase 01/02 context.

Verification:

- `.planning/phases/03-toolset/03-SPEC.md` and `03-PLAN.md` exist.
- `.planning/ROADMAP.md` references Phase 03.
- No unresolved `.planning` conflict markers remain.

### Checkpoint C: Backend Model, Schema, API Registration

- Merge capability and toolset models into `backend/app/models`.
- Merge schemas and controllers for:
  - `/api/capabilities`
  - `/api/agents/<agent_id>/capabilities`
  - `/api/toolsets`
  - provider config routes under capability API.
- Update `backend/app/__init__.py` to import models, register blueprints, seed builtin categories and builtin tool capabilities.
- Preserve desktop migration additions for sandbox session columns, agent runs, messages, service proxy, and model config.

Verification:

- `python -m py_compile backend/app/__init__.py` succeeds.
- Backend tests for capability models/API/provider config can import the app.

### Checkpoint D: Built-in Tool Catalog and Visibility

- Merge `builtin_tool_definitions.py`, `toolset_category_service.py`, `tool_provider_config_service.py`, and related tests.
- Keep the toolset rule that hidden/deferred/non-configurable tools are not counted or displayed.
- Keep implemented/configurable tools such as image info, web search, database query, image analysis, and image generation according to prior toolset decisions.
- Preserve desktop legacy `AgentTool` compatibility only where needed for existing Web/agent flows.

Verification:

- Toolset category API count matches visible list items.
- Code generation/deferred tools are not bindable.
- Provider config APIs work for configurable tools.

### Checkpoint E: Web Frontend Toolset UI

- Use the toolset branch `frontend/src/views/Tools.vue` as the Web toolset page baseline.
- Restore/add `frontend/src/api/capabilities.js` and `frontend/src/api/toolsets.js`.
- Keep desktop frontend routing and API base behavior.
- Ensure the Web toolset UI supports:
  - category rail,
  - Skill/MCP/Plugin/Tool tabs,
  - create/edit Skill,
  - markdown/zip/npx/MCP manifest import,
  - provider config dialog for configurable Tools,
  - side panel close behavior and clean manifest display rules.
- Do not add desktop client UI.

Verification:

- `npm run build` succeeds under `frontend`.
- Existing/updated frontend contract tests for toolset/provider config pass where available.

### Checkpoint F: Agent Edit Form Integration

- Merge desktop provider selector with toolset capability selector.
- Keep `adapter_name` options: Claude Code, Codex, OpenCode, and any desktop-supported fallback.
- Save Agent basic fields and capability bindings without overwriting each other.
- Reload Agent edit state so persisted bindings appear after refresh.

Verification:

- Creating an Agent can select provider and capabilities in the same form.
- Editing an existing Agent preserves provider and capability bindings.

### Checkpoint G: Sandbox Projection Integration

- Keep desktop `AgentRuntime` and `ProviderRunnerFactory`.
- Add toolset capability bootstrap text to the agent system prompt without removing desktop reporting/service instructions.
- Add a host-side step when creating sessions/adding agents to build DB-backed capability projection for all session agents.
- Write projection into the container at `/workspace/.weagent/*`.
- Ensure each Agent has:
  - `/workspace/.weagent/agents/<agent_id>/capabilities.json`
  - `/workspace/.weagent/agents/<agent_id>/skill-index.json`
  - `/workspace/.weagent/agents/<agent_id>/tool-index.json`
  - `/workspace/.weagent/agents/<agent_id>/permissions.json`

Verification:

- Sandbox smoke can list `.weagent` files.
- Agent prompt contains both desktop runtime instructions and capability projection instructions.

### Checkpoint H: MCP Runtime and Tool Call Audit

- Merge sandbox-side `capabilities.py` and `mcp_runtime.py` as support modules, not as replacements for desktop provider runtime.
- Register built-in tool handlers in `backend/app/sandbox/container/tools/__init__.py`.
- Ensure MCP server lifecycle can start a manifest-backed stdio server, list tools, call a tool, and record the call.
- Ensure built-in implemented/configured tool calls append audit records.

Verification:

- A minimal MCP fixture such as `@modelcontextprotocol/server-memory` or existing manifest smoke can start/list/call if network/dependency state allows.
- Built-in tool call smoke writes a `.weagent` run record.

### Checkpoint I: Tests, Build, and Docker Smoke

- Run focused backend tests first:
  - capability models/API/service,
  - toolset categories,
  - provider config API,
  - sandbox projection,
  - MCP runtime,
  - builtin tool runtime.
- Run broader backend pytest if focused tests pass.
- Run frontend build.
- Build Docker sandbox image if Docker is available.
- Run minimal sandbox smoke for `.weagent/*`, provider runner creation, and one Tool/MCP path.

Verification:

- Test/build results are recorded in a merge report.
- Any skipped Docker/network verification has a concrete reason.

### Checkpoint J: Commit and Push

- Confirm no conflict markers remain.
- Commit the merge with a clear message.
- Push `combine/toolset_v1.1.0` to origin.
- Provide a PR handoff summary listing resolved conflicts, verification results, and remaining risks.

Verification:

- `git status --short --branch` is clean after commit.
- `origin/combine/toolset_v1.1.0` points to the local HEAD after push.

## Conflict Policy

- `.planning/*`: keep desktop top-level context, add `03-toolset`, do not overwrite Phase 01/02.
- `.gitignore`: union both branches.
- `backend/app/sandbox/container/providers/*`: keep desktop branch.
- `backend/app/sandbox/container/agent.py`: keep desktop provider/reporting/service instructions, append capability bootstrap.
- `backend/app/sandbox/container/tools/__init__.py`: merge desktop basic tool registry with toolset implemented/configured Tool handlers.
- `backend/app/sandbox/api/routes.py`: keep desktop service proxy routes, add capability/tool/MCP session routes only if still needed.
- `backend/app/sandbox/host/manager.py`: keep desktop lifecycle and service port logic, add projection write/sync hooks.
- `frontend/src/views/Tools.vue`: prefer toolset capability UI, then adapt to desktop routing/API base.
- `frontend/src/components/AgentEditForm/index.vue`: manual merge, no one-sided checkout.
- `backend/app/adapters/*`: do not restore as runtime authority; if files appear from toolset merge, remove or quarantine unless a specific import requires a compatibility shim.

## Threat Model

- Risk: capability projection exposes another Agent's permissions.
  - Mitigation: projection writes shared catalog plus per-agent view; Agent prompt points to per-agent files.
- Risk: MCP/npx import executes untrusted code.
  - Mitigation: retain manifest preview, permission declaration, security audit, explicit user confirmation, and sandbox-only execution.
- Risk: provider config secrets leak into UI or audit logs.
  - Mitigation: keep provider config sensitive-field masking and avoid rendering raw secrets in manifests.
- Risk: desktop provider runner breaks due to old adapter imports.
  - Mitigation: preserve `ProviderRunnerFactory` as the only sandbox execution entry.
- Risk: hidden/deferred tools confuse users or inflate tab counts.
  - Mitigation: filter hidden/deferred/non-configurable tools in category count and UI list.

## Success Criteria

- [x] Merge branch is created and pushed as `combine/toolset_v1.1.0`.
- [x] Web toolset module is available on desktop backend/frontend.
- [x] Agent provider selection and capability binding both work.
- [x] Sandbox runtime preserves desktop provider architecture.
- [x] `.weagent/*` projection exists in sandbox and points each Agent to its own view.
- [x] Skill lifecycle remains usable.
- [x] Configurable Tool lifecycle remains usable.
- [x] MCP minimal runtime remains testable.
- [x] Tests/build/smoke results are reported.
