# Checkpoint 3 Summary: Frontend Capability Management

**Date:** 2026-05-28
**Branch:** `feature/toolset`
**Status:** Complete

## Delivered

- Added frontend capability API wrapper for library, imports, versions, Agent bindings, upgrades, drafts, and call records.
- Added `CapabilityLibrary.vue` with first-class Skill, Tool, MCP, and Plugin tabs/filters.
- Added Skill creation from Markdown.
- Added Markdown text/file import for Skills.
- Added Skill version creation so editing a Skill produces a new pinned version instead of mutating existing bindings.
- Added npx manifest import with parsed capability preview and permission summary.
- Added Plugin display as manifest-only scope, with no Plugin execution entrypoint.
- Added `/capabilities` route and sidebar navigation.
- Updated Agent create/edit form to use capability bindings as the primary toolset path.
- Added Agent permission grant checklist using capability version permission declarations.
- Added pinned version display and upgrade indicator hook for existing Agent bindings.
- Preserved legacy `skill` and `tool_ids` as read-only compatibility fields during v1.

## Backend Support Added During This Checkpoint

- `POST /api/capabilities/<id>/versions`
- `GET /api/agents/<agent_id>/capabilities/upgrades`
- `PUT /api/agents/<agent_id>/capabilities/<binding_id>`

These were needed by the frontend acceptance criteria for Skill editing, upgrade display, and binding permission updates.

## Files Added

- `frontend/src/api/capabilities.js`
- `frontend/src/views/CapabilityLibrary.vue`
- `frontend/tests/capability-ui-contract.test.js`

## Files Modified

- `backend/app/controllers/capability_controller.py`
- `backend/app/schemas/capability_schema.py`
- `backend/app/services/capability_service.py`
- `backend/tests/test_capability_api.py`
- `frontend/src/components/AgentEditForm/index.vue`
- `frontend/src/components/Sidebar/index.vue`
- `frontend/src/router/index.js`
- `frontend/src/views/AgentManager.vue`

## Verification

From `backend`:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py -q
```

Result: `15 passed`

From `frontend`:

```powershell
node tests\capability-ui-contract.test.js
```

Result: `capability UI contract ok`

```powershell
npm run build -- --dest dist-check
```

Result: build passed with existing bundle-size warnings for `bg.png` and `chunk-vendors`.

## Known Notes

- `npm run build` without `--dest dist-check` can fail on this machine when Windows refuses to unlink an old `frontend/dist` sourcemap. The temporary `dist-check` build path verifies compilation without touching the old dist folder.
- Backend tests still emit legacy SQLAlchemy warnings already present in earlier checkpoints.
- Runtime `.weagent/*` projection is not implemented in this checkpoint; it remains Checkpoint 4.

## Next

Checkpoint 4: build host-side projection and container `.weagent/*` materialization.
