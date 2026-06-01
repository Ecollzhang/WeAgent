import time
import unittest
from unittest.mock import patch

from flask import Flask

from app.sandbox.api import routes
from app.sandbox.host.manager import DockerContainerManager, SessionContainer


class FakeServiceClient:
    def get_service(self, service_id):
        return {"service": {"id": service_id, "port": 5173, "status": "running"}}


class FakeTokenManager:
    def __init__(self):
        self.calls = []

    def validate_service_token(self, session_id, service_id, token):
        return token == "valid-token" and session_id == "s1" and service_id == "svc_1"

    def proxy_service(self, session_id, service_id, path, method, headers, body, query_string):
        self.calls.append((session_id, service_id, path, method, query_string))
        return {
            "status_code": 200,
            "headers": [("Content-Type", "text/plain")],
            "body": b"ok",
        }

    def refresh_service_token(self, session_id, service_id, user_id=None, ttl_seconds=None):
        self.calls.append(("refresh", session_id, service_id, user_id, ttl_seconds))
        return {
            "status": "ok",
            "token": "new-token",
            "expires_at": "2026-05-30T00:00:00+00:00",
            "expires_in": ttl_seconds or 7200,
            "proxy_url": f"/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/?token=new-token",
        }


class SandboxServiceTokenStage4Test(unittest.TestCase):
    def test_manager_refresh_token_invalidates_previous_and_expires(self):
        manager = DockerContainerManager()
        session = SessionContainer("s1", "container-id", 1234, [])
        session.client = FakeServiceClient()
        manager._sessions["s1"] = session

        first = manager.refresh_service_token("s1", "svc_1", user_id="u1", ttl_seconds=60)
        second = manager.refresh_service_token("s1", "svc_1", user_id="u1", ttl_seconds=60)

        self.assertNotEqual(first["token"], second["token"])
        self.assertFalse(manager.validate_service_token("s1", "svc_1", first["token"]))
        self.assertTrue(manager.validate_service_token("s1", "svc_1", second["token"]))
        self.assertIn("?token=", second["proxy_url"])

        session.service_tokens["svc_1"]["expires_at_ts"] = time.time() - 1
        self.assertFalse(manager.validate_service_token("s1", "svc_1", second["token"]))

    def test_proxy_requires_valid_token_when_not_logged_in(self):
        fake = FakeTokenManager()
        routes._manager = fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        client = app.test_client()

        missing = client.get("/api/sandbox/sessions/s1/services/svc_1/proxy/")
        self.assertEqual(401, missing.status_code)

        invalid = client.get("/api/sandbox/sessions/s1/services/svc_1/proxy/?token=bad")
        self.assertEqual(401, invalid.status_code)

        valid = client.get("/api/sandbox/sessions/s1/services/svc_1/proxy/path?token=valid-token&x=1")
        self.assertEqual(200, valid.status_code)
        self.assertEqual(b"ok", valid.data)
        self.assertIn("weagent_preview_token=valid-token", valid.headers["Set-Cookie"])
        self.assertEqual(("s1", "svc_1", "path", "GET", "x=1"), fake.calls[0])
        routes._manager = None

    def test_refresh_token_api_requires_login_and_returns_token(self):
        fake = FakeTokenManager()
        routes._manager = fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        client = app.test_client()

        unauthenticated = client.post("/api/sandbox/sessions/s1/services/svc_1/token")
        self.assertEqual(401, unauthenticated.status_code)

        with patch("app.sandbox.api.routes._current_user_id_optional", return_value="u1"), \
             patch("app.sandbox.api.routes._session_access_allowed", return_value=True):
            response = client.post(
                "/api/sandbox/sessions/s1/services/svc_1/token",
                json={"ttl_seconds": 3600},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("new-token", response.get_json()["data"]["token"])
        self.assertIn(("refresh", "s1", "svc_1", "u1", 3600), fake.calls)
        routes._manager = None


if __name__ == "__main__":
    unittest.main()
