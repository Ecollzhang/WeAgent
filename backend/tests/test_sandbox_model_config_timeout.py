from app.sandbox.host.client import OrchestratorClient
from app.sandbox.host.manager import DockerContainerManager


def test_model_config_update_uses_short_timeout(monkeypatch):
    calls = []

    def fake_request(self, method, path, body=None, timeout=None):
        calls.append({
            "method": method,
            "path": path,
            "body": body,
            "timeout": timeout,
        })
        return {"status": "ok"}

    monkeypatch.setenv("SANDBOX_CONFIG_UPDATE_TIMEOUT_SECONDS", "4")
    monkeypatch.setattr(OrchestratorClient, "_request", fake_request)

    result = OrchestratorClient().update_model_config({"model": "deepseek-v4-pro"})

    assert result == {"status": "ok"}
    assert calls == [
        {
            "method": "POST",
            "path": "/api/config/model",
            "body": {"model": "deepseek-v4-pro"},
            "timeout": 4,
        }
    ]


def test_health_check_uses_short_timeout(monkeypatch):
    calls = []

    def fake_request(self, method, path, body=None, timeout=None):
        calls.append({
            "method": method,
            "path": path,
            "timeout": timeout,
        })
        return {"status": "ok"}

    monkeypatch.setenv("SANDBOX_HEALTH_TIMEOUT_SECONDS", "2")
    monkeypatch.setattr(OrchestratorClient, "_request", fake_request)

    result = OrchestratorClient().health_check()

    assert result == {"status": "ok"}
    assert calls == [
        {
            "method": "GET",
            "path": "/api/health",
            "timeout": 2,
        }
    ]


def test_session_info_uses_short_timeout(monkeypatch):
    calls = []

    def fake_request(self, method, path, body=None, timeout=None):
        calls.append({
            "method": method,
            "path": path,
            "timeout": timeout,
        })
        return {"agents": []}

    monkeypatch.setenv("SANDBOX_SESSION_INFO_TIMEOUT_SECONDS", "3")
    monkeypatch.setattr(OrchestratorClient, "_request", fake_request)

    result = OrchestratorClient().get_session_info()

    assert result == {"agents": []}
    assert calls == [
        {
            "method": "GET",
            "path": "/api/session",
            "timeout": 3,
        }
    ]


def test_file_reads_use_short_timeout(monkeypatch):
    calls = []

    def fake_request(self, method, path, body=None, timeout=None):
        calls.append({
            "method": method,
            "path": path,
            "timeout": timeout,
        })
        return {"content": "{}"}

    monkeypatch.setenv("SANDBOX_FILE_TIMEOUT_SECONDS", "4")
    monkeypatch.setattr(OrchestratorClient, "_request", fake_request)

    result = OrchestratorClient().read_file("agent-1", "agents/A/.claude/settings.local.json")

    assert result == {"content": "{}"}
    assert calls == [
        {
            "method": "GET",
            "path": "/api/agents/agent-1/read_file?path=agents/A/.claude/settings.local.json",
            "timeout": 4,
        }
    ]


def test_recover_sessions_prefers_agent_labels_without_container_roundtrip(monkeypatch):
    class FakeContainer:
        id = "container-1234567890"
        labels = {
            "weagent.session_id": "session-1",
            "weagent.agents": '[{"agent_id":"agent-1","role":"Agent"}]',
        }
        attrs = {
            "NetworkSettings": {
                "Ports": {
                    "8080/tcp": [{"HostPort": "18080"}],
                },
            },
        }

    class FakeContainers:
        def list(self, **_kwargs):
            return [FakeContainer()]

    class FakeDocker:
        containers = FakeContainers()

    calls = []

    def fail_get_session_info(self):
        calls.append("get_session_info")
        raise RuntimeError("container roundtrip should not be needed")

    manager = DockerContainerManager()
    manager._docker = FakeDocker()
    monkeypatch.setattr(OrchestratorClient, "get_session_info", fail_get_session_info)

    manager.recover_sessions()

    recovered = manager.get_session("session-1")
    assert recovered is not None
    assert recovered.agents_config == [{"agent_id": "agent-1", "role": "Agent"}]
    assert calls == []
