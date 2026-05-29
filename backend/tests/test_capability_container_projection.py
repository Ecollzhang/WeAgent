import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.sandbox.container.capabilities import (
    agent_bootstrap_instruction,
    write_projection,
    write_run_snapshot,
)


def _workspace_tempdir():
    base = Path.cwd() / ".pytest-tmp"
    base.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=base)


def _sample_projection():
    return {
        "schema_version": "weagent.capability_projection/v1",
        "session_id": "session-1",
        "capabilities": {
            "skill-1": {
                "id": "skill-1",
                "type": "skill",
                "name": "Review Skill",
                "version": {"id": "version-1", "version": "1.0.0"},
            },
            "mcp-1": {
                "id": "mcp-1",
                "type": "mcp",
                "name": "Example MCP",
                "version": {"id": "version-2", "version": "1.0.0"},
            },
            "plugin-1": {
                "id": "plugin-1",
                "type": "plugin",
                "name": "Example Plugin",
                "version": {"id": "version-3", "version": "1.0.0"},
            },
        },
        "skills": {
            "skill-1": {
                "capability_id": "skill-1",
                "version_id": "version-1",
                "name": "Review Skill",
                "content": "# Review Skill\nUse this checklist.",
                "manifest": {"entry": "SKILL.md", "format": "markdown"},
                "path": "/workspace/.weagent/skills/skill-1/SKILL.md",
                "manifest_path": "/workspace/.weagent/skills/skill-1/manifest.json",
            }
        },
        "mcp": {
            "mcp-1": {
                "capability_id": "mcp-1",
                "version_id": "version-2",
                "manifest": {"entry": {"command": "npx", "args": ["-y", "@example/mcp"]}},
                "path": "/workspace/.weagent/mcp/mcp-1/manifest.json",
            }
        },
        "plugins": {
            "plugin-1": {
                "capability_id": "plugin-1",
                "version_id": "version-3",
                "manifest": {"entry": {"module": "@example/plugin"}},
                "path": "/workspace/.weagent/plugins/plugin-1/manifest.json",
            }
        },
        "tools": {},
        "agents": {
            "agent-a": {
                "agent_id": "agent-a",
                "capabilities": [
                    {"capability_id": "skill-1", "type": "skill", "version_id": "version-1"},
                    {"capability_id": "mcp-1", "type": "mcp", "version_id": "version-2"},
                ],
                "skill_index": [
                    {
                        "capability_id": "skill-1",
                        "version_id": "version-1",
                        "name": "Review Skill",
                        "path": "/workspace/.weagent/skills/skill-1/SKILL.md",
                    }
                ],
                "permissions": {
                    "agent_id": "agent-a",
                    "grants": [
                        {
                            "capability_id": "skill-1",
                            "capability_version_id": "version-1",
                            "granted_permissions": ["read_workspace"],
                        }
                    ],
                },
            },
            "agent-b": {
                "agent_id": "agent-b",
                "capabilities": [],
                "skill_index": [],
                "permissions": {"agent_id": "agent-b", "grants": []},
            },
        },
    }


def test_write_projection_creates_only_canonical_weagent_runtime_files():
    projection = _sample_projection()

    with _workspace_tempdir() as workspace:
        tmp_path = Path(workspace)
        result = write_projection(projection, workspace_root=str(tmp_path))

        assert result["status"] == "ok"
        assert (tmp_path / ".weagent" / "capabilities" / "index.json").exists()
        assert (tmp_path / ".weagent" / "skills" / "skill-1" / "SKILL.md").read_text(
            encoding="utf-8"
        ).startswith("# Review Skill")
        assert (tmp_path / ".weagent" / "skills" / "skill-1" / "manifest.json").exists()
        assert (tmp_path / ".weagent" / "mcp" / "mcp-1" / "manifest.json").exists()
        assert (tmp_path / ".weagent" / "plugins" / "plugin-1" / "manifest.json").exists()

        agent_a_index = json.loads(
            (tmp_path / ".weagent" / "agents" / "agent-a" / "skill-index.json").read_text(
                encoding="utf-8"
            )
        )
        agent_b_index = json.loads(
            (tmp_path / ".weagent" / "agents" / "agent-b" / "skill-index.json").read_text(
                encoding="utf-8"
            )
        )
        assert [item["capability_id"] for item in agent_a_index["skills"]] == ["skill-1"]
        assert agent_b_index["skills"] == []
        assert (tmp_path / ".weagent" / "agents" / "agent-a" / "capabilities.json").exists()
        assert (tmp_path / ".weagent" / "agents" / "agent-a" / "permissions.json").exists()
        assert not (tmp_path / ".claude").exists()
        assert not (tmp_path / ".codex").exists()
        assert not (tmp_path / ".mcp.json").exists()


def test_write_run_snapshot_and_bootstrap_instruction():
    projection = _sample_projection()

    with _workspace_tempdir() as workspace:
        tmp_path = Path(workspace)
        write_projection(projection, workspace_root=str(tmp_path))

        result = write_run_snapshot(projection, "run-1", workspace_root=str(tmp_path))

        assert result["status"] == "ok"
        snapshot = json.loads(
            (
                tmp_path / ".weagent" / "runs" / "run-1" / "capability-snapshot.json"
            ).read_text(encoding="utf-8")
        )
        assert snapshot["session_id"] == "session-1"
        assert snapshot["agents"]["agent-a"]["skill_index"][0]["capability_id"] == "skill-1"
        assert (tmp_path / ".weagent" / "runs" / "run-1" / "calls.jsonl").read_text(
            encoding="utf-8"
        ) == ""

    instruction = agent_bootstrap_instruction("agent-a")
    assert "/workspace/.weagent/agents/agent-a/skill-index.json" in instruction
    assert "/workspace/.weagent/agents/agent-a/capabilities.json" in instruction
    assert "/workspace/.weagent/agents/agent-a/permissions.json" in instruction
    assert ".claude" not in instruction
    assert ".codex" not in instruction
    assert ".mcp.json" not in instruction
