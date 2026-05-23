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
  tests: 17
  frontend_changes: 0
---

# Plan 01 Summary: Adapter-Only Increment

## Completed

- Added `AgentRequest`, `AdapterHealth`, normalized event helpers, and shared workspace resolution.
- Switched the adapter contract to `stream(request)` while keeping `send_prompt(prompt, context=None)` as a compatibility aggregator.
- Added `AgentAdapterFactory` with registered `mock`, `claude`, `codex`, and `opencode` providers.
- Added deterministic `MockAdapter` streaming events.
- Implemented Codex and Claude Code CLI streaming adapters with JSONL parsing and `agent.failed` fallback events.
- Verified real Claude Code streaming; Claude Code 2.1.150 requires `--verbose` with `--output-format stream-json`.
- Verified real Claude Code adapter invocation with `workspace_path=E:\code for project\seedance-competition\agentshub\WeAgent`; this creates a CLI run in that E-drive workspace context but does not persist a WeAgent DB conversation yet.
- Verified real Codex adapter invocation. Codex CLI emits `item.completed` with `item.type=agent_message`; the normalizer maps this to `message.completed`.
- Added provider normalizers for text deltas, completions, tool events, artifacts, and failures.

## Deferred

- Orchestrator, message service, SSE controller, and frontend streaming UI integration were intentionally deferred after user scope clarification.
- No frontend source or lockfile changes remain in the worktree.
- Current adapter state intentionally reads only normalized message streams. Claude/Codex runtime status prompts such as MCP errors, plan-mode notices, hook prompts, and other non-message operational events are not yet surfaced in WeAgent.
- Adapter execution location is controlled by `AgentRequest.workspace_path`. If absent, `AGENT_WORKSPACE_ROOT` is used; if that is absent, the adapter falls back to the WeAgent project root. This is the future integration point for the sandbox/workspace layer.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover tests` from `backend/`: 17 tests passing.
- `PYTHONPYCACHEPREFIX=.pycache_verify python -m compileall backend/app/adapters`: passing.

## Deviations

- The original plan included frontend and orchestration integration. Scope was narrowed to an adapter-only increment to avoid changing current interfaces.

## Self-Check: PASSED

The current increment provides working Codex and Claude Code adapters behind a factory while preserving the old `get_adapter()` and `send_prompt()` compatibility surfaces.
