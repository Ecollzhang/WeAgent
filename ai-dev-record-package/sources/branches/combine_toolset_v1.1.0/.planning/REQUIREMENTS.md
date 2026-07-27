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

## Phase 3: Toolset Desktop Merge

REQ-16: Create `combine/toolset_v1.1.0` from `origin/feature/desktop_app_support_v1.0.6` and merge `origin/feature/toolset` as a module.

REQ-17: Keep Web frontend toolset management in scope while leaving desktop client toolset UI out of scope for this phase.

REQ-18: Preserve desktop sandbox provider runtime, service proxy, backend port, and provider runner architecture as the execution base.

REQ-19: Migrate toolset capability data models, schemas, controllers, services, seed logic, and DB-backed APIs into the desktop base.

REQ-20: Make Agent create/edit support both provider selection and capability bindings without overwriting either side.

REQ-21: Inject DB-backed capability runtime projection into sandbox as canonical `/workspace/.weagent/*` files.

REQ-22: Preserve real Skill projection, minimal MCP runtime/list/call records, and built-in Tool call audit records.

REQ-23: Provide Web configuration windows for configurable Tools, including create, test, save, enable, and disable flows.

REQ-24: Hide or exclude deferred/non-configurable built-in Tools from Web display and tab counts.

REQ-25: Keep desktop `.planning` Phase 01/02 as the top-level planning history and add toolset as Phase 03.

REQ-26: Verify the merged branch with focused backend tests, frontend build, and Docker sandbox smoke when Docker is available.

## Phase 4: Desktop Toolset Adapter

REQ-27: Add a desktop Toolset/Capability entry that shows category-first navigation and Skill/MCP/Plugin/Tool capability groups without exposing hidden, deferred, or unbindable empty-shell capabilities.

REQ-28: Make desktop Agent create/edit support capability bindings with pinned versions, including loading, adding, removing, saving, and refreshing bound capabilities.

REQ-29: Keep tool execution inside backend/sandbox/provider runtime; the Electron client may select, save, display, and trigger conversations but must not directly execute npx, MCP servers, Docker, scripts, or built-in Tools.

REQ-30: Prove that desktop-originated Agent sessions generate canonical `.weagent/*` runtime projection files for the selected Agent and its bound capabilities.

REQ-31: Prove that Codex provider runtime reads desktop-bound Skill/Tool/MCP information, including MCP config when applicable, from the generated capability projection.

REQ-32: Prove that Claude provider runtime receives desktop-bound Skill/Tool/MCP capability index or bootstrap context from the generated capability projection.

REQ-33: Produce auditable Phase 04 verification evidence across three layers: projection evidence, provider runtime evidence, and behavior or call-record evidence.

REQ-34: Provide core desktop Toolset management through the same backend APIs as Web, including Skill creation/editing, Markdown/zip/npx/MCP manifest import, security audit preview/detail, user capability deletion, and provider config create/test/save/enable/disable flows, while keeping execution inside backend/sandbox/provider runtime.
