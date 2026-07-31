"""Subject-pack, Agent-team and safe workflow APIs."""

import json
import re
import threading
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .extensions import db
from .access import active_membership
from .routes import teacher_course_or_none
from .subject_packs import AGENT_ROLES, SUBJECT_PACKS, WORKFLOW_TEMPLATES
from .content_models import Lesson
from .product_agent_runs import (
    build_visible_product_intent,
    build_product_prompt,
    education_action_protocol,
    product_template,
    product_workflow,
)
from .runtime_client import CoreRuntimeError
from .tool_gateway import ToolGatewayError, issue_tool_grant
from .tool_models import EducationToolCall, EducationToolGrant
from .workflow_models import EducationAgentRun, EducationWorkflow


education_workflow_api = Blueprint("education_workflow_api", __name__)
NODE_TYPES = {"agent_task", "capability_task", "transform", "validation", "approval"}
EXECUTABLE_FIELDS = {"code", "script", "shell", "command", "expression"}
ALLOWED_MODES = {"strict", "guided"}
ROLE_RUNTIME = {
    "course_designer": ("_edu_1", "课程设计师"),
    "courseware_maker": ("_edu_2", "课件制作师"),
    "exercise_generator": ("_edu_3", "习题生成器"),
    "learning_analyst": ("_edu_4", "学情分析师"),
    "learning_planner": ("_edu_5", "学习规划师"),
    "practice_coach": ("_edu_6", "练习教练"),
    "note_organizer": ("_edu_7", "笔记整理师"),
    "research_worker": ("_edu_8", "资料研究员"),
    "teaching_reviewer": ("_edu_9", "教学审校员"),
}
ROLE_ARTIFACTS = {
    "course_designer": "/workspace/shared/lesson_plan_draft.json",
    "exercise_generator": "/workspace/shared/exercises_draft.json",
    "teaching_reviewer": "/workspace/shared/review_conclusion.json",
}
TEACHER_WORKFLOW_TOOLS = [
    "edu.course.list",
    "edu.course.members.list",
    "edu.course.context.get",
    "edu.question_bank.search",
    "edu.knowledge.search",
    "edu.courseware.create",
    "edu.asset.attach",
    "edu.question_bank.upsert",
    "edu.paper.compose",
    "edu.student_insight.refresh",
]
REQUIRED_PRODUCT_WRITE_TOOL = {
    "product.roster_import": "edu.course.members.import",
    "product.courseware": "edu.courseware.create",
    "product.student_insight": "edu.student_insight.refresh",
    "product.mock_exam": "edu.mock_exam.create",
    "product.weakness_analysis": "edu.weakness.analyze",
    "product.course_mind_map": "edu.mind_map.create",
}
REQUIRED_PRODUCT_WRITE_AGENT = {
    "product.roster_import": "_edu_1",
    "product.courseware": "_edu_2",
    "product.student_insight": "_edu_4",
    "product.mock_exam": "_edu_6",
    "product.weakness_analysis": "_edu_6",
    "product.course_mind_map": "_edu_7",
}


def _tool_calls_by_agent(run):
    if not run.tool_grant_id:
        return {}
    rows = (
        EducationToolCall.query.filter_by(grant_id=run.tool_grant_id)
        .order_by(EducationToolCall.created_at.asc())
        .all()
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row.agent_id or "unknown", []).append(row.to_dict())
    return grouped


def _attach_tool_calls(run):
    grouped = _tool_calls_by_agent(run)
    nodes = []
    for stored in run.nodes or []:
        node = dict(stored)
        if node.get("type") == "agent_task":
            node["tool_calls"] = grouped.get(node.get("agent_id"), [])
        nodes.append(node)
    run.nodes = nodes
    return run


def _missing_required_product_write(run):
    """Return the required write action when Agents produced only chat output.

    A core Agent node reaching ``done`` proves that the model stopped, not that
    the requested product exists. Product workflows are complete only after the
    scoped tool gateway has recorded their durable write successfully.
    """
    required = REQUIRED_PRODUCT_WRITE_TOOL.get(run.workflow_code)
    if not required or not run.tool_grant_id:
        return required
    adopted = EducationToolCall.query.filter_by(
        grant_id=run.tool_grant_id,
        tool_name=required,
        agent_id=REQUIRED_PRODUCT_WRITE_AGENT.get(run.workflow_code),
        status="completed",
    ).first()
    return None if adopted else required


