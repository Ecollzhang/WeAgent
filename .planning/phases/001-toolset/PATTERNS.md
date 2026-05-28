# Phase 001: Toolset Capabilities v1 - Code Patterns

**Created:** 2026-05-28

## Backend API Pattern

Follow the current Flask pattern:

```text
controller -> service -> repository/model
```

Controllers should stay thin:

- parse JWT identity.
- validate request payload.
- call service.
- return `success_response` or `error_response`.

Services own business rules:

- permission validation.
- version pinning.
- import parsing.
- authorization snapshots.
- projection payload construction.

Repositories own query composition and persistence helpers.

## Model Pattern

New capability models should extend the existing `BaseModel`. Avoid SQLAlchemy reserved attribute names. Use `meta` instead of `metadata`.

Use JSON columns consistently for:

- permission arrays and authorization snapshots.
- manifests.
- input/output summaries where structured data is useful.
- version-specific data as `meta`.

## Frontend Pattern

Follow existing Vue 2 + Element UI pages:

- API wrapper in `frontend/src/api/capabilities.js`.
- Page in `frontend/src/views/CapabilityLibrary.vue`.
- Reuse Element UI forms, dialogs, tabs, tables, tags, and selects.
- Keep Agent edit changes inside `AgentEditForm` where Agent creation/editing already lives.

## Sandbox Pattern

Host-side changes belong in `backend/app/sandbox/host/manager.py` and supporting services. Container-side runtime files belong in `backend/app/sandbox/container`.

Projection should happen before Agent creation:

```text
create container
wait for orchestrator ready
POST projection payload to container
create runtime Agents
run tasks
sync call records and Skill drafts
```

## Runtime Instruction Pattern

Agent prompts should receive a compact bootstrap instead of full Skill contents:

```text
Your WeAgent capability index is available at:
- /workspace/.weagent/agents/<agent_id>/skill-index.json
- /workspace/.weagent/agents/<agent_id>/capabilities.json
- /workspace/.weagent/agents/<agent_id>/permissions.json

Read a Skill Markdown file only when it is relevant to the task.
Do not assume access to capabilities not listed in your Agent view.
```

## Commit Pattern

Use small commits per checkpoint:

- planning artifacts.
- data model foundation.
- service and API.
- frontend library.
- projection.
- Tool/MCP records.
- Plugin import.
- Skill drafts.
- verification.

