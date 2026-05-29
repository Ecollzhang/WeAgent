# Checkpoint 4 Summary: Runtime Projection

**Date:** 2026-05-29
**Branch:** `feature/toolset`
**Commit scope:** Runtime projection service, container `.weagent/*` writer, host/container bootstrap integration, and projection tests.

## Completed

- Added `backend/app/services/capability_projection_service.py`.
- Added `backend/app/sandbox/container/capabilities.py`.
- Added container API `POST /api/capabilities/projection`.
- Added host client method for applying capability projection.
- Updated host session creation to project capabilities before creating sandbox Agents.
- Updated add-Agent path to refresh projection before creating the new runtime Agent.
- Updated container orchestrator to:
  - write `.weagent/*` projection;
  - append compact Agent bootstrap instructions;
  - write run snapshots under `.weagent/runs/<run_id>/`.
- Added tests for:
  - enabled pinned bindings;
  - disabled binding exclusion;
  - per-Agent views and permission snapshots;
  - Skill/MCP/Plugin/Tool as peer capability types;
  - same Skill with different pinned versions producing separate runtime entries;
  - container `.weagent/*` file materialization;
  - host projection before Agent creation.

## Boundary Decisions Preserved

- DB remains canonical; `.weagent/*` remains disposable session runtime projection.
- v1 generates only `.weagent/*`.
- No `.claude/skills`, `.codex/skills`, or `.mcp.json` compatibility mapping is generated.
- Plugin remains manifest/import/install-record scope only; no Plugin execution.
- MCP runtime execution is still deferred to Checkpoint 6.
- Built-in Tool call JSONL audit is still deferred to Checkpoint 5.

## Verification

Run from `backend`:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py -q
```

Result:

- `21 passed`
- Warnings are existing SQLAlchemy/deprecation warnings.

Syntax check:

```powershell
python -c "import ast, pathlib; files=['app/services/capability_projection_service.py','app/sandbox/container/capabilities.py','app/sandbox/container/orchestrator.py','app/sandbox/container/server.py','app/sandbox/host/manager.py','app/sandbox/host/client.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('syntax ok')"
```

Result:

- `syntax ok`

## Next

Checkpoint 5 should connect bound built-in Tool capabilities to real call audit records:

- resolve Tool capability for an Agent from `.weagent/agents/<agent_id>/capabilities.json`;
- write call entries to `.weagent/runs/<run_id>/calls.jsonl`;
- sync those records into DB `CapabilityCallRecord`.
