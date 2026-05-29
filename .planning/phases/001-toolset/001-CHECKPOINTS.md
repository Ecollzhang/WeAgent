# Phase 001: Toolset Capabilities v1 - Checkpoints

**Created:** 2026-05-28

## Checkpoint 0: Planning Chain

**Exit criteria:**

- `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, and `STATE.md` exist.
- `001-SPEC.md`, `001-CONTEXT.md`, `001-RESEARCH.md`, `PATTERNS.md`, `001-CHECKPOINTS.md`, and `001-PLAN.md` exist.
- Branch and remote target are `feature/toolset`.

## Checkpoint 1: Data Model Foundation

**Status:** Complete

**Exit criteria:**

- Capability models exist and import cleanly.
- DB bootstrap includes capability tables.
- Model tests cover all four capability types, versions, bindings, call records, and Skill drafts.

## Checkpoint 2: Service and API

**Status:** Complete

**Exit criteria:**

- Capability service supports create/list/import/version/bind/upgrade status.
- Permission validation rejects missing required permissions.
- Authenticated API endpoints exist for library, imports, Agent bindings, drafts, and call records.

## Checkpoint 3: Frontend Capability Management

**Status:** Complete

**Exit criteria:**

- Capability Library page shows Skill, Tool, MCP, and Plugin.
- Skill Markdown create/edit/import works through API.
- Agent create/edit supports capability selection, pinned version, and permission grants.

## Checkpoint 4: Runtime Projection

**Status:** Complete

**Exit criteria:**

- Host builds injection plan from Agent bindings.
- Container writes `/workspace/.weagent/*`.
- Agent runtime receives bootstrap instructions pointing to its view files.
- No `.claude/*`, `.codex/*`, or `.mcp.json` compatibility files are generated.

## Checkpoint 5: Built-in Tool Audit

**Status:** Next

**Exit criteria:**

- At least one built-in Tool can be called through the capability binding path.
- The call writes JSONL in `.weagent/runs/<run_id>/calls.jsonl`.
- The call sync path persists a DB `CapabilityCallRecord`.

## Checkpoint 6: Minimal MCP npx Runtime

**Exit criteria:**

- A fixture npx manifest imports as MCP.
- The MCP binding requires `run_command`.
- Sandbox starts the MCP server, lists tools, performs one minimal call, and records it.

## Checkpoint 7: Plugin Manifest Import

**Exit criteria:**

- Plugin manifest import creates a Plugin capability and version.
- Plugin install record is visible.
- No Plugin execution endpoint exists.

## Checkpoint 8: Skill Draft Sync

**Exit criteria:**

- Agent-written Skill changes become DB drafts.
- User can publish a draft as a new version.
- User can save a draft as a fork.
- Existing pinned Agent bindings do not auto-upgrade.

## Checkpoint 9: End-to-End Regression

**Exit criteria:**

- Existing multi-agent message display works.
- Agent progress display works.
- Artifact display works.
- Toolset happy path works from UI through sandbox projection and call record.
