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
| R-016 | External repo/npx/upload imports use preview-before-confirm instead of direct persistence. | `003-external-toolset-import-SPEC.md` |
| R-017 | Executable npx imports run only inside a Docker import sandbox. | `003-external-toolset-import-SPEC.md` |
| R-018 | npx import inputs are parsed through an allowlist and reject shell injection forms. | `003-external-toolset-import-SPEC.md` |
| R-019 | Skill versions can persist bundle assets such as scripts, references, templates, and manifests. | `003-external-toolset-import-SPEC.md` |
| R-020 | User-uploaded Skill bundles support `.md` and `.zip` with one or more `SKILL.md` files. | `003-external-toolset-import-SPEC.md` |
| R-021 | Imports and draft publications produce security audits with risk level and inferred permissions. | `003-external-toolset-import-SPEC.md` |
| R-022 | High-risk imports or drafts can be force-published only through expert override with audit logging. | `003-external-toolset-import-SPEC.md` |
| R-023 | Agent edits to Skill bundle files sync back as drafts and require review before DB publication. | `003-external-toolset-import-SPEC.md` |
| R-024 | Runtime projection writes complete Skill bundles under `.weagent/skills/<runtime_id>/...`. | `003-external-toolset-import-SPEC.md` |
| R-025 | Toolset UI exposes file-tree and security-audit views for capabilities. | `003-external-toolset-import-SPEC.md` |
| R-026 | Agent create and edit flows support selecting default capabilities from the toolset library. | `003-external-toolset-import-SPEC.md` |
| R-027 | API keeps pinned/follow_latest version policies while v1 UI defaults to pinned plus manual upgrade. | `003-external-toolset-import-SPEC.md` |
| R-028 | Repo imports statically scan supported Skill layouts without executing repo scripts. | `003-external-toolset-import-SPEC.md` |
| R-029 | Import, audit, and expert override records are traceable from capability versions. | `003-external-toolset-import-SPEC.md` |
| R-030 | Detection engine covers syntax checks, lexical scanning, illegal library/API scanning, illegal operation scanning, and risk-to-permission mapping. | `003-external-toolset-import-SPEC.md` |
| R-031 | Built-in Tools use a versioned `weagent.tool/v1` manifest plus `TOOL.md` Agent-facing documentation. | `005-builtin-tool-runtime-SPEC.md` |
| R-032 | Built-in Tools are read-only for users and cannot be edited, deleted, or permission-mutated by user actions. | `005-builtin-tool-runtime-SPEC.md` |
| R-033 | Runtime projection writes `.weagent/tools/<runtime_id>/TOOL.md`, `manifest.json`, and per-Agent `tool-index.json`. | `005-builtin-tool-runtime-SPEC.md` |
| R-034 | Agent Tool execution requires a bound capability and sufficient granted permissions. | `005-builtin-tool-runtime-SPEC.md` |
| R-035 | Every implemented Tool call writes JSONL and DB-syncable call records with status, summaries, permissions, and timing. | `005-builtin-tool-runtime-SPEC.md` |
| R-036 | Every functional built-in category has at least one real implemented Tool; custom remains a user-owned container category. | `005-builtin-tool-runtime-SPEC.md` |
| R-037 | Deferred or requires-config Tools are visibly marked and cannot be invoked as implemented runtime Tools. | `005-builtin-tool-runtime-SPEC.md` |
| R-038 | High-risk Tool areas are split into safer sub-tools, with Git write operations, arbitrary shell, and DB writes deferred. | `005-builtin-tool-runtime-SPEC.md` |
| R-039 | User-created Tools may edit `TOOL.md` and manifest drafts, but script execution requires audit, permission confirmation, and publication. | `005-builtin-tool-runtime-SPEC.md` |
| R-040 | Built-in Tool runtime behavior is verifiable through Docker UAT across representative categories. | `005-builtin-tool-runtime-SPEC.md` |

## Non-Requirements

- No remote marketplace browsing in v1.
- No arbitrary host-side execution of npx, MCP, Plugin, or Tool code.
- No full Plugin runtime, hooks, custom UI extension runtime, or arbitrary Plugin command execution.
- No automatic `.claude/*`, `.codex/*`, or `.mcp.json` generation in v1.
- No automatic upgrade of existing Agent bindings to latest capability versions.
- No arbitrary npx or shell command execution during external toolset import.
- No persistence of `node_modules`, package caches, or binary executable files as Skill assets.
- No saved named toolset/profile bundles in the external import phase.
- No direct user edits to system built-in Tool definitions, handlers, or permission declarations.
- No arbitrary user script Tool runtime until script sandboxing, audit, and confirmation are completed.
- No built-in AI code generation, AI image understanding, generic web search, Git writes, DB writes, or production DB access in the built-in Tool runtime phase.
