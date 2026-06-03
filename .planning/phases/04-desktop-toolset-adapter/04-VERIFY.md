# Phase 04 Verification: Desktop Toolset Adapter

**Started:** 2026-06-03
**Branch:** `combine/toolset_v1.1.0`
**Status:** In progress

## Checkpoint A: Pre-flight and Baseline Audit

### Current Branch

- `git status --short --branch` reports `combine/toolset_v1.1.0...origin/combine/toolset_v1.1.0`.
- Phase 04 planning files were present but uncommitted before implementation work.

### Baseline Desktop Structure

- `clients/desktop/src/router/index.js` currently exposes `/conversations`, `/agents`, `/settings`, login/register/server setup, but no `/tools` route.
- `clients/desktop/src/views/Agents.vue` currently contains a disabled sidebar Tools button and uses legacy `tool_ids` as the primary tool picker.
- `clients/desktop/src/services/api.js` currently exposes basic Agent/message/file/model-config APIs and `getTools()`, but not capability/toolset/import/provider-config APIs.
- `clients/desktop/src/main.js` only registers a small subset of Element UI components.

### Web/Backend Reuse Points

- Web API wrappers already expose:
  - `/api/capabilities`
  - `/api/capabilities/import/preview`
  - `/api/capabilities/import/confirm`
  - `/api/capabilities/import/mcp-manifest`
  - `/api/capabilities/<id>/assets`
  - `/api/capabilities/<id>/audits`
  - `/api/capabilities/<id>/delete-impact`
  - `/api/capabilities/<id>/provider-configs`
  - `/api/agents/<agent_id>/capabilities`
  - `/api/toolsets/categories`
- Web `frontend/src/views/Tools.vue` already contains the desired import, audit, provider-config, and deletion workflows. Desktop should reuse the backend contract and port a desktop-appropriate UI.

### Baseline Build

- Command: `npm run build` in `clients/desktop`.
- Result: failed before code validation because `vite` is not installed or not available in `clients/desktop/node_modules/.bin`.
- Error: `'vite' is not recognized as an internal or external command`.
- Follow-up: install or restore desktop dependencies before final build verification.

### Plan Adjustment

The user expanded the desired outcome beyond the initial Phase 04 scope. Phase 04 SPEC/PLAN were updated so core desktop management flows are now in scope:

- Skill create/edit.
- Markdown, zip bundle, npx, and MCP manifest import.
- Security audit preview/detail and high-risk expert confirmation.
- Provider config create/test/save/enable/disable/delete.
- Runtime execution remains in backend/sandbox/provider runtime; Electron does not directly execute npx, MCP servers, Docker, scripts, or built-in Tools.

## Checkpoint B: Desktop API Wrappers

### Implemented

- Added `clients/desktop/src/api/capabilities.js`.
- Added `clients/desktop/src/api/toolsets.js`.
- Added compatibility re-export modules:
  - `clients/desktop/src/api/tools.js`
  - `clients/desktop/src/api/upload.js`
- Exported the shared desktop `request()` function from `clients/desktop/src/services/api.js` so desktop API wrappers use the same server URL and auth-token behavior as the existing desktop client.

### Covered API Families

- Capability list/detail/version/assets/audits/delete impact.
- Skill creation and version creation.
- Import preview/confirm and MCP manifest import.
- Provider config create/update/test/enable/disable/delete.
- Agent capability binding/list/delete/update.
- Toolset category list/create/update/delete.

## Checkpoint C: Desktop Toolset Entry

### Implemented

- Added desktop route `/tools`.
- Added `clients/desktop/src/views/Tools.vue` using the Web Toolset page as the functional baseline.
- Added `clients/desktop/src/components/Sidebar/index.vue` so the Toolset page has the same desktop sidebar navigation.
- Enabled Tools navigation from desktop Conversations, Agents, Settings, and the new Sidebar component.
- Registered Element UI globally in `clients/desktop/src/main.js`, because the migrated Toolset management UI uses Element dialogs, tables, tabs, forms, alerts, tags, and loading directives.

### Management Workflows Present

- Category-first navigation.
- Skill/MCP/Plugin/Tool tabs.
- Capability cards and detail panel.
- New Skill Markdown.
- Skill Markdown version edit.
- Markdown file/text import.
- zip bundle import.
- npx import preview/confirm.
- MCP manifest preview/confirm.
- Security audit preview/detail.
- High-risk expert confirmation.
- User capability delete with impact preview.
- Provider config create/test/save/enable/disable/delete.

## Checkpoint D: Desktop Agent Binding UI

### Implemented

