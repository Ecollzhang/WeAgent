# Repo Import Current Limitation

Current implementation:

```text
POST /api/capabilities/import/preview
source_type = repo
repo_path = local path visible to the backend process
```

This means the UI currently needs a local repository path. It does not yet clone or download from:

```text
https://github.com/owner/repo
owner/repo
```

For product UAT, treat remote repo import as not ready.

Recommended follow-up:

1. Accept `source_ref` as `owner/repo` or GitHub URL.
2. Clone/download into a temporary import sandbox directory.
3. Static scan supported Skill layouts.
4. Do not execute repo scripts during preview.
5. Delete the temporary clone after preview artifacts are captured.
