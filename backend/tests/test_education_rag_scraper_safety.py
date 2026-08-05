import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest


SCRAPER_PATH = (
    Path(__file__).resolve().parents[1] / "services" / "rag" / "utils" / "scraper.py"
)
SPEC = importlib.util.spec_from_file_location("education_rag_scraper", SCRAPER_PATH)
scraper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scraper)


def test_rag_scraper_rejects_private_address_before_request():
    with patch("requests.Session.get") as request:
        with pytest.raises(ValueError, match="private|loopback|reserved"):
            scraper.scrape_url("http://127.0.0.1/internal")
    request.assert_not_called()


def test_rag_scraper_rejects_private_dns_target():
    private_dns = [(2, 1, 6, "", ("169.254.169.254", 80))]
    with (
        patch("socket.getaddrinfo", return_value=private_dns),
        patch("requests.Session.get") as request,
    ):
        with pytest.raises(ValueError, match="private|loopback|reserved"):
            scraper.fetch_url("http://metadata.example/latest")
    request.assert_not_called()
