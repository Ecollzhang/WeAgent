# Phase 2 Plan 02-01 Summary: Conversation Context System

**Completed:** 2026-05-25
**Owner:** why
**Branch:** agent_adapter

## What Changed

- Added `ConversationContextService` for WeAgent-owned conversation context.
- Added bounded transcript loading with a default window of 20 messages.
- Added prompt formatting with:
  - `## Agent Instructions`
  - `## Conversation Context`
  - `## File and Artifact Context`
  - `## Current User Message`
- Updated orchestrator request construction so Claude/Codex/Mock adapters receive context-aware prompts.
- Preserved the raw user message in `AgentRequest.metadata["raw_user_message"]`.
- Added artifact/file context recording for normalized `artifact.created` events with `storagePath`.
- Updated docs to distinguish WeAgent-owned context from provider-native Claude/Codex session resume.

## Verification

- `python -m unittest discover tests`
- `python -m compileall app\adapters app\services app\controllers app\schemas`

## Boundary

This phase does not implement native Claude/Codex session resume, interactive choices, background task lifecycle, or full hook/MCP/plan-mode event UI. It focuses on context continuity inside the same WeAgent conversation.
