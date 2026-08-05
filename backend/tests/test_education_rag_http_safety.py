import io
from unittest.mock import patch

import pytest

from app.sandbox.container import tools as container_tools


class _Response:
    status = 200
    headers = {"content-type": "text/html; charset=utf-8"}

    def __init__(self, body=b"<main>lesson</main>", url="https://example.edu/lesson"):
        self._body = io.BytesIO(body)
        self._url = url

    def read(self, size=-1):
        return self._body.read(size)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_http_fetch_rejects_loopback_before_network_access():
    with patch("urllib.request.OpenerDirector.open") as network:
        with pytest.raises(ValueError, match="private|loopback|reserved"):
            container_tools._http_fetch("http://127.0.0.1/admin")
    network.assert_not_called()


def test_http_fetch_rejects_hostname_resolving_to_private_network():
    private_dns = [(2, 1, 6, "", ("10.0.0.7", 443))]
    with (
        patch("socket.getaddrinfo", return_value=private_dns),
        patch("urllib.request.OpenerDirector.open") as network,
    ):
        with pytest.raises(ValueError, match="private|loopback|reserved"):
            container_tools._http_fetch("https://school.example/lesson")
    network.assert_not_called()


def test_http_fetch_rejects_non_text_response():
    public_dns = [(2, 1, 6, "", ("93.184.216.34", 443))]
    response = _Response()
    response.headers = {"content-type": "application/octet-stream"}
    with (
        patch("socket.getaddrinfo", return_value=public_dns),
        patch("urllib.request.OpenerDirector.open", return_value=response),
    ):
        with pytest.raises(ValueError, match="content type"):
            container_tools._http_fetch("https://example.edu/archive.bin")


def test_http_fetch_returns_bounded_text_and_final_url():
    public_dns = [(2, 1, 6, "", ("93.184.216.34", 443))]
    response = _Response(body=b"x" * 151, url="https://example.edu/final")
    with (
        patch("socket.getaddrinfo", return_value=public_dns),
        patch("urllib.request.OpenerDirector.open", return_value=response),
    ):
        result = container_tools._http_fetch(
            "https://example.edu/start?secret=1",
            max_bytes=100,
        )

    assert result["url"] == "https://example.edu/final"
    assert result["body_preview"] == "x" * 100
    assert result["truncated"] is True
