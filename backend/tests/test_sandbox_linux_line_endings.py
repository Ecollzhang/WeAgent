from pathlib import Path


SANDBOX_BIN = Path(__file__).resolve().parents[1] / "app" / "sandbox" / "bin"


def test_sandbox_executables_use_linux_line_endings():
    for name in ("weagent-report", "weagent-service", "weagent-tools-mcp"):
        payload = (SANDBOX_BIN / name).read_bytes()
        assert payload.startswith(b"#!")
        assert b"\r\n" not in payload, f"{name} contains Windows CRLF line endings"
