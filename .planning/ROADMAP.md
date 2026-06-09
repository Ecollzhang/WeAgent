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

## Phase 3: Toolset Desktop Merge

**Goal:** Embed the DB-backed Toolset/Capability module from `feature/toolset` into the desktop runtime base while preserving the desktop sandbox provider architecture.

**Requirements:** REQ-16, REQ-17, REQ-18, REQ-19, REQ-20, REQ-21, REQ-22, REQ-23, REQ-24, REQ-25, REQ-26

**Canonical references:**

- `.planning/phases/03-toolset/03-SPEC.md`
- `.planning/phases/03-toolset/03-PLAN.md`
- `.planning/phases/01-agent-adapter-streaming-factory/01-01-PLAN.md`
- `.planning/phases/02-conversation-context-system/02-01-PLAN.md`
- `backend/app/sandbox/container/providers/factory.py`
- `backend/app/sandbox/container/agent.py`
- `backend/app/sandbox/host/manager.py`
- `frontend/src/components/AgentEditForm/index.vue`
- `frontend/src/views/Tools.vue`

**Planned outputs:**

- Merge branch `combine/toolset_v1.1.0`.
- Capability/Toolset DB models, APIs, seed logic, and Web UI on the desktop base.
- Agent provider selection plus capability binding in one Web form.
- Sandbox `.weagent/*` capability projection integrated with desktop provider runners.
- Minimal MCP runtime and built-in Tool call records preserved.
- Verification report covering tests, build, and sandbox smoke.

## Phase 4: Desktop Toolset Adapter

**Goal:** Give the desktop client a Toolset/Capability management entry and prove that desktop-created Agent sessions really inject bound Skill, Tool, and MCP capabilities into Codex and Claude provider runtimes.

**Requirements:** REQ-27, REQ-28, REQ-29, REQ-30, REQ-31, REQ-32, REQ-33, REQ-34

**Canonical references:**

- `.planning/phases/04-desktop-toolset-adapter/04-SPEC.md`
- `.planning/phases/04-desktop-toolset-adapter/04-PLAN.md`
- `.planning/phases/03-toolset/03-SPEC.md`
- `.planning/phases/03-toolset/03-PLAN.md`
- `clients/desktop/src/views/Agents.vue`
- `clients/desktop/src/router/index.js`
- `clients/desktop/src/services/api.js`
- `backend/app/sandbox/container/providers/codex.py`
- `backend/app/sandbox/container/providers/claude.py`
- `backend/app/sandbox/container/capabilities.py`

**Planned outputs:**

- Desktop Toolset/Capability management entry with category-first navigation and Skill/MCP/Plugin/Tool tabs.
- Desktop workflows for Skill Markdown creation/editing, Markdown/zip/npx/MCP manifest import, security audit preview/detail, capability deletion, and provider config test/save/enable/disable.
- Desktop Agent create/edit support for capability binding with pinned versions.
- Desktop API wrappers for toolset categories, capability list, and agent capability binding/unbinding.
- Runtime smoke proving desktop-originated sessions generate `.weagent/*` projection.
- Codex smoke proving MCP/Skill/Tool capability injection is visible in runtime config/context.
- Claude smoke proving Skill/Tool/MCP capability index is visible in runtime context.
- Verification report containing projection evidence, runtime evidence, and behavior/call evidence.

## Deferred

- Full execution of arbitrary user-defined script Tools.
- Full Claude Agent SDK integration.
- Codex TypeScript SDK bridge.
- Multi-run persistence table for every raw event.
- UI redesign for rich tool timeline.
- Native provider session resume for Claude/Codex.
- Interactive choice continuation protocol.
- Full desktop arbitrary script Tool editor/executor and secret-vault management UI.
