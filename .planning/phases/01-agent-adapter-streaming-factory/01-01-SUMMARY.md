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
    - backend/app/services/orchestrator_service.py
    - backend/app/services/message_service.py
    - backend/app/controllers/message_controller.py
    - backend/app/schemas/agent_schema.py
    - frontend/src/views/Dashboard.vue
    - frontend/src/store/modules/message.js
    - frontend/src/components/AgentEditForm/index.vue
    - frontend/vue.config.js
metrics:
  tests: 19
  frontend_changes: 4
---

# Plan 01 Summary: Adapter And Backend Orchestrator Increment

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
- Integrated backend orchestrator with `AgentAdapterFactory.create(agent.adapter_name)`.
- Routed `message_service.send_message(... sender_type='user')` through orchestrator instead of the mock demo response path.
- Orchestrator now broadcasts normalized adapter events, accumulates deltas, and persists one final agent message on `message.completed`.
- Added `backend/tests/test_orchestrator_adapter_stream.py` to lock the factory-stream-persist behavior.
- Updated the SSE endpoint so normalized adapter events are emitted as named events such as `message.delta`, `message.completed`, and `agent.failed`.
- Added frontend Vuex streaming message mutations and Dashboard EventSource listeners for agent streaming events.
- Allowed `mock` adapter agents in the API schema and agent edit UI so localhost/demo smoke tests can avoid slow real CLI calls.
- Disabled Vue CLI parallel workers in `frontend/vue.config.js` to avoid Windows `thread-loader` spawn EPERM during local builds.

## Deferred

- Rich frontend runtime timeline remains deferred.
- No frontend lockfile changes remain in the worktree.
- Current adapter state intentionally reads only normalized message streams. Claude/Codex runtime status prompts such as MCP errors, plan-mode notices, hook prompts, and other non-message operational events are not yet surfaced in WeAgent.
- Adapter execution location is controlled by `AgentRequest.workspace_path`. If absent, `AGENT_WORKSPACE_ROOT` is used; if that is absent, the adapter falls back to the WeAgent project root. This is the future integration point for the sandbox/workspace layer.

## Verification

- `python -m unittest discover tests` from `backend/`: 19 tests passing.
- `python -m compileall app\adapters app\services app\controllers app\schemas` from `backend/`: passing.
- `npm run build -- --no-clean` from `frontend/`: passing with existing asset-size warnings.
- Localhost smoke:
  - backend `http://127.0.0.1:5000/api/health`: 200
  - frontend `http://127.0.0.1:8080`: 200
  - mock adapter SSE emitted `agent.started`, `message.delta`, `message.completed`, and `done`
  - persisted conversation contained both user message and final agent message

## Current Boundary

- The core orchestrator/SSE/frontend streaming path is now integrated for normalized message events. Runtime status events such as hook prompts, MCP errors, plan mode notices, background tasks, and interactive choices still need a separate event-surface phase.

## Self-Check: PASSED

The current increment provides working Codex and Claude Code adapters behind a factory, routes the backend user-message path through orchestrator, streams normalized message events through SSE, renders temporary streaming agent messages in the frontend, and preserves the old `get_adapter()` and `send_prompt()` compatibility surfaces.
