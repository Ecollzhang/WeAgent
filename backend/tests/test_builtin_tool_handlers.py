import base64
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.sandbox.container import tools as container_tools


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
    "WjR9awAAAABJRU5ErkJggg=="
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def _workspace():
    base = Path.cwd() / ".pytest-tmp"
    base.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=base)


def _registry(workspace_path: Path):
    registry = container_tools.ToolRegistry(workspace_root=str(workspace_path))
    container_tools.register_builtin_tools(registry)
    return registry


def test_representative_builtin_handlers_cover_functional_categories():
    with _workspace() as workspace:
        root = Path(workspace)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text(
            "API_KEY = 'demo'\n# TODO: tighten validation\nprint('needle')\n",
            encoding="utf-8",
        )
        (root / "notes.md").write_text("# Notes\nhello document\n", encoding="utf-8")
        (root / "data.csv").write_text("name,score\nalice,1\nbob,\n", encoding="utf-8")
        (root / "image.png").write_bytes(base64.b64decode(PNG_1X1))

        registry = _registry(root)
        tool_names = {item["name"] for item in registry.list_tools()}
        assert {
            "code_search",
            "document_text_extract",
            "csv_profile",
            "image_info",
            "run_command_safe",
        }.issubset(tool_names)

        search = registry.execute("code_search", query="needle", path="src")
        assert search["matches"][0]["path"] == "src/app.py"

        review = registry.execute("code_review_scan", path="src/app.py")
        assert {item["rule"] for item in review["findings"]}.issuperset({"todo", "secret_like"})

        document = registry.execute("document_text_extract", path="notes.md")
        assert document["text"].startswith("# Notes")

        profile = registry.execute("csv_profile", path="data.csv")
        assert profile["columns"] == ["name", "score"]
        assert profile["row_count"] == 2

        image = registry.execute("image_info", path="image.png")
        assert image["format"] == "PNG"
        assert image["width"] == 1
        assert image["height"] == 1

        command = registry.execute("run_command_safe", command="echo hello")
        assert command["exit_code"] == 0
        assert "hello" in command["stdout"]


def test_http_fetch_uses_network_tool_without_external_internet():
    with _workspace() as workspace:
        root = Path(workspace)
        (root / "index.txt").write_text("hello web", encoding="utf-8")
        previous_cwd = os.getcwd()
        os.chdir(root)
        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            registry = _registry(root)
            with patch.dict(
                os.environ,
                {"WEAGENT_HTTP_FETCH_ALLOW_PRIVATE": "1"},
            ):
                result = registry.execute(
                    "http_fetch",
                    url=f"http://127.0.0.1:{server.server_port}/index.txt",
                )
            assert result["status_code"] == 200
            assert result["body_preview"] == "hello web"
        finally:
            server.shutdown()
            server.server_close()
            os.chdir(previous_cwd)
