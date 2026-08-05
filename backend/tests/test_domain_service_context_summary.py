import requests

from app.services import conversation_service as conversation_service_module


class _SpecResponse:
    status_code = 200

    @staticmethod
    def json():
        return {
            "service": "rd",
            "capabilities": [
                {"name": "项目管理", "description": "创建和管理研发项目"},
            ],
            "popular_endpoints": [
                {
                    "method": "GET",
                    "path": "/api/rd/projects",
                    "description": "获取项目列表",
                },
            ],
        }


def test_service_context_falls_back_to_host_local_spec_endpoint(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if "host.docker.internal" in url:
            raise requests.ConnectionError("host alias is unavailable")
        return _SpecResponse()

    conversation_service_module._spec_cache.clear()
    monkeypatch.setattr(requests, "get", fake_get)

    summary = conversation_service_module._build_services_summary(["rd"])

    assert calls == [
        "http://host.docker.internal:5101/api/rd/spec",
        "http://127.0.0.1:5101/api/rd/spec",
    ]
    assert "项目管理" in summary
    assert "/api/rd/projects" in summary
    assert "http://host.docker.internal:5101/api/rd/projects" in summary
