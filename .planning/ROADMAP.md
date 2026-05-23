# Roadmap

## Phase 1: Agent Adapter Streaming Factory

**Goal:** Turn the current mock-style adapter layer into a factory-created streaming adapter system for Claude Code and Codex.

**Requirements:** REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06, REQ-07

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
- Adapter factory and registry.
- Codex CLI stream adapter.
- Claude Code CLI stream adapter.
- Mock stream adapter.
- Normalizer tests and orchestration integration tests.
- Runtime notes for CLI and future SDK support.

## Deferred

- Full Claude Agent SDK integration.
- Codex TypeScript SDK bridge.
- Multi-run persistence table for every raw event.
- UI redesign for rich tool timeline.

