"""Application services for mock exams, mind maps, and student insight."""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .access import active_membership
from .content_models import LearningEvent, Lesson
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
            id=item.current_version_id
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


def create_weakness_snapshot(course_id, actor):
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
    weaknesses, recommendations = _weakness_projection(evidence)
    snapshot = WeaknessAnalysisSnapshot(
        course_id=course_id,
        student_user_id=actor,
        data_state="ready" if evidence else "insufficient",
        evidence=evidence,
        weaknesses=weaknesses,
        recommendations=recommendations,
        source_fingerprint=_checksum(
            [
                {
                    "attempt_id": attempt.id,
                    "updated_at": (
                        attempt.updated_at.isoformat()
                        if attempt.updated_at
                        else None
                    ),
                }
                for attempt in attempts
            ]
        ),
    )
    db.session.add(snapshot)
    db.session.flush()
    return snapshot


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
    return tree


def _create_mind_map_version(mind_map, actor, tree, source_refs, change_summary):
    _validate_tree(tree)
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
        tree_json=tree,
        source_refs=list(dict.fromkeys(source_refs)),
        change_summary=str(change_summary or "")[:500],
        checksum=_checksum({"tree": tree, "source_refs": source_refs}),
        created_by_user_id=actor,
    )
    db.session.add(version)
    db.session.flush()
    mind_map.current_version_id = version.id
    return version


def create_mind_map(course_id, actor, data):
    _student(course_id, actor)
    course = Course.query.filter_by(id=course_id, status="active").one()
    lessons = (
        Lesson.query.filter_by(course_id=course_id, status="published")
        .order_by(Lesson.position.asc(), Lesson.created_at.asc())
        .all()
    )
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
    )
    db.session.add(mind_map)
    db.session.flush()
    _create_mind_map_version(
        mind_map,
        actor,
        {
            "id": f"course:{course.id}",
            "label": course.title,
            "children": children,
            "source_ref": course.id,
            "source_type": "course",
        },
        source_refs,
        "Generated from published course sources",
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
        data.get("tree"),
        data.get("source_refs") or [],
        data.get("change_summary") or "",
    )
    return mind_map


def mind_map_to_dict(mind_map):
    version = CourseMindMapVersion.query.filter_by(
        id=mind_map.current_version_id
    ).first()
    return {
        "id": mind_map.id,
        "course_id": mind_map.course_id,
        "owner_user_id": mind_map.owner_user_id,
        "title": mind_map.title,
        "status": mind_map.status,
        "current_version_id": mind_map.current_version_id,
        "current_version": (
            {
                "id": version.id,
                "version_number": version.version_number,
                "tree": version.tree_json,
                "source_refs": version.source_refs or [],
                "change_summary": version.change_summary,
                "checksum": version.checksum,
                "created_by_user_id": version.created_by_user_id,
                "created_at": (
                    version.created_at.isoformat() if version.created_at else None
                ),
            }
            if version
            else None
        ),
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
        weaknesses, recommendations = _weakness_projection(item_evidence)
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
                "paper_version_id": attempt.paper_version_id,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "accuracy": attempt.accuracy,
                "submitted_at": (
                    attempt.submitted_at.isoformat()
                    if attempt.submitted_at
                    else None
                ),
            }
            for attempt in attempts
        ]
        snapshot = StudentInsightSnapshot(
            course_id=course_id,
            student_user_id=membership.user_id,
            data_state="ready" if item_evidence else "insufficient",
            summary_json={
                "accuracy": accuracy,
                "evidence_count": len(item_evidence),
                "attempt_count": len(attempts),
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
