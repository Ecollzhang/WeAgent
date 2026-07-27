# Checkpoint 5 Summary: Built-in Tool Audit

**Date:** 2026-05-29
**Branch:** `feature/toolset`
**Commit scope:** Built-in Tool capability audit records, JSONL run logs, DB sync service, and tests.

## Completed

- Updated `ToolRegistry.call_from_agent` so the real Tool execution boundary:
  - resolves the Agent's bound Tool capability from `.weagent/agents/<agent_id>/capabilities.json`;
  - checks granted permissions before executing capability-bound Tools;
  - writes completed and failed call records to `.weagent/runs/<run_id>/calls.jsonl`.
- Updated orchestrator Tool paths to pass current `run_id` and `session_id` into Tool calls.
- Added runtime helpers in `backend/app/sandbox/container/capabilities.py` for:
  - Tool permission usage;
  - bound Tool capability resolution;
  - input/output summaries;
  - JSONL append.
- Extended Tool projection payloads with source/source_ref/manifest data needed by the sandbox resolver.
- Added `backend/app/services/capability_call_sync_service.py` to persist sandbox JSONL records through the existing Capability call-record validation path.
- Updated capability call sync controller to use the sync service.
- Added `backend/tests/test_capability_tool_audit.py`.

## Verification Target

The v1 built-in Tool target is `file_operations`:

- `read_file` requires `read_workspace` and writes a completed record.
- `write_file` requires `write_workspace`; if the Agent only granted `read_workspace`, the call is denied and writes a failed record.

This keeps the checkpoint narrow while proving the capability binding path, permission snapshot, JSONL audit, and DB sync path.

## Boundary Decisions Preserved

- This checkpoint does not add MCP runtime execution.
- This checkpoint does not add Plugin execution.
- This checkpoint does not add Skill draft sync.
- Legacy non-capability Tool execution remains available when no matching `.weagent` Tool binding exists, preserving current multi-agent behavior during migration.

## Verification

Run from `backend`:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py tests/test_capability_tool_audit.py -q
```

Result:

- `24 passed`
- Warnings are existing SQLAlchemy/deprecation warnings plus current `datetime.utcnow` deprecation warnings.

Syntax check:

```powershell
python -c "import ast, pathlib; files=['app/services/capability_projection_service.py','app/services/capability_call_sync_service.py','app/sandbox/container/capabilities.py','app/sandbox/container/tools/__init__.py','app/sandbox/container/orchestrator.py','app/controllers/capability_controller.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('syntax ok')"
```

Result:

- `syntax ok`

## Next

Checkpoint 6 should implement the minimal MCP npx runtime:

- fixture npx manifest imports as MCP;
- binding requires `run_command`;
- sandbox starts the MCP server;
- sandbox lists tools and performs one minimal audited call;
- MCP calls reuse the same `.weagent/runs/<run_id>/calls.jsonl` and DB sync path.
