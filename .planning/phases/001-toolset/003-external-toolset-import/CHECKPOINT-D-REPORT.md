# Checkpoint D Report: Docker Import Sandbox and npx Preview

**Phase:** 003 External Toolset Import and Audit  
**Status:** Complete  
**Started:** 2026-06-01  

## Scope

Checkpoint D adds the execution boundary for npx installer imports:

- Parse only allowlisted npx forms.
- Run installer in a one-shot Docker container.
- Redirect `HOME`, `CODEX_HOME`, `CLAUDE_HOME`, and `AGENTS_HOME` to a temporary import directory.
- Scan generated files through the static preview service.
- Return clear errors when Docker is unavailable.

## Planned Verification

```powershell
python -m pytest tests\test_capability_npx_import_sandbox.py
docker info
```

## Progress Log

- Completed RED tests for Docker command construction, isolated agent homes, shell-injection rejection, and Docker unavailable reporting.
- Implemented `capability_npx_import_sandbox`.
- npx sources reuse the allowlisted parser from Checkpoint A.
- Docker command sets isolated `HOME`, `CODEX_HOME`, `CLAUDE_HOME`, and `AGENTS_HOME`.
- Runner output directory is scanned through the static preview service from Checkpoint B.
- Docker unavailable states return a clear error instead of falling back to host execution.
- Started Docker Desktop and verified daemon availability with `docker info`.

## Verification Results

```powershell
python -m pytest tests\test_capability_npx_import_sandbox.py
```

Result: `3 passed`.

```powershell
docker info
```

Result: Docker client and server available; server `29.5.2`, Docker Desktop backend.

```powershell
python -m pytest tests\test_capability_import_security.py tests\test_capability_assets.py tests\test_capability_detection_engine.py tests\test_capability_import_preview.py tests\test_capability_security_audit.py tests\test_capability_npx_import_sandbox.py
```

Result: `25 passed`.
