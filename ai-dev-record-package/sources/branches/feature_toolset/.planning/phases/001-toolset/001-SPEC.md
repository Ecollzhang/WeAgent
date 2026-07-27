# Phase 001: Toolset Capabilities v1 - Specification

**Created:** 2026-05-28
**Branch:** `feature/toolset`
**Source workflow:** `$gsd-spec-phase`
**Ambiguity score:** 0.11 (gate: <= 0.20)
**Requirements:** 10 locked

## Goal

WeAgent changes from an Agent form with inline `skill` text and `tool_ids` into a capability system where Skill, Tool, MCP, and Plugin are first-class DB-backed assets that can be bound to Agents, projected into each session sandbox under `.weagent/*`, authorized explicitly, and audited through real runtime records.

## Background

The current branch is based on the tested multi-agent/artifact work. The repository already has Agent CRUD, a Tools page, sandbox sessions, multi-agent progress, message display, and artifact display.

Current implementation points:

- `backend/app/models/agent.py` stores `skill` as inline text and `tool_ids` as JSON on the Agent row.
- `backend/app/models/agent_tool.py` and `backend/app/services/tool_service.py` support built-in and custom tools as a flat tool list.
- `frontend/src/components/AgentEditForm/index.vue` lets users edit an Agent, write a Skill text block, and select tools.
- `frontend/src/views/Tools.vue` manages tools, but does not represent Skill, MCP, or Plugin as peer capability types.
- `backend/app/sandbox/host/manager.py` creates one Docker container per conversation/session with `/workspace` inside the container and no host volume mount.
- `backend/app/sandbox/container/orchestrator.py` manages container-side Agents, built-in tools, session files, and ClaudeRuntime execution.
- No DB-backed Skill Library, capability versioning, Agent capability binding, permission snapshot, `.weagent/*` projection, MCP npx manifest import, Plugin manifest import, or capability call audit exists today.

## Requirements

1. **Parallel capability model**: The backend must model Skill, Tool, MCP, and Plugin as peer capability types.
   - Current: Skill is inline Agent text, Tool is a separate `AgentTool`, and MCP/Plugin have no first-class persistence.
   - Target: A DB-backed capability library stores definitions, versions, source metadata, permission declarations, and type-specific metadata for `skill`, `tool`, `mcp`, and `plugin`.
   - Acceptance: A verifier can create or seed one record for each type and retrieve them through a unified capability list API without nesting MCP/Plugin under Skill.

2. **Agent-level default bindings**: Capabilities must be bound to Agents as default configuration, not selected ad hoc per new conversation.
   - Current: Agent stores `tool_ids` and `skill` directly.
   - Target: Agent creation/editing can bind capability versions with explicit enabled state and granted permissions; the Agent stores default bindings in DB.
   - Acceptance: Creating an Agent with two capabilities persists `agent_capability_bindings`; starting a new session with that Agent uses those bindings automatically.

3. **Pinned version behavior**: Agent bindings must default to fixed capability versions.
   - Current: Existing `skill` and `tool_ids` have no version behavior.
   - Target: Each Agent binding references a `capability_version_id`; `version_policy` supports `pinned` in v1 and may reserve `follow_latest` without exposing automatic upgrades.
   - Acceptance: Updating a Skill creates a new version without changing existing Agent bindings; the Agent detail API can report that an upgrade is available.

4. **Explicit permission authorization**: Capabilities must declare permissions and Agent bindings must store authorization snapshots.
   - Current: Sandbox routes and Agent tools do not express capability-level permissions.
   - Target: Capability versions declare permissions from `read_workspace`, `write_workspace`, `run_command`, `network`, `use_secret`, `modify_skill`, and `start_service`; Agent bindings store granted permissions and an authorization snapshot.
   - Acceptance: Binding a capability requiring `run_command` fails unless the request grants `run_command`; a future capability version with expanded permissions does not silently expand existing bindings.

5. **DB source of truth with session projection**: Capability definitions must persist in DB and project into the sandbox only at session runtime.
   - Current: Session containers hold transient workspace files, while Skill/Tool data is stored in Agent/Tool rows.
   - Target: DB is the canonical source of truth; each session gets a transient `.weagent/*` runtime projection in `/workspace`.
   - Acceptance: Destroying a session removes `.weagent/*` with the container, while the capability library and Agent bindings remain available for the next session.

6. **`.weagent/*` runtime contract**: v1 must generate only WeAgent runtime files, not Claude/Codex native compatibility directories.
   - Current: There is no `.weagent/*` projection; ClaudeRuntime uses its own agent workspace behavior.
   - Target: The sandbox writes `/workspace/.weagent/capabilities/index.json`, `/workspace/.weagent/skills/<skill_id>/SKILL.md`, and per-Agent view files under `/workspace/.weagent/agents/<agent_id>/`; Agent runtime instructions include a compact bootstrap pointing to the Agent's `.weagent` view files.
   - Acceptance: A session containing an Agent with one Skill produces the shared Skill file, the Agent-specific `capabilities.json`, `skill-index.json`, and `permissions.json`, and a runtime bootstrap that references those files; no `.claude/skills`, `.codex/skills`, or `.mcp.json` files are generated in v1.

