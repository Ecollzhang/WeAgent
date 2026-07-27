# MCP Manifest UAT Example

Use this content with the MCP manifest import path.

```json
{
  "schema_version": "weagent.capability/v1",
  "source": {
    "type": "npx",
    "package": "@modelcontextprotocol/server-memory",
    "version": "latest"
  },
  "capabilities": [
    {
      "type": "mcp",
      "name": "Memory MCP",
      "description": "Official MCP memory server for graph-style memory operations.",
      "permissions": {
        "required": ["run_command"],
        "optional": []
      },
      "entry": {
        "command": "npx",
        "args": ["--yes", "@modelcontextprotocol/server-memory"]
      },
      "tools": [
        { "name": "create_entities" },
        { "name": "read_graph" },
        { "name": "search_nodes" },
        { "name": "open_nodes" }
      ]
    }
  ]
}
```

Current boundary:

- This is a manifest/import fixture, not a guarantee that every arbitrary MCP package can be installed safely.
- Runtime execution still depends on sandbox permissions, npx availability, package audit, and Agent binding.
