# Phase 1 Plan: Agent Adapter Streaming Factory

## Objective

Build a factory-created streaming adapter layer for Codex and Claude Code while preserving a stable mock fallback.

## Architecture

The backend introduces request/event helpers, provider-specific adapters, normalizers, and an adapter factory. The orchestrator consumes normalized events, broadcasts deltas, and persists the final agent message after completion.

## Tasks

### Task 1: Define Shared Adapter Contract

- [ ] Create `backend/app/adapters/types.py` with `AgentRequest`, `AdapterHealth`, `AgentEvent`, `utc_now_iso()`, and `make_event()`.
- [ ] Update `backend/app/adapters/base_adapter.py` so `stream(request)` is the abstract method.
- [ ] Keep `send_prompt(prompt, context=None)` as a compatibility aggregator over `message.delta` and `message.completed`.
- [ ] Verify with `python -m py_compile backend/app/adapters/types.py backend/app/adapters/base_adapter.py`.

### Task 2: Add Factory Registry

- [ ] Create `backend/app/adapters/factory.py` with `AgentAdapterFactory.register()`, `create()`, and `providers()`.
- [ ] Update `backend/app/adapters/__init__.py` to register `claude`, `codex`, and `opencode`.
- [ ] Keep `get_adapter(adapter_name)` available for migration compatibility.
- [ ] Add focused factory tests under `backend/tests/test_adapter_factory.py`.

### Task 3: Add Provider Normalizers

- [ ] Create `backend/app/adapters/normalizers.py`.
- [ ] Implement `normalize_codex_event(raw, request)` returning zero or more normalized events.
- [ ] Implement `normalize_claude_event(raw, request)` returning zero or more normalized events.
- [ ] Cover `message.delta`, `message.completed`, `tool.started`, `tool.completed`, `artifact.created`, and `agent.failed`.
- [ ] Add tests under `backend/tests/test_adapter_normalizers.py` with representative fake raw events.

### Task 4: Implement CLI Streaming Adapters

- [ ] Update `backend/app/adapters/codex_adapter.py` to run `codex exec --json --cd <workspace> --sandbox workspace-write --skip-git-repo-check <prompt>`.
- [ ] Update `backend/app/adapters/claude_adapter.py` to run `claude -p --output-format stream-json --include-partial-messages --permission-mode plan <prompt>`.
- [ ] Parse stdout line by line as JSON.
- [ ] Emit `agent.failed` on missing CLI, invalid startup, or non-zero exit.
- [ ] Test adapters by monkeypatching subprocess creation; do not call real Claude or Codex in unit tests.

### Task 5: Integrate Orchestrator Streaming

- [ ] Replace direct adapter class construction in `backend/app/services/orchestrator_service.py` with `AgentAdapterFactory.create(agent.adapter_name)`.
- [ ] Build an `AgentRequest` from conversation, user message, agent profile, and workspace metadata.
- [ ] Broadcast normalized events as they arrive through the existing conversation stream path.
- [ ] Accumulate deltas and persist one final agent message on `message.completed`.
- [ ] Preserve logging and visible `agent.failed` events for adapter exceptions.

### Task 6: Verify And Document

- [ ] Run `python -m compileall backend/app/adapters backend/app/services`.
- [ ] Run `python -m pytest backend/tests -q` if pytest is available.
- [ ] Update `docs/tech/modules/E_agent_adapter.md` if implementation details diverge from the current design document.
- [ ] Commit with `git add .planning backend/app/adapters backend/app/services backend/tests docs/tech/modules/E_agent_adapter.md` and `git commit -m "feat: add streaming agent adapter factory"`.

## Acceptance Criteria

- Orchestrator can invoke Codex, Claude, or Mock-like adapters through one factory.
- Adapter streams emit normalized `AgentEvent` dictionaries.
- Streaming deltas can be broadcast before final message persistence.
- Failures surface as `agent.failed` events.
- Tests do not require real Claude or Codex network/API calls.