def _attach_recoverable_draft(run, required_tool):
    """Expose one failed validated write as an editable, non-adopted draft."""
    if not run.tool_grant_id or not required_tool:
        return None
    failed = (
        EducationToolCall.query.filter_by(
            grant_id=run.tool_grant_id,
            tool_name=required_tool,
            status="failed",
        )
        .order_by(EducationToolCall.created_at.desc())
        .first()
    )
    source = (failed.sanitized_input or {}) if failed else {}
    if (
        required_tool != "edu.courseware.create"
        or not isinstance(source.get("source_json"), dict)
    ):
        return None
    draft = {
        "kind": source.get("kind") or "slide_document",
        "schema_name": source.get("schema_name")
        or "weagent.education.slide-document",
        "source_json": source["source_json"],
        "rendered_html": source.get("rendered_html") or "",
        "validation_error": failed.error_message or failed.error_code,
        "adopted": False,
    }
    output = dict(run.output or {})
    output["recoverable_draft"] = draft
    run.output = output
    return draft


def _reconcile_product_completion(run):
    """Repair historical optimistic statuses using the durable write audit."""
    if run.status != "completed":
        return False
    missing_write = _missing_required_product_write(run)
    if not missing_write:
        return False
    run.status = "partial"
    run.error_summary = (
        "Agent 团队已结束，但未写入可验收的业务产物："
        f"缺少成功的 {missing_write} 工具调用。"
    )
    _attach_recoverable_draft(run, missing_write)
    return True


def _revoke_tool_grant(run):
    if not run.tool_grant_id:
        return
    grant = EducationToolGrant.query.filter_by(id=run.tool_grant_id).first()
    if grant and grant.status == "active":
        grant.status = "revoked"
        grant.revoked_at = datetime.utcnow()


def _template(code):
    return next((item for item in WORKFLOW_TEMPLATES if item["code"] == code), None)


def _expire_stale_pending_run(run):
    """Make interrupted background launches retryable after a service restart."""
    started = run.started_at or run.created_at
    launch_timeout = max(
        120,
        int(
            current_app.config.get(
                "EDUCATION_AGENT_LAUNCH_TIMEOUT_SECONDS",
                600,
            )
        ),
    )
    if (
        run.status == "pending"
        and not run.conversation_id
        and started
        and started < datetime.utcnow() - timedelta(seconds=launch_timeout)
    ):
        run.status = "failed"
        run.error_summary = "Agent 启动过程被中断，请重新运行"
        run.finished_at = datetime.utcnow()
        _revoke_tool_grant(run)
        return True
    return False


def _run_nodes(template):
    nodes = []
    for item in template["nodes"]:
        node = dict(item)
        node["status"] = "pending"
        if node["type"] == "agent_task":
            agent_id, agent_name = ROLE_RUNTIME[node["agent_role"]]
            node.update(
                {
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "workspace_path": f"/workspace/agents/{agent_name}",
                    "output": {},
                }
            )
        nodes.append(node)
    return nodes


def _workflow_payload(template, nodes):
    runtime_nodes = [
        node for node in nodes
        if isinstance(node, dict) and node.get("type") == "agent_task"
    ]
    edges = [
        {"from": runtime_nodes[index]["id"], "to": runtime_nodes[index + 1]["id"]}
        for index in range(len(runtime_nodes) - 1)
    ]
    return {
        "id": template["code"],
        "name": template["name"],
        "execution_mode": "server_defined",
        "nodes": [
            {
                key: value
                for key, value in node.items()
                if key
                in {
                    "id",
                    "type",
                    "agent_role",
                    "agent_id",
                    "gate",
                    "finalizer",
                }
            }
            for node in runtime_nodes
        ],
        "edges": edges,
        "parallel_groups": [],
    }


def _extract_json(content):
    text = str(content or "").strip()
    if not text:
        return {}
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else {"value": value}
    except (TypeError, ValueError):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(candidate[start : end + 1])
                return value if isinstance(value, dict) else {"value": value}
            except (TypeError, ValueError):
                pass
    return {"text": text}