7. **Skill lifecycle and Agent-written drafts**: Skills must be editable in platform UI and modifiable by Agents in the session runtime without directly overwriting the user library.
   - Current: Skill is a textarea on Agent and is not a reusable library asset.
   - Target: Users can create/edit/import Markdown Skills in the capability library; Agents can modify the session runtime copy; platform sync stores Agent changes as `skill_revision_drafts`.
   - Acceptance: Editing a projected Skill in `.weagent/skills/<skill_id>/SKILL.md` creates a DB draft tied to `source_skill_id`, `source_version_id`, `session_id`, and `agent_id`; publishing the draft creates a new Skill version, while saving as fork creates a new Skill.

8. **MCP npx manifest path**: MCP v1 must require manifest import before binding or execution.
   - Current: There is no MCP model or runtime.
   - Target: Users import MCP definitions from a WeAgent-owned npx manifest schema; WeAgent parses declared server command, tools, and permissions before allowing Agent binding.
   - Acceptance: A manifest-backed MCP can be installed, started inside the sandbox via npx, list at least one tool, perform one real minimal call, and write a call record.

9. **Tool and Plugin minimum scope**: Tool and Plugin v1 must be real but deliberately narrow.
   - Current: Built-in tools exist as DB rows and container-side Python callables, but call audit is not tied to Agent capability bindings.
   - Target: Tool supports at least one built-in callable with `capability_call_records`; Plugin supports manifest import and installation records only, with no arbitrary Plugin execution.
   - Acceptance: A built-in Tool call records start/completion metadata; a Plugin manifest import creates a Plugin capability and install record but cannot execute plugin code in v1.

10. **Platform display and configuration**: The frontend must show and configure the capability library and Agent default toolset.
    - Current: Users manage Agents and Tools on separate pages; Skill is inline text.
    - Target: The platform exposes a Capability Library view and Agent create/edit flow where users can inspect, create, import, bind, authorize, and view version status for capabilities.
    - Acceptance: A user can create a Skill Markdown asset, import one Markdown Skill, import one npx manifest, bind capabilities when creating an Agent, and see pinned version plus upgrade availability.

## Boundaries

**In scope:**

- Backend data model for `Capability`, `CapabilityVersion`, `AgentCapabilityBinding`, `CapabilityCallRecord`, and `SkillRevisionDraft`.
- Migration or initialization updates needed for MySQL-compatible persistence.
- Backend APIs for listing, creating, importing, versioning, binding, authorizing, and retrieving capability records.
- Frontend capability library UI and Agent create/edit integration.
- Runtime projection into `/workspace/.weagent/*` for session sandbox containers.
- Agent-specific capability view files under `/workspace/.weagent/agents/<agent_id>/`.
- Skill Markdown lifecycle, Markdown text/file import, Agent-written draft sync, publish-as-new-version, and save-as-fork.
- Built-in capability seeding for platform capabilities.
- One minimal platform built-in Tool call record.
- One minimal npx MCP manifest import, sandbox start, tool list, call, and audit record.
- Plugin manifest import and install record only.
- Tests for core model/service/projection/authorization behavior.

**Out of scope:**

- Resolving unrelated merge conflicts from other branches.
- Installing Docker on the user's machine as part of design/spec work.
- Remote marketplace browsing, GitHub marketplace import, zip package install, or arbitrary local path package import.
- Host-backend execution of npx/MCP/Plugin code.
- Full Plugin runtime execution, hooks, custom UI extension runtime, or arbitrary plugin command execution.
- Automatic generation of `.claude/*`, `.codex/*`, or `.mcp.json` compatibility directories.
- Per-message capability installation.
- Automatic upgrade of existing Agent bindings to latest capability versions.
- Full security hardening of existing unauthenticated sandbox routes, except where capability APIs and runtime records require auth and permission checks.

## Constraints

- DB is the canonical source of truth for Agent definitions, Skill content, capability versions, bindings, permissions, imports, and drafts.
- `/workspace/.weagent/*` is a transient session runtime projection and must not be treated as long-term storage.
- The workspace in current architecture is session-scoped; Skill/Plugin/MCP/Tool library content persists in DB for reuse across future sessions.
- Workspace root owns the shared `.weagent` projection; each Agent only receives its own view under `.weagent/agents/<agent_id>/`.
- Skill content is loaded by lightweight index and path, not injected wholesale into every prompt by default.
- npx/MCP execution happens inside the sandbox container, not on the host backend.
- Capability binding authorization belongs to Agent; workspace/session manages Agents and may enforce a policy ceiling in a future phase.
- v1 supports `pinned` version policy by default; `follow_latest` may exist as a reserved model value but must not silently change runtime behavior.
- The implementation must preserve existing multi-agent messages, progress display, and artifact display behavior.
- Existing legacy `Agent.skill` and `Agent.tool_ids` behavior may remain during migration for compatibility, but new feature work must use capability bindings.

