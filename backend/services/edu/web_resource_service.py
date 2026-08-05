"""Trusted adoption boundary for remote Education knowledge resources."""

import hashlib
from datetime import datetime

from .asset_service import create_database_asset
from .knowledge_service import create_knowledge_resource
from .resource_pipeline import SearchCandidate


class WebResourceAdoptionError(ValueError):
    def __init__(self, message, error_code="web_resource_adoption_failed", status_code=400):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


def adopt_web_knowledge_resource(*, course_id, actor, data, fetcher):
    data = data if isinstance(data, dict) else {}
    url = str(data.get("url") or "").strip()
    title = str(data.get("title") or "").strip()[:200]
    license_note = str(data.get("license_note") or "").strip()[:500]
    if not url.startswith(("https://", "http://")) or not title:
        raise WebResourceAdoptionError("valid url and title are required", "invalid_source")
    if data.get("teacher_confirmed_rights") is not True or not license_note:
        raise WebResourceAdoptionError(
            "teacher must confirm source rights and license note",
            "source_rights_confirmation_required",
        )
    if fetcher is None:
        raise WebResourceAdoptionError(
            "content fetcher is not configured", "content_fetcher_unconfigured", 503
        )
    candidate = SearchCandidate(
        url=url,
        title=title,
        excerpt=str(data.get("search_excerpt") or "")[:2000],
    )
    document = fetcher.fetch(candidate)
    text_content = str(document.get("text") or "").strip()
    if not text_content:
        raise WebResourceAdoptionError(
            "fetched page has no readable body", "web_resource_fetch_failed", 422
        )
    content = text_content.encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    asset = create_database_asset(
        course_id=course_id,
        lesson_id=None,
        actor_user_id=actor,
        content=content,
        original_filename=f"web-{digest[:12]}.txt",
        media_type="text/plain; charset=utf-8",
        title=title,
        purpose="knowledge_resource",
        visibility_scope="course_teacher",
    )
    return create_knowledge_resource(
        course_id,
        actor,
        {
            "asset_id": asset.id,
            "title": title,
            "resource_type": "web_reference",
            "visibility_scope": "course_teacher",
            "metadata": {
                "source_url": str(document.get("url") or url),
                "search_excerpt": candidate.excerpt,
                "fetched_at": datetime.utcnow().isoformat(),
                "author": str(document.get("author") or "")[:200],
                "site_name": str(document.get("site_name") or "")[:200],
                "license_note": license_note,
                "sha256": digest,
                "cleaner_version": "safe-html-v1",
            },
        },
    )
