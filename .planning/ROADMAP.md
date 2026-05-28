# Toolset Capability Roadmap

**Created:** 2026-05-28
**Active branch:** `feature/toolset`

## Milestone 1: Toolset Capabilities v1

### Phase 001: Toolset Capabilities v1

**Directory:** `.planning/phases/001-toolset`
**Status:** Planned
**Goal:** Add DB-backed capability library, Agent default bindings, `.weagent/*` sandbox projection, Skill lifecycle, minimal Tool/MCP call recording, and Plugin manifest import records.

**Canonical references:**

- `.planning/phases/001-toolset/001-SPEC.md`
- `.planning/phases/001-toolset/001-CONTEXT.md`
- `.planning/phases/001-toolset/001-RESEARCH.md`
- `.planning/phases/001-toolset/PATTERNS.md`
- `.planning/phases/001-toolset/001-CHECKPOINTS.md`
- `.planning/phases/001-toolset/001-PLAN.md`

**Checkpoints:**

1. Data model and service foundation.
2. Capability API and built-in seed migration.
3. Frontend Capability Library and Agent binding UI.
4. Host-side injection plan and `.weagent/*` container projection.
5. Built-in Tool call audit.
6. Minimal npx MCP runtime.
7. Plugin manifest import.
8. Skill draft sync.
9. End-to-end verification and regression checks.

## Future Phases

### Phase 002: Claude and Codex Compatibility Mapping

Map `.weagent/*` to Claude/Codex runtime conventions without changing the DB capability contract.

### Phase 003: Sandbox Security Hardening

Harden existing sandbox routes, auth, workspace access, and permission enforcement beyond capability-specific checks.

