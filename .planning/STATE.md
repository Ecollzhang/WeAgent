---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
last_updated: "2026-06-02T00:00:00.000Z"
last_activity: 2026-06-02
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 3
  completed_plans: 2
  percent: 67
---

# Planning State

**Project:** WeAgent
**Current branch:** combine/toolset_v1.1.0
**Status:** Phase 03 planning
**Last activity:** 2026-06-02

## Accumulated Context

### Pending Todos

- Agent adapter streaming factory: define and implement a factory-created streaming adapter layer for Codex and Claude Code.
- Merge `feature/toolset` into the desktop runtime base as Phase 03.

## Decisions

- Use CLI streaming for the MVP because `codex-cli 0.128.0` and `Claude Code 2.1.148` are installed locally.
- Keep SDK integrations as a follow-up path to avoid blocking the first working adapter contract.
- Use normalized `AgentEvent` dictionaries as the only output surface consumed by orchestrator/SSE.
- Keep mock adapter behavior available for demo stability.
- After local Claude/Codex smoke tests pass, route the backend user-message path through orchestrator and adapter factory before frontend streaming UI work.
- Task 5-6 are now complete for normalized message events: backend orchestrator, SSE named events, and frontend temporary streaming message rendering.
- Phase 2 focuses on WeAgent-owned conversation context continuity: transcript, file/artifact context, compact summaries, and provider-neutral prompt assembly.
- Phase 2 is implemented with a 20-message default transcript window and `artifact.created` context recording; native provider session resume remains deferred.
- Phase 3 uses `origin/feature/desktop_app_support_v1.0.6` as the base and treats `origin/feature/toolset` as a module to embed.
- Web frontend toolset management is in scope; desktop client toolset UI is out of scope.
- Desktop sandbox provider runtime, service proxy, and backend port remain authoritative.
- Toolset capability projection, MCP runtime, provider config, and built-in Tool audit are attached to the desktop runtime instead of replacing it.
