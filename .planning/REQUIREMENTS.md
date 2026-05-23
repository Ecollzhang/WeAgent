# Requirements

## Phase 1: Agent Adapter Streaming Factory

REQ-01: Provide a unified adapter factory that creates adapters by provider name, including `codex`, `claude`, `mock`, and existing-compatible `opencode` registration.

REQ-02: Replace the full-string adapter contract with a streaming adapter contract that yields normalized `AgentEvent` dictionaries while keeping a compatibility helper for callers that still need final text.

REQ-03: Implement normalizers that translate raw Codex CLI JSONL and Claude Code stream-json events into the same event protocol.

REQ-04: Integrate adapter streams into orchestration so agent output can be broadcast incrementally and persisted as one final agent message.

REQ-05: Preserve safe fallback behavior: when real CLI execution is unavailable or fails early, surface `agent.failed` and allow a mock adapter path for demos.

REQ-06: Add focused tests for factory lookup, mock streaming, event normalization, and orchestrator stream aggregation without requiring real Claude or Codex network calls.

REQ-07: Document runtime assumptions, CLI commands, failure modes, and the future SDK upgrade path.

