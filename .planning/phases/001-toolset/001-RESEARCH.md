# Phase 001: Toolset Capabilities v1 - Research

**Created:** 2026-05-28

## External Runtime Pattern

Claude Code and Codex-style capability systems generally separate:

- instructions or Skills: lightweight discovery with on-demand file reads.
- Tools: schema-backed callable actions.
- MCP: external protocol servers exposing tools, resources, and prompts.
- Plugins: bundles or distribution units that may provide Skills, Tools, MCP servers, hooks, or manifests.

The design should follow that separation. Installing or binding a capability should not mean injecting every capability body into every prompt.

## Current WeAgent Codebase Pattern

Backend:

- Flask app factory in `backend/app/__init__.py`.
- Controller layer under `backend/app/controllers`.
- Service layer under `backend/app/services`.
- Repository layer under `backend/app/repositories`.
- SQLAlchemy models under `backend/app/models`.
- Existing tables are bootstrapped through `backend/sql/init.sql` plus runtime schema checks in `backend/app/__init__.py`.

Frontend:

- Vue 2.7 with Element UI.
- API wrappers under `frontend/src/api`.
- Major pages under `frontend/src/views`.
- Agent editing component is `frontend/src/components/AgentEditForm/index.vue`.

Sandbox:

- Host-side Docker manager in `backend/app/sandbox/host/manager.py`.
- Container-side orchestrator in `backend/app/sandbox/container/orchestrator.py`.
- Claude runtime in `backend/app/sandbox/container/agent.py`.
- Built-in container tools in `backend/app/sandbox/container/tools/__init__.py`.
- Current session files live under `/workspace/.session`.

## Implementation Implications

- Capability DB and APIs should follow the existing Controller -> Service -> Repository pattern.
- Keep legacy Agent fields during v1 to avoid breaking existing pages and seed data.
- Projection should be built on the host before Agent creation, then materialized inside the container before runtime Agents start.
- Agent runtime instructions must point to `.weagent/agents/<agent_id>/*`; otherwise projection files will exist but be unused.
- Tool and MCP call records should flow from container JSONL to DB through an explicit sync path.

## MCP Manifest Notes

Use a WeAgent-owned manifest schema for v1. Do not depend on a remote marketplace schema. The import source can be npx/package-based, but the parsed representation stored in DB should be stable:

- source package and version.
- capability type.
- declared permissions.
- command and args.
- declared tools and input schema.
- optional env requirements.

## Testing Strategy

- Unit test models and service rules without Docker.
- Unit test projection writer against a temporary workspace path.
- Use fixture manifests for npx/MCP import tests.
- Treat real Docker/npx MCP as a manual or integration smoke path unless CI environment supports Docker.
- Regression test Agent CRUD and existing Tool listing so legacy paths remain usable.