def _repair_agent_artifact(
    app, run_id, agent_role, agent_id, artifact_path, authorization, validation_error
):
    """Run the bounded validator → producer repair loop outside polling requests."""
    with app.app_context():
        run = EducationAgentRun.query.filter_by(id=run_id).first()
        if not run:
            return
        try:
            repaired = app.extensions["education_runtime_client"].repair_workspace_json(
                authorization=authorization,
                sandbox_session_id=run.sandbox_session_id,
                agent_id=agent_id,
                path=artifact_path,
                validation_error=validation_error,
                artifact_role=agent_role,
            )
            nodes = []
            for stored in run.nodes or []:
                node = dict(stored)
                if node.get("agent_role") == agent_role:
                    node["output"] = repaired
                    node["validation_status"] = "repaired"
                    node.pop("validation_error", None)
                nodes.append(node)
            output = dict(run.output or {})
            output[agent_role] = repaired
            run.nodes = nodes
            run.output = output
        except CoreRuntimeError as exc:
            nodes = []
            for stored in run.nodes or []:
                node = dict(stored)
                if node.get("agent_role") == agent_role:
                    node["validation_status"] = "failed"
                    node["validation_error"] = str(exc)
                nodes.append(node)
            run.nodes = nodes
        finally:
            db.session.commit()
            db.session.remove()


def _sync_run(run, authorization):
    runtime = current_app.extensions["education_runtime_client"]
    snapshot = runtime.get_snapshot(
        authorization=authorization,
        conversation_id=run.conversation_id,
    )
    latest_by_agent = {}
    for item in snapshot.get("agent_runs", []):
        if item.get("agent_id"):
            latest_by_agent[item["agent_id"]] = item

    workflow_agent_ids = {
        node.get("agent_id")
        for node in run.nodes or []
        if node.get("type") == "agent_task" and node.get("agent_id")
    }
    moderator = latest_by_agent.get("moderator")
    has_worker_activity = any(agent_id in latest_by_agent for agent_id in workflow_agent_ids)
    moderator_payload = _extract_json(moderator.get("content")) if moderator else {}
    moderator_has_worker_plan = (
        str(moderator_payload.get("type") or "").lower() == "plan"
        and isinstance(moderator_payload.get("tasks"), list)
        and bool(moderator_payload["tasks"])
    )
    if (
        moderator
        and moderator.get("status") in {"done", "error", "stopped"}
        and not has_worker_activity
        and not moderator_has_worker_plan
    ):
        nodes = []
        for stored in run.nodes or []:
            node = dict(stored)
            if node.get("type") == "agent_task":
                node["status"] = "skipped"
            nodes.append(node)
        run.nodes = nodes
        run.status = "failed"
        detail = str(moderator.get("error") or moderator.get("content") or "").strip()
        run.error_summary = (
            "主持 Agent 未生成 worker 执行计划"
            + (f"：{detail[:500]}" if detail else "")
        )
        run.finished_at = datetime.utcnow()
        _revoke_tool_grant(run)
        _attach_tool_calls(run)
        db.session.commit()
        return run

    nodes = []
    done_count = 0
    failed_count = 0
    agent_count = 0
    outputs = dict(run.output or {})
    repairs = []
    for stored in run.nodes or []:
        node = dict(stored)
        if node.get("type") == "agent_task":
            agent_count += 1
            core = latest_by_agent.get(node.get("agent_id"))
            if core:
                status = core.get("status")
                if status == "done":
                    node["status"] = "done"
                    node["output"] = _extract_json(core.get("content"))
                    artifact_path = (
                        None
                        if str(run.workflow_code or "").startswith("product.")
                        else ROLE_ARTIFACTS.get(node.get("agent_role"))
                    )
                    if artifact_path and run.sandbox_session_id:
                        try:
                            node["output"] = runtime.get_workspace_json(
                                authorization=authorization,
                                sandbox_session_id=run.sandbox_session_id,
                                path=artifact_path,
                                artifact_role=node.get("agent_role"),
                            )
                        except CoreRuntimeError as exc:
                            # Keep the visible message fallback, but ask the producing
                            # Agent to repair its own structured file exactly once.
                            if not node.get("validation_attempted"):
                                node["validation_attempted"] = True
                                node["validation_status"] = "repairing"
                                node["validation_error"] = str(exc)
                                repairs.append(
                                    (
                                        node.get("agent_role"),
                                        node.get("agent_id"),
                                        artifact_path,
                                        str(exc),
                                    )
                                )
                    outputs[node["agent_role"]] = node["output"]
                    done_count += 1
                elif status in {"error", "stopped"}:
                    node["status"] = "failed"
                    node["error"] = core.get("error") or "Agent execution failed"
                    failed_count += 1
                else:
                    node["status"] = "running"
        nodes.append(node)

    if failed_count:
        run.status = "partial" if done_count else "failed"
    elif agent_count and done_count == agent_count:
        missing_write = _missing_required_product_write(run)
        has_approval = any(node.get("type") == "approval" for node in nodes)
        if missing_write:
            run.status = "partial"
            run.error_summary = (
                "Agent 团队已结束，但未写入可验收的业务产物："
                f"缺少成功的 {missing_write} 工具调用。"
            )
            _attach_recoverable_draft(run, missing_write)
        else:
            run.status = "awaiting_approval" if has_approval else "completed"
            run.error_summary = None
            if has_approval:
                for node in nodes:
                    if node.get("type") == "approval":
                        node["status"] = "awaiting_approval"
        run.finished_at = datetime.utcnow()
        _revoke_tool_grant(run)
    else:
        run.status = "running"
    adopted_object = (run.output or {}).get("adopted_object")
    if adopted_object:
        outputs["adopted_object"] = adopted_object
    run.nodes = nodes
    run.output = outputs
    if run.status == "partial":
        _attach_recoverable_draft(
            run,
            REQUIRED_PRODUCT_WRITE_TOOL.get(run.workflow_code),
        )
    _attach_tool_calls(run)
    db.session.commit()
    if repairs:
        app = current_app._get_current_object()
        for agent_role, agent_id, artifact_path, validation_error in repairs:
            args = (
                app,
                run.id,
                agent_role,
                agent_id,
                artifact_path,
                authorization,
                validation_error,
            )
            if app.config.get("TESTING"):
                _repair_agent_artifact(*args)
            else:
                threading.Thread(
                    target=_repair_agent_artifact,
                    args=args,
                    daemon=True,
                    name=f"education-json-repair-{run.id[:8]}",
                ).start()
    return run


