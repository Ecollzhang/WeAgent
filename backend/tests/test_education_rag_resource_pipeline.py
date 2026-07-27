import importlib.util
from pathlib import Path


EDU_SERVICE = Path(__file__).resolve().parents[1] / "services" / "edu"
SPEC = importlib.util.spec_from_file_location(
    "education_resource_pipeline",
    EDU_SERVICE / "resource_pipeline.py",
)
resource_pipeline = importlib.util.module_from_spec(SPEC)
sys_modules = __import__("sys").modules
sys_modules[SPEC.name] = resource_pipeline
SPEC.loader.exec_module(resource_pipeline)
EducationResourcePipeline = resource_pipeline.EducationResourcePipeline
ResourceScope = resource_pipeline.ResourceScope
SearchCandidate = resource_pipeline.SearchCandidate
SafeWebPageReader = resource_pipeline.SafeWebPageReader


class _BrokenSearch:
    def search(self, query, limit):
        raise TimeoutError("primary unavailable")


class _FallbackSearch:
    def search(self, query, limit):
        return [
            SearchCandidate(
                url="https://example.edu/a",
                title="A lesson",
                excerpt="Search excerpt only",
            )
        ]


class _Reader:
    def fetch(self, candidate):
        assert candidate.excerpt == "Search excerpt only"
        return {
            "url": candidate.url,
            "title": candidate.title,
            "text": "Full cleaned lesson body",
        }


class _Retriever:
    def __init__(self):
        self.scope = None

    def retrieve(self, query, documents, scope, limit):
        self.scope = scope
        return [{"content": documents[0]["text"], "score": 0.7}]


class _Reranker:
    def rerank(self, query, results, limit):
        return [{**results[0], "score": 0.9}]


def test_pipeline_falls_back_fetches_body_and_enforces_retrieval_scope():
    retriever = _Retriever()
    pipeline = EducationResourcePipeline(
        search_providers=[_BrokenSearch(), _FallbackSearch()],
        content_fetcher=_Reader(),
        retriever=retriever,
        reranker=_Reranker(),
    )
    scope = ResourceScope(
        user_id="teacher-1",
        domain="edu",
        workspace_id="workspace-1",
        course_ids=("course-1",),
    )

    result = pipeline.research("reading lesson", scope=scope, limit=3)

    assert result["provider_index"] == 1
    assert result["results"][0]["content"] == "Full cleaned lesson body"
    assert result["results"][0]["score"] == 0.9
    assert retriever.scope == scope


def test_pipeline_returns_diagnostic_when_search_and_fetch_fallbacks_are_empty():
    class _EmptySearch:
        def search(self, query, limit):
            return []

    pipeline = EducationResourcePipeline(
        search_providers=[_BrokenSearch(), _EmptySearch()],
        content_fetcher=_Reader(),
        retriever=_Retriever(),
        reranker=_Reranker(),
    )

    result = pipeline.research(
        "missing",
        scope=ResourceScope(user_id="student-1", domain="edu"),
    )

    assert result["results"] == []
    assert result["fallback_exhausted"] is True
    assert len(result["diagnostics"]) == 2


def test_web_page_reader_rejects_http_error_pages_as_content():
    reader = SafeWebPageReader(
        fetch=lambda url, max_bytes: {
            "url": url,
            "status_code": 404,
            "content_type": "text/html",
            "body_preview": "<h1>Not found</h1>",
        }
    )

    import pytest

    with pytest.raises(RuntimeError, match="HTTP 404"):
        reader.fetch(SearchCandidate("https://example.edu/missing", "Missing"))
