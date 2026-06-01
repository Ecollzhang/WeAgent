import importlib
import time
import unittest
from unittest.mock import patch

from flask import Flask

from app.sandbox.api import routes
from app.sandbox.host.client import OrchestratorClient
from app.sandbox.host import client as host_client


class FakeWebSocket:
    def __init__(self, incoming=None):
        self.incoming = list(incoming or [])
        self.sent = []
        self.closed = False

    def receive(self):
        if self.incoming:
            return self.incoming.pop(0)
        for _ in range(20):
            if self.closed:
                break
            time.sleep(0.001)
        raise host_client.simple_websocket.ConnectionClosed()

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True


class FakeWebSocketManager:
    def __init__(self):
        self.calls = []

    def validate_service_token(self, session_id, service_id, token):
        return session_id == "s1" and service_id == "svc_1" and token == "preview-token"

    def proxy_service_websocket(self, session_id, service_id, path, client_ws, headers, query_string):
        self.calls.append((session_id, service_id, path, client_ws, headers, query_string))
        return {"status": "closed"}


class SandboxServiceWebSocketStage7Test(unittest.TestCase):
    def test_host_client_websocket_proxy_builds_ws_url_and_relays_messages(self):
        client = OrchestratorClient("localhost", 1234)
        browser_ws = FakeWebSocket(["from-browser"])
        upstream_ws = FakeWebSocket(["from-service"])
        connect_calls = []

        def fake_connect(url, headers=None):
            connect_calls.append((url, headers))
            return upstream_ws

        with patch.object(host_client.simple_websocket.Client, "connect", side_effect=fake_connect):
            result = client.proxy_service_websocket(
                service_id="svc 1",
                path="@vite/client",
                client_ws=browser_ws,
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Key": "handshake",
                    "X-Test": "yes",
                },
                query_string="v=1",
            )

        self.assertEqual({"status": "closed"}, result)
        self.assertEqual("ws://localhost:1234/api/services/svc%201/proxy/@vite/client?v=1", connect_calls[0][0])
        self.assertEqual({"X-Test": "yes"}, connect_calls[0][1])
        self.assertEqual(["from-browser"], upstream_ws.sent)
        self.assertEqual(["from-service"], browser_ws.sent)
        self.assertTrue(browser_ws.closed)
        self.assertTrue(upstream_ws.closed)

    def test_host_route_delegates_websocket_upgrade_to_manager(self):
        fake = FakeWebSocketManager()
        routes._manager = fake
        app = Flask(__name__)
        app.register_blueprint(routes.sandbox_bp, url_prefix="/api/sandbox")
        client = app.test_client()
        browser_ws = FakeWebSocket()

        with app.test_request_context(
                "/api/sandbox/sessions/s1/services/svc_1/proxy/@vite/client?token=preview-token&v=1",
                headers={"Upgrade": "websocket", "Connection": "Upgrade"},
        ), patch.object(routes.simple_websocket.Server, "accept", return_value=browser_ws):
            response = routes.proxy_service("s1", "svc_1", "@vite/client")

        self.assertEqual("", response)
        self.assertEqual("s1", fake.calls[0][0])
        self.assertEqual("svc_1", fake.calls[0][1])
        self.assertEqual("@vite/client", fake.calls[0][2])
        self.assertIs(browser_ws, fake.calls[0][3])
        self.assertEqual("v=1", fake.calls[0][5])
        routes._manager = None

    def test_container_route_proxies_websocket_to_local_service_port(self):
        stage3 = importlib.import_module("tests.test_sandbox_service_proxy_stage3")
        server = stage3.SandboxServiceProxyStage3Test._import_container_server()
        browser_ws = FakeWebSocket(["browser"])
        service_ws = FakeWebSocket(["service"])
        connect_calls = []

        def fake_connect(url, headers=None):
            connect_calls.append((url, headers))
            return service_ws

        with server.app.test_request_context(
                "/api/services/svc_1/proxy/@vite/client?v=1",
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Key": "handshake",
                    "X-Test": "yes",
                },
        ), patch.object(server.simple_websocket.Server, "accept", return_value=browser_ws), \
             patch.object(server.simple_websocket.Client, "connect", side_effect=fake_connect):
            response = server.api_proxy_preview_service("svc_1", "@vite/client")

        self.assertEqual("", response)
        self.assertEqual("ws://127.0.0.1:5173/@vite/client?v=1", connect_calls[0][0])
        self.assertEqual({"X-Test": "yes"}, connect_calls[0][1])
        self.assertEqual(["browser"], service_ws.sent)
        self.assertEqual(["service"], browser_ws.sent)


if __name__ == "__main__":
    unittest.main()
