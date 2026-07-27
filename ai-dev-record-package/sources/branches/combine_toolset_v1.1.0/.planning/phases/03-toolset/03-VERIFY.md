---
phase: 03-toolset
type: merge-verification
branch: combine/toolset_v1.1.0
base: origin/feature/desktop_app_support_v1.0.6
merged_from: origin/feature/toolset
verified_at: 2026-06-02
---

# Phase 03 Verification: Toolset Desktop Merge

## Result

Phase 03 merge is verified for the current Web + backend + sandbox runtime scope.

The merge keeps desktop sandbox/provider runtime as the authority and migrates the
toolset capability module into that runtime. Desktop client UI work remains out of
scope for this phase.

## Checkpoints

- Planning checkpoint pushed: `7662028 docs: plan toolset desktop merge`.
- Merge checkpoint pushed: `bbf6fd6 merge: combine toolset with desktop runtime`.
- Toolset planning is stored as `.planning/phases/03-toolset`.
- Old `001-toolset` planning artifacts from the toolset branch were not allowed to
  overwrite the desktop top-level planning state.

## Conflict Resolution Summary

- `.planning/*`: kept desktop Phase 01/02 top-level context and added Phase 03.
- `.gitignore`: unioned desktop and toolset ignores.
- `backend/app/sandbox/Dockerfile`: kept desktop multi-provider sandbox image.
- `backend/app/sandbox/container/agent.py`: kept desktop `AgentRuntime` and added
  capability bootstrap text.
- `backend/app/sandbox/container/orchestrator.py`: kept desktop provider runner
  flow and attached toolset projection/MCP/runtime helpers.
- `backend/app/sandbox/host/manager.py`: added DB-backed capability projection
  before agent creation.
- Web frontend: kept the toolset `Tools.vue` capability UI and desktop routing.

## Automated Verification

Commands run:

```powershell
python -m compileall app
python -m pytest tests\test_sandbox_provider_health.py tests\test_sandbox_provider_config_stage3.py tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_tool_provider_config_api.py tests\test_toolset_categories.py tests\test_builtin_tool_handlers.py tests\test_default_tool_catalog.py -q
python -m pytest -q
npm run build
Get-ChildItem -Path tests -Filter *.test.js | ForEach-Object { node $_.FullName }
```

Results:

- Backend compile: passed.
- Focused backend tests: `30 passed`.
- Full backend tests: `201 passed`.
- Frontend production build: passed with existing asset-size warnings.
- Frontend contract tests: passed.

One test isolation issue was fixed in
`backend/tests/test_sandbox_stage0_baseline.py`: it now clears `app.*` modules only
when Flask extension stubs are actually present, avoiding stale SQLAlchemy objects
after pytest collection.

## Docker/Sandbox Smoke

Docker daemon was available. The sandbox image was rebuilt:

```powershell
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

The resulting image was `weagent-sandbox:latest` with image id `de4db641c231`.

A temporary smoke container was started:

```powershell
docker run --rm -d --name weagent-toolset-merge-smoke -p 18082:8080 weagent-sandbox:latest
```

Smoke checks:

- `GET /api/health` returned `status: ok`.
- Provider health reported Claude Code, Codex, and OpenCode as available.
- `POST /api/capabilities/projection` wrote:
  - `/workspace/.weagent/capabilities/index.json`
  - `/workspace/.weagent/skills/skill-1/SKILL.md`
  - `/workspace/.weagent/agents/agent-smoke/capabilities.json`
  - `/workspace/.weagent/agents/agent-smoke/skill-index.json`
  - `/workspace/.weagent/agents/agent-smoke/tool-index.json`
  - `/workspace/.weagent/agents/agent-smoke/permissions.json`
- `POST /api/agents/create` created `agent-smoke` using the desktop `claude`
  provider runtime.
- `GET /api/agents/agent-smoke/read_file` confirmed the Agent can read its
  `.weagent/agents/agent-smoke/skill-index.json` and the projected `SKILL.md`.

The temporary smoke container was stopped and removed.

## Remaining Risks

- Real MCP execution with a public npm MCP package still depends on external
  network and package availability. Unit-level MCP runtime tests passed, but this
  verification used projection smoke rather than a live npm MCP package.
- Provider-configured tools such as web search, image analysis/generation, and
  database query require user-supplied provider configuration before live calls.
- Existing SQLAlchemy deprecation warnings remain noisy but non-blocking.