def _start_core_run(
    app,
    run_id,
    authorization,
    title,
    prompt,
    visible_prompt,
    workspace_role,
    agent_ids,
    workflow,
    education_run_grant,
):
    """Create the slow core Conversation/sandbox outside the HTTP request."""
    with app.app_context():
        run = EducationAgentRun.query.filter_by(id=run_id).first()
        if not run:
            return
        try:
            started = app.extensions["education_runtime_client"].start_workflow(
                authorization=authorization,
                title=title,
                prompt=prompt,
                visible_prompt=visible_prompt,
                workspace_role=workspace_role,
                agent_ids=agent_ids,
                workflow=workflow,
                education_run_grant=education_run_grant,
            )
            run.status = "running"
            run.conversation_id = started["conversation_id"]
            run.sandbox_session_id = started.get("sandbox_session_id")
            run.core_message_id = started.get("message_id")
            run.input_payload = {
                **(run.input_payload or {}),
                "runtime_generation": int(
                    started.get("runtime_generation") or 1
                ),
            }
            grant = EducationToolGrant.query.filter_by(
                id=run.tool_grant_id
            ).first()
            if grant:
                grant.conversation_id = run.conversation_id
        except CoreRuntimeError as exc:
            run.status = "failed"
            run.error_summary = str(exc)
            run.finished_at = datetime.utcnow()
            _revoke_tool_grant(run)
        finally:
            db.session.commit()
            db.session.remove()


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


