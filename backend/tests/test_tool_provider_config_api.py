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
            username="provider-user",
            email="provider@example.com",
            password_hash="hash",
        )
        agent = Agent(
            id="agent-1",
            name="Provider Agent",
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


def test_provider_config_can_be_created_tested_enabled_and_bound(client_context):
    client, headers, _user, agent = client_context
    _seed_catalog()
    web_search = Capability.query.filter_by(source_ref="web_search").one()

    create_response = client.post(
        f"/api/capabilities/{web_search.id}/provider-configs",
        headers=headers,
        json={
            "profile_name": "Search API",
            "provider_type": "http",
            "config": {
                "endpoint": "https://search.example.test/query",
            },
            "secret_refs": ["SEARCH_API_KEY"],
        },
    )

    assert create_response.status_code == 201
    config = create_response.get_json()["data"]
    assert config["profile_name"] == "Search API"
    assert config["provider_type"] == "http"
    assert config["status"] == "draft"
    assert config["last_test_status"] == ""
    assert config["secret_refs"] == ["SEARCH_API_KEY"]

    list_response = client.get(
        f"/api/capabilities/{web_search.id}/provider-configs",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert len(list_response.get_json()["data"]) == 1

    test_response = client.post(
        f"/api/capabilities/{web_search.id}/provider-configs/{config['id']}/test",
        headers=headers,
    )
    assert test_response.status_code == 200
    tested = test_response.get_json()["data"]
    assert tested["status"] == "draft"
    assert tested["last_test_status"] == "passed"
    assert tested["last_test_error"] == ""

    before_enable = client.get("/api/capabilities?type=tool", headers=headers)
    web_search_before = next(
        item for item in before_enable.get_json()["data"]
        if item["source_ref"] == "web_search"
    )
    assert web_search_before["configured_profiles_count"] == 0
    assert web_search_before["bindable"] is False

    enable_response = client.post(
        f"/api/capabilities/{web_search.id}/provider-configs/{config['id']}/enable",
        headers=headers,
    )
    assert enable_response.status_code == 200
    enabled = enable_response.get_json()["data"]
    assert enabled["status"] == "valid"

    after_enable = client.get("/api/capabilities?type=tool", headers=headers)
    web_search_after = next(
        item for item in after_enable.get_json()["data"]
        if item["source_ref"] == "web_search"
    )
    assert web_search_after["configured_profiles_count"] == 1
    assert web_search_after["bindable"] is True

    bind_response = client.post(
        f"/api/agents/{agent.id}/capabilities",
        headers=headers,
        json={
            "capability_version_id": web_search.latest_version_id,
            "granted_permissions": ["network"],
        },
    )
    assert bind_response.status_code == 201

    disable_response = client.post(
        f"/api/capabilities/{web_search.id}/provider-configs/{config['id']}/disable",
        headers=headers,
    )
    assert disable_response.status_code == 200
    assert disable_response.get_json()["data"]["status"] == "disabled"

    after_disable = client.get("/api/capabilities?type=tool", headers=headers)
    web_search_disabled = next(
        item for item in after_disable.get_json()["data"]
        if item["source_ref"] == "web_search"
    )
    assert web_search_disabled["configured_profiles_count"] == 0
    assert web_search_disabled["bindable"] is False


def test_provider_config_requires_supported_provider_and_successful_test(client_context):
    client, headers, _user, _agent = client_context
    _seed_catalog()
    database_query = Capability.query.filter_by(source_ref="database_query").one()

    unsupported_response = client.post(
        f"/api/capabilities/{database_query.id}/provider-configs",
        headers=headers,
        json={
            "profile_name": "Wrong Provider",
            "provider_type": "http",
            "config": {"endpoint": "https://db.example.test"},
        },
    )
    assert unsupported_response.status_code == 400
    assert "provider_type is not supported" in unsupported_response.get_json()["message"]

    create_response = client.post(
        f"/api/capabilities/{database_query.id}/provider-configs",
        headers=headers,
        json={
            "profile_name": "Readonly DB",
            "provider_type": "database",
            "config": {
                "driver": "mysql",
                "connection_alias": "MYSQL_ANALYTICS",
                "readonly": False,
            },
            "secret_refs": ["MYSQL_ANALYTICS"],
        },
    )
    assert create_response.status_code == 201
    config = create_response.get_json()["data"]

    enable_before_test = client.post(
        f"/api/capabilities/{database_query.id}/provider-configs/{config['id']}/enable",
        headers=headers,
    )
    assert enable_before_test.status_code == 400
    assert "must pass testing before enable" in enable_before_test.get_json()["message"]

    test_response = client.post(
        f"/api/capabilities/{database_query.id}/provider-configs/{config['id']}/test",
        headers=headers,
    )
    assert test_response.status_code == 400
    failed = test_response.get_json()["data"]
    assert failed["status"] == "invalid"
    assert failed["last_test_status"] == "failed"
    assert "readonly must be true" in failed["last_test_error"]
