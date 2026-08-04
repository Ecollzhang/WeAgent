import json

import pytest

from app.sandbox.container.tools import ToolRegistry, _call_service_api, _list_services


def test_list_services_returns_only_current_agent_view(monkeypatch):
    monkeypatch.setenv(
        "SERVICE_REGISTRY",
        json.dumps(
            {
                "edu": "http://edu:5102",
                "rag": "http://rag:5104",
                "rd": "http://rd:5101",
            }
        ),
    )
    monkeypatch.setenv(
        "AGENT_SERVICE_VIEWS",
        json.dumps({"_edu_8": ["edu", "rag"], "_edu_9": ["edu"]}),
    )

    assert set(_list_services(_weagent_agent_id="_edu_8")["services"]) == {
        "edu",
        "rag",
    }
    assert set(_list_services(_weagent_agent_id="_edu_9")["services"]) == {"edu"}


def test_call_service_api_rejects_borrowed_and_education_write_services(monkeypatch):
    monkeypatch.setenv(
        "SERVICE_REGISTRY",
        json.dumps(
            {
                "edu": "http://edu:5102",
                "rag": "http://rag:5104",
                "rd": "http://rd:5101",
            }
        ),
    )
    monkeypatch.setenv(
        "AGENT_SERVICE_VIEWS",
        json.dumps({"_edu_9": ["edu"]}),
    )

    borrowed = _call_service_api(
        "rag",
        path="/api/rag/spec",
        _weagent_agent_id="_edu_9",
    )
    write = _call_service_api(
        "edu",
        method="POST",
        path="/api/edu/lessons",
        body={"title": "forbidden"},
        _weagent_agent_id="_edu_9",
    )

    assert borrowed["status"] == "error"
    assert borrowed["error_code"] == "service_not_allowed"
    assert write["status"] == "error"
    assert write["error_code"] == "protected_action_required"


def test_tool_registry_passes_server_trusted_agent_identity(monkeypatch):
    monkeypatch.setenv(
        "SERVICE_REGISTRY",
        json.dumps({"edu": "http://edu:5102", "rag": "http://rag:5104"}),
    )
    monkeypatch.setenv(
        "AGENT_SERVICE_VIEWS",
        json.dumps({"reviewer": ["edu"]}),
    )
    registry = ToolRegistry()
    registry.register("list_services", _list_services)

    result = json.loads(
        registry.call_from_agent(
            "reviewer",
            "list_services",
            {"_weagent_agent_id": "researcher"},
        )
    )

    assert result["status"] == "ok"
    assert set(result["result"]["services"]) == {"edu"}
