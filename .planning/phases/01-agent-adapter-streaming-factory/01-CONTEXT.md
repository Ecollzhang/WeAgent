# Phase 1: Agent Adapter Streaming Factory - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning
**Source:** Conversation and repository scan

<domain>
## Phase Boundary

This phase defines the architecture and implementation path for a unified adapter factory that can stream messages from Codex and Claude Code. It covers backend adapter contracts, event normalization, orchestration integration, and tests. It does not redesign the frontend UI or introduce persistent event tables beyond the current message persistence path.
</domain>

<decisions>
## Implementation Decisions

### Adapter Contract

- **D-01:** The canonical adapter method is `stream(request) -> Iterator[AgentEvent]`.
- **D-02:** A compatibility helper may aggregate streamed events into final text for older call sites.
- **D-03:** Adapter output must be normalized before it reaches orchestrator or SSE broadcasting.

### Provider Strategy

- **D-04:** Codex MVP path uses `codex exec --json --cd <workspace> --sandbox workspace-write`.
- **D-05:** Claude MVP path uses `claude -p --output-format stream-json --include-partial-messages`.
- **D-06:** SDK support remains a follow-up enhancement after the CLI path works.
- **D-13:** Workspace resolution uses `AGENT_WORKSPACE_ROOT` when configured, and falls back to the current `WeAgent` project root for the MVP.

### Safety And Fallback

- **D-07:** Mock adapter remains available and testable.
- **D-08:** CLI missing, parse failures, stderr, and non-zero exit codes become `agent.failed` events rather than silent failures.

### Persistence And Broadcast

- **D-09:** The orchestrator accumulates text deltas and persists a final agent message after stream completion.
- **D-10:** Streaming events should be broadcast incrementally through the existing real-time path before final persistence.
- **D-11:** The primary user-facing stream path is the REST message API plus SSE endpoint used by `Dashboard.vue`; Socket.IO should not be the only supported path.
- **D-12:** The frontend must handle `message.delta`, `message.completed`, and `agent.failed` SSE events for an in-progress agent bubble.

### the agent's Discretion

- Exact Python data structure form may be `dataclass` or plain dict if tests prove compatibility with existing Flask JSON serialization.
- Initial artifact detection may be limited to explicit event fields and file-path hints.
</decisions>

<canonical_refs>
## Canonical References

### Adapter and protocol docs

- `docs/tech/modules/E_agent_adapter.md` - target adapter layer concept.
- `docs/tech/modules/C_data_protocol.md` - `AgentEvent` protocol shape.
- `docs/tech/appendices/event_protocol_reference.md` - SSE event examples and frontend consumption expectations.

### Current backend implementation

- `backend/app/adapters/base_adapter.py` - current adapter base contract.
- `backend/app/adapters/__init__.py` - current provider registry.
- `backend/app/adapters/claude_adapter.py` - current Claude mock adapter.
- `backend/app/adapters/codex_adapter.py` - current Codex mock adapter.
- `backend/app/services/orchestrator_service.py` - current adapter invocation path.
- `backend/app/services/message_service.py` - existing SSE queue and mock response logic.
- `backend/app/controllers/message_controller.py` - current SSE formatting behavior.
- `frontend/src/views/Dashboard.vue` - current EventSource consumer.
- `frontend/src/store/modules/message.js` - current message append/update store.
</canonical_refs>

<specifics>
## Specific Ideas

- Keep CLI commands fully wrapped inside adapter files.
- Add normalizer modules so provider-specific raw event shapes do not leak upward.
- Resolve `workspace_path` centrally so Codex and Claude adapters do not each invent their own workspace rules.
- Tests should fake subprocess lines instead of invoking real Claude or Codex.
- The first accepted event set is `agent.started`, `message.delta`, `tool.started`, `tool.completed`, `artifact.created`, `message.completed`, and `agent.failed`.
- Keep frontend changes minimal: add streaming event listeners and store mutations, not a chat redesign.
</specifics>

<deferred>
## Deferred Ideas

- Rich frontend tool timeline.
- Redis pub/sub replacement for in-memory queues.
- SDK-first Claude/Codex integrations.
- Persistent raw event audit tables.
</deferred>
