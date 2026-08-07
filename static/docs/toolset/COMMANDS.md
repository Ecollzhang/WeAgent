# Typical TOOL / Skill / Plugin / MCP Sources

This file separates what is usable in the current implementation from examples that describe the intended product direction.

## Current WeAgent UAT Inputs

### Skill: Markdown

Use:

```text
toolset/01-markdown-skill.md
```

### Skill: zip bundle

Use:

```text
toolset/02-skill-bundle.zip
```

### Skill: npx installer

Use:

```text
npx skills add eze-is/web-access
```

or:

```text
npx @orchestra-research/ai-research-skills
```

### TOOL: built-in platform capability

Current TOOL items are seeded by WeAgent. They do not have a download command yet.

Test them by opening the Tool tab in the toolset page and checking the virtual file view:

```text
tool-definition.json
manifest.json
```

## Current Boundary Examples

### MCP

Typical MCP packages often require command arguments, for example filesystem roots or API keys. The current npx import parser only accepts safe installer forms and rejects arbitrary arguments.

Do not treat this as a currently supported WeAgent import command:

```text
npx -y @modelcontextprotocol/server-filesystem /workspace
```

Recommended follow-up:

- Add a dedicated MCP install form.
- Parse package, version, command args, environment requirements, and permissions separately.
- Preview the manifest before allowing Agent binding.

### Plugin

Plugin is currently manifest/install-record oriented. A generic plugin runtime installer is not ready.

Do not treat this as a currently supported WeAgent import command:

```text
npx @example/weagent-plugin-pack
```

Recommended follow-up:

- Require manifest import first.
- Show declared permissions and included capabilities.
- Allow binding only after manifest audit.

## API Smoke Notes

For current UI testing, prefer:

1. Markdown import.
2. zip bundle import.
3. npx Skill installer import.
4. Built-in Tool detail view.

Skip remote repo, generic MCP install, and generic Plugin runtime install until those flows are explicitly implemented.
