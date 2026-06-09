---
name: bundle-review-helper
description: Use this skill to review a small feature bundle with a checklist, a validation script, and a reusable report template.
---

# Bundle Review Helper

Use this skill when a user wants a structured review of a small feature bundle.

## Workflow

1. Read `references/review-policy.md`.
2. Run or inspect `scripts/check.mjs` only when script execution is explicitly allowed.
3. Produce a report using `templates/report-template.md`.

## Safety

Ask before running scripts. If script execution is not allowed, inspect the script statically.
