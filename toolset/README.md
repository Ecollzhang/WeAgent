# WeAgent Toolset UAT Fixtures

This folder contains files and source strings for real-environment testing of the 003 toolset import flow.

Use these with the guide:

```text
.planning/phases/001-toolset/003-external-toolset-import/REAL-ENV-UAT-GUIDE.zh-CN.md
```

## Files

- `01-markdown-skill.md`: paste or upload as a Markdown Skill import.
- `02-skill-bundle.zip`: upload as a zip bundle import.
- `02-zipbundle-source/`: source files used to build the zip bundle.
- `03-repo-current-limitation.md`: why repo import is not included as a remote URL fixture yet.
- `04-npx-import-sources.md`: npx source strings to paste into the import wizard.
- `COMMANDS.md`: typical TOOL / Skill / Plugin / MCP commands and current support boundaries.

## Current Repo Import Boundary

The current backend implementation scans a local `repo_path`. It does not yet clone remote GitHub URLs.
Because of that, this folder does not pretend to provide a remote repo fixture. Remote repo import should be implemented as a follow-up.