@education_workflow_api.post("/workflow-runs")
@jwt_required()
def start_workflow_run():
    user_id = get_jwt_identity()
    payload = request.get_json(silent=True) or {}
    course_id = str(payload.get("course_id") or "").strip()
    lesson_id = str(payload.get("lesson_id") or "").strip()
    workflow_code = str(payload.get("workflow_code") or "reading_lesson").strip()
    course = teacher_course_or_none(course_id, user_id)
    if not course:
        return jsonify({"error": "course not found"}), 404
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first()
    if not lesson:
        return jsonify({"error": "lesson not found"}), 404
    template = _template(workflow_code)
    if not template:
        return jsonify({"error": "workflow template not found"}), 404
    nodes = _run_nodes(template)
    agent_ids = [
        node["agent_id"] for node in nodes if node.get("type") == "agent_task"
    ]
    requirements = str(payload.get("teacher_requirements") or "").strip()
    prompt = (
        "请按选定教育工作流协作生成一份可编辑教案和结构化习题草稿。\n"
        f"课程：{course.title}\n"
        f"学科：{course.subject_code}；学段：{course.grade_band}\n"
        f"课时：{lesson.title}\n"
        f"学习领域：{lesson.learning_domain}；文本类型：{lesson.text_genre_code}；"
        f"课型：{lesson.lesson_type_code}；时长：{lesson.duration_minutes} 分钟\n"
        f"教师补充要求：{requirements or '无'}\n"
        "【课程设计师】调用课程设计 Skill，输出唯一 canonical JSON 到 "
        "/workspace/shared/lesson_plan_draft.json。根对象只允许使用 "
        "subject_code、learning_domain、text_genre_code、lesson_type_code、"
        "title、duration_minutes、objectives、stages；objectives 是由 "
        "{id, description} 构成的非空数组；stages 是由 {name, "
        "duration_minutes, teacher_activity, student_activity, assessment} "
        "构成的非空数组。禁止 meta/content 包装、activities 字符串、"
        "同义字段或历史 schema。\n"
        "【习题生成器】调用“中英阅读与写作习题设计”Skill，先读取上述教案 JSON。\n"
        "【内容设计规范】根据当前学科、学段、课型和文本类型设计可作答的阅读与写作"
        "练习；题目必须覆盖教学目标，具备合理的难度梯度、用时和分值，答案与解析"
        "仅供教师使用。\n"
        "【机器产物规范】唯一正式产物写到 "
        "/workspace/shared/exercises_draft.json。根对象只使用 meta 和 questions；"
        "questions 至少一道，每题必须包含 id、type、prompt、answer、difficulty、"
        "score，可选 options、explanation、common_mistakes、knowledge_points、"
        "objective_ids。type 只能是 single_choice、multiple_choice、fill_blank、"
        "short_answer、writing；difficulty 只能是 easy、medium、hard。"
        "options 只能是未编号的纯文本数组，例如 [\"Excitement\", \"Nervousness\"]，"
        "禁止包含 A.、B. 等标签或对象。不得使用中文枚举、同义字段或历史 schema。"
        "写入后必须做 JSON 解析和 schema 自检；不得生成 .js、可执行代码、Markdown "
        "代码块或只回复文件路径。\n"
        "【教学审校员】读取教案与习题 JSON，检查目标覆盖、答案、难度、年级适配和"
        "学生端答案泄露，写入 /workspace/shared/review_conclusion.json。\n"
        "所有内容仅保存为教师草稿，不得自动发布。"
    )
    prompt += (
        "\n【业务工具采纳协议——与文件产物协议严格分离】\n"
        "1. /workspace/shared/*.json 是 Agent 间协作与前端预览产物；"
        "它们不是持久化业务数据，也不能用 .js 或仅返回文件路径代替。\n"
        "2. `education_action` 是把已完成自检的结果写入 Education 数据库的"
        "唯一协议。工具会自动绑定当前用户、教师角色和课程；arguments 中"
        "严禁传 course_id、actor_user_id、user_id、role 或任何 token。\n"
        "3. 课程设计师完成 lesson_plan_draft.json 后，再调用 "
        "`education_action`：action=`edu.courseware.create`，kind=`lesson_plan`，"
        "source_json 使用完整教案对象，publish 不存在且不得自行发布；"
        "idempotency_key=`course-designer-lesson-plan-v1`。\n"
        "4. 习题生成器完成 exercises_draft.json 并通过 JSON/schema 自检后，"
        "把 questions 转换成题库协议再调用 `education_action`："
        "action=`edu.question_bank.upsert`；将文件字段 answer 映射为 "
        "correct_answer，保留 explanation、knowledge_points、difficulty、score，"
        "选择题 options 仍为无 A/B 编号的纯文本；publish=false；"
        "idempotency_key=`exercise-generator-question-batch-v1`。\n"
        "5. 教学审校员使用 `edu.course.context.get`、"
        "`edu.question_bank.search` 检查已采纳草稿；不得发布课程、题目或试卷。"
        "任何工具校验失败时先按 error_code 修正结构，再以新的幂等键重试。"
    )
    prompt += "\n" + education_action_protocol(
        courseware_kind="lesson_plan",
        lesson_scoped=True,
    )
    workflow = _workflow_payload(template, nodes)
    run = EducationAgentRun(
        course_id=course_id,
        lesson_id=lesson_id,
        requested_by=user_id,
        workflow_code=template["code"],
        workflow_name=template["name"],
        status="pending",
        nodes=nodes,
        input_payload={"teacher_requirements": requirements},
        started_at=datetime.utcnow(),
    )
    db.session.add(run)
    db.session.flush()
    try:
        tool_grant, raw_tool_grant = issue_tool_grant(
            actor_user_id=user_id,
            course_id=course_id,
            allowed_tools=TEACHER_WORKFLOW_TOOLS,
            capability_ids=["builtin:education_actions"],
            agent_run_id=run.id,
        )
    except ToolGatewayError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    run.tool_grant_id = tool_grant.id
    db.session.commit()

    app = current_app._get_current_object()
    launch_args = (
        app,
        run.id,
        request.headers.get("Authorization", ""),
        f"{course.title} · {lesson.title} · Agent 教案协作",
        prompt,
        (
            f"请为课时“{lesson.title}”协作生成可编辑教案和结构化习题。"
            + (f"补充要求：{requirements}" if requirements else "")
        ),
        "teacher",
        agent_ids,
        workflow,
        raw_tool_grant,
    )
    if app.config.get("TESTING"):
        _start_core_run(*launch_args)
    else:
        threading.Thread(
            target=_start_core_run,
            args=launch_args,
            daemon=True,
            name=f"education-run-{run.id[:8]}",
        ).start()
    db.session.expire_all()
    refreshed = EducationAgentRun.query.filter_by(id=run.id).first()
    _attach_tool_calls(refreshed)
    return jsonify(refreshed.to_dict()), 202


