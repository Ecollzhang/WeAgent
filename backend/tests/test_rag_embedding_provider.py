import importlib.util
import math
import sys
from pathlib import Path
from types import SimpleNamespace


RAG_ROOT = Path(__file__).resolve().parents[1] / "services" / "rag"
EMBEDDING_SERVICE_PATH = RAG_ROOT / "services" / "embedding_service.py"


def _load_embedding_module(monkeypatch, config):
    monkeypatch.setitem(
        sys.modules,
        "config",
        SimpleNamespace(Config=config),
    )
    spec = importlib.util.spec_from_file_location(
        "rag_embedding_service_under_test",
        EMBEDDING_SERVICE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cosine(left, right):
    return sum(a * b for a, b in zip(left, right)) / (
        math.sqrt(sum(value * value for value in left))
        * math.sqrt(sum(value * value for value in right))
    )


def test_local_embedding_is_deterministic_and_retrieves_related_text(monkeypatch):
    config = SimpleNamespace(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="local-hash-embedding-v1",
        EMBEDDING_API_KEY="",
        EMBEDDING_BASE_URL="",
    )
    module = _load_embedding_module(monkeypatch, config)
    service = module.EmbeddingService()

    query = service.embed_single("AI risk management functions govern map measure manage")
    related = service.embed_single(
        "The AI RMF Core contains four functions: GOVERN, MAP, MEASURE, and MANAGE."
    )
    unrelated = service.embed_single(
        "A classroom writing lesson uses peer feedback and a final reflection."
    )

    assert len(query) == 768
    assert query == service.embed_single(
        "AI risk management functions govern map measure manage"
    )
    assert _cosine(query, related) > _cosine(query, unrelated)


def test_local_embedding_health_check_is_real_and_self_contained(monkeypatch):
    config = SimpleNamespace(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="local-hash-embedding-v1",
        EMBEDDING_API_KEY="",
        EMBEDDING_BASE_URL="",
    )
    module = _load_embedding_module(monkeypatch, config)

    status = module.EmbeddingService().health_status()

    assert status == {
        "healthy": True,
        "provider": "local",
        "model": "local-hash-embedding-v1",
        "dimension": 768,
    }


def test_ollama_health_check_reports_unreachable_provider(monkeypatch):
    config = SimpleNamespace(
        EMBEDDING_PROVIDER="ollama",
        EMBEDDING_MODEL="nomic-embed-text:latest",
        EMBEDDING_API_KEY="",
        EMBEDDING_BASE_URL="http://localhost:11434",
    )
    module = _load_embedding_module(monkeypatch, config)

    def fail_request(*args, **kwargs):
        raise module.requests.ConnectionError("connection refused")

    monkeypatch.setattr(module.requests, "get", fail_request)
    status = module.EmbeddingService().health_status()

    assert status["healthy"] is False
    assert status["provider"] == "ollama"
    assert "connection refused" in status["error"]
