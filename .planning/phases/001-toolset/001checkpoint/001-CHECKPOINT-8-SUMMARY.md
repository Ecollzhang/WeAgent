# Checkpoint 8 Summary: Skill Draft Sync

**Date:** 2026-05-29
**Branch:** `feature/toolset`
**Commit scope:** Runtime Skill draft detection, host/API draft sync, manager integration, and regression coverage.

## Completed

- Added runtime Skill baseline tracking during `.weagent/*` projection:
  - writes original `SKILL.md` checksum and content under `.weagent/drafts/skills/<runtime_id>/baseline.json`;
  - keeps `.weagent/skills/<runtime_id>/SKILL.md` as the editable session copy;
  - avoids duplicate draft payloads for the same runtime edit checksum.
- Added container-side draft collection:
  - compares current runtime `SKILL.md` against the projected baseline;
  - emits draft payloads tied to `session_id`, `agent_id`, `source_skill_id`, and `source_version_id`;
  - stores the latest draft payload under `.weagent/drafts/skills/<runtime_id>/<agent_id>.json`.
- Added DB draft sync service and authenticated API:
  - `POST /api/capabilities/drafts/sync`;
  - validates Agent ownership, Skill visibility, and source version identity;
  - persists `SkillRevisionDraft(status='pending_review')`;
  - treats same pending checksum as idempotent.
- Integrated host manager sync after Agent message, chain, and delegation calls.
- Preserved existing publish and fork flow:
  - publishing a draft creates a new Skill version;
  - saving as fork creates a new Skill capability;
  - pinned Agent bindings remain on their original version unless explicitly upgraded.

## First-Principles Check

The core invariant is that DB remains the durable source of truth while `.weagent/*` is a disposable session runtime projection. This checkpoint preserves that invariant by allowing Agent/platform runtime edits only to create reviewable drafts. Runtime edits do not directly overwrite the user Skill library, do not publish automatically, and do not move pinned Agent bindings.

## Verification

Focused Skill draft sync tests:

```powershell
python -m pytest tests/test_capability_skill_draft_sync.py -q
```

Result:

- `3 passed`

Capability regression:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py tests/test_capability_tool_audit.py tests/test_capability_mcp_runtime.py tests/test_capability_skill_draft_sync.py -q
```

Result:

- `33 passed`
- Warnings are existing SQLAlchemy/deprecation warnings plus current `datetime.utcnow` deprecation warnings.

Syntax check:

```powershell
python -c "import ast, pathlib; files=['app/sandbox/container/capabilities.py','app/services/capability_draft_sync_service.py','app/schemas/capability_schema.py','app/controllers/capability_controller.py','app/sandbox/container/orchestrator.py','app/sandbox/container/server.py','app/sandbox/host/client.py','app/sandbox/host/manager.py','tests/test_capability_skill_draft_sync.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('syntax ok')"
```

Result:

- `syntax ok`

## Next

Checkpoint 9 should run end-to-end regression checks:

- existing multi-agent message display;
- Agent progress display;
- artifact display;
- UI-to-sandbox toolset happy path, including `.weagent/*` projection, built-in Tool call record, Skill draft, MCP call record, and Plugin no-execution boundary.
