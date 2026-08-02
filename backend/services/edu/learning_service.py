"""Application services for mock exams, mind maps, and student insight."""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import median

from .access import active_membership
from .content_models import Assignment, Feedback, LearningEvent, Lesson, Submission
from .extensions import db
from .knowledge_models import (
    AssessmentAnswerVersion,
    AssessmentItem,
    AssessmentItemVersion,
    AssessmentPaper,
    AssessmentPaperVersion,
    KnowledgeResource,
)
from .knowledge_service import question_version_to_dict
from .learning_models import (
    CourseMindMap,
    CourseMindMapVersion,
    MockExamAttempt,
    StudentInsightSnapshot,
    WeaknessAnalysisSnapshot,
)
from .models import Course, CourseMembership


@dataclass
class LearningServiceError(Exception):
    message: str
    status_code: int = 400
    error_code: str = "invalid_learning_request"


def _checksum(value):
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _student(course_id, actor):
    membership = active_membership(course_id, actor, "student")
    if not membership:
        raise LearningServiceError("course not found", 404, "course_not_found")
    return membership


def _teacher(course_id, actor):
    membership = active_membership(course_id, actor, "teacher")
    if not membership:
        raise LearningServiceError("course not found", 404, "course_not_found")
    return membership


def _paper_version(paper):
    return AssessmentPaperVersion.query.filter_by(
        id=paper.current_version_id
    ).first()


def _paper_for_student(course_id, paper_id, actor):
    paper = AssessmentPaper.query.filter_by(
        id=paper_id,
        course_id=course_id,
        status="published",
    ).first()
    if not paper or (
        paper.generated_for_user_id
        and paper.generated_for_user_id != actor
    ):
        raise LearningServiceError("paper not found", 404, "paper_not_found")
    return paper


def _select_question_versions(course_id, data):
    mix = data.get("difficulty_mix") or {}
    requested_counts = {}
    if mix:
        if not isinstance(mix, dict):
            raise LearningServiceError(
                "difficulty_mix must be an object",
                400,
                "invalid_difficulty_mix",
            )
        for difficulty in ("easy", "medium", "hard"):
            try:
                requested_counts[difficulty] = int(mix.get(difficulty) or 0)
            except (TypeError, ValueError):
                requested_counts[difficulty] = -1
            if requested_counts[difficulty] < 0:
                raise LearningServiceError(
                    "difficulty counts must be non-negative",
                    400,
                    "invalid_difficulty_mix",
                )
    try:
        count = int(
            data.get("question_count")
            or (sum(requested_counts.values()) if requested_counts else 10)
        )
    except (TypeError, ValueError):
        count = 0
    if not 1 <= count <= 50:
        raise LearningServiceError(
            "question_count must be between 1 and 50",
            400,
            "invalid_question_count",
        )
    rows = (
        AssessmentItem.query.filter_by(course_id=course_id, status="published")
        .order_by(AssessmentItem.created_at.asc())
        .all()
    )
    candidates = []
    wanted_points = {
        str(value).strip()
        for value in (data.get("knowledge_points") or [])
        if str(value).strip()
    }
    for item in rows:
        version = AssessmentItemVersion.query.filter_by(
            id=item.published_version_id
        ).first()
        if not version:
            continue
        if wanted_points and not wanted_points.intersection(
            set(version.knowledge_points or [])
        ):
            continue
        candidates.append((item, version))

    if mix:
        selected = []
        for difficulty in ("easy", "medium", "hard"):
            wanted = requested_counts[difficulty]
            matching = [
                row
                for row in candidates
                if row[1].difficulty == difficulty and row not in selected
            ]
            selected.extend(matching[:wanted])
        if sum(requested_counts.values()) != count:
            raise LearningServiceError(
                "difficulty_mix counts must equal question_count",
                400,
                "invalid_difficulty_mix",
            )
    else:
        selected = candidates[:count]
    if len(selected) < count:
        raise LearningServiceError(
            "not enough published questions match this blueprint",
            409,
            "insufficient_questions",
        )
    return selected[:count]


def _create_generated_paper(course_id, actor, data):
    selected = _select_question_versions(course_id, data)
    try:
        duration = int(data.get("duration_minutes") or 30)
    except (TypeError, ValueError):
        duration = 0
    if not 1 <= duration <= 600:
        raise LearningServiceError(
            "duration_minutes must be between 1 and 600",
            400,
            "invalid_duration",
        )
    title = str(data.get("title") or "Personal mock exam").strip()
    version_ids = [version.id for _, version in selected]
    total_score = sum(version.score for _, version in selected)
    paper = AssessmentPaper(
        course_id=course_id,
        title=title,
        purpose="mock_exam",
        owner_user_id=actor,
        generated_for_user_id=actor,
        visibility_scope="owner_private",
        status="published",
        published_by=actor,
        published_at=datetime.utcnow(),
    )
    db.session.add(paper)
    db.session.flush()
    paper_version = AssessmentPaperVersion(
        paper_id=paper.id,
        version_number=1,
        item_version_ids=version_ids,
        sections=[
            {
                "title": "Mock exam",
                "item_version_ids": version_ids,
                "score": total_score,
            }
        ],
        total_score=total_score,
        duration_minutes=duration,
        blueprint={
            "question_count": len(version_ids),
            "difficulty_mix": data.get("difficulty_mix") or {},
            "knowledge_points": data.get("knowledge_points") or [],
        },
        checksum=_checksum(
            {
                "item_version_ids": version_ids,
                "total_score": total_score,
                "duration_minutes": duration,
            }
        ),
        created_by_user_id=actor,
    )
    db.session.add(paper_version)
    db.session.flush()
    paper.current_version_id = paper_version.id
    paper.published_version_id = paper_version.id
    return paper


