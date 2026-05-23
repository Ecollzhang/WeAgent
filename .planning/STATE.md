# Planning State

**Project:** WeAgent
**Current branch:** agent_adapter
**Status:** Planning
**Last activity:** 2026-05-23

## Accumulated Context

### Pending Todos

- Agent adapter streaming factory: define and implement a factory-created streaming adapter layer for Codex and Claude Code.

## Decisions

- Use CLI streaming for the MVP because `codex-cli 0.128.0` and `Claude Code 2.1.148` are installed locally.
- Keep SDK integrations as a follow-up path to avoid blocking the first working adapter contract.
- Use normalized `AgentEvent` dictionaries as the only output surface consumed by orchestrator/SSE.
- Keep mock adapter behavior available for demo stability.

