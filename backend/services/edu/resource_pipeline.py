"""Education research pipeline contracts.

Search results contain discovery metadata and excerpts only.  Every selected
URL is fetched and cleaned before retrieval, and every retriever call receives
an immutable server-issued scope.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class SearchCandidate:
    url: str
    title: str
    excerpt: str = ""


@dataclass(frozen=True)
class ResourceScope:
    user_id: str
    domain: str = "edu"
    workspace_id: str | None = None
    course_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not str(self.user_id or "").strip():
            raise ValueError("Resource scope requires an authenticated user_id")
        if self.domain != "edu":
            raise ValueError("Education resource scope must use domain='edu'")


class SearchProvider(Protocol):
    def search(self, query: str, limit: int) -> Sequence[SearchCandidate]: ...


class ContentFetcher(Protocol):
    def fetch(self, candidate: SearchCandidate) -> dict[str, Any]: ...


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        documents: Sequence[dict[str, Any]],
        scope: ResourceScope,
        limit: int,
    ) -> list[dict[str, Any]]: ...


class Reranker(Protocol):
    def rerank(
        self,
        query: str,
        results: Sequence[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]: ...


class WikipediaSearchProvider:
    """Keyless public discovery provider with a stable JSON contract."""

    def __init__(self, language="zh", fetch=None):
        if fetch is None:
            from app.sandbox.container.tools import _http_fetch

            fetch = _http_fetch
        self.language = language if language in {"zh", "en"} else "zh"
        self._fetch = fetch

    def search(self, query: str, limit: int) -> Sequence[SearchCandidate]:
        params = urllib.parse.urlencode(
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": max(1, min(int(limit or 5), 20)),
                "prop": "info|extracts",
                "inprop": "url",
                "exintro": 1,
                "explaintext": 1,
                "exsentences": 2,
                "format": "json",
                "origin": "*",
            }
        )
        response = self._fetch(
            f"https://{self.language}.wikipedia.org/w/api.php?{params}",
            max_bytes=120_000,
        )
        if int(response.get("status_code") or 0) != 200:
            raise RuntimeError("Wikipedia search is unavailable")
        payload = json.loads(response.get("body_preview") or "{}")
        pages = ((payload.get("query") or {}).get("pages") or {}).values()
        return [
            SearchCandidate(
                url=str(page.get("fullurl") or "").strip(),
                title=str(page.get("title") or "").strip(),
                excerpt=str(page.get("extract") or "").strip(),
            )
            for page in pages
            if page.get("fullurl") and page.get("title")
        ][:limit]


class DuckDuckGoSearchProvider:
    """Fallback discovery provider using the public Instant Answer API."""

    def __init__(self, fetch=None):
        if fetch is None:
            from app.sandbox.container.tools import _http_fetch

            fetch = _http_fetch
        self._fetch = fetch

    def search(self, query: str, limit: int) -> Sequence[SearchCandidate]:
        params = urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        )
        response = self._fetch(
            f"https://api.duckduckgo.com/?{params}", max_bytes=120_000
        )
        if int(response.get("status_code") or 0) != 200:
            raise RuntimeError("Fallback search is unavailable")
        payload = json.loads(response.get("body_preview") or "{}")
        rows = []
        if payload.get("AbstractURL"):
            rows.append(
                SearchCandidate(
                    url=payload["AbstractURL"],
                    title=payload.get("Heading") or query,
                    excerpt=payload.get("AbstractText") or "",
                )
            )
        for topic in payload.get("RelatedTopics") or []:
            nested = topic.get("Topics") if isinstance(topic, dict) else None
            for item in (nested or [topic]):
                if isinstance(item, dict) and item.get("FirstURL"):
                    rows.append(
                        SearchCandidate(
                            url=item["FirstURL"],
                            title=(item.get("Text") or query).split(" - ", 1)[0],
                            excerpt=item.get("Text") or "",
                        )
                    )
        return rows[: max(1, min(int(limit or 5), 20))]


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)

    def handle_data(self, data):
        if not self._ignored_depth and data.strip():
            self.parts.append(data.strip())


class SafeWebPageReader:
    """Fetch a public text page through the sandbox SSRF-safe network seam."""

    def __init__(self, fetch=None, max_bytes: int = 120_000):
        if fetch is None:
            from app.sandbox.container.tools import _http_fetch

            fetch = _http_fetch
        self._fetch = fetch
        self._max_bytes = max_bytes

    def fetch(self, candidate: SearchCandidate) -> dict[str, Any]:
        response = self._fetch(candidate.url, max_bytes=self._max_bytes)
        status_code = int(response.get("status_code") or 0)
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(
                f"Content fetch failed with HTTP {status_code or 'unknown'}"
            )
        body = response.get("body_preview") or ""
        content_type = (response.get("content_type") or "").lower()
        if "html" in content_type:
            parser = _TextExtractor()
            parser.feed(body)
            text = "\n".join(parser.parts)
        else:
            text = body.strip()
        return {
            "url": response.get("url") or candidate.url,
            "title": candidate.title,
            "text": text,
            "search_excerpt": candidate.excerpt,
        }


class LexicalRetriever:
    """Small deterministic retrieval adapter for freshly fetched documents."""

    def retrieve(self, query, documents, scope, limit):
        terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
        rows = []
        for document in documents:
            haystack = f"{document.get('title', '')} {document.get('text', '')}".lower()
            hits = sum(1 for term in terms if term in haystack)
            rows.append({**document, "retrieval_score": hits / max(1, len(terms))})
        return sorted(rows, key=lambda row: row["retrieval_score"], reverse=True)[:limit]


class ScoreReranker:
    def rerank(self, query, results, limit):
        return [
            {**row, "score": round(float(row.get("retrieval_score") or 0), 4)}
            for row in results[:limit]
        ]


def build_public_resource_pipeline():
    """Build isolated provider adapters; business code never sees provider JSON."""

    return EducationResourcePipeline(
        search_providers=[
            WikipediaSearchProvider("zh"),
            WikipediaSearchProvider("en"),
            DuckDuckGoSearchProvider(),
        ],
        content_fetcher=SafeWebPageReader(),
        retriever=LexicalRetriever(),
        reranker=ScoreReranker(),
    )


class EducationResourcePipeline:
    def __init__(
        self,
        *,
        search_providers: Sequence[SearchProvider],
        content_fetcher: ContentFetcher,
        retriever: Retriever,
        reranker: Reranker,
    ):
        self.search_providers = tuple(search_providers)
        self.content_fetcher = content_fetcher
        self.retriever = retriever
        self.reranker = reranker

    def research(
        self,
        query: str,
        *,
        scope: ResourceScope,
        limit: int = 5,
    ) -> dict[str, Any]:
        query = str(query or "").strip()
        if not query:
            raise ValueError("query is required")
        limit = max(1, min(int(limit or 5), 20))
        diagnostics: list[dict[str, Any]] = []

        for provider_index, provider in enumerate(self.search_providers):
            try:
                candidates = list(provider.search(query, limit))
            except Exception as exc:
                diagnostics.append(
                    {
                        "stage": "search",
                        "provider_index": provider_index,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
            if not candidates:
                diagnostics.append(
                    {
                        "stage": "search",
                        "provider_index": provider_index,
                        "status": "empty",
                    }
                )
                continue

            documents = []
            for candidate in candidates[:limit]:
                try:
                    document = self.content_fetcher.fetch(candidate)
                except Exception as exc:
                    diagnostics.append(
                        {
                            "stage": "fetch",
                            "provider_index": provider_index,
                            "url": candidate.url,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
                    continue
                if (document.get("text") or "").strip():
                    documents.append(document)
            if not documents:
                continue

            retrieved = self.retriever.retrieve(
                query,
                documents,
                scope,
                limit,
            )
            ranked = self.reranker.rerank(query, retrieved, limit)
            return {
                "query": query,
                "provider_index": provider_index,
                "results": list(ranked)[:limit],
                "diagnostics": diagnostics,
                "fallback_exhausted": False,
            }

        return {
            "query": query,
            "provider_index": None,
            "results": [],
            "diagnostics": diagnostics,
            "fallback_exhausted": True,
        }