def create_mock_exam(course_id, actor, data):
    _student(course_id, actor)
    paper_id = data.get("paper_id")
    paper = (
        _paper_for_student(course_id, paper_id, actor)
        if paper_id
        else _create_generated_paper(course_id, actor, data)
    )
    paper_version = _paper_version(paper)
    if not paper_version:
        raise LearningServiceError(
            "paper version is unavailable",
            409,
            "paper_version_missing",
        )
    attempt = MockExamAttempt(
        course_id=course_id,
        paper_version_id=paper_version.id,
        student_user_id=actor,
    )
    db.session.add(attempt)
    db.session.flush()
    return attempt


def _attempt_questions(attempt):
    paper_version = AssessmentPaperVersion.query.filter_by(
        id=attempt.paper_version_id
    ).first()
    if not paper_version:
        return []
    versions = {
        row.id: row
        for row in AssessmentItemVersion.query.filter(
            AssessmentItemVersion.id.in_(paper_version.item_version_ids or [])
        ).all()
    }
    return [
        versions[version_id]
        for version_id in (paper_version.item_version_ids or [])
        if version_id in versions
    ]


def attempt_to_dict(attempt):
    questions = _attempt_questions(attempt)
    return {
        "id": attempt.id,
        "course_id": attempt.course_id,
        "paper_version_id": attempt.paper_version_id,
        "student_user_id": attempt.student_user_id,
        "status": attempt.status,
        "answers": attempt.answers_json or {},
        "questions": [
            question_version_to_dict(version, include_answer=False)
            for version in questions
        ],
        "score": attempt.score,
        "max_score": attempt.max_score,
        "accuracy": attempt.accuracy,
        "evidence": attempt.evidence_json or [],
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "submitted_at": (
            attempt.submitted_at.isoformat() if attempt.submitted_at else None
        ),
        "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
        "updated_at": attempt.updated_at.isoformat() if attempt.updated_at else None,
    }


def _attempt_for_owner(attempt_id, actor):
    attempt = MockExamAttempt.query.filter_by(
        id=attempt_id,
        student_user_id=actor,
    ).first()
    if not attempt or not active_membership(attempt.course_id, actor, "student"):
        raise LearningServiceError(
            "mock exam not found",
            404,
            "mock_exam_not_found",
        )
    return attempt


def save_mock_answers(attempt_id, actor, data):
    attempt = _attempt_for_owner(attempt_id, actor)
    if attempt.status != "in_progress":
        raise LearningServiceError(
            "submitted mock exam is immutable",
            409,
            "mock_exam_submitted",
        )
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise LearningServiceError(
            "answers must be an object keyed by question version id",
            400,
            "invalid_answers",
        )
    allowed = {version.id for version in _attempt_questions(attempt)}
    if not set(answers).issubset(allowed):
        raise LearningServiceError(
            "answers contain a question outside this paper",
            400,
            "answer_scope_violation",
        )
    attempt.answers_json = answers
    return attempt


def _normalize_answer(value, question_type):
    if question_type == "single_choice":
        return str(value or "").strip().upper()
    if question_type == "multiple_choice":
        if not isinstance(value, list):
            return []
        return sorted({str(item).strip().upper() for item in value})
    if isinstance(value, list):
        return [str(item).strip().casefold() for item in value]
    return " ".join(str(value or "").split()).casefold()


def submit_mock_exam(attempt_id, actor):
    attempt = _attempt_for_owner(attempt_id, actor)
    if attempt.status != "in_progress":
        return attempt
    questions = _attempt_questions(attempt)
    answers = attempt.answers_json or {}
    evidence = []
    earned = 0.0
    max_score = 0.0
    objective_count = 0
    correct_count = 0
    pending_subjective = False
    for version in questions:
        answer = AssessmentAnswerVersion.query.filter_by(
            item_version_id=version.id
        ).first()
        if not answer:
            raise LearningServiceError(
                "answer key is unavailable",
                409,
                "answer_key_missing",
            )
        submitted = answers.get(version.id)
        if version.question_type in {"short_answer", "writing"}:
            correct = None
            awarded = None
            pending_subjective = True
        else:
            objective_count += 1
            max_score += version.score
            correct = _normalize_answer(
                submitted,
                version.question_type,
            ) == _normalize_answer(
                answer.correct_answer,
                version.question_type,
            )
            awarded = version.score if correct else 0.0
            earned += awarded
            if correct:
                correct_count += 1
        evidence.append(
            {
                "attempt_id": attempt.id,
                "item_id": version.item_id,
                "item_version_id": version.id,
                "knowledge_points": version.knowledge_points or [],
                "difficulty": version.difficulty,
                "question_type": version.question_type,
                "submitted_answer": submitted,
                "correct_answer": answer.correct_answer,
                "correct": correct,
                "score": awarded,
                "max_score": version.score,
                "explanation": answer.explanation,
            }
        )
    attempt.evidence_json = evidence
    attempt.score = earned if objective_count else None
    attempt.max_score = max_score if objective_count else None
    attempt.accuracy = (
        correct_count / objective_count if objective_count else None
    )
    attempt.status = "pending_review" if pending_subjective else "submitted"
    attempt.submitted_at = datetime.utcnow()
    db.session.add(
        LearningEvent(
            course_id=attempt.course_id,
            actor_user_id=actor,
            event_type="MockExamSubmitted",
            object_type="mock_exam_attempt",
            object_id=attempt.id,
            payload={
                "score": attempt.score,
                "max_score": attempt.max_score,
                "accuracy": attempt.accuracy,
                "paper_version_id": attempt.paper_version_id,
            },
        )
    )
    create_weakness_snapshot(attempt.course_id, actor)
    return attempt


