import pytest

from app import create_app, db
from app.models.agent import Agent
from app.models.user import User
from app.services.capability_projection_service import build_capability_projection
from app.services.capability_service import capability_service
from app.services.toolset_category_service import toolset_category_service


FUNCTIONAL_CATEGORIES = {
    "tool_code",
    "tool_file",
    "tool_web",
    "tool_data",
    "tool_image",
    "tool_sys",
}


@pytest.fixture()
def app_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_builtin_tools():
    toolset_category_service.seed_builtin_categories()
    capability_service.seed_builtin_tool_capabilities()
    tools, error = capability_service.list_capabilities("user-1", "tool")
    assert error is None
    return [item for item in tools if item["is_builtin"]]


def test_builtin_tool_versions_have_manifest_docs_and_category_coverage(app_context):
    tools = _seed_builtin_tools()
    assert tools

    implemented_categories = set()
    for tool in tools:
        latest = tool["latest_version"]
        manifest = latest["manifest"]
        assert latest["content"].startswith("# "), tool["name"]
        assert manifest["schema_version"] == "weagent.tool/v1", tool["name"]
        assert manifest["runtime"] == "builtin", tool["name"]
        assert manifest["handler"], tool["name"]
        assert manifest["tool_names"], tool["name"]
        assert manifest["input_schema"]["type"] == "object", tool["name"]
        assert manifest["output_schema"]["type"] == "object", tool["name"]
        assert "required" in latest["permissions"], tool["name"]
        assert manifest["permissions"] == latest["permissions"], tool["name"]
        assert manifest["audit"]["record_input"] is True, tool["name"]
        assert manifest["ui"]["status"] in {
            "implemented",
            "partial",
            "requires_config",
            "deferred",
        }, tool["name"]
        if manifest["ui"]["status"] == "implemented":
            implemented_categories.add(tool["category_id"])

    assert FUNCTIONAL_CATEGORIES.issubset(implemented_categories)
    assert "tool_custom" not in implemented_categories


def test_builtin_tool_projection_exposes_tool_index_and_doc_paths(app_context):
    user = User(
        id="user-1",
        username="tool-contract-user",
        email="tool-contract@example.com",
        password_hash="hash",
    )
    agent = Agent(
        id="agent-1",
        name="Tool Agent",
        agent_type="custom",
        adapter_name="claude",
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add_all([user, agent])
    db.session.commit()
    tools = _seed_builtin_tools()
    code_search = next(item for item in tools if item["source_ref"] == "code_search")

    result, error = capability_service.bind_to_agent(
        agent_id=agent.id,
        capability_version_id=code_search["latest_version"]["id"],
        granted_permissions=["read_workspace"],
    )
    assert error is None
    assert result["capability"]["id"] == code_search["id"]

    projection = build_capability_projection(
        session_id="session-1",
        agents=[{"agent_id": agent.id, "role": agent.name}],
    )

    tool_record = projection["tools"][code_search["id"]]
    assert tool_record["doc_path"] == f"/workspace/.weagent/tools/{code_search['id']}/TOOL.md"
    assert tool_record["manifest_path"] == (
        f"/workspace/.weagent/tools/{code_search['id']}/manifest.json"
    )
    assert tool_record["tool_names"] == ["code_search"]
    assert tool_record["status"] == "implemented"
    assert tool_record["content"].startswith("# ")

    agent_view = projection["agents"][agent.id]
    assert agent_view["tool_index"] == [
        {
            "capability_id": code_search["id"],
            "runtime_id": code_search["id"],
            "version_id": code_search["latest_version"]["id"],
            "name": "代码搜索",
            "description": code_search["description"],
            "tool_names": ["code_search"],
            "permissions": {"required": ["read_workspace"], "optional": []},
            "status": "implemented",
            "doc_path": f"/workspace/.weagent/tools/{code_search['id']}/TOOL.md",
        }
    ]
    assert ".weagent/agents/agent-1/tool-index.json" in agent_view["bootstrap"]
