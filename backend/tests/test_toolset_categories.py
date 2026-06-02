import pytest
from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.capability import Capability
from app.models.capability import CapabilityVersion
from app.models.toolset_category import ToolsetCategory
from app.models.user import User
from app.services.capability_service import capability_service
from app.services.toolset_category_service import toolset_category_service


@pytest.fixture()
def client_context():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            id="user-1",
            username="toolset-user",
            email="toolset@example.com",
            password_hash="hash",
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=user.id)
        yield app.test_client(), {"Authorization": f"Bearer {token}"}, user
        db.session.remove()
        db.drop_all()


def test_builtin_categories_are_seeded_and_count_visible_capability_types(client_context):
    client, headers, _user = client_context
    toolset_category_service.seed_builtin_categories()
    capability_service.seed_builtin_tool_capabilities()

    response = client.get("/api/toolsets/categories", headers=headers)

    assert response.status_code == 200
    categories = response.get_json()["data"]
    code_category = next(item for item in categories if item["id"] == "tool_code")
    assert code_category["name"] == "代码工具"
    assert code_category["is_builtin"] is True
    assert code_category["counts"]["tool"] >= 1
    assert set(code_category["counts"]) == {"skill", "mcp", "plugin", "tool"}

    code_generator = Capability.query.filter_by(source_ref="code_generator").one()
    assert code_generator.category_id == "tool_code"


def test_builtin_memory_mcp_is_seeded_as_real_npx_capability(client_context):
    client, headers, _user = client_context
    toolset_category_service.seed_builtin_categories()
    capability_service.seed_builtin_tool_capabilities()

    response = client.get("/api/toolsets/categories", headers=headers)

    assert response.status_code == 200
    categories = response.get_json()["data"]
    data_category = next(item for item in categories if item["id"] == "tool_data")
    assert data_category["counts"]["mcp"] >= 1

    memory = Capability.query.filter_by(
        type="mcp",
        source="builtin",
        source_ref="@modelcontextprotocol/server-memory",
    ).one()
    version = CapabilityVersion.query.get(memory.latest_version_id)
    assert memory.category_id == "tool_data"
    assert version.permissions == {"required": ["run_command"], "optional": []}
    assert version.manifest["entry"] == {
        "command": "npx",
        "args": ["--yes", "@modelcontextprotocol/server-memory"],
    }
    tool_names = [tool["name"] for tool in version.manifest["tools"]]
    assert {"create_entities", "read_graph", "search_nodes", "open_nodes"}.issubset(tool_names)


def test_user_category_crud_and_delete_rehomes_capabilities(client_context):
    client, headers, _user = client_context
    toolset_category_service.seed_builtin_categories()

    create_response = client.post(
        "/api/toolsets/categories",
        headers=headers,
        json={
            "name": "研究工具",
            "icon": "el-icon-data-line",
            "color": "#2f80ed",
        },
    )
    assert create_response.status_code == 201
    category = create_response.get_json()["data"]
    assert category["name"] == "研究工具"
    assert category["is_builtin"] is False

    update_response = client.put(
        f"/api/toolsets/categories/{category['id']}",
        headers=headers,
        json={"name": "论文研究", "color": "#16a34a"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["data"]["name"] == "论文研究"

    skill_response = client.post(
        "/api/capabilities/skills",
        headers=headers,
        json={
            "name": "Paper Reviewer",
            "markdown": "# Paper Reviewer\nCheck claims.",
            "category_id": category["id"],
        },
    )
    assert skill_response.status_code == 201
    skill = skill_response.get_json()["data"]
    assert skill["category_id"] == category["id"]

    delete_response = client.delete(
        f"/api/toolsets/categories/{category['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 200
    assert ToolsetCategory.query.get(category["id"]) is None
    assert Capability.query.get(skill["id"]).category_id == "tool_custom"


def test_capability_create_and_import_support_category_filters(client_context):
    client, headers, _user = client_context
    toolset_category_service.seed_builtin_categories()

    skill_response = client.post(
        "/api/capabilities/skills",
        headers=headers,
        json={
            "name": "Code Skill",
            "markdown": "# Code Skill\nImprove code.",
            "category_id": "tool_code",
        },
    )
    assert skill_response.status_code == 201

    markdown_response = client.post(
        "/api/capabilities/import/markdown",
        headers=headers,
        json={
            "markdown": "# Web Skill\nSearch carefully.",
            "source_ref": "paste",
            "category_id": "tool_web",
        },
    )
    assert markdown_response.status_code == 201

    manifest_response = client.post(
        "/api/capabilities/import/npx-manifest",
        headers=headers,
        json={
            "source_ref": "npx:@example/toolset@1.0.0",
            "category_id": "tool_code",
            "manifest": {
                "schema_version": "weagent.capability/v1",
                "source": {
                    "type": "npx",
                    "package": "@example/toolset",
                    "version": "1.0.0",
                },
                "capabilities": [
                    {
                        "type": "mcp",
                        "name": "Code MCP",
                        "permissions": {"required": ["run_command"], "optional": []},
                        "tools": [{"name": "lint"}],
                    },
                    {
                        "type": "plugin",
                        "name": "Data Plugin",
                        "category": "tool_data",
                        "permissions": {"required": [], "optional": []},
                    },
                ],
            },
        },
    )
    assert manifest_response.status_code == 201
    imported = manifest_response.get_json()["data"]
    assert imported[0]["category_id"] == "tool_code"
    assert imported[1]["category_id"] == "tool_data"

    code_list = client.get(
        "/api/capabilities?category_id=tool_code",
        headers=headers,
    )
    names = {item["name"] for item in code_list.get_json()["data"]}
    assert {"Code Skill", "Code MCP"}.issubset(names)
    assert "Web Skill" not in names


def test_category_counts_exclude_archived_capabilities(client_context):
    client, headers, _user = client_context
    toolset_category_service.seed_builtin_categories()
    first, error = capability_service.create_skill(
        user_id="user-1",
        name="Visible Code Skill",
        markdown="# Visible Code Skill",
        category_id="tool_code",
    )
    assert error is None
    second, error = capability_service.create_skill(
        user_id="user-1",
        name="Archived Code Skill",
        markdown="# Archived Code Skill",
        category_id="tool_code",
    )
    assert error is None

    _result, error = capability_service.archive_user_capability(
        user_id="user-1",
        capability_id=second["id"],
    )
    assert error is None

    response = client.get("/api/toolsets/categories", headers=headers)

    assert response.status_code == 200
    code_category = next(
        item for item in response.get_json()["data"] if item["id"] == "tool_code"
    )
    assert code_category["counts"]["skill"] == 1

    list_response = client.get(
        "/api/capabilities?category_id=tool_code&type=skill",
        headers=headers,
    )
    assert [item["name"] for item in list_response.get_json()["data"]] == [
        first["name"]
    ]


def test_cannot_mutate_builtin_or_other_users_category(client_context):
    client, headers, _user = client_context
    toolset_category_service.seed_builtin_categories()
    other = ToolsetCategory(
        user_id="user-2",
        name="Other Private",
        slug="other-private",
        icon="el-icon-lock",
        color="#64748b",
        is_builtin=False,
    )
    db.session.add(other)
    db.session.commit()

    builtin_delete = client.delete("/api/toolsets/categories/tool_code", headers=headers)
    assert builtin_delete.status_code == 400

    update_other = client.put(
        f"/api/toolsets/categories/{other.id}",
        headers=headers,
        json={"name": "Stolen"},
    )
    assert update_other.status_code == 404
