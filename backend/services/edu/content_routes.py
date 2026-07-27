"""Membership-scoped Education content and teaching-loop API."""

import hashlib
import json
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .content_models import (
    Assignment,
    CourseUnit,
    EducationContent,
    EducationContentVersion,
    Feedback,
    LearningEvent,
    Lesson,
    LessonActivity,
    PublishedLessonVersion,
    Submission,
    SubmissionVersion,
)
from .extensions import db
from .models import Course, CourseMembership


education_content_api = Blueprint("education_content_api", __name__)

SUBJECT_GENRES = {
    "high_school_english": {
        "narrative", "expository", "argumentative", "practical",
        "news", "biography", "literary",
    },
    "primary_chinese": {
        "narrative", "scenery", "expository", "fairy_tale", "fable",
        "poetry", "ancient_poetry", "practical", "composition",
    },
}
LEARNING_DOMAINS = {"reading", "writing", "integrated"}
LESSON_TYPES = {"reading", "writing", "reading_writing", "integrated"}
ACTIVITY_TYPES = {"resource", "reading", "presentation", "practice", "assignment", "writing"}
CONTENT_KINDS = {
    "lesson_plan", "rich_document", "slide_document", "assessment", "rubric",
    "teacher_feedback", "student_note", "learning_plan", "knowledge_card",
}


def _membership(course_id, user_id, role=None):
    query = CourseMembership.query.filter_by(
        course_id=course_id, user_id=user_id, status="active"
    )
    if role:
        query = query.filter_by(role=role)
    return query.first()


def _teacher_course(course_id, user_id):
    if not _membership(course_id, user_id, "teacher"):
        return None
    return Course.query.filter_by(id=course_id, status="active").first()


def _course_member(course_id, user_id):
    return _membership(course_id, user_id)


def _lesson_for_member(lesson_id, user_id, role=None):
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if not lesson or not _membership(lesson.course_id, user_id, role):
        return None
    return lesson


