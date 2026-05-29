# Requirements

## Phase 1: Agent Adapter Streaming Factory

REQ-01: Provide a unified adapter factory that creates adapters by provider name, including `codex`, `claude`, `mock`, and existing-compatible `opencode` registration.

REQ-02: Replace the full-string adapter contract with a streaming adapter contract that yields normalized `AgentEvent` dictionaries while keeping a compatibility helper for callers that still need final text.

REQ-03: Implement normalizers that translate raw Codex CLI JSONL and Claude Code stream-json events into the same event protocol.

REQ-04: Integrate adapter streams into orchestration so agent output can be broadcast incrementally and persisted as one final agent message.

REQ-05: Preserve safe fallback behavior: when real CLI execution is unavailable or fails early, surface `agent.failed` and allow a mock adapter path for demos.

REQ-06: Add focused tests for factory lookup, mock streaming, event normalization, and orchestrator stream aggregation without requiring real Claude or Codex network calls.

REQ-07: Document runtime assumptions, CLI commands, failure modes, and the future SDK upgrade path.

REQ-08: Update the primary frontend SSE consumer so `message.delta`, `message.completed`, and `agent.failed` events can render an in-progress agent response instead of waiting for a fully persisted message.

## Phase 2: Conversation Context System

REQ-09: Build a conversation-scoped context builder that can load a bounded transcript from persisted WeAgent messages and format it for adapter execution.

REQ-10: Preserve agent-visible file context across turns by recording normalized file/tool/artifact context when adapter events expose read, write, or artifact paths.

REQ-11: Add a compact conversation context summary that can be stored and reused without sending the entire raw transcript on every turn.

REQ-12: Inject conversation context into Claude/Codex prompts through a provider-neutral prompt assembly layer while keeping `adapter.stream(AgentRequest)` as the public adapter entry point.

REQ-13: Keep context behavior deterministic and testable: turn 2 in the same conversation must receive turn 1 user/agent content and recorded file context.

REQ-14: Avoid claiming native Claude/Codex session parity in this phase; native provider resume, interactive choices, background jobs, and hook UI are deferred unless they are required to preserve text/file context.

REQ-15: Document the exact context contract, retention limits, and provider-dependent gaps so frontend/manual tests can distinguish WeAgent conversation context from provider-native runtime state.
