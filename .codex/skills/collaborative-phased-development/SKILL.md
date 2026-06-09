---
name: collaborative-phased-development
description: Structured collaboration workflow for software delivery where Codex should first restate and clarify the user's requirements, then design a phased implementation plan with confirmation questions, execute one phase at a time, write or run tests for each phase, wait for user inspection between phases, and iterate on corrections before continuing. Use when the user asks to follow their established collaboration habit, phased delivery process, staged implementation, requirements-to-plan workflow, or step-by-step project execution with acceptance criteria.
---

# Collaborative Phased Development

Use this skill to manage software work as a staged collaboration rather than a single large implementation pass.

## Core Workflow

1. Restate the requirement before designing or coding.
   - Summarize what the user asked for in concrete terms.
   - Identify affected surfaces: backend, Web, desktop, Android, tests, docs, data model, build scripts, deployment.
   - State assumptions explicitly.
   - Do not start implementation until the requirement is understood enough to produce a plan.

2. Produce a方案 before implementation.
   - Break the work into phases.
   - For each phase, define:
     - Goal
     - Scope
     - Files or modules likely affected
     - Acceptance criteria
     - Test or verification method
   - Include questions that must be confirmed before implementation.
   - Prefer batching questions so the user can answer once.

3. Ask only useful confirmation questions.
   - Ask about behavior, priority, platform scope, data persistence, API contract, compatibility, UX constraints, and test environment.
   - Avoid asking questions that can be answered by reading the codebase.
   - If a safe assumption is available, state it and proceed after the user confirms the plan.

4. Execute one phase at a time.
   - Implement only the current approved phase.
   - Keep changes scoped to that phase.
   - Do not silently expand scope into later phases.
   - If a later-phase dependency is discovered, stop and update the plan.

5. Test each phase.
   - Write or update focused tests when behavior is testable.
   - If automated tests are impractical, create a concrete manual verification checklist.
   - Run the relevant tests/builds before reporting completion.
   - Report failed or skipped tests with the reason.

6. Report phase completion.
   - Summarize what changed.
   - List verification results.
   - State remaining known risks or unfinished items.
   - Ask the user to inspect the phase result.
   - Wait for the user to request corrections or the next phase.

7. Handle corrections before continuing.
   - Treat user feedback as the active phase priority.
   - Fix regressions or mismatches first.
   - Re-run the phase verification.
   - Only continue to the next phase after the current phase is accepted or explicitly deferred.

## Output Templates

### Requirement Restatement

```markdown
我理解你的需求是：

- ...
- ...

当前我会先确认这些点：

- ...

我的默认假设是：

- ...
```

### Phased Plan

```markdown
方案：

阶段 1：...
目标：...
范围：...
验收标准：...
测试方式：...

阶段 2：...
目标：...
范围：...
验收标准：...
测试方式：...

需要你确认：

1. ...
2. ...
```

### Phase Completion Report

```markdown
阶段 X 已完成。

改动：
- ...

验证：
- ...

请检查这一阶段结果。确认后我再继续下一阶段；如果不符合预期，我先修正这一阶段。
```

## Operating Rules

- Prefer code reading before planning detailed implementation.
- Keep the plan updated when discoveries change the work.
- Use repository conventions rather than inventing new architecture.
- Preserve user changes in a dirty worktree.
- Use focused tests that match the phase risk.
- Do not claim completion without verification.
- Do not move to the next phase merely because implementation is done; wait for user acceptance when the workflow calls for inspection.
- If the user asks to skip planning or “直接实现”, obey the newer instruction and implement directly.

## Testing Standard

For each phase, choose the strongest practical verification:

- Unit tests for pure logic, service methods, reducers, schemas, parsers, and helpers.
- Integration tests for API contracts, persistence, socket/event flows, and cross-module behavior.
- Build checks for frontend or packaging changes.
- Manual checklist for UI layout, visual behavior, platform-specific behavior, or environment-dependent flows.

When writing tests is not practical, explain why and provide exact manual verification steps.

## Collaboration Contract

Default loop:

1. User gives requirement.
2. Codex restates requirement.
3. Codex proposes phased plan and confirmation questions.
4. User answers or negotiates.
5. Codex executes phase 1.
6. Codex tests phase 1.
7. User inspects.
8. Codex fixes or proceeds to phase 2.

Continue until all phases are accepted or the user changes direction.
