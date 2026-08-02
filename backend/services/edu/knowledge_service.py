"""Application commands for the course Knowledge Center."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

from .access import active_membership
from .asset_models import EducationAsset
from .asset_service import asset_to_dict
from .extensions import db
from .knowledge_models import (
    AssessmentAnswerVersion,
    AssessmentItem,
    AssessmentItemVersion,
    AssessmentPaper,
    AssessmentPaperVersion,
    AssessmentStimulus,
    AssessmentStimulusVersion,
    KnowledgeResource,
)
from .models import Course


QUESTION_TYPES = {
    "single_choice",
    "multiple_choice",
    "true_false",
    "fill_blank",
    "short_answer",
    "writing",
}
DIFFICULTIES = {"easy", "medium", "hard"}
PAPER_PURPOSES = {"practice", "assignment", "mock_exam", "diagnostic"}
RESOURCE_VISIBILITY = {"course_teacher", "course_published"}
INGESTION_STATES = {"pending", "processing", "ready", "failed", "archived"}
STIMULUS_TYPES = {"reading_passage", "image_text", "reference_material"}
OPTION_LABEL = re.compile(r"^\s*(?:[A-Z]|[1-9]\d*)\s*[.)、:：]\s+")


@dataclass
class KnowledgeServiceError(Exception):
    message: str
    status_code: int = 400
    error_code: str = "invalid_knowledge_object"


def _checksum(value):
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _teacher(course_id, actor):
    membership = active_membership(course_id, actor, "teacher")
    if not membership:
        raise KnowledgeServiceError("course not found", 404, "course_not_found")
    return membership


def _member(course_id, actor):
    membership = active_membership(course_id, actor)
    if not membership:
        raise KnowledgeServiceError("course not found", 404, "course_not_found")
    return membership


def validate_question_payload(data):
    question_type = str(data.get("question_type") or "")
    if question_type not in QUESTION_TYPES:
        raise KnowledgeServiceError(
            "unsupported question_type",
            400,
            "invalid_question_type",
        )
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        raise KnowledgeServiceError(
            "prompt is required",
            400,
            "question_prompt_required",
        )
    difficulty = str(data.get("difficulty") or "")
    if difficulty not in DIFFICULTIES:
        raise KnowledgeServiceError(
            "difficulty must be easy, medium, or hard",
            400,
            "invalid_difficulty",
        )
    try:
        score = float(data.get("score"))
    except (TypeError, ValueError):
        raise KnowledgeServiceError(
            "score must be a positive number",
            400,
            "invalid_score",
        )
    if score <= 0 or score > 1000:
        raise KnowledgeServiceError(
            "score must be a positive number",
            400,
            "invalid_score",
        )
    options = data.get("options") or []
    if question_type in {"single_choice", "multiple_choice"}:
        if (
            not isinstance(options, list)
            or not 2 <= len(options) <= 12
            or not all(isinstance(option, str) and option.strip() for option in options)
        ):
            raise KnowledgeServiceError(
                "choice questions require 2 to 12 plain-text options",
                400,
                "invalid_options",
            )
        if any(OPTION_LABEL.match(option) for option in options):
            raise KnowledgeServiceError(
                "options must contain plain text without A/B or numeric labels",
                400,
                "non_canonical_options",
            )
        options = [option.strip() for option in options]
    elif options:
        raise KnowledgeServiceError(
            "non-choice questions must not contain options",
            400,
            "invalid_options",
        )
    knowledge_points = data.get("knowledge_points") or []
    if not isinstance(knowledge_points, list) or not all(
        isinstance(point, str) and point.strip() for point in knowledge_points
    ):
        raise KnowledgeServiceError(
            "knowledge_points must be a list of text values",
            400,
            "invalid_knowledge_points",
        )
    correct_answer = data.get("correct_answer")
    if correct_answer is None or correct_answer == "":
        raise KnowledgeServiceError(
            "correct_answer is required",
            400,
            "correct_answer_required",
        )
    if question_type == "single_choice":
        if (
            not isinstance(correct_answer, str)
            or len(correct_answer.strip()) != 1
            or not "A" <= correct_answer.strip().upper() <= chr(64 + len(options))
        ):
            raise KnowledgeServiceError(
                "single-choice answer must be an option letter",
                400,
                "invalid_correct_answer",
            )
        correct_answer = correct_answer.strip().upper()
    if question_type == "multiple_choice":
        if not isinstance(correct_answer, list) or not correct_answer:
            raise KnowledgeServiceError(
                "multiple-choice answer must be a list of option letters",
                400,
                "invalid_correct_answer",
            )
        correct_answer = [str(value).strip().upper() for value in correct_answer]
        allowed = {chr(65 + index) for index in range(len(options))}
        if len(set(correct_answer)) != len(correct_answer) or not set(correct_answer) <= allowed:
            raise KnowledgeServiceError(
                "multiple-choice answer contains invalid option letters",
                400,
                "invalid_correct_answer",
            )
    if question_type == "true_false":
        if not isinstance(correct_answer, bool):
            raise KnowledgeServiceError(
                "true-false answer must be a boolean",
                400,
                "invalid_correct_answer",
            )
    if question_type == "fill_blank":
        if not isinstance(correct_answer, (str, list)) or (
            isinstance(correct_answer, list)
            and not correct_answer
        ):
            raise KnowledgeServiceError(
                "fill-blank answer must be text or a non-empty list",
                400,
                "invalid_correct_answer",
            )
    stimulus_version_id = data.get("stimulus_version_id") or None
    stimulus_order = data.get("stimulus_order")
    if stimulus_version_id:
        stimulus_version = AssessmentStimulusVersion.query.filter_by(
            id=stimulus_version_id
        ).first()
        stimulus = (
            AssessmentStimulus.query.filter_by(id=stimulus_version.stimulus_id).first()
            if stimulus_version
            else None
        )
        if not stimulus or stimulus.course_id != data.get("course_id"):
            raise KnowledgeServiceError(
                "stimulus version is unavailable",
                400,
                "invalid_stimulus_version",
            )
        try:
            stimulus_order = int(stimulus_order)
        except (TypeError, ValueError):
            raise KnowledgeServiceError(
                "stimulus_order is required for grouped questions",
                400,
                "invalid_stimulus_order",
            )
        if stimulus_order < 1:
            raise KnowledgeServiceError(
                "stimulus_order must be positive",
                400,
                "invalid_stimulus_order",
            )
    else:
        stimulus_order = None
    return {
        "question_type": question_type,
        "prompt": prompt,
        "options": options,
        "difficulty": difficulty,
        "score": score,
        "knowledge_points": [point.strip() for point in knowledge_points],
        "grade_band": str(data.get("grade_band") or "").strip() or None,
        "source_context": data.get("source_context") or {},
        "correct_answer": correct_answer,
        "explanation": str(data.get("explanation") or "").strip(),
        "rubric": data.get("rubric") or {},
        "stimulus_version_id": stimulus_version_id,
        "stimulus_order": stimulus_order,
    }


def _create_question_version(item, actor, data):
    canonical = validate_question_payload({**data, "course_id": item.course_id})
    previous = (
        AssessmentItemVersion.query.filter_by(item_id=item.id)
        .order_by(AssessmentItemVersion.version_number.desc())
        .first()
    )
    version = AssessmentItemVersion(
        item_id=item.id,
        version_number=(previous.version_number + 1 if previous else 1),
        question_type=canonical["question_type"],
        prompt=canonical["prompt"],
        options=canonical["options"],
        difficulty=canonical["difficulty"],
        score=canonical["score"],
        knowledge_points=canonical["knowledge_points"],
        grade_band=canonical["grade_band"],
        source_context=canonical["source_context"],
        stimulus_version_id=canonical["stimulus_version_id"],
        stimulus_order=canonical["stimulus_order"],
        checksum=_checksum(
            {
                key: canonical[key]
                for key in (
                    "question_type",
                    "prompt",
                    "options",
                    "difficulty",
                    "score",
                    "knowledge_points",
                    "grade_band",
                    "source_context",
                    "stimulus_version_id",
                    "stimulus_order",
                )
            }
        ),
        created_by_user_id=actor,
    )
    db.session.add(version)
    db.session.flush()
    answer = AssessmentAnswerVersion(
        item_version_id=version.id,
        correct_answer=canonical["correct_answer"],
        explanation=canonical["explanation"],
        rubric=canonical["rubric"],
        created_by_user_id=actor,
    )
    db.session.add(answer)
    item.current_version_id = version.id
    return version


def create_question(course_id, actor, data, *, source_type="teacher"):
    _teacher(course_id, actor)
    title = str(data.get("title") or "").strip()
    if not title:
        raise KnowledgeServiceError(
            "title is required",
            400,
            "question_title_required",
        )
    item = AssessmentItem(
        course_id=course_id,
        title=title,
        owner_user_id=actor,
        source_type=source_type,
        source_agent_run_id=data.get("source_agent_run_id"),
    )
    db.session.add(item)
    db.session.flush()
    _create_question_version(item, actor, data)
    return item


def add_question_version(item, actor, data):
    _teacher(item.course_id, actor)
    if item.status == "archived":
        raise KnowledgeServiceError(
            "question is archived",
            409,
            "question_archived",
        )
    if data.get("title"):
        item.title = str(data["title"]).strip()
    _create_question_version(item, actor, data)
    return item


def publish_question(item, actor):
    _teacher(item.course_id, actor)
    if not item.current_version_id:
        raise KnowledgeServiceError(
            "question has no current version",
            409,
            "question_version_missing",
        )
    item.status = "published"
    item.published_version_id = item.current_version_id
    item.published_by = actor
    item.published_at = datetime.utcnow()
    return item


def question_version_to_dict(version, *, include_answer=False):
    payload = {
        "id": version.id,
        "item_id": version.item_id,
        "version_number": version.version_number,
        "question_type": version.question_type,
        "prompt": version.prompt,
        "options": version.options or [],
        "difficulty": version.difficulty,
        "score": version.score,
        "knowledge_points": version.knowledge_points or [],
        "grade_band": version.grade_band,
        "source_context": version.source_context or {},
        "stimulus_version_id": version.stimulus_version_id,
        "stimulus_order": version.stimulus_order,
        "checksum": version.checksum,
        "created_by_user_id": version.created_by_user_id,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }
    if include_answer:
        answer = AssessmentAnswerVersion.query.filter_by(
            item_version_id=version.id
        ).first()
        if answer:
            payload["answer"] = {
                "correct_answer": answer.correct_answer,
                "explanation": answer.explanation,
                "rubric": answer.rubric or {},
            }
    return payload


def question_to_dict(item, *, include_answer=False, use_published=False):
    selected_version_id = (
        item.published_version_id if use_published else item.current_version_id
    )
    version = AssessmentItemVersion.query.filter_by(
        id=selected_version_id
    ).first()
    return {
        "id": item.id,
        "course_id": item.course_id,
        "title": item.title,
        "source_type": item.source_type,
        "source_agent_run_id": item.source_agent_run_id,
        "status": item.status,
        "current_version_id": item.current_version_id,
        "published_version_id": item.published_version_id,
        "current_version": (
            question_version_to_dict(version, include_answer=include_answer)
            if version
            else None
        ),
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _stimulus_text(content):
    if not isinstance(content, dict):
        return ""
    paragraphs = content.get("paragraphs")
    if isinstance(paragraphs, list):
        return "\n".join(str(row).strip() for row in paragraphs if str(row).strip())
    return str(content.get("text") or "").strip()


def _create_stimulus_version(stimulus, actor, data):
    content = data.get("content")
    if not isinstance(content, dict) or not _stimulus_text(content):
        raise KnowledgeServiceError(
            "stimulus content is required", 400, "stimulus_content_required"
        )
    source_refs = data.get("source_refs") or []
    if not isinstance(source_refs, list):
        raise KnowledgeServiceError(
            "source_refs must be a list", 400, "invalid_source_refs"
        )
    previous = (
        AssessmentStimulusVersion.query.filter_by(stimulus_id=stimulus.id)
        .order_by(AssessmentStimulusVersion.version_number.desc())
        .first()
    )
    text_value = _stimulus_text(content)
    language = str(data.get("language") or "").strip() or None
    count = len(text_value.split()) if language == "en" else len(text_value.replace("\n", ""))
    version = AssessmentStimulusVersion(
        stimulus_id=stimulus.id,
        version_number=(previous.version_number + 1 if previous else 1),
        content_json=content,
        source_refs=source_refs,
        language=language,
        word_or_character_count=count,
        checksum=_checksum({"content": content, "source_refs": source_refs, "language": language}),
        created_by_user_id=actor,
    )
    db.session.add(version)
    db.session.flush()
    stimulus.current_version_id = version.id
    return version


def create_stimulus(course_id, actor, data):
    _teacher(course_id, actor)
    title = str(data.get("title") or "").strip()
    stimulus_type = str(data.get("stimulus_type") or "reading_passage")
    if not title:
        raise KnowledgeServiceError("title is required", 400, "stimulus_title_required")
    if stimulus_type not in STIMULUS_TYPES:
        raise KnowledgeServiceError(
            "unsupported stimulus_type", 400, "invalid_stimulus_type"
        )
    stimulus = AssessmentStimulus(
        course_id=course_id,
        title=title,
        stimulus_type=stimulus_type,
        owner_user_id=actor,
    )
    db.session.add(stimulus)
    db.session.flush()
    _create_stimulus_version(stimulus, actor, data)
    return stimulus


def add_stimulus_version(stimulus, actor, data):
    _teacher(stimulus.course_id, actor)
    if data.get("title"):
        stimulus.title = str(data["title"]).strip()
    _create_stimulus_version(stimulus, actor, data)
    return stimulus


def publish_stimulus(stimulus, actor):
    _teacher(stimulus.course_id, actor)
    if not stimulus.current_version_id:
        raise KnowledgeServiceError(
            "stimulus has no current version", 409, "stimulus_version_missing"
        )
    stimulus.status = "published"
    stimulus.published_version_id = stimulus.current_version_id
    stimulus.published_by = actor
    stimulus.published_at = datetime.utcnow()
    return stimulus


def stimulus_version_to_dict(version):
    return {
        "id": version.id,
        "stimulus_id": version.stimulus_id,
        "version_number": version.version_number,
        "content": version.content_json or {},
        "source_refs": version.source_refs or [],
        "language": version.language,
        "word_or_character_count": version.word_or_character_count,
        "checksum": version.checksum,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def stimulus_to_dict(stimulus, *, use_published=False):
    selected_version_id = (
        stimulus.published_version_id if use_published else stimulus.current_version_id
    )
    version = AssessmentStimulusVersion.query.filter_by(id=selected_version_id).first()
    return {
        "id": stimulus.id,
        "course_id": stimulus.course_id,
        "title": stimulus.title,
        "stimulus_type": stimulus.stimulus_type,
        "status": stimulus.status,
        "current_version_id": stimulus.current_version_id,
        "published_version_id": stimulus.published_version_id,
        "current_version": stimulus_version_to_dict(version) if version else None,
        "published_at": stimulus.published_at.isoformat() if stimulus.published_at else None,
    }


def compose_paper(course_id, actor, data):
    _teacher(course_id, actor)
    title = str(data.get("title") or "").strip()
    if not title:
        raise KnowledgeServiceError(
            "title is required",
            400,
            "paper_title_required",
        )
    purpose = str(data.get("purpose") or "practice")
    if purpose not in PAPER_PURPOSES:
        raise KnowledgeServiceError(
            "unsupported paper purpose",
            400,
            "invalid_paper_purpose",
        )
    item_ids = data.get("item_ids")
    if not isinstance(item_ids, list) or not item_ids:
        raise KnowledgeServiceError(
            "item_ids must contain at least one question",
            400,
            "paper_items_required",
        )
    if len(set(item_ids)) != len(item_ids):
        raise KnowledgeServiceError(
            "item_ids must not contain duplicates",
            400,
            "duplicate_paper_items",
        )
    items = {
        item.id: item
        for item in AssessmentItem.query.filter(
            AssessmentItem.course_id == course_id,
            AssessmentItem.id.in_(item_ids),
            AssessmentItem.status == "published",
        ).all()
    }
    if any(item_id not in items for item_id in item_ids):
        raise KnowledgeServiceError(
            "paper contains an unavailable question",
            400,
            "paper_item_unavailable",
        )
    versions = [
        AssessmentItemVersion.query.filter_by(
            id=items[item_id].published_version_id
        ).one()
        for item_id in item_ids
    ]
    try:
        duration = int(data.get("duration_minutes") or 0)
    except (TypeError, ValueError):
        duration = 0
    if not 1 <= duration <= 600:
        raise KnowledgeServiceError(
            "duration_minutes must be between 1 and 600",
            400,
            "invalid_paper_duration",
        )
    version_ids = [version.id for version in versions]
    total_score = sum(version.score for version in versions)
    sections = data.get("sections") or [
        {
            "title": "Questions",
            "item_version_ids": version_ids,
            "score": total_score,
        }
    ]
    paper = AssessmentPaper(
        course_id=course_id,
        title=title,
        purpose=purpose,
        owner_user_id=actor,
    )
    db.session.add(paper)
    db.session.flush()
    version = AssessmentPaperVersion(
        paper_id=paper.id,
        version_number=1,
        item_version_ids=version_ids,
        sections=sections,
        total_score=total_score,
        duration_minutes=duration,
        blueprint=data.get("blueprint") or {},
        checksum=_checksum(
            {
                "item_version_ids": version_ids,
                "sections": sections,
                "total_score": total_score,
                "duration_minutes": duration,
            }
        ),
        created_by_user_id=actor,
    )
    db.session.add(version)
    db.session.flush()
    paper.current_version_id = version.id
    return paper


def publish_paper(paper, actor):
    _teacher(paper.course_id, actor)
    if not paper.current_version_id:
        raise KnowledgeServiceError(
            "paper has no current version",
            409,
            "paper_version_missing",
        )
    paper.status = "published"
    paper.published_version_id = paper.current_version_id
    paper.published_by = actor
    paper.published_at = datetime.utcnow()
    return paper


def add_paper_version(paper, actor, data):
    _teacher(paper.course_id, actor)
    if paper.status == "archived":
        raise KnowledgeServiceError("paper is archived", 409, "paper_archived")
    item_ids = data.get("item_ids")
    if not isinstance(item_ids, list) or not item_ids:
        raise KnowledgeServiceError(
            "item_ids must contain at least one question", 400, "paper_items_required"
        )
    if len(set(item_ids)) != len(item_ids):
        raise KnowledgeServiceError(
            "item_ids must not contain duplicates", 400, "duplicate_paper_items"
        )
    items = {
        item.id: item
        for item in AssessmentItem.query.filter(
            AssessmentItem.course_id == paper.course_id,
            AssessmentItem.id.in_(item_ids),
            AssessmentItem.status == "published",
        ).all()
    }
    if any(not items.get(item_id) or not items[item_id].published_version_id for item_id in item_ids):
        raise KnowledgeServiceError(
            "paper contains an unavailable question", 400, "paper_item_unavailable"
        )
    versions = [
        AssessmentItemVersion.query.filter_by(
            id=items[item_id].published_version_id
        ).one()
        for item_id in item_ids
    ]
    try:
        duration = int(data.get("duration_minutes") or 0)
    except (TypeError, ValueError):
        duration = 0
    if not 1 <= duration <= 600:
        raise KnowledgeServiceError(
            "duration_minutes must be between 1 and 600", 400, "invalid_paper_duration"
        )
    if data.get("title"):
        paper.title = str(data["title"]).strip()
    if data.get("purpose"):
        purpose = str(data["purpose"])
        if purpose not in PAPER_PURPOSES:
            raise KnowledgeServiceError(
                "unsupported paper purpose", 400, "invalid_paper_purpose"
            )
        paper.purpose = purpose
    previous = (
        AssessmentPaperVersion.query.filter_by(paper_id=paper.id)
        .order_by(AssessmentPaperVersion.version_number.desc())
        .first()
    )
    version_ids = [version.id for version in versions]
    total_score = sum(version.score for version in versions)
    sections = data.get("sections") or [
        {"title": "Questions", "item_version_ids": version_ids, "score": total_score}
    ]
    version = AssessmentPaperVersion(
        paper_id=paper.id,
        version_number=(previous.version_number + 1 if previous else 1),
        item_version_ids=version_ids,
        sections=sections,
        total_score=total_score,
        duration_minutes=duration,
        blueprint=data.get("blueprint") or {},
        checksum=_checksum(
            {
                "item_version_ids": version_ids,
                "sections": sections,
                "total_score": total_score,
                "duration_minutes": duration,
            }
        ),
        created_by_user_id=actor,
    )
    db.session.add(version)
    db.session.flush()
    paper.current_version_id = version.id
    return paper


def paper_to_dict(paper, *, use_published=False):
    selected_version_id = (
        paper.published_version_id if use_published else paper.current_version_id
    )
    version = AssessmentPaperVersion.query.filter_by(
        id=selected_version_id
    ).first()
    return {
        "id": paper.id,
        "course_id": paper.course_id,
        "title": paper.title,
        "purpose": paper.purpose,
        "generated_for_user_id": paper.generated_for_user_id,
        "visibility_scope": paper.visibility_scope,
        "status": paper.status,
        "current_version_id": paper.current_version_id,
        "published_version_id": paper.published_version_id,
        "current_version": (
            {
                "id": version.id,
                "paper_id": version.paper_id,
                "version_number": version.version_number,
                "item_version_ids": version.item_version_ids or [],
                "sections": version.sections or [],
                "total_score": version.total_score,
                "duration_minutes": version.duration_minutes,
                "blueprint": version.blueprint or {},
                "checksum": version.checksum,
                "created_at": (
                    version.created_at.isoformat() if version.created_at else None
                ),
            }
            if version
            else None
        ),
        "published_at": paper.published_at.isoformat() if paper.published_at else None,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
    }


def paper_preview(paper, actor, *, mode="student", version_id=None):
    membership = _member(paper.course_id, actor)
    is_teacher = membership.role == "teacher"
    if mode not in {"student", "teacher"}:
        raise KnowledgeServiceError("unsupported preview mode", 400, "invalid_preview_mode")
    if mode == "teacher" and not is_teacher:
        raise KnowledgeServiceError("paper not found", 404, "paper_not_found")
    if not is_teacher and paper.status != "published":
        raise KnowledgeServiceError("paper not found", 404, "paper_not_found")
    selected_id = (
        version_id
        if is_teacher and version_id
        else paper.current_version_id
        if is_teacher
        else paper.published_version_id
    )
    version = AssessmentPaperVersion.query.filter_by(
        id=selected_id, paper_id=paper.id
    ).first()
    if not version:
        raise KnowledgeServiceError("paper version not found", 404, "paper_version_not_found")
    item_versions = {
        row.id: row
        for row in AssessmentItemVersion.query.filter(
            AssessmentItemVersion.id.in_(version.item_version_ids or [])
        ).all()
    }
    ordered = [item_versions[row_id] for row_id in version.item_version_ids or [] if row_id in item_versions]
    stimulus_ids = []
    for item_version in ordered:
        if item_version.stimulus_version_id and item_version.stimulus_version_id not in stimulus_ids:
            stimulus_ids.append(item_version.stimulus_version_id)
    stimulus_versions = {
        row.id: row
        for row in AssessmentStimulusVersion.query.filter(
            AssessmentStimulusVersion.id.in_(stimulus_ids)
        ).all()
    } if stimulus_ids else {}
    stimuli = []
    for stimulus_id in stimulus_ids:
        stimulus_version = stimulus_versions.get(stimulus_id)
        if not stimulus_version:
            continue
        stimulus = AssessmentStimulus.query.filter_by(id=stimulus_version.stimulus_id).first()
        stimuli.append(
            {
                **stimulus_version_to_dict(stimulus_version),
                "title": stimulus.title if stimulus else "Reading material",
                "stimulus_type": stimulus.stimulus_type if stimulus else "reading_passage",
            }
        )
    return {
        "paper": paper_to_dict(paper, use_published=not is_teacher),
        "version_id": version.id,
        "mode": mode,
        "stimuli": stimuli,
        "questions": [
            question_version_to_dict(row, include_answer=is_teacher and mode == "teacher")
            for row in ordered
        ],
        "sections": version.sections or [],
    }


def create_knowledge_resource(course_id, actor, data):
    _teacher(course_id, actor)
    asset = EducationAsset.query.filter_by(
        id=data.get("asset_id"),
        course_id=course_id,
        status="active",
    ).first()
    if not asset:
        raise KnowledgeServiceError(
            "asset not found",
            404,
            "asset_not_found",
        )
    title = str(data.get("title") or asset.title).strip()
    visibility = str(data.get("visibility_scope") or "course_teacher")
    if visibility not in RESOURCE_VISIBILITY:
        raise KnowledgeServiceError(
            "unsupported visibility_scope",
            400,
            "invalid_visibility",
        )
    if visibility == "course_published":
        asset.visibility_scope = "course_published"
    resource = KnowledgeResource(
        course_id=course_id,
        asset_id=asset.id,
        title=title,
        resource_type=str(data.get("resource_type") or "reference"),
        visibility_scope=visibility,
        ingestion_status="pending",
        rag_scope=(
            f"course/{course_id}/published"
            if visibility == "course_published"
            else f"course/{course_id}/teacher"
        ),
        metadata_json=data.get("metadata") or {},
        owner_user_id=actor,
    )
    db.session.add(resource)
    db.session.flush()
    return resource


def knowledge_resource_to_dict(resource):
    asset = EducationAsset.query.filter_by(id=resource.asset_id).first()
    return {
        "id": resource.id,
        "course_id": resource.course_id,
        "asset_id": resource.asset_id,
        "title": resource.title,
        "resource_type": resource.resource_type,
        "visibility_scope": resource.visibility_scope,
        "ingestion_status": resource.ingestion_status,
        "ingestion_error": resource.ingestion_error,
        "rag_scope": resource.rag_scope,
        "metadata": resource.metadata_json or {},
        "status": resource.status,
        "asset": asset_to_dict(asset) if asset else None,
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
        "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
    }
