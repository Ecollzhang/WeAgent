# Phase 2: Conversation Context System - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning
**Source:** User clarification during adapter phase follow-up

<domain>
## Phase Boundary

This phase focuses only on WeAgent-owned conversation context continuity.

The target user experience is:

- A user chats with Claude/Codex through the WeAgent frontend.
- The agent reads or reasons about files during one turn.
- The user continues in the same WeAgent conversation.
- The next agent invocation can see relevant prior conversation content and recorded file context.

This is not a full native Claude Code or Codex runtime parity phase. Native provider session resume, interactive option selection, background jobs, hook UI, MCP status UI, and full tool timeline rendering remain separate follow-up work unless a small part is required to preserve text/file context.
</domain>

<decisions>
## Implementation Decisions

### Context Ownership

- WeAgent must own the durable conversation context rather than relying only on Claude/Codex native process sessions.
- Context continuity is scoped by WeAgent `conversation_id`.
- The first implementation should work even when Codex uses `--ephemeral`.
- Provider-native resume can be added later as an optimization, not as the core context mechanism.

### Context Contents

- The context builder must include recent user and agent messages from the same conversation.
- The context builder must include a compact summary of prior relevant file/tool/artifact context when available.
- File context should prioritize file paths and short descriptions over full file contents.
- Full file contents should not be blindly replayed every turn; the agent can re-read files from the workspace if needed.
- Recorded context must distinguish:
  - user/agent transcript
  - files read or touched
  - artifacts created
  - prior final agent response
  - provider status or recoverable warnings

### Adapter Boundary

- `adapter.stream(AgentRequest)` remains the provider adapter entry point.
- Provider adapters should receive a ready-to-send prompt.
- Prompt assembly should happen before calling the adapter, preferably in orchestrator/context service code.
- Claude/Codex adapter internals should not query the database directly.

### Testing Direction

- Tests must prove that a second user message in the same conversation receives prior conversation context.
- Tests must prove recorded file context can be injected into the next agent prompt.
- Tests should use fake adapters and repositories where possible; real Claude/Codex CLI calls are smoke tests, not unit tests.
</decisions>

<canonical_refs>
## Canonical References

Downstream agents MUST read these before planning or implementing.

### Orchestration and Message Flow

- `.planning/ROADMAP.md` - Phase 2 scope and requirement IDs.
- `.planning/REQUIREMENTS.md` - REQ-09 through REQ-15.
- `backend/app/services/orchestrator_service.py` - current adapter request construction point.
- `backend/app/services/message_service.py` - user message persistence and orchestrator trigger path.
- `backend/app/repositories/message_repo.py` - message retrieval patterns.
- `backend/app/models/message.py` - persisted message fields.

### Adapter Contract

- `backend/app/adapters/types.py` - `AgentRequest` already has `conversation_history`.
- `backend/app/adapters/claude_adapter.py` - current Claude prompt handoff.
- `backend/app/adapters/codex_adapter.py` - current Codex prompt handoff and `WEAGENT_CODEX_HOME` behavior.
- `backend/app/adapters/normalizers.py` - normalized events, including `message.completed`, `artifact.created`, `agent.status`, and `agent.failed`.
- `backend/tests/test_orchestrator_adapter_stream.py` - existing orchestrator stream tests.
- `backend/tests/test_cli_streaming_adapters.py` - adapter contract tests.

### Protocol Docs

- `docs/tech/modules/C_data_protocol.md` - event/message protocol.
- `docs/tech/modules/D_orchestrator.md` - orchestration boundary.
- `docs/tech/modules/E_agent_adapter.md` - adapter boundary and current capability notes.
- `docs/report/agent-adapter-frontend-test-and-gsd-report.md` - current frontend/adapter verification and Codex runtime notes.
</canonical_refs>

<specifics>
## Specific Ideas

- Add a `ConversationContextService` or similarly named module under `backend/app/services/`.
- Add a compact data type such as `ConversationContext` with:
  - `transcript`
  - `file_context`
  - `artifact_context`
  - `summary`
  - `limits`
- Store durable context in a minimal backend-owned location. Acceptable first options:
  - new database model/table for context entries
  - JSON metadata on existing conversation/config if already available
  - context summary derived on demand from messages/artifacts if no schema change is needed
- Add a prompt builder that formats context as a clear system/context block before the current user message.
- Keep token limits explicit and conservative.
- If normalized provider events do not expose file reads yet, capture artifacts now and design file-read capture as a narrow extension point.
</specifics>

<deferred>
## Deferred Ideas

- Claude native session resume.
- Codex native thread/session resume.
- Interactive provider choices and continuation protocol.
- Background sub-agent lifecycle UI.
- Complete MCP/hook/plan-mode runtime event surface.
- Rich frontend timeline for every tool and file event.
</deferred>

---

*Phase: 02-conversation-context-system*
*Context gathered: 2026-05-25*
