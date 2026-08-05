"""Course Knowledge Center HTTP API."""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .access import active_membership
from .extensions import db
from .asset_service import AssetServiceError
from .knowledge_models import (
    AssessmentItem,
    AssessmentPaper,
    AssessmentStimulus,
    AssessmentStimulusVersion,
    KnowledgeResource,
)
from .knowledge_service import (
    KnowledgeServiceError,
    add_paper_version,
    add_question_version,
    add_stimulus_version,
    compose_paper,
    create_knowledge_resource,
    create_question,
    create_stimulus,
    knowledge_resource_to_dict,
    paper_to_dict,
    paper_preview,
    publish_paper,
    publish_question,
    publish_stimulus,
    question_to_dict,
    stimulus_to_dict,
)
from .rag_ingestion import (
    ingest_knowledge_resource,
    refresh_knowledge_resource_status,
)
from .web_resource_service import WebResourceAdoptionError, adopt_web_knowledge_resource


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
    use_published = membership.role != "teacher"
    items = [
        question_to_dict(
            row,
            include_answer=membership.role == "teacher",
            use_published=use_published,
        )
        for row in rows
    ]
    groups = {}
    referenced_version_ids = {
        (item.get("current_version") or {}).get("stimulus_version_id")
        for item in items
        if (item.get("current_version") or {}).get("stimulus_version_id")
    }
    stable_stimulus_ids = {
        row.id: row.stimulus_id
        for row in AssessmentStimulusVersion.query.filter(
            AssessmentStimulusVersion.id.in_(referenced_version_ids)
        ).all()
    } if referenced_version_ids else {}
    for item in items:
        version = item.get("current_version") or {}
        stimulus_version_id = version.get("stimulus_version_id")
        if stimulus_version_id:
            stimulus_id = stable_stimulus_ids.get(stimulus_version_id)
            if stimulus_id:
                groups.setdefault(stimulus_id, []).append(item)
    stimuli = []
    if groups:
        stimulus_rows = AssessmentStimulus.query.filter_by(course_id=course_id).all()
        for stimulus in stimulus_rows:
            serialized = stimulus_to_dict(stimulus, use_published=use_published)
            grouped_questions = groups.get(stimulus.id, [])
            if not grouped_questions:
                continue
            grouped_questions.sort(
                key=lambda row: (row.get("current_version") or {}).get("stimulus_order") or 0
            )
            serialized["questions"] = grouped_questions
            serialized["question_count"] = len(grouped_questions)
            stimuli.append(serialized)
    standalone = [
        item for item in items if not (item.get("current_version") or {}).get("stimulus_version_id")
    ]
    return jsonify({"items": items, "stimuli": stimuli, "standalone_items": standalone})


@education_knowledge_api.post("/courses/<course_id>/stimuli")
@jwt_required()
def create_stimulus_route(course_id):
    try:
        stimulus = create_stimulus(
            course_id, get_jwt_identity(), request.get_json(silent=True) or {}
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(stimulus_to_dict(stimulus)), 201


@education_knowledge_api.get("/courses/<course_id>/stimuli")
@jwt_required()
def list_stimuli(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    query = AssessmentStimulus.query.filter_by(course_id=course_id)
    if membership.role != "teacher":
        query = query.filter_by(status="published")
    else:
        query = query.filter(AssessmentStimulus.status != "archived")
    rows = query.order_by(AssessmentStimulus.created_at.desc()).all()
    return jsonify(
        {
            "items": [
                stimulus_to_dict(row, use_published=membership.role != "teacher")
                for row in rows
            ]
        }
    )


@education_knowledge_api.post("/stimuli/<stimulus_id>/versions")
@jwt_required()
def create_stimulus_version_route(stimulus_id):
    stimulus = AssessmentStimulus.query.filter_by(id=stimulus_id).first()
    if not stimulus:
        return jsonify({"error": "stimulus not found"}), 404
    try:
        add_stimulus_version(
            stimulus, get_jwt_identity(), request.get_json(silent=True) or {}
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(stimulus_to_dict(stimulus)), 201


@education_knowledge_api.post("/stimuli/<stimulus_id>/publish")
@jwt_required()
def publish_stimulus_route(stimulus_id):
    stimulus = AssessmentStimulus.query.filter_by(id=stimulus_id).first()
    if not stimulus:
        return jsonify({"error": "stimulus not found"}), 404
    try:
        publish_stimulus(stimulus, get_jwt_identity())
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(stimulus_to_dict(stimulus))


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
        query = query.filter(
            AssessmentPaper.status == "published",
            db.or_(
                AssessmentPaper.generated_for_user_id.is_(None),
                AssessmentPaper.generated_for_user_id == actor,
            ),
        )
    else:
        query = query.filter(AssessmentPaper.status != "archived")
    rows = query.order_by(AssessmentPaper.created_at.desc()).all()
    return jsonify(
        {
            "items": [
                paper_to_dict(row, use_published=membership.role != "teacher")
                for row in rows
            ]
        }
    )


@education_knowledge_api.get("/papers/<paper_id>")
@jwt_required()
def get_paper_route(paper_id):
    paper = AssessmentPaper.query.filter_by(id=paper_id).first()
    actor = get_jwt_identity()
    membership = active_membership(paper.course_id, actor) if paper else None
    if not paper or not membership or (membership.role != "teacher" and paper.status != "published"):
        return jsonify({"error": "paper not found"}), 404
    return jsonify(paper_to_dict(paper, use_published=membership.role != "teacher"))


@education_knowledge_api.get("/papers/<paper_id>/preview")
@jwt_required()
def preview_paper_route(paper_id):
    paper = AssessmentPaper.query.filter_by(id=paper_id).first()
    if not paper:
        return jsonify({"error": "paper not found"}), 404
    try:
        payload = paper_preview(
            paper,
            get_jwt_identity(),
            mode=request.args.get("mode", "student"),
            version_id=request.args.get("version_id"),
        )
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(payload)


@education_knowledge_api.post("/papers/<paper_id>/versions")
@jwt_required()
def create_paper_version_route(paper_id):
    paper = AssessmentPaper.query.filter_by(id=paper_id).first()
    if not paper:
        return jsonify({"error": "paper not found"}), 404
    try:
        add_paper_version(
            paper, get_jwt_identity(), request.get_json(silent=True) or {}
        )
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(paper_to_dict(paper)), 201


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
        ingest_knowledge_resource(resource)
        db.session.commit()
    except KnowledgeServiceError as error:
        return _service_error(error)
    return jsonify(knowledge_resource_to_dict(resource)), 201


@education_knowledge_api.post("/courses/<course_id>/knowledge-resources/adopt-url")
@jwt_required()
def adopt_web_resource(course_id):
    actor = get_jwt_identity()
    membership = active_membership(course_id, actor)
    if not membership or membership.role != "teacher":
        return jsonify({"error": "course not found"}), 404
    try:
        resource = adopt_web_knowledge_resource(
            course_id=course_id,
            actor=actor,
            data=request.get_json(silent=True) or {},
            fetcher=current_app.config.get("EDUCATION_CONTENT_FETCHER"),
        )
        db.session.commit()
        ingest_knowledge_resource(resource)
        db.session.commit()
    except (AssetServiceError, KnowledgeServiceError) as error:
        return _service_error(error)
    except WebResourceAdoptionError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": str(error)[:500], "error_code": "web_resource_fetch_failed"}), 422
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
    refreshed = False
    for row in rows:
        refreshed = refresh_knowledge_resource_status(row) or refreshed
    if refreshed:
        db.session.commit()
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