def _weakness_projection(evidence):
    totals = defaultdict(lambda: {"attempted": 0, "wrong": 0, "evidence_ids": []})
    for row in evidence:
        if row.get("correct") is None:
            continue
        for point in row.get("knowledge_points") or ["未标注知识点"]:
            totals[point]["attempted"] += 1
            if not row["correct"]:
                totals[point]["wrong"] += 1
                totals[point]["evidence_ids"].append(row.get("item_version_id"))
    weaknesses = [
        {
            "knowledge_point": point,
            "attempted_count": values["attempted"],
            "wrong_count": values["wrong"],
            "error_rate": (
                values["wrong"] / values["attempted"] if values["attempted"] else 0
            ),
            "evidence_item_version_ids": values["evidence_ids"],
        }
        for point, values in totals.items()
        if values["wrong"] > 0
    ]
    weaknesses.sort(
        key=lambda row: (-row["error_rate"], -row["wrong_count"], row["knowledge_point"])
    )
    recommendations = [
        {
            "knowledge_point": row["knowledge_point"],
            "action": (
                f"复习“{row['knowledge_point']}”的课程材料，并完成一组同类证据题。"
            ),
            "recommended_question_count": min(5, max(2, row["wrong_count"] + 1)),
            "evidence_item_version_ids": row["evidence_item_version_ids"],
        }
        for row in weaknesses
    ]
    return weaknesses, recommendations


def _feedback_text_items(value):
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        items = []
        for row in value:
            items.extend(_feedback_text_items(row))
        return items
    if isinstance(value, dict):
        items = []
        for row in value.values():
            items.extend(_feedback_text_items(row))
        return items
    return []


def _assignment_feedback_evidence(course_id, student_user_id):
    assignments = Assignment.query.filter_by(
        course_id=course_id,
        status="published",
    ).all()
    assignments_by_id = {row.id: row for row in assignments}
    if not assignments_by_id:
        return []
    submissions = Submission.query.filter(
        Submission.assignment_id.in_(list(assignments_by_id)),
        Submission.student_user_id == student_user_id,
        Submission.status.in_(("graded", "revision_requested")),
    ).all()
    evidence = []
    for submission in submissions:
        assignment = assignments_by_id[submission.assignment_id]
        feedback = (
            Feedback.query.filter_by(
                submission_version_id=submission.current_version_id,
                status="released",
            )
            .order_by(Feedback.released_at.desc())
            .first()
        )
        feedback_json = feedback.feedback_json if feedback else {}
        points = []
        for key in ("weaknesses", "improvements", "issues", "next_steps"):
            points.extend(_feedback_text_items((feedback_json or {}).get(key)))
        has_explicit_weakness = bool(points)
        if not points:
            points.extend(_feedback_text_items((feedback_json or {}).get("comment")))
        points = list(dict.fromkeys(point for point in points if point))
        normalized_score = _normalized_score(
            submission.final_score,
            assignment.max_score,
        )
        if not points:
            points = [assignment.title]
        for point in points:
            evidence.append(
                {
                    "source_type": "assignment_feedback",
                    "submission_id": submission.id,
                    "assignment_id": assignment.id,
                    "assignment_title": assignment.title,
                    "feedback_id": feedback.id if feedback else None,
                    "item_version_id": submission.current_version_id,
                    "knowledge_points": [point],
                    "correct": (
                        False if has_explicit_weakness else normalized_score >= 80
                    ),
                    "score": submission.final_score,
                    "max_score": assignment.max_score,
                    "explanation": point,
                    "submitted_at": (
                        submission.submitted_at.isoformat()
                        if submission.submitted_at
                        else None
                    ),
                    "graded_at": (
                        submission.graded_at.isoformat()
                        if submission.graded_at
                        else None
                    ),
                }
            )
    return evidence


