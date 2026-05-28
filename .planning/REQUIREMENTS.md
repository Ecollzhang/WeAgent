# Toolset Capabilities Requirements

**Created:** 2026-05-28
**Milestone:** Toolset Capabilities v1

## Requirement Index

| ID | Requirement | Source |
|---|---|---|
| R-001 | Skill, Tool, MCP, and Plugin are peer capability types. | `001-SPEC.md` |
| R-002 | Capabilities are stored in DB with versions, source data, and permission declarations. | `001-SPEC.md` |
| R-003 | Agents store default capability bindings, not ad hoc per-conversation selections. | `001-SPEC.md` |
| R-004 | Agent capability bindings default to pinned capability versions. | `001-SPEC.md` |
| R-005 | Capability permissions require explicit authorization snapshots at binding time. | `001-SPEC.md` |
| R-006 | Session sandbox startup projects selected capabilities into `/workspace/.weagent/*`. | `001-SPEC.md` |
| R-007 | v1 writes only `.weagent/*`; Claude/Codex compatibility directories are deferred. | `001-SPEC.md` |
| R-008 | Skill Markdown can be created, edited, imported, projected, changed by Agent, drafted, published, or forked. | `001-SPEC.md` |
| R-009 | MCP import requires a manifest before binding or execution. | `001-SPEC.md` |
| R-010 | npx/MCP execution happens only inside the sandbox container. | `001-SPEC.md` |
| R-011 | At least one built-in Tool call writes a real capability call record. | `001-SPEC.md` |
| R-012 | At least one npx MCP server can start, list tools, perform one minimal call, and record it. | `001-SPEC.md` |
| R-013 | Plugin v1 supports manifest import and install records only. | `001-SPEC.md` |
| R-014 | The platform UI displays and configures the Capability Library and Agent default toolset. | `001-SPEC.md` |
| R-015 | Existing multi-agent messages, progress display, and artifact display do not regress. | `001-SPEC.md` |

## Non-Requirements

- No remote marketplace browsing in v1.
- No arbitrary host-side execution of npx, MCP, Plugin, or Tool code.
- No full Plugin runtime, hooks, custom UI extension runtime, or arbitrary Plugin command execution.
- No automatic `.claude/*`, `.codex/*`, or `.mcp.json` generation in v1.
- No automatic upgrade of existing Agent bindings to latest capability versions.