def _product_options(payload, product_code=None):
    options = payload.get("options") or {}
    if not isinstance(options, dict):
        raise ValueError("options must be an object")
    if len(json.dumps(options, ensure_ascii=False)) > 20_000:
        raise ValueError("options are too large")
    normalized = dict(options)
    for field, maximum in (("title", 200), ("requirements", 2000)):
        if field in normalized:
            normalized[field] = str(normalized[field] or "").strip()[:maximum]
    if "question_count" in normalized:
        count = int(normalized["question_count"])
        if not 1 <= count <= 30:
            raise ValueError("question_count must be between 1 and 30")
        normalized["question_count"] = count
    if "duration_minutes" in normalized:
        duration = int(normalized["duration_minutes"])
        if not 5 <= duration <= 180:
            raise ValueError("duration_minutes must be between 5 and 180")
        normalized["duration_minutes"] = duration
    if product_code == "courseware":
        theme_style = str(
            normalized.get("theme_style") or "clear_classroom"
        ).strip()
        allowed_styles = {
            "clear_classroom",
            "paper_annotation",
            "storybook",
            "dark_focus",
        }
        if theme_style not in allowed_styles:
            raise ValueError("theme_style is not a supported presentation style")
        normalized["theme_style"] = theme_style
    if product_code == "roster_import":
        members = normalized.get("members")
        if not isinstance(members, list) or not 1 <= len(members) <= 100:
            raise ValueError("members must contain 1 to 100 rows")
        normalized_members = []
        seen = set()
        for index, row in enumerate(members):
            if not isinstance(row, dict):
                raise ValueError(f"members[{index}] must be an object")
            user_id = str(row.get("user_id") or "").strip()
            display_name = str(row.get("display_name") or "").strip()
            if not user_id or len(user_id) > 100 or user_id in seen:
                raise ValueError(
                    f"members[{index}].user_id is invalid or duplicated"
                )
            if len(display_name) > 80:
                raise ValueError(f"members[{index}].display_name is too long")
            seen.add(user_id)
            normalized_members.append(
                {"user_id": user_id, "display_name": display_name}
            )
        normalized["members"] = normalized_members
    return normalized


