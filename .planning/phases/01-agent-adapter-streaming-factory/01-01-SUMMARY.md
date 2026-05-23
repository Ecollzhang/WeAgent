---
phase: 01-agent-adapter-streaming-factory
plan: "01"
subsystem: agent-adapters
tags:
  - adapter
  - streaming
  - factory
key-files:
  created:
    - backend/app/adapters/types.py
    - backend/app/adapters/factory.py
    - backend/app/adapters/mock_adapter.py
    - backend/app/adapters/normalizers.py
    - backend/tests/test_adapter_factory.py
    - backend/tests/test_adapter_normalizers.py
    - backend/tests/test_cli_streaming_adapters.py
    - backend/tests/test_mock_streaming_adapter.py
    - backend/tests/test_support.py
  modified:
    - backend/app/adapters/__init__.py
    - backend/app/adapters/base_adapter.py
    - backend/app/adapters/claude_adapter.py
    - backend/app/adapters/codex_adapter.py
    - backend/app/adapters/opencode_adapter.py
metrics:
  tests: 15
  frontend_changes: 0
---

# Plan 01 Summary: Adapter-Only Increment

## Completed

- Added `AgentRequest`, `AdapterHealth`, normalized event helpers, and shared workspace resolution.
- Switched the adapter contract to `stream(request)` while keeping `send_prompt(prompt, context=None)` as a compatibility aggregator.
- Added `AgentAdapterFactory` with registered `mock`, `claude`, `codex`, and `opencode` providers.
- Added deterministic `MockAdapter` streaming events.
- Implemented Codex and Claude Code CLI streaming adapters with JSONL parsing and `agent.failed` fallback events.
- Added provider normalizers for text deltas, completions, tool events, artifacts, and failures.

## Deferred

- Orchestrator, message service, SSE controller, and frontend streaming UI integration were intentionally deferred after user scope clarification.
- No frontend source or lockfile changes remain in the worktree.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover tests` from `backend/`: 15 tests passing.
- `PYTHONPYCACHEPREFIX=.pycache_verify python -m compileall backend/app/adapters`: passing.

## Deviations

- The original plan included frontend and orchestration integration. Scope was narrowed to an adapter-only increment to avoid changing current interfaces.

## Self-Check: PASSED

The current increment provides working Codex and Claude Code adapters behind a factory while preserving the old `get_adapter()` and `send_prompt()` compatibility surfaces.
