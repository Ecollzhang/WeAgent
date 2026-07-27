# Checkpoint A Report: Contract Tests and Model Skeleton

**Phase:** 003 External Toolset Import and Audit  
**Status:** Complete  
**Started:** 2026-06-01  

## Scope

Checkpoint A establishes the backend contract for external toolset import before implementing preview UI or Docker execution:

- Import source parser for allowed npx forms.
- Bundle file validation for paths, sensitive files, and executable/binary files.
- Detection engine for syntax, lexical, illegal library/API, illegal operation, permission inference, and risk scoring.
- Persistence models for version assets, import jobs, and security audits.
- Version checksum coverage for Skill assets.

## Planned Verification

```powershell
python -m pytest tests\test_capability_import_security.py tests\test_capability_assets.py tests\test_capability_detection_engine.py
```

## Progress Log

- Completed RED tests for npx parser, bundle file validation, detection engine, asset models, import jobs, audits, and asset-aware checksums.
- Implemented `capability_import_security` with allowlisted npx parser and bundle path/file validation.
- Implemented `capability_detection_engine` with syntax, lexical, illegal library/API, illegal operation, permission inference, and risk aggregation rules.
- Added `CapabilityVersionAsset`, `CapabilityImportJob`, and `CapabilitySecurityAudit` models.
- Extended `CapabilityService.create_skill` and `create_version` to accept assets and include normalized asset summaries in version checksums.
- Updated app startup model imports and `backend/sql/init.sql` for the new tables.
- Targeted verification passed.

## Verification Results

```powershell
python -m pytest tests\test_capability_import_security.py tests\test_capability_assets.py tests\test_capability_detection_engine.py
```

Result: `14 passed`.

```powershell
python -m pytest tests\test_capability_service.py tests\test_capability_models.py
```

Result: `9 passed`.

```powershell
git diff --check -- backend\app\models\capability.py backend\app\models\__init__.py backend\app\services\capability_service.py backend\app\services\capability_import_security.py backend\app\services\capability_detection_engine.py backend\app\__init__.py backend\sql\init.sql backend\tests\test_capability_import_security.py backend\tests\test_capability_assets.py backend\tests\test_capability_detection_engine.py .planning\phases\001-toolset\003-external-toolset-import\CHECKPOINT-A-REPORT.md
```

Result: no whitespace errors; CRLF warnings only.

## Notes

- This checkpoint does not execute npx and does not require Docker.
- Full preview/confirm APIs are left for later checkpoints.
- Current detection engine is intentionally deterministic and lightweight; later checkpoints can replace best-effort parsing with richer parsers while preserving the audit item contract.