@education_workflow_api.post("/product-agent-runs")
@jwt_required()
def start_product_agent_run():
    user_id = get_jwt_identity()
    payload = request.get_json(silent=True) or {}
    course_id = str(payload.get("course_id") or "").strip()
    product_code = str(payload.get("product_code") or "").strip()
    contract = product_workflow(product_code)
    if not contract:
        return jsonify({"error": "product Agent workflow not found"}), 404
    membership = active_membership(course_id, user_id)
    if not membership:
        return jsonify({"error": "course not found"}), 404
    if membership.role != contract["role"]:
        return jsonify({"error": "product Agent workflow is not available"}), 403

    lesson_id = str(payload.get("lesson_id") or "").strip() or None
    if contract["requires_lesson"] and not lesson_id:
        return jsonify({"error": "lesson_id is required"}), 400
    lesson = None
    if lesson_id:
        lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first()
        if not lesson:
            return jsonify({"error": "lesson not found"}), 404
    try:
        options = _product_options(payload, product_code)
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400

    template = product_template(product_code)
    nodes = _run_nodes(template)
    agent_ids = [
        node["agent_id"] for node in nodes if node.get("type") == "agent_task"
    ]
    prompt = build_product_prompt(
        product_code,
        membership.course,
        options,
        lesson=lesson,
    )
    visible_prompt = build_visible_product_intent(
        product_code,
        options,
        lesson=lesson,
    )
    workflow = _workflow_payload(template, nodes)
    run = EducationAgentRun(
        course_id=course_id,
        lesson_id=lesson_id,
        requested_by=user_id,
        workflow_code=template["code"],
        workflow_name=template["name"],
        status="pending",
        nodes=nodes,
        input_payload={
            "product_code": product_code,
            "options": options,
            "display_title": (
                str(options.get("title") or "").strip()
                or (lesson.title if lesson else membership.course.title)
            ),
        },
        started_at=datetime.utcnow(),
    )
    db.session.add(run)
    db.session.flush()
    try:
        tool_grant, raw_tool_grant = issue_tool_grant(
            actor_user_id=user_id,
            course_id=course_id,
            allowed_tools=contract["tools"],
            capability_ids=["builtin:education_actions"],
            agent_run_id=run.id,
        )
    except ToolGatewayError as error:
        db.session.rollback()
        return jsonify(
            {"error": error.message, "error_code": error.error_code}
        ), error.status_code
    run.tool_grant_id = tool_grant.id
    db.session.commit()

    title_target = lesson.title if lesson else membership.course.title
    local_started_at = datetime.utcnow() + timedelta(hours=8)
    conversation_title = (
        f"{membership.course.title}｜Education·{title_target}"
        f"（{template['name']}）｜{local_started_at:%Y-%m-%d %H:%M}"
    )
    app = current_app._get_current_object()
    launch_args = (
        app,
        run.id,
        request.headers.get("Authorization", ""),
        conversation_title,
        prompt,
        visible_prompt,
        membership.role,
        agent_ids,
        workflow,
        raw_tool_grant,
    )
    if app.config.get("TESTING"):
        _start_core_run(*launch_args)
    else:
        threading.Thread(
            target=_start_core_run,
            args=launch_args,
            daemon=True,
            name=f"education-product-run-{run.id[:8]}",
        ).start()
    db.session.expire_all()
    refreshed = EducationAgentRun.query.filter_by(id=run.id).first()
    _attach_tool_calls(refreshed)
    return jsonify(refreshed.to_dict()), 202


def _member_owned_product_run(run_id, user_id):
    run = EducationAgentRun.query.filter_by(id=run_id).first()
    if (
        not run
        or not str(run.workflow_code or "").startswith("product.")
        or run.requested_by != user_id
        or not active_membership(run.course_id, user_id)
    ):
        return None
    return run


