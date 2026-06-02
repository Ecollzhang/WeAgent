# Checkpoint 7 Summary: Plugin Manifest Import

**Date:** 2026-05-29
**Branch:** `feature/toolset`
**Commit scope:** Plugin install records, Plugin import visibility, Capability Library display, and no-execution guard tests.

## Completed

- Added `PluginInstallRecord` as a manifest-only v1 install record:
  - user;
  - Plugin capability and version;
  - source/source ref;
  - npx package name/version;
  - install status;
  - original manifest subset;
  - included capability references.
- Updated npx manifest import so `type = plugin` creates both:
  - `Capability(type='plugin')`;
  - initial `CapabilityVersion`;
  - `PluginInstallRecord(status='installed')`.
- Updated capability responses so Plugin list/detail payloads include `install_record`.
- Updated MySQL bootstrap schema with `plugin_install_records`.
- Updated Capability Library display so Plugin cards/details show install status/package/version.
- Added tests proving:
  - Plugin manifest import creates an install record;
  - Plugin detail API exposes manifest and install record;
  - no Plugin execute endpoint exists in v1.

## Verification Target

Checkpoint 7 stays deliberately narrow:

- Plugin is a first-class capability type.
- Plugin import creates durable DB records.
- Plugin install status is visible to the platform.
- Plugin code is not executed and no execute endpoint is exposed.

## Boundary Decisions Preserved

- No Plugin runtime execution.
- No Plugin hooks.
- No Plugin UI extension execution.
- No arbitrary command execution.
- Plugin remains a package/source/install record in v1.

## Verification

Focused tests:

```powershell
python -m pytest tests/test_capability_service.py::test_import_plugin_manifest_creates_install_record tests/test_capability_api.py::test_plugin_manifest_detail_exposes_install_record_without_execution_endpoint -q
```

Result:

- `2 passed`

Capability regression:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py tests/test_capability_tool_audit.py tests/test_capability_mcp_runtime.py -q
```

Result:

- `30 passed`
- Warnings are existing SQLAlchemy/deprecation warnings plus current `datetime.utcnow` deprecation warnings.

Frontend build:

```powershell
npm run build
```

Result:

- Build completed.
- Existing bundle-size warnings remain for large assets/vendor chunks.

## Next

Checkpoint 8 should implement Skill draft sync:

- detect changes to projected `.weagent/skills/<runtime_id>/SKILL.md`;
- create `SkillRevisionDraft(status='pending_review')`;
- keep pinned Agent bindings unchanged when drafts are published or forked.
