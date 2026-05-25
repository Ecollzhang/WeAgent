# Roadmap

## Phase 1: Agent Adapter Streaming Factory

**Goal:** Turn the current mock-style adapter layer into a factory-created streaming adapter system for Claude Code and Codex.

**Requirements:** REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06, REQ-07, REQ-08

**Canonical references:**

- `docs/tech/modules/E_agent_adapter.md`
- `docs/tech/modules/C_data_protocol.md`
- `docs/tech/appendices/event_protocol_reference.md`
- `backend/app/adapters/base_adapter.py`
- `backend/app/adapters/__init__.py`
- `backend/app/services/orchestrator_service.py`
- `backend/app/services/message_service.py`

**Planned outputs:**

- Adapter request/event data structures.
- Shared workspace policy using `AGENT_WORKSPACE_ROOT` with project-root fallback.
- Adapter factory and registry.
- Codex CLI stream adapter.
- Claude Code CLI stream adapter.
- Mock stream adapter.
- Normalizer tests and orchestration integration tests.
- Minimal frontend SSE event handling for streaming agent responses.
- Runtime notes for CLI and future SDK support.

## Phase 2: Conversation Context System

**Goal:** Give each WeAgent conversation its own durable context so Claude/Codex adapters can continue from prior turns, including recent messages, files the agent interacted with, artifacts, and concise run summaries.

**Requirements:** REQ-09, REQ-10, REQ-11, REQ-12, REQ-13, REQ-14, REQ-15

**Canonical references:**

- `backend/app/services/orchestrator_service.py`
- `backend/app/services/message_service.py`
- `backend/app/adapters/types.py`
- `backend/app/adapters/claude_adapter.py`
- `backend/app/adapters/codex_adapter.py`
- `backend/app/adapters/normalizers.py`
- `backend/app/models/message.py`
- `backend/app/models/artifact.py`
- `docs/tech/modules/C_data_protocol.md`
- `docs/tech/modules/D_orchestrator.md`
- `docs/tech/modules/E_agent_adapter.md`

**Planned outputs:**

- Conversation-scoped context builder that loads recent transcript and compact state.
- Context event capture for files read or touched when provider events expose that data.
- Durable context summary record or metadata path for each conversation.
- Prompt assembly that injects context into Claude/Codex without changing the public adapter contract.
- Tests proving turn 2 can see turn 1 messages and recorded file context.
- Documentation of what context is preserved and what is still provider-dependent.

## Deferred

- Full Claude Agent SDK integration.
- Codex TypeScript SDK bridge.
- Multi-run persistence table for every raw event.
- UI redesign for rich tool timeline.
- Native provider session resume for Claude/Codex.
- Interactive choice continuation protocol.
