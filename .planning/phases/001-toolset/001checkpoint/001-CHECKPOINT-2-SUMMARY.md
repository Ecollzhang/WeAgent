# Checkpoint 2 Summary: Service and API

**Date:** 2026-05-28
**Branch:** `feature/toolset`
**Status:** Complete

## Delivered

- Added capability repository and service foundation for Skill, MCP, Plugin, and Tool capability records.
- Added permission declaration/grant validation for Agent bindings.
- Added pinned Agent binding authorization snapshots.
- Added upgrade status checks so newer Skill versions do not move existing Agent bindings.
- Added npx manifest import for MCP/Plugin/Skill definitions.
- Added built-in Tool capability seeding from existing platform Tool templates.
- Added authenticated capability APIs for:
  - library list/detail/version lookup
  - Skill create and Markdown import
  - npx manifest import
  - Agent default capability bind/list
  - Skill draft list/publish/fork
  - call record sync/list
- Added Agent create/update support for `capability_bindings` while preserving legacy `skill` and `tool_ids`.
- Added user-scope protection so Agents cannot bind another user's private capability versions.

## Files Added

- `backend/app/repositories/capability_repo.py`
- `backend/app/services/capability_service.py`
- `backend/app/schemas/capability_schema.py`
- `backend/app/controllers/capability_controller.py`
- `backend/tests/test_capability_service.py`
- `backend/tests/test_capability_api.py`

## Files Modified

- `backend/app/__init__.py`
- `backend/app/controllers/agent_controller.py`
- `backend/app/schemas/agent_schema.py`
- `backend/app/services/agent_service.py`

## Verification

From `backend`:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py -q
```

Result: `13 passed`

```powershell
python -c "from pathlib import Path; files=['app/services/capability_service.py','app/schemas/capability_schema.py','app/controllers/capability_controller.py','app/controllers/agent_controller.py','app/services/agent_service.py','app/__init__.py']; [compile(Path(f).read_text(encoding='utf-8'), f, 'exec') for f in files]; print('syntax ok')"
```

Result: `syntax ok`

## Known Notes

- Test output still includes existing SQLAlchemy warnings from legacy `Query.get`, `datetime.utcnow`, and the pre-existing `artifacts`/`messages` drop-order cycle.
- Plugin execution remains intentionally out of scope; v1 only imports and records plugin manifests.
- Runtime projection, Tool call JSONL, and MCP runtime are still future checkpoints.

## Next

Checkpoint 3: implement frontend Capability Library and Agent binding UI against the new API.