def _weakness_evidence(course_id, actor):
    _student(course_id, actor)
    attempts = (
        MockExamAttempt.query.filter(
            MockExamAttempt.course_id == course_id,
            MockExamAttempt.student_user_id == actor,
            MockExamAttempt.status.in_(("submitted", "pending_review")),
        )
        .order_by(MockExamAttempt.submitted_at.asc())
        .all()
    )
    evidence = []
    for attempt in attempts:
        for row in attempt.evidence_json or []:
            evidence.append({**row, "attempt_id": attempt.id})
    evidence.extend(_assignment_feedback_evidence(course_id, actor))
    return evidence


def create_weakness_snapshot(course_id, actor, *, evidence=None):
    evidence = _weakness_evidence(course_id, actor) if evidence is None else evidence
    weaknesses, recommendations = _weakness_projection(evidence)
    snapshot = WeaknessAnalysisSnapshot(
        course_id=course_id,
        student_user_id=actor,
        data_state="ready" if evidence else "insufficient",
        evidence=evidence,
        weaknesses=weaknesses,
        recommendations=recommendations,
        source_fingerprint=_checksum(
            evidence
        ),
    )
    db.session.add(snapshot)
    db.session.flush()
    return snapshot


def ensure_weakness_snapshot(course_id, actor):
    """Return a projection matching current official evidence, rebuilding if stale."""
    evidence = _weakness_evidence(course_id, actor)
    fingerprint = _checksum(evidence)
    latest = (
        WeaknessAnalysisSnapshot.query.filter_by(
            course_id=course_id,
            student_user_id=actor,
        )
        .order_by(WeaknessAnalysisSnapshot.created_at.desc())
        .first()
    )
    if latest and latest.source_fingerprint == fingerprint:
        return latest
    return create_weakness_snapshot(course_id, actor, evidence=evidence)


def weakness_to_dict(snapshot):
    return {
        "id": snapshot.id,
        "course_id": snapshot.course_id,
        "student_user_id": snapshot.student_user_id,
        "data_state": snapshot.data_state,
        "evidence": snapshot.evidence or [],
        "weaknesses": snapshot.weaknesses or [],
        "recommendations": snapshot.recommendations or [],
        "source_fingerprint": snapshot.source_fingerprint,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }


def _validate_tree(tree):
    if not isinstance(tree, dict):
        raise LearningServiceError(
            "tree must be an object",
            400,
            "invalid_mind_map_tree",
        )
    seen = set()
    count = 0

    allowed_colors = {
        "auto", "teal", "blue", "indigo", "violet", "amber", "orange", "rose", "slate"
    }

    def visit(node, depth):
        nonlocal count
        if not isinstance(node, dict) or depth > 12:
            raise LearningServiceError(
                "mind-map tree exceeds the supported shape",
                400,
                "invalid_mind_map_tree",
            )
        node_id = str(node.get("id") or "").strip()
        label = str(node.get("label") or "").strip()
        children = node.get("children", [])
        if not node_id or node_id in seen or not label or not isinstance(children, list):
            raise LearningServiceError(
                "mind-map nodes require unique ids, labels, and child lists",
                400,
                "invalid_mind_map_tree",
            )
        color_token = str(node.get("color_token") or "auto")
        if color_token not in allowed_colors:
            raise LearningServiceError(
                "unsupported mind-map color token",
                400,
                "invalid_mind_map_color",
            )
        node["color_token"] = color_token
        seen.add(node_id)
        count += 1
        if count > 500:
            raise LearningServiceError(
                "mind map exceeds 500 nodes",
                400,
                "mind_map_too_large",
            )
        for child in children:
            visit(child, depth + 1)

    visit(tree, 0)
    return tree, seen


def _normalize_mind_map_document(mind_map, value):
    if isinstance(value, dict) and value.get("schema_name") == "education_mind_map_v2":
        document = dict(value)
        root = document.get("root")
    else:
        document = {
            "schema_name": "education_mind_map_v2",
            "scope_type": mind_map.scope_type or "course",
            "lesson_ids": mind_map.lesson_ids or [],
            "root": value,
            "relations": [],
            "view": {"direction": "right", "theme": "education_clear"},
        }
        root = value
    root, node_ids = _validate_tree(root)
    scope_type = str(document.get("scope_type") or mind_map.scope_type or "course")
    lesson_ids = document.get("lesson_ids") or []
    if scope_type != mind_map.scope_type or list(lesson_ids) != list(mind_map.lesson_ids or []):
        raise LearningServiceError(
            "mind-map scope cannot change inside a content version",
            400,
            "invalid_mind_map_scope",
        )
    relations = document.get("relations") or []
    if not isinstance(relations, list) or len(relations) > 1000:
        raise LearningServiceError(
            "relations must be a list of at most 1000 edges",
            400,
            "invalid_mind_map_relations",
        )
    relation_ids = set()
    normalized_relations = []
    for relation in relations:
        if not isinstance(relation, dict):
            raise LearningServiceError(
                "every relation must be an object", 400, "invalid_mind_map_relations"
            )
        relation_id = str(relation.get("id") or "").strip()
        source = str(relation.get("from") or "").strip()
        target = str(relation.get("to") or "").strip()
        label = str(relation.get("label") or "").strip()[:100]
        relation_type = str(relation.get("type") or "cross_link").strip()
        if (
            not relation_id
            or relation_id in relation_ids
            or source not in node_ids
            or target not in node_ids
            or source == target
            or relation_type != "cross_link"
        ):
            raise LearningServiceError(
                "relations require unique ids and existing distinct endpoints",
                400,
                "invalid_mind_map_relations",
            )
        relation_ids.add(relation_id)
        normalized_relations.append(
            {"id": relation_id, "from": source, "to": target, "label": label, "type": relation_type}
        )
    view = document.get("view") or {}
    direction = str(view.get("direction") or "right")
    theme = str(view.get("theme") or "education_clear")
    if direction not in {"right", "both", "down"} or theme != "education_clear":
        raise LearningServiceError(
            "unsupported mind-map view", 400, "invalid_mind_map_view"
        )
    return {
        "schema_name": "education_mind_map_v2",
        "scope_type": scope_type,
        "lesson_ids": list(lesson_ids),
        "root": root,
        "relations": normalized_relations,
        "view": {"direction": direction, "theme": theme},
    }