@education_workflow_api.get("/product-agent-runs/<run_id>")
@jwt_required()
def get_product_agent_run(run_id):
    user_id = get_jwt_identity()
    run = _member_owned_product_run(run_id, user_id)
    if not run:
        return jsonify({"error": "product Agent run not found"}), 404
    if _expire_stale_pending_run(run):
        db.session.commit()
    if run.status in {"running", "pending"} and run.conversation_id:
        try:
            _sync_run(run, request.headers.get("Authorization", ""))
        except CoreRuntimeError as exc:
            run.error_summary = str(exc)
            db.session.commit()
    if _reconcile_product_completion(run):
        db.session.commit()
    _attach_tool_calls(run)
    return jsonify(run.to_dict())


@education_workflow_api.get("/courses/<course_id>/product-agent-runs")
@jwt_required()
def list_product_agent_runs(course_id):
    user_id = get_jwt_identity()
    if not active_membership(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    query = EducationAgentRun.query.filter(
        EducationAgentRun.course_id == course_id,
        EducationAgentRun.requested_by == user_id,
        EducationAgentRun.workflow_code.like("product.%"),
    )
    product_code = str(request.args.get("product_code") or "").strip()
    if product_code:
        query = query.filter(
            EducationAgentRun.workflow_code == f"product.{product_code}"
        )
    runs = query.order_by(EducationAgentRun.created_at.desc()).limit(50).all()
    changed = False
    for listed_run in runs:
        changed = _expire_stale_pending_run(listed_run) or changed
        changed = _reconcile_product_completion(listed_run) or changed
    if changed:
        db.session.commit()
    for run in runs:
        _attach_tool_calls(run)
    return jsonify({"items": [run.to_dict() for run in runs], "total": len(runs)})


@education_workflow_api.get(
    "/conversations/<conversation_id>/product-context"
)
@jwt_required()
def get_product_conversation_context(conversation_id):
    user_id = get_jwt_identity()
    run = (
        EducationAgentRun.query.filter_by(
            conversation_id=conversation_id,
            requested_by=user_id,
        )
        .filter(EducationAgentRun.workflow_code.like("product.%"))
        .order_by(EducationAgentRun.created_at.desc())
        .first()
    )
    if not run:
        return jsonify({"error": "Education conversation context not found"}), 404
    membership = active_membership(run.course_id, user_id)
    if not membership:
        return jsonify({"error": "Education conversation context not found"}), 404
    if _expire_stale_pending_run(run):
        db.session.commit()
    if _reconcile_product_completion(run):
        db.session.commit()
    _attach_tool_calls(run)
    lesson = (
        Lesson.query.filter_by(id=run.lesson_id, course_id=run.course_id).first()
        if run.lesson_id
        else None
    )
    run_data = run.to_dict()
    return jsonify(
        {
            "course": {
                "id": membership.course.id,
                "title": membership.course.title,
                "membership_role": membership.role,
            },
            "lesson": (
                {"id": lesson.id, "title": lesson.title}
                if lesson
                else None
            ),
            "run": run_data,
            "progress": {
                "agent_count": run_data["agent_count"],
                "completed_count": run_data["completed_agent_count"],
            },
        }
    )


@education_workflow_api.get("/workflow-runs/<run_id>")
@jwt_required()
def get_workflow_run(run_id):
    user_id = get_jwt_identity()
    run = EducationAgentRun.query.filter_by(id=run_id).first()
    if not run or not teacher_course_or_none(run.course_id, user_id):
        return jsonify({"error": "workflow run not found"}), 404
    if _expire_stale_pending_run(run):
        db.session.commit()
    if run.status in {"running", "pending", "awaiting_approval"} and run.conversation_id:
        try:
            _sync_run(run, request.headers.get("Authorization", ""))
        except CoreRuntimeError as exc:
            run.error_summary = str(exc)
            db.session.commit()
    _attach_tool_calls(run)
    return jsonify(run.to_dict())


@education_workflow_api.get("/courses/<course_id>/workflow-runs")
@jwt_required()
def list_workflow_runs(course_id):
    user_id = get_jwt_identity()
    if not teacher_course_or_none(course_id, user_id):
        return jsonify({"error": "course not found"}), 404
    runs = EducationAgentRun.query.filter_by(course_id=course_id).order_by(
        EducationAgentRun.created_at.desc()
    ).all()
    if any(_expire_stale_pending_run(run) for run in runs):
        db.session.commit()
    for run in runs:
        _attach_tool_calls(run)
    return jsonify({"items": [run.to_dict() for run in runs]})