## Acceptance Criteria

- [ ] The backend exposes a unified capability list that contains Skill, Tool, MCP, and Plugin records.
- [ ] A user can create and edit a Skill Markdown capability in DB.
- [ ] A user can import a Skill from Markdown text or Markdown file content.
- [ ] A user can import an npx manifest and produce MCP/Plugin/Skill capability definitions from it.
- [ ] A user can create an Agent and bind pinned capability versions with explicit granted permissions.
- [ ] Existing Agent bindings do not change when a newer Skill version is published.
- [ ] Starting a session with an Agent writes `.weagent/*` runtime files under `/workspace`.
- [ ] The session projection includes shared capability files and per-Agent view files.
- [ ] Agent modification of a runtime Skill creates a DB draft revision without publishing automatically.
- [ ] User confirmation can publish a draft as a new Skill version or save it as a fork.
- [ ] A built-in Tool can be invoked and writes a call record with Agent, session, capability version, permissions, status, input summary, and output summary.
- [ ] An MCP server imported from npx manifest can be started in sandbox, list tools, perform one minimal call, and write a call record.
- [ ] A Plugin manifest can be imported and installed as a record without executing plugin code.
- [ ] No v1 runtime projection creates `.claude/skills`, `.codex/skills`, or `.mcp.json`.
- [ ] Existing multi-agent message display, progress display, and artifact display continue to work after capability projection is added.

## Ambiguity Report

| Dimension | Score | Min | Status | Notes |
|---|---:|---:|---|---|
| Goal Clarity | 0.93 | 0.75 | met | Toolset capability target is specific and maps to DB, UI, sandbox, and audit behavior. |
| Boundary Clarity | 0.90 | 0.70 | met | v1 explicitly includes Skill full lifecycle, minimal Tool/MCP real calls, and Plugin manifest-only scope. |
| Constraint Clarity | 0.86 | 0.65 | met | DB source of truth, session-scoped sandbox, `.weagent/*` only, explicit permissions, and pinned versions are locked. |
| Acceptance Criteria | 0.82 | 0.70 | met | Pass/fail checks cover model, UI, projection, Skill drafts, Tool/MCP calls, and Plugin import. |
| **Ambiguity** | **0.11** | **<= 0.20** | met | Ready for planning. |

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|---|---|---|---|
| 1 | Researcher | Which branch and baseline should toolset work use? | Work starts from `feature/toolset`, based on `origin/feature/multi-agent-and-artifact-v1`. |
| 1 | Researcher | Does current branch already isolate workspace and connect Claude? | Session sandbox and Claude Code CLI path exist, but no capability library or `.weagent` injection exists. |
| 2 | Simplifier | Should Skill be only Markdown rendered into prompt? | No. Skill is a DB-backed Markdown asset with workspace runtime projection. |
| 2 | Simplifier | Is the toolset only Skill? | No. Skill, MCP, Plugin, and Tool are peer capability types. |
| 3 | Boundary Keeper | What is v1 scope across capability types? | Skill full lifecycle; Tool/MCP minimal real call records; Plugin manifest import/install record only. |
| 3 | Boundary Keeper | Where should execution happen? | npx/MCP/Plugin/Tool runtime behavior runs in workspace sandbox, not host backend. |
| 4 | Failure Analyst | What permission policy prevents silent overreach? | Capabilities declare permissions; Agent bindings store explicit authorization snapshots. |
| 4 | Failure Analyst | How should injection compare with Claude/Codex patterns? | Use lightweight index and on-demand reads; do not inject all content into prompt. |
| 5 | Seed Closer | Where are runtime files written? | Only `.weagent/*` in v1; no `.claude/*`, `.codex/*`, or `.mcp.json`. |
| 5 | Seed Closer | What owns binding and default injection? | Agent owns default capability bindings; workspace/session manages Agents and projects runtime files. |
| 6 | Seed Closer | How do versions behave? | Bindings default to pinned capability versions; UI can show upgrade availability. |
| 6 | Seed Closer | How are Agent-written Skill changes persisted? | Session runtime changes become DB draft revisions; user confirms publish-as-new-version or save-as-fork. |
| 6 | Seed Closer | How should MCP npx import work? | Manifest must be imported and parsed before binding or execution. |

---

*Phase: 001-toolset*
*Spec created: 2026-05-28*
*Next step: `$gsd-plan-phase 001` implementation planning.*