- Updated `clients/desktop/src/views/Agents.vue` to use capability binding as the primary toolset UX.
- Agent create/edit now loads:
  - toolset categories,
  - bindable capabilities,
  - existing Agent capability bindings.
- Agent create/edit can add Skill/MCP/Plugin/Tool bindings with pinned versions.
- Existing bindings can be removed through the real `DELETE /api/agents/<agent_id>/capabilities/<binding_id>` API.
- Save payload now includes `capability_bindings` while preserving provider selection and legacy `tool_ids` compatibility metadata.

## Checkpoint D2: Desktop Management Workflows

### Implemented

- Desktop Tools page exposes the same core management flows as Web through backend APIs.
- Electron still does not directly execute npx, MCP servers, Docker, scripts, or built-in Tools.

## Desktop Build Check

- Command: `node "G:\software\Node\node_modules\npm\bin\npm-cli.js" run build` in `clients/desktop`.
- Result: passed.
- Notes:
  - Vite reports the usual chunk-size warning for the large Element UI bundle.
  - The build emitted `Tools-*.js` and `Tools-*.css`, proving the desktop Toolset route/page compiles.
  - Dependency installation required calling the real npm CLI directly because the local npm shim points to a missing AppData npm path.
  - `npm install` reported 11 dependency audit issues in the existing Electron/Vue2 dependency tree; this was not fixed in this checkpoint because it may require dependency upgrades outside the Toolset feature scope.

## Checkpoint E: Runtime Projection Evidence

### Evidence

- Existing projection tests were rerun and passed.
- `tests/test_capability_projection.py` proves DB-backed Agent bindings generate:
  - shared `.weagent/capabilities/index.json`,
  - per-agent `.weagent/agents/<agent_id>/capabilities.json`,
  - per-agent `skill-index.json`,
  - per-agent `tool-index.json`,
  - per-agent `permissions.json`.
- `tests/test_capability_container_projection.py` proves container-side projection writing/reading works.

### Command

```powershell
python -m pytest tests\test_capability_projection.py tests\test_capability_container_projection.py -q
```

This subset was included in the provider/runtime verification command below.

## Checkpoint F: Codex Provider Evidence

### Evidence

- `tests/test_sandbox_codex_runner_stage4.py::test_setup_writes_bound_mcp_servers_into_codex_config` proves Codex reads the bound Agent capability view and writes the MCP server into `config.toml`.
- The asserted config contains:
  - `[mcp_servers.memory_mcp]`
  - `command = "npx"`
  - `args = ["--yes", "@modelcontextprotocol/server-memory"]`
- This is config/runtime evidence without requiring live Codex network access.

## Checkpoint G: Claude Provider Evidence

### Evidence

- Added `tests/test_sandbox_provider_runner_stage2.py::test_claude_setup_writes_capability_bootstrap_to_prompt_files`.
- The test proves Claude provider setup writes both `.claude/agent.md` and `CLAUDE.md` with the capability bootstrap paths:
  - `/workspace/.weagent/agents/agent-1/capabilities.json`
  - `/workspace/.weagent/agents/agent-1/skill-index.json`
  - `/workspace/.weagent/agents/agent-1/tool-index.json`
  - `/workspace/.weagent/agents/agent-1/permissions.json`
- This is prompt/context evidence without requiring live Claude network access.

## Checkpoint H: Built-in Tool / MCP Binding Evidence

### Evidence

- `tests/test_configured_tool_runtime_gate.py` proves configured Tool projection and call-record behavior.
- `tests/test_capability_mcp_runtime.py` proves imported npx MCP bindings require `run_command`, can be represented in runtime projection, and can be used through the MCP runtime path.
- `tests/test_builtin_tool_handlers.py` proves implemented built-in Tool handlers remain callable through the sandbox tool registry.

## Runtime Verification Commands

### Provider Injection Subset

```powershell
python -m pytest tests\test_sandbox_provider_runner_stage2.py tests\test_sandbox_codex_runner_stage4.py tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_capability_mcp_runtime.py tests\test_configured_tool_runtime_gate.py -q
```

Result: `37 passed`.

### Toolset Capability Subset

```powershell
python -m pytest tests\test_capability_api.py tests\test_capability_import_preview.py tests\test_capability_import_confirm.py tests\test_capability_import_security.py tests\test_capability_npx_import_sandbox.py tests\test_capability_mcp_runtime.py tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_tool_provider_config_api.py tests\test_builtin_tool_handlers.py tests\test_configured_tool_runtime_gate.py tests\test_toolset_categories.py -q
```

Result: `60 passed`.
