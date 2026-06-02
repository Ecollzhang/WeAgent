# Toolset Planning State

**Updated:** 2026-06-01
**Active branch:** `feature/toolset`
**Remote target:** `origin/feature/toolset`
**Current phase:** `001-toolset`
**Status:** 005 built-in Tool runtime SPEC/PLAN drafted

## Completed

- Reviewed current branch baseline.
- Confirmed workspace is session-scoped and Claude Code path exists.
- Confirmed toolset model should contain Skill, Tool, MCP, and Plugin as peer capability types.
- Confirmed DB is canonical source of truth and `.weagent/*` is session runtime projection.
- Confirmed Agent owns default capability bindings; workspace/session manages Agents.
- Confirmed pinned versions are default.
- Confirmed explicit authorization snapshots are required.
- Confirmed npx/MCP execution happens inside sandbox.
- Confirmed v1 writes only `.weagent/*`.
- Created SPEC, PLAN, CONTEXT, RESEARCH, PATTERNS, and CHECKPOINTS artifacts for phase 001.
- Completed Checkpoint 1 data model foundation.
- Completed Checkpoint 2 service/API foundation.
- Completed Checkpoint 3 frontend Capability Library and Agent binding UI.
- Completed Checkpoint 4 runtime projection and `.weagent/*` injection path.
- Completed Checkpoint 5 built-in Tool call audit through capability bindings.
- Completed Checkpoint 6 minimal MCP npx runtime inside the sandbox.
- Completed Checkpoint 7 Plugin manifest import and install-record visibility.
- Completed Checkpoint 8 Skill draft sync from workspace runtime changes to DB drafts.
- Completed Checkpoint 9 end-to-end regression and preservation checks.
- Added 003 External Toolset Import and Audit SPEC/PLAN.
- Confirmed ability-library mode comes first; named toolset/profile bundles are deferred.
- Confirmed Agent create and edit flows both need default capability selection.
- Confirmed npx executable imports require Docker import sandbox with basic in-container safety checks.
- Confirmed uploaded script changes may be drafted by Agent but require user review, re-audit, and confirmation before DB publication.
- Confirmed expert mode permits high-risk publication only with second confirmation and audit logging.
- Clarified detection engine requirements for syntax checks, lexical scanning, illegal library/API scanning, illegal operation scanning, and risk-to-permission mapping.
- Confirmed built-in Tools are mostly display shells today, while sandbox runtime only has a few basic callables.
- Confirmed built-in Tools must be read-only for users; user-created Tools may be editable after audit and publication.
- Confirmed Tool Markdown is necessary for Agent instructions, but manifest and handler remain the execution contract.
- Confirmed Tool disclosure should be progressive: Agent sees tool index first, then reads `TOOL.md` when needed.
- Added 005 Built-in Tool Runtime and Markdown Contract SPEC/PLAN.

## Current Branch Notes

- Local branch has been moved to `feature/toolset`.
- Upstream is `origin/feature/toolset`.
- Existing untracked `.claude/logs/` and `.planning/STATE.md.lock` should not be included in toolset commits.

## Next Action

Review `005-builtin-tool-runtime-SPEC.md` and `005-builtin-tool-runtime-PLAN.md`, then begin Checkpoint A if the scope is approved.
