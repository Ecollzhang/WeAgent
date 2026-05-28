# Phase 001: Toolset Capabilities v1 - Context

**Created:** 2026-05-28
**Status:** Ready for implementation planning

## Locked Decisions

### Capability Types

`Skill`, `Tool`, `MCP`, and `Plugin` are peer capability types. Plugin is a package/source record that may contain or reference other capability definitions, but it is not a subtype of Skill.

### Source of Truth

DB is canonical for durable capability definitions, versions, Agent definitions, Agent capability bindings, authorization snapshots, import data, call records, and Skill drafts. `/workspace/.weagent/*` is a session-scoped runtime projection and disappears with the sandbox.

### Agent Binding Model

Users configure default capabilities when creating or editing an Agent. A session uses the Agent's saved default capability bindings. New conversations do not choose capabilities independently in v1.

### Version Policy

Agent bindings default to `pinned` and store `capability_version_id`. A reserved `follow_latest` value can exist in data structures, but v1 UI and runtime behavior must not silently auto-upgrade existing Agents.

### Permission Model

Capability versions declare permissions from:

- `read_workspace`
- `write_workspace`
- `run_command`
- `network`
- `use_secret`
- `modify_skill`
- `start_service`

Agent bindings store `granted_permissions` and `authorization_snapshot`. In v1, declared permissions are treated as required unless the manifest explicitly marks them as optional. Optional permissions can be omitted, but required permissions must be granted before binding.

### Runtime Layout

v1 writes only:

```text
/workspace/.weagent/
  capabilities/index.json
  skills/<skill_id>/SKILL.md
  skills/<skill_id>/manifest.json
  mcp/<mcp_id>/manifest.json
  plugins/<plugin_id>/manifest.json
  agents/<agent_id>/capabilities.json
  agents/<agent_id>/skill-index.json
  agents/<agent_id>/permissions.json
  runs/<run_id>/capability-snapshot.json
  runs/<run_id>/calls.jsonl
  drafts/skills/<skill_id>/
```

No `.claude/skills`, `.codex/skills`, or `.mcp.json` compatibility files are generated in v1.

### Agent Runtime Discovery

Projection alone is not enough. Agent startup must include a compact WeAgent capability bootstrap section in the Agent runtime instructions. The bootstrap points the Agent to:

- `/workspace/.weagent/agents/<agent_id>/skill-index.json`
- `/workspace/.weagent/agents/<agent_id>/capabilities.json`
- `/workspace/.weagent/agents/<agent_id>/permissions.json`

The bootstrap tells the Agent to read Skill Markdown only when the task requires it. It does not inject every Skill body into the initial prompt.

### Skill Draft Flow

Agent-written changes to `/workspace/.weagent/skills/<skill_id>/SKILL.md` affect only the current session immediately. The platform syncs those changes to DB as `SkillRevisionDraft(status='pending_review')`. The user can publish as a new version, save as fork, or reject.

### MCP npx Import

MCP v1 requires manifest import before binding or execution. Manifest import parses server command, tool declarations, source package, version, and permissions. npx execution occurs only inside the sandbox container.

### Plugin Scope

Plugin v1 stores manifest, source, included capability references, and install records. Plugin code execution, hooks, UI extensions, and arbitrary commands are out of scope.

### Call Record Sync

Call record sync should be a distinct service boundary, not part of projection. Use a backend `capability_call_sync_service` or equivalent callback path to persist container-side JSONL records into `CapabilityCallRecord`.

### Model Naming

Avoid `metadata` as a SQLAlchemy model attribute name. Use `meta` or `extra` for JSON metadata fields.

## Proposed WeAgent Manifest Schema

```json
{
  "schema_version": "weagent.capability/v1",
  "source": {
    "type": "npx",
    "package": "@example/mcp-server",
    "version": "1.0.0"
  },
  "capabilities": [
    {
      "type": "mcp",
      "name": "Example MCP",
      "description": "Example MCP server",
      "permissions": {
        "required": ["run_command"],
        "optional": ["network"]
      },
      "entry": {
        "command": "npx",
        "args": ["-y", "@example/mcp-server"]
      },
      "tools": [
        {
          "name": "echo",
          "description": "Echo input",
          "input_schema": {
            "type": "object",
            "properties": {
              "text": { "type": "string" }
            },
            "required": ["text"]
          }
        }
      ]
    }
  ]
}
```

## Open Implementation Choices

- The host should push projection through a new container API endpoint before Agent creation. This avoids environment size limits.
- Legacy `Agent.skill` should first be shown as migration context rather than auto-migrated into a user Skill.

