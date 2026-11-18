---
name: write-technical-document
description: Create, revise, or audit one Chinese Markdown technical document from verified project facts. Use when the user asks to write a single technical document, architecture document, developer documentation, system design document, deployment/runbook document, or technical project documentation, especially when the output must combine Diataxis, Google/Microsoft style guidance, ADR/MADR decision context, and project source-code evidence.
---

# Write Technical Document

## Core Contract

Produce one Markdown technical document. Do not split the final deliverable into multiple documents unless the user explicitly changes the requirement.

Use Chinese as the main language and keep necessary English technical terms. First mention of an important term must include a Chinese explanation and the English original, for example: 架构决策记录（Architecture Decision Record, ADR）.

Do not invent facts. If a fact cannot be verified from the repository, user-provided material, runtime output, or cited source, mark it as `待确认`.

## Before Writing

Ask for requirements before drafting when the user has not already provided them. Keep questions short and focus on decisions that change the document:

1. Who is the primary reader?
2. What must the single document help the reader do or understand?
3. Which repository, branch, build, or artifact is the source of truth?
4. Which sections are required or forbidden?
5. Should the document include screenshots, diagrams, API examples, runbook steps, or ADR-style decisions?

If the user has already answered these questions in context, do not ask again. State the assumptions and proceed.

Before selecting a structure, inspect the project facts. Prefer this evidence order:

1. Current code, configuration, routes, models, tests, scripts, lockfiles, and build files.
2. Git branches, commit history, release notes, and generated reports.
3. Existing project docs and READMEs.
4. External writing frameworks and templates. These guide structure and style, but never override project facts.

If internet access is available and template choice is unclear, open The Good Docs Project template page and select only the relevant patterns. If internet access is unavailable, use `references/single-doc-templates.md`.

## Writing Workflow

1. State the document goal, reader, evidence sources, and assumptions.
2. Choose a single-document structure using Diataxis:
   - Tutorial: teach a newcomer through one successful path.
   - How-to guide: provide executable steps for a specific task.
   - Reference: describe APIs, commands, data models, configuration, and limits.
   - Explanation: explain architecture, decisions, tradeoffs, and behavior.
3. For one full technical document, combine quadrants deliberately instead of mixing them randomly:
   - Start with conclusion and scope.
   - Explain architecture and decisions.
   - Provide executable setup, operation, and verification steps.
   - Add reference-lite tables only where they reduce ambiguity.
   - End with risks, limitations, troubleshooting, and `待确认` items.
4. Draft an outline first for substantial documents. Fill the body only after the outline is stable or the user asks to proceed autonomously.
5. Bind major claims to evidence paths, commands, tests, screenshots, links, or branch names.
6. Review for factual drift, reader fit, style rules, and single-document cohesion.

## Section Rules

- Put the conclusion before details.
- Make each section solve one problem.
- Use executable steps. Avoid subjective words such as “显然”, “简单”, “容易”, “只需” unless quoting the user.
- Format parameters, variables, filenames, commands, paths, endpoints, classes, functions, and environment variables with code style.
- Explain the purpose before every code block.
- After every code block, explain expected output, side effects, or cautions.
- Keep formulas, variable names, and function names unchanged.
- Use a formal, concise tone. Avoid marketing language.
- Use headings, whitespace, lists, diagrams, code snippets, screenshots, and tables to reduce cognitive load, not to add decoration.
- Prefer numbered lists for ordered procedures and bullets for unordered facts.
- Use descriptive link text.

## ADR/MADR Integration

Do not dump architecture decisions into a large table as the primary form. When a module depends on a meaningful decision, place a short decision block near that module:

```markdown
### 模块名

结论：一句话说明这个模块的职责或实现选择。

#### 背景

为什么需要这个决策？问题、约束、读者需要知道的上下文是什么？

#### 决策

最终选择了什么方案？如果有替代方案，只写影响理解的关键对比。

#### 方案内容

方案实现了什么效果？包含哪些子模块、接口、数据流、前后依赖、边界和限制？

#### 证据

- `path/to/file`
- `command`
- `test name`
```

Use ADR/MADR blocks only for decisions that affect architecture, operation, security, compatibility, data flow, or maintenance. Small implementation details can stay in normal prose.

## Template Resources

Read these references only when needed:

- `references/source-guidelines.md`: compressed rules absorbed from Google Developer Documentation Style Guide, Microsoft Style Guide, Diataxis, and the user's Chinese writing rules.
- `references/single-doc-templates.md`: single-document structure patterns adapted from Diataxis and The Good Docs Project templates.

## Final Review Checklist

Before presenting the document or claiming it is ready, verify:

- The output is one Markdown document.
- The first page tells the reader what the system is, what this document covers, and what is `待确认`.
- Every major feature or architecture claim has evidence or is marked `待确认`.
- Old or conflicting facts are removed or explicitly labeled as historical.
- Commands and code blocks include purpose and expected result or caution.
- ADR/MADR content is attached to relevant modules instead of isolated as a decision table.
- Terminology is consistent and important first-use terms include Chinese explanation plus English original.
- The document is concise enough to read and detailed enough to execute.