def _json_checksum(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event(course_id, actor, event_type, object_type, object_id, payload=None):
    db.session.add(
        LearningEvent(
            course_id=course_id,
            actor_user_id=actor,
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            payload=payload or {},
        )
    )


def _unit_dict(unit):
    return {
        "id": unit.id, "course_id": unit.course_id, "title": unit.title,
        "position": unit.position, "status": unit.status,
    }


def _lesson_dict(lesson):
    return {
        "id": lesson.id, "course_id": lesson.course_id, "unit_id": lesson.unit_id,
        "title": lesson.title, "learning_domain": lesson.learning_domain,
        "theme_code": lesson.theme_code, "text_genre_code": lesson.text_genre_code,
        "lesson_type_code": lesson.lesson_type_code,
        "duration_minutes": lesson.duration_minutes, "position": lesson.position,
        "status": lesson.status,
        "current_published_version_id": lesson.current_published_version_id,
    }


def _content_dict(content):
    return {
        "id": content.id, "course_id": content.course_id, "lesson_id": content.lesson_id,
        "kind": content.kind, "owner_user_id": content.owner_user_id,
        "visibility_scope": content.visibility_scope,
        "current_version_id": content.current_version_id, "status": content.status,
    }


def _version_dict(version):
    return {
        "id": version.id, "content_id": version.content_id,
        "version_number": version.version_number, "schema_name": version.schema_name,
        "schema_version": version.schema_version, "source_json": version.source_json,
        "rendered_html": version.rendered_html,
        "parent_version_id": version.parent_version_id,
        "change_summary": version.change_summary, "checksum": version.checksum,
        "created_by_user_id": version.created_by_user_id,
    }


def _validate_plan(lesson, source):
    required = {"subject_code", "learning_domain", "text_genre_code", "objectives", "stages"}
    if not isinstance(source, dict) or not required.issubset(source):
        return "lesson plan is missing required structured fields"
    if not isinstance(source["objectives"], list) or not source["objectives"]:
        return "lesson plan objectives are required"
    if not isinstance(source["stages"], list) or not source["stages"]:
        return "lesson plan stages are required"
    course = Course.query.get(lesson.course_id)
    if (
        source["subject_code"] != course.subject_code
        or source["learning_domain"] != lesson.learning_domain
        or source["text_genre_code"] != lesson.text_genre_code
    ):
        return "lesson plan template does not match lesson classification"
    return None


@education_content_api.post("/courses/<course_id>/units")
@jwt_required()
def create_unit(course_id):
    user_id = get_jwt_identity()
    if not _teacher_course(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    unit = CourseUnit(
        course_id=course_id, title=title, position=int(data.get("position") or 0)
    )
    db.session.add(unit)
    db.session.commit()
    return jsonify(_unit_dict(unit)), 201


@education_content_api.post("/courses/<course_id>/lessons")
@jwt_required()
def create_lesson(course_id):
    user_id = get_jwt_identity()
    course = _teacher_course(course_id, user_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    data = request.get_json(silent=True) or {}
    domain = str(data.get("learning_domain") or "")
    genre = str(data.get("text_genre_code") or "")
    lesson_type = str(data.get("lesson_type_code") or "")
    if not str(data.get("title") or "").strip():
        return jsonify({"error": "title is required"}), 400
    if (
        domain not in LEARNING_DOMAINS
        or genre not in SUBJECT_GENRES.get(course.subject_code, set())
        or lesson_type not in LESSON_TYPES
    ):
        return jsonify({"error": "lesson classification is not supported by subject template"}), 400
    unit_id = data.get("unit_id")
    if unit_id and not CourseUnit.query.filter_by(id=unit_id, course_id=course_id).first():
        return jsonify({"error": "unit not found"}), 404
    try:
        duration = int(data.get("duration_minutes") or 0)
        position = int(data.get("position") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "duration and position must be integers"}), 400
    if duration < 1 or duration > 600:
        return jsonify({"error": "invalid duration_minutes"}), 400
    lesson = Lesson(
        course_id=course_id, unit_id=unit_id, title=str(data["title"]).strip(),
        learning_domain=domain, theme_code=str(data.get("theme_code") or "").strip(),
        text_genre_code=genre, lesson_type_code=lesson_type,
        duration_minutes=duration, position=position,
    )
    db.session.add(lesson)
    db.session.commit()
    return jsonify(_lesson_dict(lesson)), 201


@education_content_api.get("/courses/<course_id>/structure")
@jwt_required()
def get_course_structure(course_id):
    user_id = get_jwt_identity()
    membership = _course_member(course_id, user_id)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    lesson_query = Lesson.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        lesson_query = lesson_query.filter_by(status="published")
    lessons = lesson_query.order_by(Lesson.position.asc(), Lesson.created_at.asc()).all()
    lessons_by_unit = {}
    for lesson in lessons:
        lessons_by_unit.setdefault(lesson.unit_id, []).append(_lesson_dict(lesson))
    units = CourseUnit.query.filter_by(
        course_id=course_id, status="active"
    ).order_by(CourseUnit.position.asc(), CourseUnit.created_at.asc()).all()
    return jsonify(
        {
            "course_id": course_id,
            "units": [
                {**_unit_dict(unit), "lessons": lessons_by_unit.get(unit.id, [])}
                for unit in units
            ],
            "ungrouped_lessons": lessons_by_unit.get(None, []),
        }
    )


@education_content_api.post("/lessons/<lesson_id>/activities")
@jwt_required()
def create_activity(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    data = request.get_json(silent=True) or {}
    activity_type = str(data.get("activity_type") or "")
    title = str(data.get("title") or "").strip()
    if activity_type not in ACTIVITY_TYPES or not title:
        return jsonify({"error": "valid activity_type and title are required"}), 400
    activity = LessonActivity(
        course_id=lesson.course_id, lesson_id=lesson.id, activity_type=activity_type,
        title=title, position=int(data.get("position") or 0),
        content_version_id=data.get("content_version_id"),
        student_payload=data.get("student_payload") or {},
        teacher_payload=data.get("teacher_payload") or {},
    )
    db.session.add(activity)
    db.session.commit()
    return jsonify({
        "id": activity.id, "lesson_id": activity.lesson_id,
        "activity_type": activity.activity_type, "title": activity.title,
        "position": activity.position, "content_version_id": activity.content_version_id,
        "student_payload": activity.student_payload,
    }), 201


def _create_version(content, data, user_id):
    source = data.get("source_json")
    lesson = Lesson.query.get(content.lesson_id) if content.lesson_id else None
    if content.kind == "lesson_plan":
        error = _validate_plan(lesson, source)
        if error:
            return None, error
    if not isinstance(source, dict):
        return None, "source_json must be an object"
    latest = (
        EducationContentVersion.query.filter_by(content_id=content.id)
        .order_by(EducationContentVersion.version_number.desc()).first()
    )
    version = EducationContentVersion(
        content_id=content.id, version_number=(latest.version_number + 1 if latest else 1),
        schema_name=str(data.get("schema_name") or "").strip(),
        schema_version=str(data.get("schema_version") or "1.0"),
        source_json=source, rendered_html=data.get("rendered_html"),
        parent_version_id=latest.id if latest else None,
        change_summary=str(data.get("change_summary") or ""),
        created_by_user_id=user_id, source_agent_run_id=data.get("source_agent_run_id"),
        checksum=_json_checksum(source),
    )
    if not version.schema_name:
        return None, "schema_name is required"
    db.session.add(version)
    db.session.flush()
    content.current_version_id = version.id
    return version, None


@education_content_api.post("/lessons/<lesson_id>/contents")
@jwt_required()
def create_content(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind") or "")
    if kind not in CONTENT_KINDS:
        return jsonify({"error": "unsupported content kind"}), 400
    content = EducationContent(
        course_id=lesson.course_id, lesson_id=lesson.id, kind=kind,
        owner_user_id=user_id,
        visibility_scope=str(data.get("visibility_scope") or "course_teacher"),
    )
    db.session.add(content)
    version, error = _create_version(content, data, user_id)
    if error:
        db.session.rollback()
        return jsonify({"error": error}), 400
    db.session.commit()
    return jsonify({"content": _content_dict(content), "version": _version_dict(version)}), 201


@education_content_api.post("/contents/<content_id>/versions")
@jwt_required()
def create_content_version(content_id):
    user_id = get_jwt_identity()
    content = EducationContent.query.filter_by(id=content_id).first()
    if not content or not _membership(content.course_id, user_id, "teacher"):
        return jsonify({"error": "content not found"}), 404
    version, error = _create_version(content, request.get_json(silent=True) or {}, user_id)
    if error:
        db.session.rollback()
        return jsonify({"error": error}), 400
    db.session.commit()
    return jsonify({"content": _content_dict(content), "version": _version_dict(version)}), 201


def _publication_dict(publication, include_teacher=False):
    result = {
        "id": publication.id, "lesson_id": publication.lesson_id,
        "version_number": publication.version_number,
        "lesson_plan_version_id": publication.lesson_plan_version_id,
        "student_release_manifest": publication.student_release_manifest,
        "published_by": publication.published_by,
        "published_at": publication.published_at.isoformat(),
        "status": publication.status,
    }
    if include_teacher:
        result["teacher_evaluation_manifest"] = publication.teacher_evaluation_manifest
    return result


@education_content_api.post("/lessons/<lesson_id>/publish")
@jwt_required()
def publish_lesson(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    key = str(request.headers.get("Idempotency-Key") or "").strip()
    if not key:
        return jsonify({"error": "Idempotency-Key is required"}), 400
    existing = PublishedLessonVersion.query.filter_by(
        lesson_id=lesson_id, idempotency_key=key
    ).first()
    if existing:
        return jsonify(_publication_dict(existing, include_teacher=True))
    activities = LessonActivity.query.filter_by(
        lesson_id=lesson.id, status="draft"
    ).order_by(LessonActivity.position.asc()).all()
    if not activities:
        return jsonify({"error": "lesson requires at least one activity"}), 400
    plan = (
        db.session.query(EducationContentVersion)
        .join(EducationContent, EducationContent.id == EducationContentVersion.content_id)
        .filter(
            EducationContent.lesson_id == lesson.id,
            EducationContent.kind == "lesson_plan",
            EducationContent.current_version_id == EducationContentVersion.id,
        ).first()
    )
    if not plan:
        return jsonify({"error": "lesson requires a current lesson plan"}), 400
    student_activities = [
        {
            "id": row.id, "type": row.activity_type, "title": row.title,
            "position": row.position, **(row.student_payload or {}),
        }
        for row in activities
    ]
    teacher_activities = [
        {"id": row.id, **(row.teacher_payload or {})} for row in activities
    ]
    previous = (
        PublishedLessonVersion.query.filter_by(lesson_id=lesson.id)
        .order_by(PublishedLessonVersion.version_number.desc()).first()
    )
    PublishedLessonVersion.query.filter_by(
        lesson_id=lesson.id, status="active"
    ).update({"status": "withdrawn"})
    publication = PublishedLessonVersion(
        lesson_id=lesson.id,
        version_number=(previous.version_number + 1 if previous else 1),
        lesson_plan_version_id=plan.id,
        student_release_manifest={
            "lesson": {
                "id": lesson.id, "title": lesson.title,
                "learning_domain": lesson.learning_domain,
            },
            "activities": student_activities,
        },
        teacher_evaluation_manifest={"activities": teacher_activities},
        idempotency_key=key, published_by=user_id,
    )
    db.session.add(publication)
    db.session.flush()
    lesson.status = "published"
    lesson.current_published_version_id = publication.id
    for row in activities:
        row.status = "published"
    _event(lesson.course_id, user_id, "LessonPublished", "lesson", lesson.id)
    db.session.commit()
    return jsonify(_publication_dict(publication, include_teacher=True)), 201


@education_content_api.get("/lessons/<lesson_id>/release")
@jwt_required()
def get_student_release(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id)
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    publication = PublishedLessonVersion.query.filter_by(
        id=lesson.current_published_version_id, status="active"
    ).first()
    if not publication:
        return jsonify({"error": "published lesson not found"}), 404
    _event(lesson.course_id, user_id, "LessonViewed", "lesson", lesson.id)
    db.session.commit()
    return jsonify(_publication_dict(publication, include_teacher=False))


@education_content_api.get("/lessons/<lesson_id>/publication")
@jwt_required()
def get_teacher_publication(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    publication = PublishedLessonVersion.query.filter_by(
        id=lesson.current_published_version_id, status="active"
    ).first()
    if not publication:
        return jsonify({"error": "published lesson not found"}), 404
    return jsonify(_publication_dict(publication, include_teacher=True))


def _assignment_dict(assignment, include_evaluation=False):
    result = {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "lesson_id": assignment.lesson_id,
        "title": assignment.title,
        "kind": assignment.kind,
        "instruction_json": assignment.instruction_json,
        "max_attempts": assignment.max_attempts,
        "allow_revision_after_feedback": assignment.allow_revision_after_feedback,
        "status": assignment.status,
        "published_at": (
            assignment.published_at.isoformat() if assignment.published_at else None
        ),
    }
    if include_evaluation:
        result["evaluation_json"] = assignment.evaluation_json
    return result


def _submission_dict(submission):
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "student_user_id": submission.student_user_id,
        "status": submission.status,
        "current_version_id": submission.current_version_id,
        "attempt_count": submission.attempt_count,
        "submitted_at": (
            submission.submitted_at.isoformat() if submission.submitted_at else None
        ),
        "final_score": submission.final_score,
        "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
    }


def _submission_version_dict(version):
    return {
        "id": version.id,
        "submission_id": version.submission_id,
        "version_number": version.version_number,
        "answer_json": version.answer_json,
        "artifact_ids": version.artifact_ids,
        "submitted_at": version.submitted_at.isoformat(),
        "source_version_id": version.source_version_id,
        "checksum": version.checksum,
    }


def _assignment_for_member(assignment_id, user_id, role=None):
    assignment = Assignment.query.filter_by(id=assignment_id).first()
    if not assignment or not _membership(assignment.course_id, user_id, role):
        return None
    return assignment


@education_content_api.post("/lessons/<lesson_id>/assignments")
@jwt_required()
def create_assignment(lesson_id):
    user_id = get_jwt_identity()
    lesson = _lesson_for_member(lesson_id, user_id, "teacher")
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    kind = str(data.get("kind") or "")
    instruction = data.get("instruction_json")
    evaluation = data.get("evaluation_json") or {}
    if not title or kind not in {"quiz", "writing", "mixed"}:
        return jsonify({"error": "valid title and kind are required"}), 400
    if not isinstance(instruction, dict) or not instruction:
        return jsonify({"error": "instruction_json is required"}), 400
    if not isinstance(evaluation, dict):
        return jsonify({"error": "evaluation_json must be an object"}), 400
    try:
        max_attempts = int(data.get("max_attempts", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "max_attempts must be an integer"}), 400
    if not 1 <= max_attempts <= 20:
        return jsonify({"error": "invalid max_attempts"}), 400
    assignment = Assignment(
        course_id=lesson.course_id,
        lesson_id=lesson.id,
        title=title,
        kind=kind,
        instruction_json=instruction,
        evaluation_json=evaluation,
        max_attempts=max_attempts,
        allow_revision_after_feedback=bool(
            data.get("allow_revision_after_feedback", True)
        ),
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify(_assignment_dict(assignment, include_evaluation=False)), 201


@education_content_api.post("/assignments/<assignment_id>/publish")
@jwt_required()
def publish_assignment(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "teacher")
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    if assignment.status != "published":
        assignment.status = "published"
        assignment.published_by = user_id
        assignment.published_at = datetime.utcnow()
        _event(
            assignment.course_id,
            user_id,
            "AssignmentPublished",
            "assignment",
            assignment.id,
        )
        db.session.commit()
    return jsonify(_assignment_dict(assignment, include_evaluation=True))


@education_content_api.get("/courses/<course_id>/assignments")
@jwt_required()
def list_assignments(course_id):
    user_id = get_jwt_identity()
    membership = _course_member(course_id, user_id)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = Assignment.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        query = query.filter_by(status="published")
    assignments = query.order_by(Assignment.created_at.asc()).all()
    return jsonify(
        {
            "items": [
                _assignment_dict(row, include_evaluation=membership.role == "teacher")
                for row in assignments
            ]
        }
    )


@education_content_api.post("/assignments/<assignment_id>/submissions")
@jwt_required()
def submit_assignment(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id, "student")
    if not assignment or assignment.status != "published":
        return jsonify({"error": "assignment not found"}), 404
    data = request.get_json(silent=True) or {}
    answer = data.get("answer_json")
    if not isinstance(answer, dict) or not answer:
        return jsonify({"error": "answer_json is required"}), 400
    submission = Submission.query.filter_by(
        assignment_id=assignment.id, student_user_id=user_id
    ).first()
    if not submission:
        submission = Submission(
            assignment_id=assignment.id, student_user_id=user_id
        )
        db.session.add(submission)
        db.session.flush()
    if submission.attempt_count >= assignment.max_attempts:
        return jsonify({"error": "maximum attempts reached"}), 409
    source_version_id = data.get("source_version_id")
    if submission.current_version_id and source_version_id != submission.current_version_id:
        return jsonify({"error": "source_version_id must reference the current submission"}), 409
    now = datetime.utcnow()
    version = SubmissionVersion(
        submission_id=submission.id,
        version_number=submission.attempt_count + 1,
        answer_json=answer,
        artifact_ids=data.get("artifact_ids") or [],
        submitted_at=now,
        source_version_id=source_version_id,
        checksum=_json_checksum(answer),
    )
    db.session.add(version)
    db.session.flush()
    submission.current_version_id = version.id
    submission.attempt_count += 1
    submission.status = "submitted" if submission.attempt_count == 1 else "revised"
    submission.submitted_at = now
    _event(
        assignment.course_id,
        user_id,
        "AssignmentSubmitted",
        "submission",
        submission.id,
        {"attempt": submission.attempt_count},
    )
    db.session.commit()
    return jsonify(
        {
            "submission": _submission_dict(submission),
            "version": _submission_version_dict(version),
        }
    ), 201


@education_content_api.get("/assignments/<assignment_id>/submissions")
@jwt_required()
def list_submissions(assignment_id):
    user_id = get_jwt_identity()
    assignment = _assignment_for_member(assignment_id, user_id)
    if not assignment:
        return jsonify({"error": "assignment not found"}), 404
    membership = _membership(assignment.course_id, user_id)
    query = Submission.query.filter_by(assignment_id=assignment.id)
    if membership.role != "teacher":
        query = query.filter_by(student_user_id=user_id)
    return jsonify({"items": [_submission_dict(row) for row in query.all()]})


def _submission_for_reviewer(submission_id, user_id):
    submission = Submission.query.filter_by(id=submission_id).first()
    if not submission:
        return None, None
    assignment = Assignment.query.filter_by(id=submission.assignment_id).first()
    if not assignment or not _membership(assignment.course_id, user_id, "teacher"):
        return None, None
    return submission, assignment


@education_content_api.post("/submissions/<submission_id>/feedback")
@jwt_required()
def release_feedback(submission_id):
    user_id = get_jwt_identity()
    submission, assignment = _submission_for_reviewer(submission_id, user_id)
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    data = request.get_json(silent=True) or {}
    feedback_json = data.get("feedback_json")
    if not isinstance(feedback_json, dict) or not feedback_json:
        return jsonify({"error": "feedback_json is required"}), 400
    try:
        score = float(data["score"]) if data.get("score") is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "score must be numeric"}), 400
    if score is not None and score < 0:
        return jsonify({"error": "score cannot be negative"}), 400
    feedback = Feedback(
        submission_version_id=submission.current_version_id,
        feedback_json=feedback_json,
        status="released",
        score=score,
        released_by=user_id,
    )
    db.session.add(feedback)
    submission.status = "graded"
    submission.final_score = score
    submission.graded_by = user_id
    submission.graded_at = datetime.utcnow()
    _event(
        assignment.course_id,
        user_id,
        "FeedbackReleased",
        "submission",
        submission.id,
        {"student_user_id": submission.student_user_id, "score": score},
    )
    db.session.commit()
    return jsonify(
        {
            "id": feedback.id,
            "submission_version_id": feedback.submission_version_id,
            "feedback_json": feedback.feedback_json,
            "score": feedback.score,
            "status": feedback.status,
        }
    ), 201


@education_content_api.get("/submissions/<submission_id>/feedback")
@jwt_required()
def list_feedback(submission_id):
    user_id = get_jwt_identity()
    submission = Submission.query.filter_by(id=submission_id).first()
    if not submission:
        return jsonify({"error": "submission not found"}), 404
    assignment = Assignment.query.filter_by(id=submission.assignment_id).first()
    membership = _membership(assignment.course_id, user_id)
    if not membership or (
        membership.role != "teacher" and submission.student_user_id != user_id
    ):
        return jsonify({"error": "submission not found"}), 404
    versions = SubmissionVersion.query.filter_by(submission_id=submission.id).all()
    version_ids = [row.id for row in versions]
    rows = (
        Feedback.query.filter(Feedback.submission_version_id.in_(version_ids))
        .order_by(Feedback.released_at.asc())
        .all()
        if version_ids
        else []
    )
    return jsonify(
        {
            "items": [
                {
                    "id": row.id,
                    "submission_version_id": row.submission_version_id,
                    "feedback_json": row.feedback_json,
                    "score": row.score,
                    "status": row.status,
                    "released_at": row.released_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@education_content_api.get("/courses/<course_id>/analytics")
@jwt_required()
def course_analytics(course_id):
    user_id = get_jwt_identity()
    if not _teacher_course(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    active_students = CourseMembership.query.filter_by(
        course_id=course_id, role="student", status="active"
    ).count()
    assignments = Assignment.query.filter_by(
        course_id=course_id, status="published"
    ).all()
    lessons_by_id = {
        row.id: row
        for row in Lesson.query.filter_by(course_id=course_id).all()
    }
    learning_domain_counts = {}
    assignment_kind_counts = {}
    for assignment in assignments:
        assignment_kind_counts[assignment.kind] = (
            assignment_kind_counts.get(assignment.kind, 0) + 1
        )
        lesson = lessons_by_id.get(assignment.lesson_id)
        if lesson:
            learning_domain_counts[lesson.learning_domain] = (
                learning_domain_counts.get(lesson.learning_domain, 0) + 1
            )
    assignment_ids = [row.id for row in assignments]
    submissions = (
        Submission.query.filter(Submission.assignment_id.in_(assignment_ids)).all()
        if assignment_ids
        else []
    )
    submitted_students = len({row.student_user_id for row in submissions})
    denominator = active_students * len(assignments)
    completion_rate = round(len(submissions) / denominator, 4) if denominator else 0.0
    scores = [row.final_score for row in submissions if row.final_score is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else None
    event_rows = (
        db.session.query(LearningEvent.event_type, db.func.count(LearningEvent.id))
        .filter(LearningEvent.course_id == course_id)
        .group_by(LearningEvent.event_type)
        .all()
    )
    return jsonify(
        {
            "course_id": course_id,
            "active_students": active_students,
            "published_assignments": len(assignments),
            "submitted_students": submitted_students,
            "completion_rate": completion_rate,
            "average_score": average_score,
            "learning_domain_counts": learning_domain_counts,
            "assignment_kind_counts": assignment_kind_counts,
            "event_counts": {event_type: count for event_type, count in event_rows},
        }
    )
