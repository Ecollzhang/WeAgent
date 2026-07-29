"""HTTP APIs for student products and teacher evidence views."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .access import active_membership
from .extensions import db
from .learning_models import (
    CourseMindMap,
    MockExamAttempt,
    StudentInsightSnapshot,
    WeaknessAnalysisSnapshot,
)
from .learning_service import (
    LearningServiceError,
    add_mind_map_version,
    attempt_to_dict,
    build_class_insight_overview,
    create_mind_map,
    create_mock_exam,
    create_weakness_snapshot,
    insight_to_dict,
    mind_map_to_dict,
    refresh_student_insights,
    save_mock_answers,
    submit_mock_exam,
    weakness_to_dict,
)


education_learning_api = Blueprint("education_learning_api", __name__)


def _error(error):
    db.session.rollback()
    return jsonify(
        {"error": error.message, "error_code": error.error_code}
    ), error.status_code


@education_learning_api.post("/courses/<course_id>/mock-exams")
@jwt_required()
def create_mock_exam_route(course_id):
    try:
        attempt = create_mock_exam(
            course_id,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(attempt_to_dict(attempt)), 201


@education_learning_api.get("/courses/<course_id>/mock-exams")
@jwt_required()
def list_mock_exams(course_id):
    actor = get_jwt_identity()
    if not active_membership(course_id, actor, "student"):
        return jsonify({"error": "course not found"}), 404
    rows = (
        MockExamAttempt.query.filter_by(
            course_id=course_id,
            student_user_id=actor,
        )
        .order_by(MockExamAttempt.created_at.desc())
        .all()
    )
    return jsonify({"items": [attempt_to_dict(row) for row in rows]})


@education_learning_api.get("/mock-exams/<attempt_id>")
@jwt_required()
def get_mock_exam(attempt_id):
    actor = get_jwt_identity()
    attempt = MockExamAttempt.query.filter_by(
        id=attempt_id,
        student_user_id=actor,
    ).first()
    if not attempt or not active_membership(attempt.course_id, actor, "student"):
        return jsonify({"error": "mock exam not found"}), 404
    return jsonify(attempt_to_dict(attempt))


@education_learning_api.put("/mock-exams/<attempt_id>/answers")
@jwt_required()
def save_mock_exam_answers(attempt_id):
    try:
        attempt = save_mock_answers(
            attempt_id,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(attempt_to_dict(attempt))


@education_learning_api.post("/mock-exams/<attempt_id>/submit")
@jwt_required()
def submit_mock_exam_route(attempt_id):
    try:
        attempt = submit_mock_exam(attempt_id, get_jwt_identity())
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(attempt_to_dict(attempt))


@education_learning_api.post("/courses/<course_id>/weakness-analysis")
@jwt_required()
def create_weakness_route(course_id):
    try:
        snapshot = create_weakness_snapshot(course_id, get_jwt_identity())
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(weakness_to_dict(snapshot)), 201


@education_learning_api.get("/courses/<course_id>/weakness-analysis")
@jwt_required()
def get_weakness_route(course_id):
    actor = get_jwt_identity()
    if not active_membership(course_id, actor, "student"):
        return jsonify({"error": "course not found"}), 404
    snapshot = (
        WeaknessAnalysisSnapshot.query.filter_by(
            course_id=course_id,
            student_user_id=actor,
        )
        .order_by(WeaknessAnalysisSnapshot.created_at.desc())
        .first()
    )
    if not snapshot:
        return jsonify(
            {
                "course_id": course_id,
                "student_user_id": actor,
                "data_state": "insufficient",
                "evidence": [],
                "weaknesses": [],
                "recommendations": [],
            }
        )
    return jsonify(weakness_to_dict(snapshot))


@education_learning_api.post("/courses/<course_id>/mind-maps")
@jwt_required()
def create_mind_map_route(course_id):
    try:
        mind_map = create_mind_map(
            course_id,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(mind_map_to_dict(mind_map)), 201


@education_learning_api.get("/courses/<course_id>/mind-maps")
@jwt_required()
def list_mind_maps(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = CourseMindMap.query.filter_by(course_id=course_id, status="active")
    if membership.role != "teacher":
        query = query.filter_by(owner_user_id=actor)
    rows = query.order_by(CourseMindMap.updated_at.desc()).all()
    return jsonify({"items": [mind_map_to_dict(row) for row in rows]})


@education_learning_api.get("/mind-maps/<mind_map_id>")
@jwt_required()
def get_mind_map_route(mind_map_id):
    actor = get_jwt_identity()
    mind_map = CourseMindMap.query.filter_by(id=mind_map_id, status="active").first()
    membership = (
        active_membership(mind_map.course_id, actor) if mind_map else None
    )
    if not mind_map or not membership or (
        membership.role != "teacher" and mind_map.owner_user_id != actor
    ):
        return jsonify({"error": "mind map not found"}), 404
    return jsonify(mind_map_to_dict(mind_map))


@education_learning_api.post("/mind-maps/<mind_map_id>/versions")
@jwt_required()
def add_mind_map_version_route(mind_map_id):
    mind_map = CourseMindMap.query.filter_by(id=mind_map_id, status="active").first()
    if not mind_map:
        return jsonify({"error": "mind map not found"}), 404
    try:
        add_mind_map_version(
            mind_map,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(mind_map_to_dict(mind_map)), 201


@education_learning_api.post("/courses/<course_id>/student-insights/refresh")
@jwt_required()
def refresh_insights_route(course_id):
    try:
        snapshots = refresh_student_insights(course_id, get_jwt_identity())
        db.session.commit()
    except LearningServiceError as error:
        return _error(error)
    return jsonify(
        {
            "class_overview": build_class_insight_overview(course_id),
            "items": [insight_to_dict(row) for row in snapshots],
        }
    ), 201


@education_learning_api.get("/courses/<course_id>/student-insights")
@jwt_required()
def list_insights_route(course_id):
    actor = get_jwt_identity()
    if not active_membership(course_id, actor, "teacher"):
        return jsonify({"error": "course not found"}), 404
    rows = (
        StudentInsightSnapshot.query.filter_by(course_id=course_id)
        .order_by(StudentInsightSnapshot.created_at.desc())
        .all()
    )
    latest = {}
    for row in rows:
        latest.setdefault(row.student_user_id, row)
    return jsonify(
        {
            "class_overview": build_class_insight_overview(course_id),
            "items": [insight_to_dict(row) for row in latest.values()],
        }
    )