def _create_mind_map_version(mind_map, actor, document, source_refs, change_summary):
    document = _normalize_mind_map_document(mind_map, document)
    if not isinstance(source_refs, list) or not all(
        isinstance(value, str) for value in source_refs
    ):
        raise LearningServiceError(
            "source_refs must be a list of ids",
            400,
            "invalid_source_refs",
        )
    previous = (
        CourseMindMapVersion.query.filter_by(mind_map_id=mind_map.id)
        .order_by(CourseMindMapVersion.version_number.desc())
        .first()
    )
    version = CourseMindMapVersion(
        mind_map_id=mind_map.id,
        version_number=(previous.version_number + 1 if previous else 1),
        tree_json=document,
        source_refs=list(dict.fromkeys(source_refs)),
        change_summary=str(change_summary or "")[:500],
        checksum=_checksum({"document": document, "source_refs": source_refs}),
        created_by_user_id=actor,
    )
    db.session.add(version)
    db.session.flush()
    mind_map.current_version_id = version.id
    return version


def create_mind_map(course_id, actor, data):
    _student(course_id, actor)
    course = Course.query.filter_by(id=course_id, status="active").one()
    published_lessons = (
        Lesson.query.filter_by(course_id=course_id, status="published")
        .order_by(Lesson.position.asc(), Lesson.created_at.asc())
        .all()
    )
    scope_type = str(data.get("scope_type") or "course").strip()
    if scope_type not in {"course", "lesson", "custom"}:
        raise LearningServiceError("unsupported mind-map scope", 400, "invalid_mind_map_scope")
    requested_lesson_ids = data.get("lesson_ids") or []
    if not isinstance(requested_lesson_ids, list):
        raise LearningServiceError("lesson_ids must be a list", 400, "invalid_mind_map_scope")
    published_by_id = {lesson.id: lesson for lesson in published_lessons}
    if scope_type == "course":
        lesson_ids = [lesson.id for lesson in published_lessons]
    else:
        lesson_ids = list(dict.fromkeys(str(value) for value in requested_lesson_ids if value))
        if (scope_type == "lesson" and len(lesson_ids) != 1) or not lesson_ids:
            raise LearningServiceError(
                "lesson scope requires one published lesson", 400, "invalid_mind_map_scope"
            )
        if any(lesson_id not in published_by_id for lesson_id in lesson_ids):
            raise LearningServiceError(
                "one or more lessons are unavailable", 400, "invalid_mind_map_scope"
            )
    lessons = [published_by_id[lesson_id] for lesson_id in lesson_ids]
    resources = (
        KnowledgeResource.query.filter_by(
            course_id=course_id,
            status="active",
            visibility_scope="course_published",
        )
        .order_by(KnowledgeResource.created_at.asc())
        .all()
    )
    children = [
        {
            "id": f"lesson:{lesson.id}",
            "label": lesson.title,
            "children": [],
            "source_ref": lesson.id,
            "source_type": "lesson",
        }
        for lesson in lessons
    ] + [
        {
            "id": f"resource:{resource.id}",
            "label": resource.title,
            "children": [],
            "source_ref": resource.id,
            "source_type": "knowledge_resource",
        }
        for resource in resources
    ]
    source_refs = [lesson.id for lesson in lessons] + [
        resource.id for resource in resources
    ]
    mind_map = CourseMindMap(
        course_id=course_id,
        owner_user_id=actor,
        title=str(data.get("title") or f"{course.title}思维导图").strip(),
        scope_type=scope_type,
        lesson_ids=lesson_ids,
    )
    db.session.add(mind_map)
    db.session.flush()
    generated_document = {
        "schema_name": "education_mind_map_v2",
        "scope_type": scope_type,
        "lesson_ids": lesson_ids,
        "root": {
            "id": f"course:{course.id}",
            "label": (lessons[0].title if scope_type == "lesson" else course.title),
            "children": children,
            "source_ref": course.id,
            "source_type": "course",
        },
        "relations": [],
        "view": {"direction": "right", "theme": "education_clear"},
    }
    supplied_document = data.get("document") or data.get("tree")
    supplied_refs = data.get("source_refs")
    _create_mind_map_version(
        mind_map,
        actor,
        supplied_document or generated_document,
        supplied_refs if isinstance(supplied_refs, list) else source_refs,
        str(data.get("change_summary") or "Generated from published course sources"),
    )
    return mind_map


