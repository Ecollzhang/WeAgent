"""Run the real Phase 3 Education product-Agent acceptance workflows.

The script reuses an existing isolated teacher account and course. It verifies
that product runs complete through durable Education tools instead of treating
chat text or sandbox paths as accepted business artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import time

from education_phase3_uat import Api, UATFailure, check, login


TERMINAL_STATES = {"completed", "failed", "cancelled"}


def successful_tool_calls(run):
    return [
        call
        for node in run.get("nodes") or []
        if isinstance(node, dict)
        for call in node.get("tool_calls") or []
        if isinstance(call, dict) and call.get("status") == "completed"
    ]


def wait_for_run(api: Api, run_id: str, timeout_seconds: int):
    deadline = time.monotonic() + timeout_seconds
    history = []
    while time.monotonic() < deadline:
        run = api.json(
            "GET",
            f"/api/domain/edu/product-agent-runs/{run_id}",
            timeout=(5, 60),
        )
        state = str(run.get("status") or "unknown")
        if not history or history[-1] != state:
            history.append(state)
            print(
                json.dumps({"run_id": run_id, "status": state}, ensure_ascii=False),
                flush=True,
            )
        if state in TERMINAL_STATES:
            return run, history
        time.sleep(3)
    raise UATFailure(f"product Agent run {run_id} exceeded {timeout_seconds}s")


def run_product(
    api: Api,
    *,
    course_id: str,
    product_code: str,
    options: dict,
    timeout_seconds: int,
    lesson_id: str | None = None,
):
    payload = {
        "course_id": course_id,
        "product_code": product_code,
        "options": options,
    }
    if lesson_id:
        payload["lesson_id"] = lesson_id
    started = api.json(
        "POST",
        "/api/domain/edu/product-agent-runs",
        expected=202,
        timeout=(5, 90),
        json=payload,
    )
    run, history = wait_for_run(api, started["id"], timeout_seconds)
    check(
        run.get("status") == "completed",
        f"{product_code} failed: {run.get('error_summary') or run.get('status')}",
    )
    calls = successful_tool_calls(run)
    check(run.get("conversation_id"), f"{product_code} has no linked conversation")
    check(calls, f"{product_code} completed without a durable Education tool call")
    return run, history, calls


def run(
    base_url: str,
    teacher_username: str,
    course_id: str,
    lesson_id: str,
    timeout_seconds: int,
):
    password = os.getenv("WEAGENT_UAT_PASSWORD", "")
    check(len(password) >= 10, "WEAGENT_UAT_PASSWORD must contain at least 10 characters")
    teacher = login(base_url, teacher_username, password)

    before_contents = {
        item["id"]
        for item in teacher.json(
            "GET", f"/api/domain/edu/lessons/{lesson_id}/contents"
        ).get("items")
        or []
    }
    results = {}

    courseware_run, history, calls = run_product(
        teacher,
        course_id=course_id,
        lesson_id=lesson_id,
        product_code="courseware",
        options={
            "theme_style": "dark_focus",
            "requirements": "根据当前教案生成 6 至 8 页可直接授课的课件，突出证据、推理支架、写作迁移与退出任务。",
        },
        timeout_seconds=timeout_seconds,
    )
    courseware_calls = [call for call in calls if call.get("tool_name") == "edu.courseware.create"]
    check(courseware_calls, "dark-focus courseware did not call edu.courseware.create")
    after_contents = teacher.json(
        "GET", f"/api/domain/edu/lessons/{lesson_id}/contents"
    ).get("items") or []
    generated = [
        item
        for item in after_contents
        if item.get("id") not in before_contents and item.get("kind") == "slide_document"
    ]
    check(len(generated) == 1, "dark-focus Agent did not create exactly one slide document")
    content_id = generated[0]["id"]
    visual_qa = teacher.json(
        "GET",
        f"/api/domain/edu/contents/{content_id}/visual-qa",
        timeout=(5, 90),
    )
    check(visual_qa.get("status") == "passed", "dark-focus visual QA did not pass")
    check(visual_qa.get("theme_style") == "dark_focus", "dark-focus theme was not preserved")
    for export_format, content_type in (
        ("html", "text/html"),
        ("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("pdf", "application/pdf"),
    ):
        response = teacher.request(
            "GET",
            f"/api/domain/edu/contents/{content_id}/export?format={export_format}",
            timeout=(5, 90),
        )
        check(
            content_type in response.headers.get("Content-Type", ""),
            f"{export_format} export has the wrong content type",
        )
        check(len(response.content) > 1000, f"{export_format} export is unexpectedly small")
    results["courseware"] = {
        "run_id": courseware_run["id"],
        "conversation_id": courseware_run["conversation_id"],
        "content_id": content_id,
        "theme_style": visual_qa["theme_style"],
        "slide_count": visual_qa["slide_count"],
        "visual_qa": visual_qa["status"],
        "state_history": history,
    }

    question_run, history, calls = run_product(
        teacher,
        course_id=course_id,
        product_code="question_generation",
        options={
            "question_count": 3,
            "difficulty": "medium",
            "knowledge_points": ["文本证据", "人物态度", "写作迁移"],
            "requirements": "生成三道规范单选题，选项不带 A/B 前缀，答案唯一且解析可追溯。",
        },
        timeout_seconds=timeout_seconds,
    )
    check(
        any(call.get("tool_name") == "edu.question_bank.upsert" for call in calls),
        "question Agent did not call edu.question_bank.upsert",
    )
    results["question_generation"] = {
        "run_id": question_run["id"],
        "conversation_id": question_run["conversation_id"],
        "state_history": history,
        "adopted_object": (question_run.get("output") or {}).get("adopted_object"),
    }

    paper_run, history, calls = run_product(
        teacher,
        course_id=course_id,
        product_code="paper_generation",
        options={
            "title": "Phase 3 Agent 阅读诊断卷",
            "question_count": 4,
            "duration_minutes": 30,
            "requirements": "只从当前课程已发布题目中冻结四道题，不得伪造题目。",
        },
        timeout_seconds=timeout_seconds,
    )
    check(
        any(call.get("tool_name") == "edu.paper.compose" for call in calls),
        "paper Agent did not call edu.paper.compose",
    )
    results["paper_generation"] = {
        "run_id": paper_run["id"],
        "conversation_id": paper_run["conversation_id"],
        "state_history": history,
        "adopted_object": (paper_run.get("output") or {}).get("adopted_object"),
    }

    knowledge_run, history, calls = run_product(
        teacher,
        course_id=course_id,
        product_code="knowledge_research",
        options={
            "query": "narrative reading comprehension evidence education",
            "license_note": "Wikipedia CC BY-SA 4.0；教师已核对教学使用权",
            "requirements": "检索与叙事阅读证据相关的开放资料，重新抓取正文后保存为教师草稿。",
        },
        timeout_seconds=timeout_seconds,
    )
    tool_names = {call.get("tool_name") for call in calls}
    check("edu.web.research" in tool_names, "knowledge Agent did not call edu.web.research")
    check(
        "edu.knowledge.resource.adopt" in tool_names,
        "knowledge Agent did not adopt a refetched knowledge resource",
    )
    results["knowledge_research"] = {
        "run_id": knowledge_run["id"],
        "conversation_id": knowledge_run["conversation_id"],
        "state_history": history,
        "adopted_object": (knowledge_run.get("output") or {}).get("adopted_object"),
    }

    for item in results.values():
        context = teacher.json(
            "GET",
            f"/api/domain/edu/conversations/{item['conversation_id']}/product-context",
        )
        check(context.get("run", {}).get("id") == item["run_id"], "chat linkage is stale")

    return {
        "status": "passed",
        "teacher_username": teacher_username,
        "course_id": course_id,
        "lesson_id": lesson_id,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5002")
    parser.add_argument("--teacher-username", required=True)
    parser.add_argument("--course-id", required=True)
    parser.add_argument("--lesson-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    try:
        result = run(
            args.base_url,
            args.teacher_username,
            args.course_id,
            args.lesson_id,
            max(120, args.timeout_seconds),
        )
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
