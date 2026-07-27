"""Subject-pack, Agent-team and safe workflow APIs."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .extensions import db
from .routes import teacher_course_or_none
from .subject_packs import AGENT_ROLES, SUBJECT_PACKS, WORKFLOW_TEMPLATES
from .workflow_models import EducationWorkflow


education_workflow_api = Blueprint("education_workflow_api", __name__)
NODE_TYPES = {"agent_task", "capability_task", "transform", "validation", "approval"}
EXECUTABLE_FIELDS = {"code", "script", "shell", "command", "expression"}
ALLOWED_MODES = {"strict", "guided"}


def validate_workflow(payload):
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(nodes, list) or not nodes:
        return "nodes are required"
    if not isinstance(edges, list):
        return "edges must be a list"
    if len(nodes) > 30:
        return "workflow exceeds max nodes"

    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id"):
            return "every node requires an id"
        if node["id"] in by_id:
            return "node ids must be unique"
        if node.get("type") not in NODE_TYPES:
            return "unsupported node type"
        if EXECUTABLE_FIELDS.intersection(node):
            return "workflow nodes cannot contain executable code"
        by_id[node["id"]] = node

    adjacency = {node_id: [] for node_id in by_id}
    indegree = {node_id: 0 for node_id in by_id}
    for edge in edges:
        source, target = edge.get("from"), edge.get("to")
        if source not in by_id or target not in by_id:
            return "edge references an unknown node"
        adjacency[source].append(target)
        indegree[target] += 1

    queue = [node_id for node_id, count in indegree.items() if count == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(by_id):
        return "workflow cannot contain a cycle"

    gates = {
        node.get("gate")
        for node in nodes
        if node.get("type") == "approval"
    }
    if "teacher_publish" not in gates:
        return "required approval gate teacher_publish is missing"
    return None


@education_workflow_api.get("/subject-packs")
@jwt_required()
def list_subject_packs():
    return jsonify({"items": SUBJECT_PACKS})


@education_workflow_api.get("/agent-roles")
@jwt_required()
def list_agent_roles():
    return jsonify({"items": AGENT_ROLES})


@education_workflow_api.get("/workflow-templates")
@jwt_required()
def list_workflow_templates():
    return jsonify({"items": WORKFLOW_TEMPLATES})


@education_workflow_api.post("/courses/<course_id>/workflows")
@jwt_required()
def create_workflow(course_id):
    user_id = get_jwt_identity()
    if not teacher_course_or_none(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    payload = request.get_json(silent=True) or {}
    if not str(payload.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    if payload.get("scope", "course") not in {"personal", "course"}:
        return jsonify({"error": "scope must be personal or course"}), 400
    if payload.get("execution_mode", "guided") not in ALLOWED_MODES:
        return jsonify({"error": "adaptive workflows are not available in MVP"}), 400
    error = validate_workflow(payload)
    if error:
        return jsonify({"error": error}), 400

    gates = sorted(
        {
            node["gate"]
            for node in payload["nodes"]
            if node.get("type") == "approval" and node.get("gate")
        }
    )
    workflow = EducationWorkflow(
        course_id=course_id,
        owner_user_id=user_id,
        name=payload["name"].strip(),
        scope=payload.get("scope", "course"),
        execution_mode=payload.get("execution_mode", "guided"),
        nodes=payload["nodes"],
        edges=payload["edges"],
        required_approval_gates=gates,
    )
    db.session.add(workflow)
    db.session.commit()
    return jsonify(workflow.to_dict()), 201


@education_workflow_api.get("/courses/<course_id>/workflows")
@jwt_required()
def list_course_workflows(course_id):
    user_id = get_jwt_identity()
    if not teacher_course_or_none(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    workflows = EducationWorkflow.query.filter_by(course_id=course_id).order_by(
        EducationWorkflow.created_at.asc()
    ).all()
    return jsonify({"items": [workflow.to_dict() for workflow in workflows]})
