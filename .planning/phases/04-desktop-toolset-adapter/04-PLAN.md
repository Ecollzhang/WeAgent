---
phase: 04-desktop-toolset-adapter
plan: "04"
type: feature
wave: 1
depends_on:
  - 03-toolset
files_expected:
  - .planning/ROADMAP.md
  - clients/desktop/src/router/index.js
  - clients/desktop/src/services/api.js
  - clients/desktop/src/views/Agents.vue
  - clients/desktop/src/views/Tools.vue
  - clients/desktop/src/styles.css
  - backend/app/sandbox/container/providers/codex.py
  - backend/app/sandbox/container/providers/claude.py
  - backend/app/sandbox/container/agent.py
  - backend/app/sandbox/container/capabilities.py
  - backend/tests/*
  - clients/desktop/*
requirements:
  - REQ-27
  - REQ-28
  - REQ-29
  - REQ-30
  - REQ-31
  - REQ-32
  - REQ-33
  - REQ-34
must_haves:
  truths:
    - D-11: Electron 客户端不直接执行工具；工具由后端/sandbox/provider runtime 执行。
    - D-12: 桌面端本阶段只做入口、绑定、展示和触发。
    - D-13: 完整管理能力继续由 Web 端承接，桌面端后续再补。
    - D-14: 桌面端 Agent capability binding 默认固定版本。
    - D-15: Phase 04 必须验证 Codex 和 Claude 两条 provider 路径。
    - D-16: 验收必须包含投影证据、运行证据、行为证据。
  artifacts:
    - path: .planning/phases/04-desktop-toolset-adapter/04-SPEC.md
      provides: Locked desktop toolset adapter requirements and boundaries.
    - path: .planning/phases/04-desktop-toolset-adapter/04-PLAN.md
      provides: Execution checkpoints and verification route.
    - path: .planning/phases/04-desktop-toolset-adapter/04-VERIFY.md
      provides: To be created during execution with desktop/Codex/Claude smoke evidence.
---

# Phase 04 Plan: Desktop Toolset Adapter

## Objective

Add a desktop-client entry point for Toolset/Capability management and prove that desktop-created Agent sessions really inject and use bound Skill, Tool, and MCP capabilities through Codex and Claude provider runtimes.

## Strategy

Reuse Phase 03 backend APIs and runtime projection. Keep execution centralized in backend/sandbox/provider runtime. The desktop client should become a capability-aware management and binding surface, not a local tool executor.

## Checkpoints

### Checkpoint A: Pre-flight and Baseline Audit

- Confirm current branch is `combine/toolset_v1.1.0`.
- Confirm working tree state before editing.
- Inspect `clients/desktop` route/sidebar/API structure.
- Inspect Web `AgentEditForm` capability picker and reuse the smallest practical subset for desktop.
- Inspect backend capability routes and agent binding payload shape.

Verification:

- Record baseline in implementation notes or `04-VERIFY.md`.
- No implementation starts before the desktop UI and runtime evidence route is understood.

### Checkpoint B: Desktop API Wrappers

- Add desktop API service functions for:
  - listing toolset categories,
  - listing capabilities with filters,
  - listing agent capability bindings,
  - binding a capability version to an Agent,
  - deleting/unbinding an Agent capability binding,
  - checking upgrades if needed for display,
  - creating/editing Skill versions,
  - Markdown/zip/npx/MCP manifest import preview and confirm,
  - capability assets/audits/delete impact,
  - provider config create/test/save/enable/disable/delete.
- Keep existing desktop auth/server-url behavior.
- Reuse Web-side endpoint semantics instead of introducing desktop-only management routes.

Verification:

- Desktop API functions use the same backend paths as Web.
- API wrappers can be contract-tested or smoke-tested against the running backend.

### Checkpoint C: Desktop Toolset Entry

- Enable the sidebar Tools button.
- Add `clients/desktop/src/views/Tools.vue`.
- Add route `/tools`.
- Display:
  - first-level categories,
  - Skill/MCP/Plugin/Tool tabs,
  - capability cards,
  - source/status/version/permission summary,
  - clear disabled state for unbindable or unconfigured capabilities.
- Expose create/import/edit/delete/config/test controls through backend APIs; do not execute external processes in Electron.

Verification:

- Desktop can open `/tools`.
- Counts match visible capability cards.
- Hidden/deferred/unconfigured empty-shell Tools are not shown as bindable.

### Checkpoint D: Desktop Agent Binding UI

- Replace or augment old desktop `tool_ids` selector with capability binding selection.
- Preserve provider selector: Claude, Codex, OpenCode where supported.
- On create/edit:
  - load bindable capabilities grouped by category/type,
  - add selected capability as pinned latest version,
  - show required/optional permissions,
  - save capability bindings through real backend binding API,
  - remove existing binding through real unbind API.
- Keep legacy `tool_ids` only as compatibility metadata if backend still returns it; do not make it the primary toolset UX.

Verification:

- New Agent can be saved with at least one Skill and one MCP/Tool binding.
- Editing existing Agent reloads and preserves bindings.
- Removing a binding updates backend and UI after refresh.

### Checkpoint D2: Desktop Management Workflows

- Add desktop flows for:
  - new Skill Markdown,
  - edit Skill Markdown version,
  - Markdown file/text import,
  - zip bundle import,
  - npx import preview/confirm,
  - MCP manifest preview/confirm,
  - audit preview and saved audit display,
  - high-risk expert confirmation,
  - user capability delete with impact preview,
  - provider config create/test/save/enable/disable/delete.
- Keep all execution on backend/sandbox routes.

Verification:

- Each workflow calls the expected backend endpoint.
- Import preview shows security audit.
- High-risk confirm requires override confirmation and reason.
- Provider config can be tested before enabling.

### Checkpoint E: Runtime Projection from Desktop Session

- Create or select a desktop Agent with known test capabilities.
- Start a desktop-originated conversation/session.
- Confirm host/session creation writes DB-backed capability projection.
- Inspect `.weagent/*` in the sandbox workspace.

Verification:

- Evidence exists for:
  - `.weagent/capabilities/index.json`
  - `.weagent/agents/<agent_id>/capabilities.json`
  - `.weagent/agents/<agent_id>/skill-index.json`
  - `.weagent/agents/<agent_id>/tool-index.json`
  - `.weagent/agents/<agent_id>/permissions.json`

### Checkpoint F: Codex Provider Evidence

- Use a Codex Agent created or edited from desktop.
- Bind a small test Skill and a known MCP manifest/config.
- Start a session and inspect Codex runtime config/logs.
- Confirm Codex config includes MCP server entries derived from bound capabilities.
- Confirm prompt/context includes capability entry points.
- Send a simple prompt that asks the Agent to use or report the bound test capability.

Verification:

- Codex config/log evidence captured.
- MCP server appears under Codex runtime config if bound.
- Model output or provider log proves the capability context is present.
- If network/model access fails, record the exact environment failure and keep config/prompt evidence.

### Checkpoint G: Claude Provider Evidence

- Use a Claude Agent created or edited from desktop.
- Bind a small test Skill and at least one Tool/MCP capability.
- Start a session and inspect Claude runtime prompt/context/logs.
- Confirm Claude receives capability index path or capability bootstrap instructions.
- Send a simple prompt that asks the Agent to use or report the bound test capability.

Verification:

- Claude prompt/context/log evidence captured.
- Model output or provider log proves capability context is present.
- If external Claude access fails, record the exact environment failure and keep prompt/config evidence.

### Checkpoint H: Built-in Tool Binding Evidence

- Bind one implemented built-in Tool such as image info if available and visible.
- Confirm it appears in `tool-index.json` and permissions.
- Trigger a minimal safe call where runtime supports it, or verify tool registry can resolve the bound tool.
- Confirm call record is written when a call occurs.

Verification:

- Tool index evidence captured.
- Call record evidence captured, or a clear limitation is documented if provider cannot trigger the call in this phase.

### Checkpoint I: Desktop Build and UI Smoke

- Run desktop build or equivalent package check.
- Run focused desktop frontend tests if available.
- Start backend, frontend/desktop dev server if needed.
- Use browser/Electron smoke to verify:
  - login/server setup still works,
  - `/agents` still works,
  - `/tools` works,
  - Agent create/edit binding works.

Verification:

- Build/test commands and results recorded in `04-VERIFY.md`.
- Screenshots may be attached or referenced if needed.

### Checkpoint J: Verification Report and Handoff

- Create `.planning/phases/04-desktop-toolset-adapter/04-VERIFY.md`.
- Include:
  - changed files,
  - desktop UI checks,
  - API checks,
  - projection evidence,
  - Codex evidence,
  - Claude evidence,
  - Tool/MCP call evidence,
  - skipped checks and why.
- Summarize remaining work for full desktop management UI.

Verification:

- `04-VERIFY.md` contains the three evidence layers.
- Remaining risks are explicit and actionable.

## UI Policy

- Desktop Tools page is a management surface for core capability workflows.
- Category is the first-level navigation.
- Skill/MCP/Plugin/Tool are second-level tabs inside the selected category.
- Agent binding UI defaults to fixed versions.
- The UI should not show raw manifest JSON as the main user-facing content.
- Disabled or unconfigured capabilities must explain why they cannot be bound.
- Import and provider config dialogs may show editable JSON where JSON is the actual user input.

## Runtime Policy

- No direct Electron-side process execution.
- No desktop-side npx/MCP/Docker/script spawning.
- Runtime execution remains in backend/sandbox/provider.
- Codex/Claude verification must use desktop-created or desktop-edited Agents.
- `.weagent/*` remains the canonical runtime projection.

## Test Fixtures

Preferred fixtures:

- Skill: a tiny test Skill with obvious instruction text, for example "When asked about desktop toolset smoke, answer with DESKTOP_SKILL_OK".
- MCP: a minimal known MCP server already supported by the project, such as memory MCP if available in the local environment.
- Tool: an implemented safe built-in Tool such as image info, because it does not require external provider credentials.

## Success Criteria

- [x] Desktop has a usable toolset entry.
- [x] Desktop Agent create/edit supports capability binding.
- [x] Desktop-originated sessions generate `.weagent/*`.
- [x] Codex provider evidence proves capability/MCP injection.
- [x] Claude provider evidence proves capability context injection.
- [x] Markdown/zip/npx/MCP import flows are available from desktop.
- [x] Audit preview/detail and provider config test flows are available from desktop.
- [x] At least one Skill behavior is visible in output or logs.
- [x] At least one Tool/MCP binding is visible in index/config/call record.
- [x] Desktop client does not directly execute tools.
- [x] Verification report is complete.
