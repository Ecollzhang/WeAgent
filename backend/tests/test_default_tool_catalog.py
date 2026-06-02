import pytest
from flask_jwt_extended import create_access_token

from app import create_app, db
from app.models.agent import Agent
from app.models.capability import Capability
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
        agent = Agent(
            id="agent-1",
            name="Catalog Agent",
            agent_type="custom",
            adapter_name="claude",
            user_id=user.id,
            created_by=user.id,
        )
        db.session.add_all([user, agent])
        db.session.commit()
        token = create_access_token(identity=user.id)
        yield app.test_client(), {"Authorization": f"Bearer {token}"}, user, agent
        db.session.remove()
        db.drop_all()


def _seed_catalog():
    toolset_category_service.seed_builtin_categories()
    capability_service.seed_builtin_tool_capabilities()


def test_default_tool_catalog_hides_code_generator_and_marks_configurable_tools(client_context):
    client, headers, _user, _agent = client_context
    _seed_catalog()

    list_response = client.get("/api/capabilities?type=tool", headers=headers)

    assert list_response.status_code == 200
    tools = {item["source_ref"]: item for item in list_response.get_json()["data"]}

    assert "code_generator" not in tools
    assert tools["code_search"]["bindable"] is True
    assert tools["code_search"]["visibility"] == "visible"
    assert tools["code_search"]["latest_version"]["manifest"]["ui"]["status"] == "implemented"

    for source_ref in (
        "web_search",
        "image_analysis",
        "image_generation",
        "database_query",
    ):
        tool = tools[source_ref]
        manifest = tool["latest_version"]["manifest"]
        assert tool["visibility"] == "visible"
        assert tool["configurable"] is True
        assert tool["bindable"] is False
        assert tool["configured_profiles_count"] == 0
        assert manifest["ui"]["status"] == "requires_config"
        assert manifest["ui"]["configurable"] is True

    categories_response = client.get("/api/toolsets/categories", headers=headers)
    assert categories_response.status_code == 200
    categories = categories_response.get_json()["data"]
    code_category = next(item for item in categories if item["id"] == "tool_code")
    assert code_category["counts"]["tool"] == 2


def test_hidden_and_unconfigured_tools_cannot_be_bound_to_agent(client_context):
    client, headers, _user, agent = client_context
    _seed_catalog()

    hidden = Capability.query.filter_by(source_ref="code_generator").one()
    hidden_version_id = hidden.latest_version_id
    hidden_response = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={
            "capability_version_id": hidden_version_id,
            "granted_permissions": [],
        },
    )

    assert hidden_response.status_code == 400
    assert "not bindable" in hidden_response.get_json()["message"]

    unconfigured = Capability.query.filter_by(source_ref="web_search").one()
    unconfigured_response = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={
            "capability_version_id": unconfigured.latest_version_id,
            "granted_permissions": ["network"],
        },
    )

    assert unconfigured_response.status_code == 400
    assert "requires configuration" in unconfigured_response.get_json()["message"]

    implemented = Capability.query.filter_by(source_ref="code_search").one()
    accepted = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={
            "capability_version_id": implemented.latest_version_id,
            "granted_permissions": ["read_workspace"],
        },
    )

    assert accepted.status_code == 201
