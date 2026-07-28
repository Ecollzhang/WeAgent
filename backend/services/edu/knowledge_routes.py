"""Course Knowledge Center HTTP API."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .access import active_membership
from .extensions import db
from .knowledge_models import (
    AssessmentItem,
    AssessmentPaper,
    KnowledgeResource,
)
from .knowledge_service import (
    KnowledgeServiceError,
    add_question_version,
    compose_paper,
    create_knowledge_resource,
    create_question,
    knowledge_resource_to_dict,
    paper_to_dict,
    publish_paper,
    publish_question,
    question_to_dict,
)


education_knowledge_api = Blueprint("education_knowledge_api", __name__)


def _service_error(error):
    db.session.rollback()
    return jsonify(
        {"error": error.message, "error_code": error.error_code}
    ), error.status_code


@education_knowledge_api.post("/courses/<course_id>/questions")
@jwt_required()
def create_question_route(course_id):
    try:
        item = create_question(
            course_id,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(question_to_dict(item, include_answer=True)), 201


@education_knowledge_api.get("/courses/<course_id>/questions")
@jwt_required()
def list_questions(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = AssessmentItem.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        query = query.filter_by(status="published")
    else:
        query = query.filter(AssessmentItem.status != "archived")
    rows = query.order_by(AssessmentItem.created_at.desc()).all()
    return jsonify(
        {
            "items": [
                question_to_dict(
                    row,
                    include_answer=membership.role == "teacher",
                )
                for row in rows
            ]
        }
    )


@education_knowledge_api.post("/questions/<question_id>/versions")
@jwt_required()
def create_question_version_route(question_id):
    item = AssessmentItem.query.filter_by(id=question_id).first()
    if not item:
        return jsonify({"error": "question not found"}), 404
    try:
        add_question_version(
            item,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(question_to_dict(item, include_answer=True)), 201


@education_knowledge_api.post("/questions/<question_id>/publish")
@jwt_required()
def publish_question_route(question_id):
    item = AssessmentItem.query.filter_by(id=question_id).first()
    if not item:
        return jsonify({"error": "question not found"}), 404
    try:
        publish_question(item, get_jwt_identity())
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(question_to_dict(item, include_answer=True))


@education_knowledge_api.post("/courses/<course_id>/papers/compose")
@jwt_required()
def compose_paper_route(course_id):
    try:
        paper = compose_paper(
            course_id,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(paper_to_dict(paper)), 201


@education_knowledge_api.get("/courses/<course_id>/papers")
@jwt_required()
def list_papers(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = AssessmentPaper.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        query = query.filter_by(status="published")
    else:
        query = query.filter(AssessmentPaper.status != "archived")
    rows = query.order_by(AssessmentPaper.created_at.desc()).all()
    return jsonify({"items": [paper_to_dict(row) for row in rows]})


@education_knowledge_api.post("/papers/<paper_id>/publish")
@jwt_required()
def publish_paper_route(paper_id):
    paper = AssessmentPaper.query.filter_by(id=paper_id).first()
    if not paper:
        return jsonify({"error": "paper not found"}), 404
    try:
        publish_paper(paper, get_jwt_identity())
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(paper_to_dict(paper))


@education_knowledge_api.post("/courses/<course_id>/knowledge-resources")
@jwt_required()
def create_resource_route(course_id):
    try:
        resource = create_knowledge_resource(
            course_id,
            get_jwt_identity(),
            request.get_json(silent=True) or {},
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(knowledge_resource_to_dict(resource)), 201


@education_knowledge_api.get("/courses/<course_id>/knowledge-resources")
@jwt_required()
def list_resources(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = KnowledgeResource.query.filter_by(course_id=course_id, status="active")
    if membership.role != "teacher":
        query = query.filter_by(visibility_scope="course_published")
    rows = query.order_by(KnowledgeResource.created_at.desc()).all()
    return jsonify({"items": [knowledge_resource_to_dict(row) for row in rows]})


@education_knowledge_api.get("/courses/<course_id>/knowledge-center")
@jwt_required()
def knowledge_center_summary(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    question_query = AssessmentItem.query.filter_by(course_id=course_id)
    paper_query = AssessmentPaper.query.filter_by(course_id=course_id)
    resource_query = KnowledgeResource.query.filter_by(course_id=course_id, status="active")
    if membership.role != "teacher":
        question_query = question_query.filter_by(status="published")
        paper_query = paper_query.filter_by(status="published")
        resource_query = resource_query.filter_by(
            visibility_scope="course_published"
        )
    return jsonify(
        {
            "course_id": course_id,
            "membership_role": membership.role,
            "counts": {
                "questions": question_query.count(),
                "papers": paper_query.count(),
                "knowledge_resources": resource_query.count(),
            },
        }
    )

