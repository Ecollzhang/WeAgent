# WeAgent Toolset Capability Project

**Created:** 2026-05-28
**Active branch:** `feature/toolset`
**Remote target:** `origin/feature/toolset`
**Status:** Planning chain ready for implementation

## Objective

Build WeAgent's first real toolset capability layer so users can create, import, display, authorize, bind, inject, and audit Skill, Tool, MCP, and Plugin capabilities.

## Current Baseline

The working branch is based on the tested multi-agent and artifact branch. The existing system already supports Agent management, multi-agent messages, progress display, sandbox sessions, and artifact display. It does not yet have DB-backed reusable Skills, MCP/Plugin capability records, Agent capability bindings, pinned capability versions, `.weagent/*` runtime projection, or capability call audit records.

## Working Agreements

- All planning and implementation work for this milestone happens on `feature/toolset`.
- Pushes for this milestone target `origin/feature/toolset`.
- `.planning/` is the project planning source for this toolset phase.
- Do not push toolset commits to `feature/multi-agent-and-artifact-v1`.
- Keep existing multi-agent, progress, and artifact behavior working throughout implementation.

## Deliverables

- Capability data model for Skill, Tool, MCP, and Plugin as peer types.
- User-level Capability Library stored in DB.
- Agent-level default capability bindings with pinned versions and explicit authorization snapshots.
- Runtime projection into `/workspace/.weagent/*`.
- Skill Markdown lifecycle with Agent-written draft review.
- Minimal real Tool call recording.
- Minimal npx MCP import, start, tool list, call, and recording.
- Plugin manifest import and install records without Plugin execution.

## Phase Index

- `001-toolset`: Toolset Capabilities v1.

