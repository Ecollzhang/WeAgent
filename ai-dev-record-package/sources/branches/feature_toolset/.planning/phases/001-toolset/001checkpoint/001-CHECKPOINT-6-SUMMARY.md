# Checkpoint 6 Summary: Minimal MCP npx Runtime

**Date:** 2026-05-29
**Branch:** `feature/toolset`
**Commit scope:** Sandbox-side MCP runtime, MCP HTTP bridge methods, audited MCP call records, and tests.

## Completed

- Added `backend/app/sandbox/container/mcp_runtime.py`:
  - starts manifest-backed MCP servers inside the sandbox workspace;
  - speaks minimal JSON-RPC over stdio for `initialize`, `tools/list`, and `tools/call`;
  - stops individual or all running MCP servers;
  - enforces Agent-bound MCP authorization before start/call.
- Extended `.weagent` runtime helpers in `backend/app/sandbox/container/capabilities.py` for:
  - resolving Agent-bound MCP capabilities by `runtime_id`;
  - summarizing MCP call inputs and outputs;
  - writing MCP records through the same JSONL call path used by built-in Tools.
- Integrated MCP runtime into the container orchestrator:
  - starts/stops MCP servers;
  - lists MCP tools;
  - calls MCP tools with run snapshot creation and session id propagation.
- Added container API endpoints under `/api/mcp/*` and host client wrappers for:
  - list running servers;
  - start server;
  - list tools;
  - call tool;
  - stop server.
- Added `backend/tests/test_capability_mcp_runtime.py`.

## Verification Target

The v1 MCP target is deliberately minimal:

- import a fixture `source.type = npx` manifest as an MCP capability;
- prove Agent binding rejects missing required `run_command`;
- project a fixture MCP server into `.weagent/mcp/<runtime_id>/manifest.json`;
- start the server from the manifest command inside the sandbox workspace;
- list the fixture `echo` tool;
- call `echo`;
- write a `call_type = mcp` JSONL record with Agent, session, run, capability, version, permission, input, output, timing, and status metadata.

## Boundary Decisions Preserved

- MCP execution is sandbox-side only; the host backend only calls container APIs.
- Runtime uses the `.weagent/*` projection and does not create `.mcp.json`, `.claude/*`, or `.codex/*`.
- Plugin execution remains out of scope.
- This checkpoint does not add Skill draft sync.
- The unit fixture avoids network/package download; it validates the manifest-backed process/runtime path without depending on an external npm registry.

## Verification

Run from `backend`:

```powershell
python -m pytest tests/test_capability_mcp_runtime.py -q
```

Result:

- `4 passed`
- Warnings are existing SQLAlchemy/deprecation warnings plus current `datetime.utcnow` deprecation warnings.

Capability regression:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py tests/test_capability_tool_audit.py tests/test_capability_mcp_runtime.py -q
```

Result:

- `28 passed`
- Warnings are existing SQLAlchemy/deprecation warnings plus current `datetime.utcnow` deprecation warnings.

Syntax check:

```powershell
python -c "import ast, pathlib; files=['app/sandbox/container/mcp_runtime.py','app/sandbox/container/capabilities.py','app/sandbox/container/orchestrator.py','app/sandbox/container/server.py','app/sandbox/host/client.py','tests/test_capability_mcp_runtime.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8'), filename=f) for f in files]; print('syntax ok')"
```

Result:

- `syntax ok`

## Next

Checkpoint 7 should implement Plugin manifest import/install-record visibility while preserving the v1 boundary that Plugin code is not executable.
