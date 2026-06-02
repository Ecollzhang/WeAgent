---
name: code-review-triage
description: Use this skill when reviewing code changes and producing a concise triage of correctness, security, test, and maintainability risks.
---

# Code Review Triage Skill

Use this skill when the user asks for a focused review of code changes, pull requests, or implementation diffs.

## Workflow

1. Inspect the changed files and identify the user-visible behavior being changed.
2. Prioritize findings by severity: correctness, security, data loss, regression risk, then maintainability.
3. For each finding, include the file path, the concrete failure mode, and a minimal fix direction.
4. If no issue is found, say so clearly and list remaining test gaps.

## Output

Return:

- Findings first, ordered by severity.
- Open questions only when they block judgment.
- A short verification summary.

## Boundaries

- Do not rewrite unrelated code.
- Do not treat style-only preferences as defects.
- Do not approve risky behavior without a test or explicit rationale.
