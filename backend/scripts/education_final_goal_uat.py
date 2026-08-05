"""Run the live, persistent Education Goal acceptance flow.

This script talks only to the running core gateway. It creates disposable UAT
accounts and durable business records, runs the real multi-Agent courseware
workflow, verifies the canonical tool write and exports its editable PPTX, then
recycles only the sandbox created by that workflow and proves rehydration.

Set WEAGENT_UAT_PASSWORD in the process environment. The password, JWTs,
invitation token, model output and tool grant are never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import requests


TERMINAL_RUN_STATES = {"completed", "partial", "failed", "cancelled"}


class UATFailure(RuntimeError):
    pass


class CoreApi:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int | tuple[int, ...] = 200,
        timeout: tuple[int, int] = (5, 45),
        **kwargs,
    ) -> requests.Response:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=timeout,
            **kwargs,
        )
        expected_codes = (expected,) if isinstance(expected, int) else expected
        if response.status_code not in expected_codes:
            try:
                body = response.json()
            except ValueError:
                body = {"body_sha256": hashlib.sha256(response.content).hexdigest()[:12]}
            if isinstance(body, dict):
                body.pop("token", None)
                body.pop("access_token", None)
                body.pop("refresh_token", None)
            raise UATFailure(
                f"{method} {path}: expected {expected_codes}, "
                f"got {response.status_code}: {body}"
            )
        return response

    def json(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        response = self.request(method, path, **kwargs)
        try:
            payload = response.json()
        except ValueError as exc:
            raise UATFailure(f"{method} {path}: response is not JSON") from exc
        if not isinstance(payload, dict):
            raise UATFailure(f"{method} {path}: response must be an object")
        return payload


def _auth_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict) or not data.get("access_token"):
        raise UATFailure("authentication response does not contain an access token")
    return data


def _register(base_url: str, username: str, email: str, password: str) -> dict[str, Any]:
    api = CoreApi(base_url)
    payload = api.json(
        "POST",
        "/api/auth/register",
        expected=201,
        json={"username": username, "email": email, "password": password},
    )
    return _auth_data(payload)


def _assert(condition: Any, message: str):
    if not condition:
        raise UATFailure(message)


def _wait_for_product_run(
    api: CoreApi,
    run_id: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any], list[str]]:
    deadline = time.monotonic() + timeout_seconds
    history: list[str] = []
    while time.monotonic() < deadline:
        run = api.json(
            "GET",
            f"/api/domain/edu/product-agent-runs/{run_id}",
            timeout=(5, 60),
        )
        state = str(run.get("status") or "unknown")
        if not history or history[-1] != state:
            history.append(state)
            print(f"[UAT] product Agent state: {state}", file=sys.stderr, flush=True)
        if state in TERMINAL_RUN_STATES:
            return run, history
        time.sleep(2)
    raise UATFailure("product Agent run exceeded the UAT timeout")


def _successful_tool_calls(run: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for node in run.get("nodes") or []
        if isinstance(node, dict)
        for call in node.get("tool_calls") or []
        if isinstance(call, dict) and call.get("status") == "completed"
    ]


def _docker_stop_verified(container_id: str, conversation_id: str):
    inspected = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{index .Config.Labels "weagent.session_id"}}',
            container_id,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if inspected.returncode != 0:
        raise UATFailure("UAT sandbox container cannot be inspected")
    if inspected.stdout.strip() != conversation_id:
        raise UATFailure("refusing to stop a container outside the UAT conversation")
    stopped = subprocess.run(
        ["docker", "stop", container_id],
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
    )
    if stopped.returncode != 0:
        raise UATFailure("UAT sandbox container could not be stopped")


def run(base_url: str, timeout_seconds: int, recycle_sandbox: bool) -> dict[str, Any]:
    password = os.getenv("WEAGENT_UAT_PASSWORD", "")
    if len(password) < 10:
        raise UATFailure("WEAGENT_UAT_PASSWORD must contain at least 10 characters")

    suffix = f"{time.strftime('%m%d%H%M')}{uuid.uuid4().hex[:5]}"
    teacher_username = f"edu_goal_teacher_{suffix}"
    student_username = f"edu_goal_student_{suffix}"
    outsider_username = f"edu_goal_outsider_{suffix}"
    teacher_auth = _register(
        base_url,
        teacher_username,
        f"{teacher_username}@example.test",
        password,
    )
    student_auth = _register(
        base_url,
        student_username,
        f"{student_username}@example.test",
        password,
    )
    outsider_auth = _register(
        base_url,
        outsider_username,
        f"{outsider_username}@example.test",
        password,
    )
    teacher = CoreApi(base_url, teacher_auth["access_token"])
    student = CoreApi(base_url, student_auth["access_token"])
    outsider = CoreApi(base_url, outsider_auth["access_token"])

    course = teacher.json(
        "POST",
        "/api/domain/edu/courses",
        expected=201,
        json={
            "title": f"高中英语读写成品验收 {suffix}",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
        },
    )
    course_id = course["id"]
    teacher.json(
        "PUT",
        f"/api/domain/edu/courses/{course_id}/me/profile",
        json={"display_name": "顾老师（成品验收）"},
    )
    invitation = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/invitations",
        expected=201,
        json={"max_uses": 1, "expires_in_hours": 2},
    )
    student.json(
        "POST",
        "/api/domain/edu/invitations/accept",
        json={"token": invitation["token"]},
    )
    student.json(
        "PUT",
        f"/api/domain/edu/courses/{course_id}/me/profile",
        json={"display_name": "林同学（成品验收）"},
    )
    members = teacher.json(
        "GET",
        f"/api/domain/edu/courses/{course_id}/members",
    ).get("items") or []
    _assert(
        {"顾老师（成品验收）", "林同学（成品验收）"}.issubset(
            {item.get("display_name") for item in members}
        ),
        "course member display names were not persisted",
    )
    outsider.request(
        "GET",
        f"/api/domain/edu/courses/{course_id}",
        expected=404,
    )

    unit = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/units",
        expected=201,
        json={"title": "Narrative Reading to Writing", "position": 1},
    )
    lesson = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/lessons",
        expected=201,
        json={
            "unit_id": unit["id"],
            "title": "A Choice That Changed the Story",
            "learning_domain": "integrated",
            "theme_code": "growth_and_choices",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
            "position": 1,
        },
    )
    lesson_id = lesson["id"]
    lesson_plan = {
        "subject_code": "high_school_english",
        "learning_domain": "integrated",
        "text_genre_code": "narrative",
        "lesson_type_code": "reading_writing",
        "title": "A Choice That Changed the Story",
        "duration_minutes": 45,
        "objectives": [
            {
                "id": "objective-evidence",
                "description": "Infer a character's change from actions, dialogue and narrative detail.",
            },
            {
                "id": "objective-transfer",
                "description": "Rewrite a turning point with evidence, a clear choice and reflective language.",
            },
        ],
        "stages": [
            {
                "id": "stage-notice",
                "name": "Notice the turning point",
                "duration_minutes": 12,
                "teacher_activity": "Model how action and dialogue reveal a decision.",
                "student_activity": "Mark evidence and explain the character's emotional shift.",
                "assessment": "Evidence-to-inference response.",
            },
            {
                "id": "stage-write",
                "name": "Transfer evidence into writing",
                "duration_minutes": 25,
                "teacher_activity": "Model a decision-action-reflection paragraph.",
                "student_activity": "Rewrite the turning point and peer review evidence.",
                "assessment": "Short narrative scored for evidence, coherence and expression.",
            },
        ],
    }
    teacher.json(
        "POST",
        f"/api/domain/edu/lessons/{lesson_id}/contents",
        expected=201,
        json={
            "kind": "lesson_plan",
            "schema_name": "weagent.education.lesson-plan",
            "schema_version": "1.0",
            "source_json": lesson_plan,
            "rendered_html": (
                "<!doctype html><html><body><h1>A Choice That Changed the Story</h1>"
                "<p>Read evidence, explain change, then rewrite the turning point.</p>"
                "</body></html>"
            ),
            "change_summary": "Live UAT teaching source",
        },
    )

    assignment = teacher.json(
        "POST",
        f"/api/domain/edu/lessons/{lesson_id}/assignments",
        expected=201,
        json={
            "title": "Turning-point evidence paragraph",
            "kind": "writing",
            "instruction_json": {
                "prompt": "Rewrite the turning point in 100-120 words and cite two details.",
                "student_rubric": ["evidence", "coherence", "expression"],
            },
            "evaluation_json": {
                "answer_key": ["Private teacher exemplar"],
                "rubric": {"evidence": 4, "coherence": 3, "expression": 3},
            },
            "max_attempts": 2,
        },
    )
    assignment_id = assignment["id"]
    teacher.json(
        "POST",
        f"/api/domain/edu/assignments/{assignment_id}/publish",
    )
    student_assignment = student.json(
        "GET",
        f"/api/domain/edu/assignments/{assignment_id}",
    )
    _assert(
        "evaluation_json" not in student_assignment
        and "Private teacher exemplar" not in json.dumps(student_assignment),
        "student assignment leaked teacher-only evaluation data",
    )
    answer = {
        "text": (
            "At first, Mia stepped away from the stage because her hands were shaking. "
            "Then she remembered her partner's quiet promise and chose to return. "
            "That small decision changed fear into responsibility."
        )
    }
    student.json(
        "PUT",
        f"/api/domain/edu/assignments/{assignment_id}/submission/draft",
        json={"answer_json": answer},
    )
    recovered = student.json(
        "GET",
        f"/api/domain/edu/assignments/{assignment_id}/submission",
    )
    _assert(
        recovered.get("draft", {}).get("answer_json") == answer,
        "student draft recovery did not preserve the answer",
    )
    submitted = student.json(
        "POST",
        f"/api/domain/edu/assignments/{assignment_id}/submissions",
        expected=201,
        json={},
    )
    submission_id = submitted["submission"]["id"]
    teacher.json(
        "POST",
        f"/api/domain/edu/submissions/{submission_id}/feedback",
        expected=201,
        json={
            "score": 8.5,
            "feedback_json": {
                "strengths": ["The turning point is supported by two concrete details."],
                "next_steps": ["Add one reflective sentence after the decision."],
            },
        },
    )
    feedback = student.json(
        "GET",
        f"/api/domain/edu/submissions/{submission_id}/feedback",
    )
    _assert(len(feedback.get("items") or []) == 1, "student feedback was not released")

    before_contents = {
        item["id"]
        for item in teacher.json(
            "GET",
            f"/api/domain/edu/lessons/{lesson_id}/contents",
        ).get("items") or []
    }
    started = teacher.json(
        "POST",
        "/api/domain/edu/product-agent-runs",
        expected=202,
        timeout=(5, 90),
        json={
            "course_id": course_id,
            "lesson_id": lesson_id,
            "product_code": "courseware",
            "options": {
                "theme_style": "paper_annotation",
                "requirements": (
                    "制作 6-8 页可直接授课的高中英语读写课件。保留教案目标，"
                    "呈现文本证据、推理支架、写作迁移和退出任务；页面简洁、中文指令准确。"
                ),
            },
        },
    )
    run_id = started["id"]
    run_record, state_history = _wait_for_product_run(
        teacher,
        run_id,
        timeout_seconds,
    )
    _assert(
        run_record.get("status") == "completed",
        "real product Agent did not reach completed: "
        + str(run_record.get("error_summary") or run_record.get("status")),
    )
    completed_calls = _successful_tool_calls(run_record)
    _assert(
        any(
            call.get("tool_name") == "edu.courseware.create"
            and call.get("agent_id") == "_edu_2"
            for call in completed_calls
        ),
        "designated courseware Agent _edu_2 did not complete edu.courseware.create",
    )
    _assert(run_record.get("conversation_id"), "product run has no linked conversation")
    conversation_id = run_record["conversation_id"]

    contents = teacher.json(
        "GET",
        f"/api/domain/edu/lessons/{lesson_id}/contents",
    ).get("items") or []
    generated = [
        item
        for item in contents
        if item.get("id") not in before_contents
        and item.get("kind") == "slide_document"
    ]
    _assert(len(generated) == 1, "Agent did not create exactly one canonical slide document")
    content_id = generated[0]["id"]
    visual_qa = teacher.json(
        "GET",
        f"/api/domain/edu/contents/{content_id}/visual-qa",
        timeout=(5, 90),
    )
    _assert(
        visual_qa.get("status") == "passed",
        f"generated deck visual QA is {visual_qa.get('status')}",
    )
    _assert(
        visual_qa.get("theme_style") == "paper_annotation",
        "generated deck did not preserve the selected style",
    )

    html_export = teacher.request(
        "GET",
        f"/api/domain/edu/contents/{content_id}/export?format=html",
    )
    _assert(
        "text/html" in html_export.headers.get("Content-Type", ""),
        "HTML export has the wrong content type",
    )
    pptx_export = teacher.request(
        "GET",
        f"/api/domain/edu/contents/{content_id}/export?format=pptx",
        timeout=(5, 90),
    )
    _assert(
        pptx_export.content.startswith(b"PK") and len(pptx_export.content) > 10_000,
        "PPTX export is not a valid editable Office package",
    )
    deck_path = (
        Path(tempfile.gettempdir())
        / "weagent-education-goal-uat"
        / f"live-agent-{content_id}.pptx"
    )
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    deck_path.write_bytes(pptx_export.content)

    context = teacher.json(
        "GET",
        f"/api/domain/edu/conversations/{conversation_id}/product-context",
    )
    _assert(
        context.get("run", {}).get("id") == run_id,
        "chat-to-product context did not resolve the run",
    )
    history = teacher.json(
        "GET",
        f"/api/domain/edu/courses/{course_id}/product-agent-runs?product_code=courseware",
    )
    _assert(
        any(item.get("id") == run_id for item in history.get("items") or []),
        "product history cannot trace the live run",
    )
    conversation = teacher.json(
        "GET",
        f"/api/conversations/{conversation_id}",
    ).get("data") or {}
    outsider.request(
        "GET",
        f"/api/conversations/{conversation_id}",
        expected=404,
    )
    messages_before = teacher.json(
        "GET",
        f"/api/messages/conversation/{conversation_id}?page=1&per_page=100",
    ).get("data") or {}
    outsider.request(
        "GET",
        f"/api/messages/conversation/{conversation_id}",
        expected=404,
    )
    _assert(
        len(messages_before.get("items") or []) >= 4,
        "multi-Agent chat history is incomplete",
    )

    recovery_evidence = {"performed": False}
    if recycle_sandbox:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            conversation = teacher.json(
                "GET",
                f"/api/conversations/{conversation_id}",
            ).get("data") or {}
            if (conversation.get("sandbox_runtime") or {}).get("snapshot_available"):
                break
            time.sleep(2)
        runtime_before = conversation.get("sandbox_runtime") or {}
        _assert(runtime_before.get("snapshot_available"), "sandbox snapshot was not persisted")
        generation_before = int(runtime_before.get("generation") or 1)
        container_before = str(conversation.get("sandbox_container_id") or "")
        _assert(container_before, "conversation has no sandbox container id")
        _docker_stop_verified(container_before, conversation_id)
        preflight = teacher.json(
            "GET",
            (
                f"/api/conversations/{conversation_id}/runtime-preflight"
                "?required_tools=education_action"
                "&agent_ids=_edu_1,_edu_2,_edu_9"
            ),
            timeout=(5, 360),
        ).get("data") or {}
        _assert(preflight.get("ready") is True, "rehydrated runtime preflight failed")
        conversation_after = teacher.json(
            "GET",
            f"/api/conversations/{conversation_id}",
        ).get("data") or {}
        runtime_after = conversation_after.get("sandbox_runtime") or {}
        _assert(
            int(runtime_after.get("generation") or 0) == generation_before + 1,
            "sandbox generation did not advance after recycle",
        )
        _assert(
            conversation_after.get("sandbox_container_id") != container_before,
            "sandbox recycle reused the stopped container",
        )
        messages_after = teacher.json(
            "GET",
            f"/api/messages/conversation/{conversation_id}?page=1&per_page=100",
        ).get("data") or {}
        _assert(
            messages_after.get("total") == messages_before.get("total"),
            "chat history changed during sandbox recovery",
        )
        recovery_evidence = {
            "performed": True,
            "generation_before": generation_before,
            "generation_after": runtime_after.get("generation"),
            "snapshot_available": runtime_after.get("snapshot_available"),
            "restored_files": preflight.get("restored_files", 0),
        }

    analytics = teacher.json(
        "GET",
        f"/api/domain/edu/courses/{course_id}/analytics",
    )
    _assert(analytics.get("completion_rate") == 1.0, "teacher analytics is incomplete")

    return {
        "status": "passed",
        "browser_account": {
            "teacher_username": teacher_username,
            "student_username": student_username,
        },
        "records": {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "assignment_id": assignment_id,
            "product_run_id": run_id,
            "conversation_id": conversation_id,
            "content_id": content_id,
        },
        "business_loop": {
            "member_display_names": True,
            "student_draft_recovery": True,
            "teacher_feedback_release": True,
            "completion_rate": analytics.get("completion_rate"),
            "cross_user_isolation": True,
        },
        "agent_workflow": {
            "state_history": state_history,
            "completed_agents": sum(
                1
                for node in run_record.get("nodes") or []
                if node.get("type") == "agent_task" and node.get("status") == "done"
            ),
            "successful_tool_calls": sorted(
                {call.get("tool_name") for call in completed_calls if call.get("tool_name")}
            ),
            "conversation_linked": True,
            "history_linked": True,
        },
        "presentation": {
            "theme_style": visual_qa.get("theme_style"),
            "slide_count": visual_qa.get("slide_count"),
            "visual_qa": visual_qa.get("status"),
            "rendered_pptx": (visual_qa.get("rendered_pptx") or {}).get("status"),
            "html_bytes": len(html_export.content),
            "pptx_bytes": len(pptx_export.content),
            "pptx_path": str(deck_path),
        },
        "sandbox_recovery": recovery_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5002")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--recycle-sandbox", action="store_true")
    args = parser.parse_args()
    try:
        result = run(
            args.base_url,
            max(120, args.timeout_seconds),
            args.recycle_sandbox,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"status": "failed", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
