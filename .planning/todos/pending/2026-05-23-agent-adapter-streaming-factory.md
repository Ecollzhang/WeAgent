---
created: 2026-05-23T06:28:43.851Z
title: Agent adapter streaming factory
area: backend
files:
  - backend/app/adapters/base_adapter.py
  - backend/app/adapters/__init__.py
  - backend/app/adapters/claude_adapter.py
  - backend/app/adapters/codex_adapter.py
  - backend/app/services/orchestrator_service.py
  - backend/app/services/message_service.py
  - docs/tech/modules/E_agent_adapter.md
  - docs/tech/appendices/event_protocol_reference.md
---

## Problem

The current adapter layer exposes `send_prompt(prompt, context=None) -> str`, so Claude, Codex, and OpenCode responses are treated as one completed message. This blocks incremental UI updates, makes tool events invisible, and forces the orchestrator to know too much about each provider's behavior.

## Solution

Introduce a factory-created streaming adapter contract:

- `AgentAdapterFactory.create(provider, config)` returns a provider-specific adapter.
- Each adapter exposes `stream(request) -> Iterator[AgentEvent]`.
- Codex and Claude Code adapters read CLI JSONL/stream-json output and pass raw events through provider-specific normalizers.
- The orchestrator consumes only normalized events, broadcasts `message.delta` as they arrive, and persists final text after `message.completed`.
- Mock remains the stable fallback adapter for demos and local development.