def _mind_map_access(mind_map, actor, *, write=False):
    membership = active_membership(mind_map.course_id, actor)
    if not membership:
        raise LearningServiceError(
            "mind map not found",
            404,
            "mind_map_not_found",
        )
    if membership.role == "teacher":
        return membership
    if membership.role == "student" and mind_map.owner_user_id == actor:
        return membership
    raise LearningServiceError(
        "mind map not found",
        404,
        "mind_map_not_found",
    )


def add_mind_map_version(mind_map, actor, data):
    _mind_map_access(mind_map, actor, write=True)
    _create_mind_map_version(
        mind_map,
        actor,
        data.get("document") or data.get("tree"),
        data.get("source_refs") or [],
        data.get("change_summary") or "",
    )
    return mind_map


def mind_map_version_to_dict(mind_map, version):
    if not version:
        return None
    stored = version.tree_json or {}
    document = _normalize_mind_map_document(mind_map, stored)
    return {
        "id": version.id,
        "version_number": version.version_number,
        "document": document,
        "tree": document["root"],
        "relations": document["relations"],
        "source_refs": version.source_refs or [],
        "change_summary": version.change_summary,
        "checksum": version.checksum,
        "created_by_user_id": version.created_by_user_id,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


def mind_map_to_dict(mind_map):
    version = CourseMindMapVersion.query.filter_by(id=mind_map.current_version_id).first()
    return {
        "id": mind_map.id,
        "course_id": mind_map.course_id,
        "owner_user_id": mind_map.owner_user_id,
        "title": mind_map.title,
        "scope_type": mind_map.scope_type or "course",
        "lesson_ids": mind_map.lesson_ids or [],
        "status": mind_map.status,
        "current_version_id": mind_map.current_version_id,
        "current_version": mind_map_version_to_dict(mind_map, version),
        "created_at": mind_map.created_at.isoformat() if mind_map.created_at else None,
        "updated_at": mind_map.updated_at.isoformat() if mind_map.updated_at else None,
    }


def refresh_student_insights(course_id, actor):
    _teacher(course_id, actor)
    students = CourseMembership.query.filter_by(
        course_id=course_id,
        role="student",
        status="active",
    ).all()
    published_assignments = Assignment.query.filter_by(
        course_id=course_id,
        status="published",
    ).all()
    assignments_by_id = {item.id: item for item in published_assignments}
    assignment_ids = list(assignments_by_id)
    submissions = (
        Submission.query.filter(Submission.assignment_id.in_(assignment_ids)).all()
        if assignment_ids
        else []
    )
    submissions_by_student = defaultdict(list)
    for submission in submissions:
        submissions_by_student[submission.student_user_id].append(submission)
    lessons = {
        row.id: row for row in Lesson.query.filter_by(course_id=course_id).all()
    }
    snapshots = []
    for membership in students:
        attempts = (
            MockExamAttempt.query.filter(
                MockExamAttempt.course_id == course_id,
                MockExamAttempt.student_user_id == membership.user_id,
                MockExamAttempt.status.in_(("submitted", "pending_review")),
            )
            .order_by(MockExamAttempt.submitted_at.asc())
            .all()
        )
        item_evidence = [
            row
            for attempt in attempts
            for row in (attempt.evidence_json or [])
        ]
        assignment_feedback_evidence = _assignment_feedback_evidence(
            course_id,
            membership.user_id,
        )
        weaknesses, recommendations = _weakness_projection(
            item_evidence + assignment_feedback_evidence
        )
        objective = [
            row for row in item_evidence if row.get("correct") is not None
        ]
        accuracy = (
            sum(1 for row in objective if row["correct"]) / len(objective)
            if objective
            else None
        )
        evidence = [
            {
                "object_type": "mock_exam_attempt",
                "object_id": attempt.id,
                "assessment_id": attempt.paper_version_id,
                "assessment_title": "模拟考试",
                "paper_version_id": attempt.paper_version_id,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "normalized_score": _normalized_score(
                    attempt.score,
                    attempt.max_score,
                ),
                "accuracy": attempt.accuracy,
                "score_status": "deterministic",
                "submitted_at": (
                    attempt.submitted_at.isoformat()
                    if attempt.submitted_at
                    else None
                ),
            }
            for attempt in attempts
        ]
        assignment_evidence = []
        pending_review_count = 0
        for submission in submissions_by_student.get(membership.user_id, []):
            assignment = assignments_by_id.get(submission.assignment_id)
            if not assignment or submission.status == "draft":
                continue
            lesson = lessons.get(assignment.lesson_id)
            if submission.final_score is None or not submission.graded_at:
                pending_review_count += 1
                continue
            assignment_evidence.append(
                {
                    "object_type": "assignment_submission",
                    "object_id": submission.id,
                    "assessment_id": assignment.id,
                    "assessment_title": assignment.title,
                    "assignment_id": assignment.id,
                    "lesson_id": assignment.lesson_id,
                    "learning_domain": (
                        lesson.learning_domain if lesson else None
                    ),
                    "score": submission.final_score,
                    "max_score": assignment.max_score,
                    "normalized_score": _normalized_score(
                        submission.final_score,
                        assignment.max_score,
                    ),
                    "score_status": "teacher_confirmed",
                    "submitted_at": (
                        submission.submitted_at.isoformat()
                        if submission.submitted_at
                        else None
                    ),
                    "graded_at": submission.graded_at.isoformat(),
                }
            )
        evidence = assignment_evidence + evidence
        official_scores = [
            row["normalized_score"]
            for row in evidence
            if row.get("normalized_score") is not None
        ]
        submitted_assignment_count = sum(
            1
            for row in submissions_by_student.get(membership.user_id, [])
            if row.status != "draft"
        )
        assignment_completion_rate = (
            submitted_assignment_count / len(published_assignments)
            if published_assignments
            else 0.0
        )
        if official_scores or item_evidence:
            data_state = "ready"
        elif pending_review_count:
            data_state = "pending_review"
        else:
            data_state = "insufficient"
        snapshot = StudentInsightSnapshot(
            course_id=course_id,
            student_user_id=membership.user_id,
            data_state=data_state,
            summary_json={
                "accuracy": accuracy,
                "evidence_count": (
                    len(item_evidence) + len(assignment_feedback_evidence)
                ),
                "assignment_feedback_evidence_count": len(
                    assignment_feedback_evidence
                ),
                "attempt_count": len(attempts),
                "official_score_count": len(official_scores),
                "official_average_score": (
                    round(sum(official_scores) / len(official_scores), 2)
                    if official_scores
                    else None
                ),
                "assignment_completion_rate": round(
                    assignment_completion_rate,
                    4,
                ),
                "pending_review_count": pending_review_count,
            },
            evidence_json=evidence,
            weaknesses_json=weaknesses,
            recommendations_json=recommendations,
            generated_by_user_id=actor,
        )
        db.session.add(snapshot)
        snapshots.append(snapshot)
    db.session.flush()
    return snapshots


def _normalized_score(score, max_score):
    try:
        score = float(score)
        max_score = float(max_score)
    except (TypeError, ValueError):
        return None
    if max_score <= 0:
        return None
    return round(max(0.0, min(score / max_score * 100, 100.0)), 2)


def _score_distribution(scores):
    buckets = [
        ("0–59", 0, 60),
        ("60–69", 60, 70),
        ("70–79", 70, 80),
        ("80–89", 80, 90),
        ("90–100", 90, 101),
    ]
    return [
        {
            "label": label,
            "minimum": lower,
            "maximum": 100 if upper == 101 else upper - 1,
            "count": sum(1 for score in scores if lower <= score < upper),
        }
        for label, lower, upper in buckets
    ]


def build_class_insight_overview(course_id):
    """Aggregate only official, normalized grade evidence for one course."""
    students = CourseMembership.query.filter_by(
        course_id=course_id,
        role="student",
        status="active",
    ).all()
    published_assignments = Assignment.query.filter_by(
        course_id=course_id,
        status="published",
    ).all()
    assignment_ids = [item.id for item in published_assignments]
    submissions = (
        Submission.query.filter(Submission.assignment_id.in_(assignment_ids)).all()
        if assignment_ids
        else []
    )
    assignment_by_id = {item.id: item for item in published_assignments}
    evidence = []
    pending_review_count = 0
    submitted_assignment_count = 0
    for submission in submissions:
        if submission.status == "draft":
            continue
        submitted_assignment_count += 1
        assignment = assignment_by_id.get(submission.assignment_id)
        if not assignment:
            continue
        if submission.final_score is None or not submission.graded_at:
            pending_review_count += 1
            continue
        normalized = _normalized_score(
            submission.final_score,
            assignment.max_score,
        )
        if normalized is None:
            continue
        evidence.append(
            {
                "student_user_id": submission.student_user_id,
                "object_type": "assignment_submission",
                "assessment_id": assignment.id,
                "assessment_title": assignment.title,
                "normalized_score": normalized,
                "submitted_at": submission.submitted_at,
            }
        )
    attempts = MockExamAttempt.query.filter(
        MockExamAttempt.course_id == course_id,
        MockExamAttempt.status.in_(("submitted", "pending_review")),
        MockExamAttempt.score.isnot(None),
    ).all()
    for attempt in attempts:
        normalized = _normalized_score(attempt.score, attempt.max_score)
        if normalized is None:
            continue
        evidence.append(
            {
                "student_user_id": attempt.student_user_id,
                "object_type": "mock_exam_attempt",
                "assessment_id": attempt.paper_version_id,
                "assessment_title": "模拟考试",
                "normalized_score": normalized,
                "submitted_at": attempt.submitted_at,
            }
        )
    scores = [row["normalized_score"] for row in evidence]
    trend_groups = defaultdict(list)
    trend_meta = {}
    for row in evidence:
        key = (row["object_type"], row["assessment_id"])
        trend_groups[key].append(row["normalized_score"])
        trend_meta[key] = row
    trend = []
    for key, values in trend_groups.items():
        meta = trend_meta[key]
        timestamps = [
            row["submitted_at"]
            for row in evidence
            if (row["object_type"], row["assessment_id"]) == key
            and row.get("submitted_at")
        ]
        trend.append(
            {
                "object_type": key[0],
                "assessment_id": key[1],
                "assessment_title": meta["assessment_title"],
                "average_score": round(sum(values) / len(values), 2),
                "graded_count": len(values),
                "submitted_at": max(timestamps).isoformat() if timestamps else None,
            }
        )
    trend.sort(key=lambda row: row.get("submitted_at") or "")
    expected_assignments = len(students) * len(published_assignments)
    return {
        "course_id": course_id,
        "data_state": "ready" if scores else (
            "pending_review" if pending_review_count else "insufficient"
        ),
        "score_unit": "percentage",
        "official_score_policy": "deterministic_or_teacher_confirmed",
        "student_count": len(students),
        "graded_student_count": len(
            {row["student_user_id"] for row in evidence}
        ),
        "pending_review_count": pending_review_count,
        "completion_rate": round(
            submitted_assignment_count / expected_assignments,
            4,
        ) if expected_assignments else 0.0,
        "evidence_count": len(evidence),
        "highest_score": max(scores) if scores else None,
        "lowest_score": min(scores) if scores else None,
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "median_score": round(float(median(scores)), 2) if scores else None,
        "score_distribution": _score_distribution(scores),
        "trend": trend,
    }


def build_assignment_grade_overview(course_id, assignment_id=None):
    """Build one assignment distribution plus a course-wide assignment trend."""
    assignments = (
        Assignment.query.filter_by(course_id=course_id, status="published")
        .order_by(Assignment.published_at.asc(), Assignment.created_at.asc())
        .all()
    )
    if not assignments:
        return {
            "course_id": course_id,
            "data_state": "insufficient",
            "assignment_catalog": [],
            "selected_assignment": None,
            "score_distribution": _score_distribution([]),
            "course_assignment_trend": [],
            "graded_count": 0,
            "pending_review_count": 0,
        }
    by_id = {row.id: row for row in assignments}
    if assignment_id and assignment_id not in by_id:
        raise LearningServiceError(
            "assignment not found", 404, "assignment_not_found"
        )
    assignment_ids = list(by_id)
    submissions = Submission.query.filter(
        Submission.assignment_id.in_(assignment_ids),
        Submission.status != "draft",
    ).all()
    by_assignment = defaultdict(list)
    for submission in submissions:
        by_assignment[submission.assignment_id].append(submission)

    def official_scores(assignment):
        rows = []
        for submission in by_assignment.get(assignment.id, []):
            if submission.final_score is None or not submission.graded_at:
                continue
            normalized = _normalized_score(submission.final_score, assignment.max_score)
            if normalized is not None:
                rows.append(normalized)
        return rows

    selected = by_id.get(assignment_id) if assignment_id else None
    if not selected:
        selected = next(
            (row for row in reversed(assignments) if official_scores(row)),
            assignments[-1],
        )
    scores = official_scores(selected)
    selected_submissions = by_assignment.get(selected.id, [])
    pending_count = sum(
        1
        for row in selected_submissions
        if row.final_score is None or not row.graded_at
    )
    students = CourseMembership.query.filter_by(
        course_id=course_id, role="student", status="active"
    ).count()
    trend = []
    for assignment in assignments:
        values = official_scores(assignment)
        trend.append(
            {
                "assignment_id": assignment.id,
                "assessment_id": assignment.id,
                "assessment_title": assignment.title,
                "average_score": round(sum(values) / len(values), 2) if values else None,
                "highest_score": max(values) if values else None,
                "lowest_score": min(values) if values else None,
                "graded_count": len(values),
                "published_at": assignment.published_at.isoformat() if assignment.published_at else None,
            }
        )
    catalog = [
        {
            "id": row.id,
            "title": row.title,
            "max_score": row.max_score,
            "graded_count": len(official_scores(row)),
            "published_at": row.published_at.isoformat() if row.published_at else None,
        }
        for row in assignments
    ]
    return {
        "course_id": course_id,
        "data_state": "ready" if scores else ("pending_review" if pending_count else "insufficient"),
        "score_unit": "percentage",
        "assignment_catalog": catalog,
        "selected_assignment": next(row for row in catalog if row["id"] == selected.id),
        "student_count": students,
        "submitted_count": len(selected_submissions),
        "graded_count": len(scores),
        "pending_review_count": pending_count,
        "submission_rate": round(len(selected_submissions) / students, 4) if students else 0.0,
        "highest_score": max(scores) if scores else None,
        "lowest_score": min(scores) if scores else None,
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "median_score": round(float(median(scores)), 2) if scores else None,
        "score_distribution": _score_distribution(scores),
        "course_assignment_trend": trend,
    }


def insight_to_dict(snapshot):
    return {
        "id": snapshot.id,
        "course_id": snapshot.course_id,
        "student_user_id": snapshot.student_user_id,
        "data_state": snapshot.data_state,
        "summary": snapshot.summary_json or {},
        "evidence": snapshot.evidence_json or [],
        "weaknesses": snapshot.weaknesses_json or [],
        "recommendations": snapshot.recommendations_json or [],
        "generated_by_user_id": snapshot.generated_by_user_id,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }
