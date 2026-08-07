# npx Import Sources

Paste one source string at a time into the toolset import wizard's `npx` mode.

## Skill installer examples

```text
npx skills add eze-is/web-access
```

Expected:

- Accepted by the allowlist parser.
- Runs inside Docker import sandbox.
- If the package emits a `SKILL.md`, preview should show imported Skill candidates.

```text
npx @orchestra-research/ai-research-skills
```

Expected:

- Accepted by the allowlist parser.
- Runs inside Docker import sandbox.
- May discover multiple Skill candidates if the package writes skills to a supported folder.

## Injection rejection examples

These should be rejected before Docker execution:

```text
npx skills add eze-is/web-access && whoami
```

```text
cmd /c npx skills add eze-is/web-access
```

```text
npx @orchestra-research/ai-research-skills > out.txt
```
