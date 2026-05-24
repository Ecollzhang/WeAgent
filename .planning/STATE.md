---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-05-24T00:00:00.000Z"
last_activity: 2026-05-24
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 1
  completed_plans: 0
  percent: 80
---

# Planning State

**Project:** WeAgent
**Current branch:** agent_adapter
**Status:** Executing Phase 01
**Last activity:** 2026-05-24

## Accumulated Context

### Pending Todos

- Agent adapter streaming factory: define and implement a factory-created streaming adapter layer for Codex and Claude Code.

## Decisions

- Use CLI streaming for the MVP because `codex-cli 0.128.0` and `Claude Code 2.1.148` are installed locally.
- Keep SDK integrations as a follow-up path to avoid blocking the first working adapter contract.
- Use normalized `AgentEvent` dictionaries as the only output surface consumed by orchestrator/SSE.
- Keep mock adapter behavior available for demo stability.
- After local Claude/Codex smoke tests pass, route the backend user-message path through orchestrator and adapter factory before frontend streaming UI work.
