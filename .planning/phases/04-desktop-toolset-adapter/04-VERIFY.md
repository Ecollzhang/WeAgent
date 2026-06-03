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

