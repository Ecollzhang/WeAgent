# WeAgent Project Context

**Project:** WeAgent
**Branch:** agent_adapter
**Date:** 2026-05-23

## Purpose

WeAgent is a multi-agent collaboration platform with a Flask backend, Vue frontend, and real-time message delivery. The current adapter layer returns full mock strings through `send_prompt()`. The next architecture step is to introduce a factory-driven adapter gateway that can stream normalized events from Claude Code and Codex.

## Current Architecture Read

- Backend stack: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-SocketIO, SSE-style message stream.
- Frontend stack: Vue 2, Vuex, Element UI, Axios, Socket.IO client utilities.
- Existing adapter files: `backend/app/adapters/base_adapter.py`, `backend/app/adapters/claude_adapter.py`, `backend/app/adapters/codex_adapter.py`, `backend/app/adapters/opencode_adapter.py`, `backend/app/adapters/__init__.py`.
- Existing orchestration entry: `backend/app/services/orchestrator_service.py`.
- Existing stream path: `backend/app/services/message_service.py` and `backend/app/controllers/message_controller.py`.

## Working Constraints

- Keep `.claude/logs/` untouched because it is an existing untracked local artifact.
- Do not implement business-code changes until the GSD plan is reviewed.
- Use CLI-based MVP first because local `codex` and `claude` commands are installed.
- Preserve a mock adapter as the demo and fallback path.

