"""Seed and verify the persistent Education Phase 3 acceptance dataset.

The script uses only public core-gateway APIs. Credentials are supplied through
environment variables and are never printed. The resulting records remain in
the development database for browser acceptance after this script exits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid

import requests


class UATFailure(RuntimeError):
    pass


class Api:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def request(self, method: str, path: str, *, expected=(200,), **kwargs):
        timeout = kwargs.pop("timeout", (5, 90))
        response = self.session.request(
            method, f"{self.base_url}{path}", timeout=timeout, **kwargs
        )
        expected_codes = (expected,) if isinstance(expected, int) else expected
        if response.status_code not in expected_codes:
            try:
                detail = response.json()
            except ValueError:
                detail = {"body_sha256": hashlib.sha256(response.content).hexdigest()[:12]}
            if isinstance(detail, dict):
                for key in ("token", "access_token", "refresh_token"):
                    detail.pop(key, None)
            raise UATFailure(
                f"{method} {path}: expected {expected_codes}, got "
                f"{response.status_code}: {detail}"
            )
        return response

    def json(self, method: str, path: str, **kwargs):
        payload = self.request(method, path, **kwargs).json()
        if not isinstance(payload, dict):
            raise UATFailure(f"{method} {path}: expected JSON object")
        return payload


def check(condition, message):
    if not condition:
        raise UATFailure(message)


def login(base_url: str, username: str, password: str) -> Api:
    response = Api(base_url).json(
        "POST", "/api/auth/login", json={"username": username, "password": password}
    )
    data = response.get("data") or {}
    check(data.get("access_token"), "login response is missing access token")
    return Api(base_url, data["access_token"])


def publish_lesson(api: Api, lesson: dict, subject_code: str):
    if lesson.get("status") == "published":
        return lesson
    publish_path = f"/api/domain/edu/lessons/{lesson['id']}/publish"
    publish_headers = {"Idempotency-Key": f"phase3-lesson-{lesson['id']}"}
    response = api.request(
        "POST", publish_path, expected=(200, 201, 400), headers=publish_headers, json={}
    )
    if response.status_code in {200, 201}:
        return lesson
    api.json(
        "POST",
        f"/api/domain/edu/lessons/{lesson['id']}/contents",
        expected=201,
        json={
            "kind": "lesson_plan",
            "schema_name": "weagent.education.lesson-plan",
            "schema_version": "1.0",
            "source_json": {
                "title": lesson["title"],
                "subject_code": subject_code,
                "learning_domain": lesson.get("learning_domain") or "integrated",
                "text_genre_code": lesson.get("text_genre_code") or "narrative",
                "objectives": ["提取文本证据", "说明人物与事件关系", "完成表达迁移"],
                "stages": [{"title": "阅读与表达", "duration_minutes": 45}],
            },
            "rendered_html": f"<h1>{lesson['title']}</h1><p>阅读、证据与表达迁移。</p>",
        },
    )
    api.json(
        "POST",
        f"/api/domain/edu/lessons/{lesson['id']}/contents",
        expected=201,
        json={
            "kind": "rich_document",
            "visibility_scope": "course_students",
            "schema_name": "weagent.education.rich-document",
            "schema_version": "1.0",
            "source_json": {"title": lesson["title"], "format": "html"},
            "rendered_html": f"<article><h1>{lesson['title']}</h1><p>阅读材料与课堂任务。</p></article>",
        },
    )
    api.json(
        "POST",
        publish_path,
        expected=(200, 201),
        headers=publish_headers,
        json={},
    )
    return lesson


def create_lesson(
    api: Api, course_id: str, unit_id: str, title: str, position: int, subject_code: str
):
    lesson = api.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/lessons",
        expected=201,
        json={
            "unit_id": unit_id,
            "title": title,
            "learning_domain": "integrated",
            "theme_code": "growth_and_evidence",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
            "position": position,
        },
    )
    publish_lesson(api, lesson, subject_code)
    lesson["status"] = "published"
    return lesson


def ensure_student_member(teacher: Api, student: Api, course_id: str):
    response = student.request(
        "GET",
        f"/api/domain/edu/courses/{course_id}",
        expected=(200, 404),
    )
    if response.status_code == 200:
        return
    invitation = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/invitations",
        expected=201,
        json={"max_uses": 1, "expires_in_hours": 4},
    )
    student.json(
        "POST",
        "/api/domain/edu/invitations/accept",
        json={"token": invitation["token"]},
    )


def upload_asset(
    api: Api,
    course_id: str,
    *,
    title: str,
    purpose: str,
    filename: str,
    content: bytes,
    media_type: str,
    visibility_scope: str = "course_teacher",
    lesson_id: str | None = None,
):
    data = {
        "title": title,
        "purpose": purpose,
        "visibility_scope": visibility_scope,
    }
    if lesson_id:
        data["lesson_id"] = lesson_id
    return api.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/assets",
        expected=201,
        data=data,
        files={"file": (filename, content, media_type)},
    )


def create_knowledge_fixture(api: Api, course_id: str, suffix: str):
    body = (
        "Phase 3 开放教学资料。内容围绕阅读证据、人物行动、情感变化与写作迁移，"
        "由 UAT 自建，不依赖临时沙箱。"
    ).encode("utf-8")
    asset = upload_asset(
        api,
        course_id,
        title=f"课程知识资料 {suffix}",
        purpose="knowledge_resource",
        filename=f"phase3-knowledge-{suffix}.txt",
        content=body,
        media_type="text/plain",
    )
    resource = api.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/knowledge-resources",
        expected=201,
        json={
            "asset_id": asset["id"],
            "title": asset["title"],
            "resource_type": "open_education_fixture",
            "visibility_scope": "course_teacher",
            "metadata": {
                "source_type": "uat_authored",
                "license_note": "UAT 自建教学材料",
                "sha256": asset["sha256"],
            },
        },
    )
    return {"asset": asset, "resource": resource}


def create_questions_and_paper(
    api: Api,
    course_id: str,
    *,
    subject_label: str,
    count: int,
    suffix: str,
):
    question_ids = []
    for index in range(1, count + 1):
        question = api.json(
            "POST",
            f"/api/domain/edu/courses/{course_id}/questions",
            expected=201,
            json={
                "title": f"{subject_label}证据题 {index}",
                "question_type": "single_choice",
                "prompt": f"第 {index} 题：哪一项最能作为人物态度变化的文本证据？",
                "options": [
                    "前后行动形成清晰变化",
                    "只出现一个无关地名",
                    "段落字数发生变化",
                    "标点数量略有不同",
                ],
                "difficulty": ("easy", "medium", "medium", "hard")[(index - 1) % 4],
                "score": 5,
                "knowledge_points": ["文本证据", "人物形象"],
                "correct_answer": "A",
                "explanation": "行动前后的变化能直接支撑人物态度变化。",
            },
        )
        api.json("POST", f"/api/domain/edu/questions/{question['id']}/publish")
        question_ids.append(question["id"])
    paper = api.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/papers/compose",
        expected=201,
        json={
            "title": f"{subject_label}阅读诊断卷 {suffix}",
            "purpose": "diagnostic",
            "duration_minutes": 30,
            "item_ids": question_ids,
        },
    )
    paper = api.json("POST", f"/api/domain/edu/papers/{paper['id']}/publish")
    return {"question_ids": question_ids, "paper": paper}


def create_mind_map_fixture(
    student: Api,
    course_id: str,
    *,
    title: str,
    scope_type: str,
    lesson_ids: list[str],
):
    return student.json(
        "POST",
        f"/api/domain/edu/courses/{course_id}/mind-maps",
        expected=201,
        json={
            "title": title,
            "scope_type": scope_type,
            "lesson_ids": lesson_ids,
        },
    )


def run(base_url: str, teacher_username: str, student_username: str):
    password = os.getenv("WEAGENT_UAT_PASSWORD", "")
    check(len(password) >= 10, "WEAGENT_UAT_PASSWORD must contain at least 10 characters")
    teacher = login(base_url, teacher_username, password)
    student = login(base_url, student_username, password)
    suffix = uuid.uuid4().hex[:6]

    courses = teacher.json("GET", "/api/domain/edu/courses").get("items") or []
    check(courses, "teacher account has no baseline course")
    english_courses = [
        course for course in courses if course.get("subject_code") == "high_school_english"
    ]
    check(english_courses, "teacher account has no high-school English baseline course")
    english_course = english_courses[0]
    ensure_student_member(teacher, student, english_course["id"])
    english_units = teacher.json(
        "GET", f"/api/domain/edu/courses/{english_course['id']}/structure"
    )
    units = english_units.get("units") or []
    check(units, "baseline course has no unit")
    existing_lessons = [lesson for unit in units for lesson in unit.get("lessons") or []]
    for lesson in existing_lessons:
        publish_lesson(teacher, lesson, "high_school_english")
    while len(existing_lessons) < 3:
        index = len(existing_lessons) + 1
        existing_lessons.append(
            create_lesson(
                teacher,
                english_course["id"],
                units[0]["id"],
                f"Evidence Workshop {index} · Phase 3",
                index,
                "high_school_english",
            )
        )

    chinese_course = teacher.json(
        "POST",
        "/api/domain/edu/courses",
        expected=201,
        json={
            "title": f"小学语文阅读写作 Phase 3 {suffix}",
            "subject_code": "primary_chinese",
            "grade_band": "primary",
        },
    )
    invitation = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{chinese_course['id']}/invitations",
        expected=201,
        json={"max_uses": 1, "expires_in_hours": 4},
    )
    student.json(
        "POST",
        "/api/domain/edu/invitations/accept",
        json={"token": invitation["token"]},
    )
    unit = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{chinese_course['id']}/units",
        expected=201,
        json={"title": "叙事阅读与表达", "position": 1},
    )
    chinese_lessons = [
        create_lesson(
            teacher, chinese_course["id"], unit["id"], title, index, "primary_chinese"
        )
        for index, title in enumerate(
            ("人物与事件线索", "关键语句与情感", "从阅读到片段写作"), 1
        )
    ]

    private_asset = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{chinese_course['id']}/assets",
        expected=201,
        data={
            "title": "课时一阅读材料",
            "purpose": "lesson_material",
            "visibility_scope": "course_teacher",
            "lesson_id": chinese_lessons[0]["id"],
        },
        files={"file": ("phase3-reading.txt", "阅读材料：人物行动推动事件发展。", "text/plain")},
    )
    student_private = student.json(
        "GET", f"/api/domain/edu/courses/{chinese_course['id']}/assets"
    ).get("items") or []
    check(private_asset["id"] not in {row["id"] for row in student_private}, "private asset leaked")
    teacher.json(
        "PATCH",
        f"/api/domain/edu/assets/{private_asset['id']}",
        json={"visibility_scope": "course_published"},
    )
    student_published = student.json(
        "GET",
        f"/api/domain/edu/courses/{chinese_course['id']}/assets",
        params={"lesson_id": chinese_lessons[0]["id"]},
    ).get("items") or []
    check(private_asset["id"] in {row["id"] for row in student_published}, "published asset missing")

    assignment = teacher.json(
        "POST",
        f"/api/domain/edu/lessons/{chinese_lessons[0]['id']}/assignments",
        expected=201,
        json={
            "title": "人物行动与情感证据",
            "kind": "writing",
            "max_score": 20,
            "instruction_json": {
                "html": "<p>阅读材料，找出两处人物行动，并写一段 150 字左右的感受。</p>"
            },
            "evaluation_json": {"rubric": {"证据": 8, "表达": 8, "规范": 4}},
            "source_asset_ids": [private_asset["id"]],
        },
    )
    teacher.json("POST", f"/api/domain/edu/assignments/{assignment['id']}/publish")
    updated = teacher.json(
        "PATCH",
        f"/api/domain/edu/assignments/{assignment['id']}",
        json={
            "current_version_id": assignment["current_version"]["id"],
            "title": "人物行动、情感与写作迁移",
            "instruction_json": {
                "html": "<p>阅读材料，圈出行动与情感证据，再完成 150 字片段写作。</p>"
            },
        },
    )
    student_before = student.json("GET", f"/api/domain/edu/assignments/{assignment['id']}")
    check(student_before["title"] == "人物行动与情感证据", "draft assignment leaked before republish")
    teacher.json("POST", f"/api/domain/edu/assignments/{assignment['id']}/publish")
    student_after = student.json("GET", f"/api/domain/edu/assignments/{assignment['id']}")
    check(student_after["title"] == updated["title"], "republished assignment is stale")

    question = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{chinese_course['id']}/questions",
        expected=201,
        json={
            "title": "人物行动的作用",
            "question_type": "single_choice",
            "prompt": "人物连续两次回头，最能说明什么？",
            "options": ["十分犹豫", "完全轻松", "毫不在意", "非常愤怒"],
            "difficulty": "medium",
            "score": 5,
            "knowledge_points": ["人物形象", "细节描写"],
            "correct_answer": "A",
            "explanation": "连续回头这一动作体现犹豫与牵挂。",
        },
    )
    teacher.json("POST", f"/api/domain/edu/questions/{question['id']}/publish")
    paper = teacher.json(
        "POST",
        f"/api/domain/edu/courses/{chinese_course['id']}/papers/compose",
        expected=201,
        json={
            "title": "叙事阅读诊断卷",
            "purpose": "diagnostic",
            "duration_minutes": 20,
            "item_ids": [question["id"]],
        },
    )

    mind_map = student.json(
        "POST",
        f"/api/domain/edu/courses/{chinese_course['id']}/mind-maps",
        expected=201,
        json={
            "title": "人物—事件—情感关系图",
            "scope_type": "custom",
            "lesson_ids": [lesson["id"] for lesson in chinese_lessons[:2]],
        },
    )
    document = {
        "schema_name": "education_mind_map_v2",
        "scope_type": "custom",
        "lesson_ids": [lesson["id"] for lesson in chinese_lessons[:2]],
        "root": {
            "id": "root",
            "label": "叙事阅读",
            "children": [
                {"id": "action", "label": "人物行动", "children": []},
                {"id": "emotion", "label": "情感变化", "children": []},
                {"id": "event", "label": "事件发展", "children": []},
            ],
        },
        "relations": [
            {"id": "rel-1", "from": "action", "to": "emotion", "label": "表现", "type": "cross_link"},
            {"id": "rel-2", "from": "action", "to": "event", "label": "推动", "type": "cross_link"},
        ],
        "view": {"direction": "right", "theme": "education_clear"},
    }
    mind_map = student.json(
        "POST",
        f"/api/domain/edu/mind-maps/{mind_map['id']}/versions",
        expected=201,
        json={"document": document, "source_refs": [], "change_summary": "建立跨课时关系"},
    )

    # Build the complete Phase 3 acceptance dataset around the same two users.
    courseware_assets = {}
    lesson_materials = {}
    assignment_sources = {}
    knowledge_fixtures = {}
    course_specs = (
        (english_course, existing_lessons, "高中英语", "english"),
        (chinese_course, chinese_lessons, "小学语文", "chinese"),
    )
    for course, lessons, subject_label, key in course_specs:
        first_deck = upload_asset(
            teacher,
            course["id"],
            title=f"{subject_label}课堂课件 A",
            purpose="courseware",
            filename=f"phase3-{key}-deck-a.html",
            content=(
                f"<!doctype html><meta charset='utf-8'><title>{subject_label}课堂课件 A</title>"
                f"<main><h1>{lessons[0]['title']}</h1><p>文本证据与表达迁移。</p></main>"
            ).encode("utf-8"),
            media_type="text/html",
            lesson_id=lessons[0]["id"],
        )
        second_deck = upload_asset(
            teacher,
            course["id"],
            title=f"{subject_label}课堂课件 B",
            purpose="courseware",
            filename=f"phase3-{key}-deck-b.html",
            content=(
                f"<!doctype html><meta charset='utf-8'><title>{subject_label}课堂课件 B</title>"
                f"<main><h1>{lessons[1]['title']}</h1><p>活动支架与退出任务。</p></main>"
            ).encode("utf-8"),
            media_type="text/html",
            visibility_scope="course_published",
            lesson_id=lessons[1]["id"],
        )
        courseware_assets[key] = [first_deck, second_deck]

        student_before_toggle = student.json(
            "GET",
            f"/api/domain/edu/courses/{course['id']}/assets",
            params={"purpose": "courseware", "lesson_id": lessons[0]["id"]},
        ).get("items") or []
        check(
            first_deck["id"] not in {row["id"] for row in student_before_toggle},
            f"{key} private courseware leaked before publish",
        )
        teacher.json(
            "PATCH",
            f"/api/domain/edu/assets/{first_deck['id']}",
            json={"visibility_scope": "course_published"},
        )
        student_after_toggle = student.json(
            "GET",
            f"/api/domain/edu/courses/{course['id']}/assets",
            params={"purpose": "courseware", "lesson_id": lessons[0]["id"]},
        ).get("items") or []
        check(
            first_deck["id"] in {row["id"] for row in student_after_toggle},
            f"{key} published courseware is missing from student view",
        )
        teacher.json(
            "PATCH",
            f"/api/domain/edu/assets/{first_deck['id']}",
            json={"visibility_scope": "course_teacher"},
        )
        student_after_withdraw = student.json(
            "GET",
            f"/api/domain/edu/courses/{course['id']}/assets",
            params={"purpose": "courseware", "lesson_id": lessons[0]["id"]},
        ).get("items") or []
        check(
            first_deck["id"] not in {row["id"] for row in student_after_withdraw},
            f"{key} withdrawn courseware remained visible",
        )
        teacher.json(
            "PATCH",
            f"/api/domain/edu/assets/{first_deck['id']}",
            json={"visibility_scope": "course_published"},
        )

        if key == "english":
            lesson_materials[key] = upload_asset(
                teacher,
                course["id"],
                title="英语课时阅读材料",
                purpose="lesson_material",
                filename="phase3-english-reading.txt",
                content=b"Open UAT text: actions reveal a character's changing attitude.",
                media_type="text/plain",
                visibility_scope="course_published",
                lesson_id=lessons[0]["id"],
            )
        else:
            lesson_materials[key] = private_asset

        assignment_sources[key] = upload_asset(
            teacher,
            course["id"],
            title=f"{subject_label}作业附件",
            purpose="assignment_source",
            filename=f"phase3-{key}-assignment.txt",
            content=(f"{subject_label}作业附件：请标注两处证据并完成写作。".encode("utf-8")),
            media_type="text/plain",
            visibility_scope="course_published",
            lesson_id=lessons[0]["id"],
        )
        knowledge_fixtures[key] = create_knowledge_fixture(
            teacher,
            course["id"],
            f"{key}-{suffix}",
        )

        disposable = upload_asset(
            teacher,
            course["id"],
            title=f"{subject_label}待归档课件",
            purpose="courseware",
            filename=f"phase3-{key}-archive.html",
            content=b"<!doctype html><p>archive UAT</p>",
            media_type="text/html",
            visibility_scope="course_published",
            lesson_id=lessons[2]["id"],
        )
        archived = teacher.json(
            "DELETE",
            f"/api/domain/edu/assets/{disposable['id']}",
        )
        check(archived.get("status") == "archived", f"{key} asset was not archived")
        student.request(
            "GET",
            disposable["download_url"],
            expected=404,
        )

    # Attach a canonical assignment_source to the already versioned Chinese assignment.
    chinese_draft = teacher.json(
        "PATCH",
        f"/api/domain/edu/assignments/{assignment['id']}",
        json={
            "current_version_id": updated["current_version"]["id"],
            "source_asset_ids": [assignment_sources["chinese"]["id"]],
        },
    )
    chinese_student_before = student.json(
        "GET", f"/api/domain/edu/assignments/{assignment['id']}"
    )
    check(
        chinese_student_before["published_version"]["version_number"]
        < chinese_draft["current_version"]["version_number"],
        "Chinese assignment draft leaked before republish",
    )
    teacher.json("POST", f"/api/domain/edu/assignments/{assignment['id']}/publish")
    chinese_student_after = student.json(
        "GET", f"/api/domain/edu/assignments/{assignment['id']}"
    )
    check(
        chinese_student_after["published_version"]["version_number"]
        == chinese_draft["current_version"]["version_number"],
        "Chinese assignment attachment version was not republished",
    )

    long_html = "".join(
        f"<p>{index:02d}. 阅读人物行动与情感变化，引用文本证据并完成表达迁移。"
        "这是一段用于验证长内容滚动边界的自建 UAT 文本。</p>"
        for index in range(1, 81)
    )
    english_assignment = teacher.json(
        "POST",
        f"/api/domain/edu/lessons/{existing_lessons[0]['id']}/assignments",
        expected=201,
        json={
            "title": "Long narrative evidence assignment",
            "kind": "writing",
            "max_score": 20,
            "max_attempts": 2,
            "instruction_json": {"html": long_html},
            "evaluation_json": {"rubric": {"evidence": 8, "reasoning": 8, "language": 4}},
            "source_asset_ids": [assignment_sources["english"]["id"]],
        },
    )
    teacher.json(
        "POST",
        f"/api/domain/edu/assignments/{english_assignment['id']}/publish",
    )
    english_v2 = teacher.json(
        "PATCH",
        f"/api/domain/edu/assignments/{english_assignment['id']}",
        json={
            "current_version_id": english_assignment["current_version"]["id"],
            "title": "Long narrative evidence and writing assignment",
            "instruction_json": {"html": long_html + "<p>Draft v2 adds a reflective exit task.</p>"},
        },
    )
    english_student_before = student.json(
        "GET", f"/api/domain/edu/assignments/{english_assignment['id']}"
    )
    check(
        english_student_before["title"] == english_assignment["title"],
        "English assignment draft leaked before republish",
    )
    teacher.json(
        "POST",
        f"/api/domain/edu/assignments/{english_assignment['id']}/publish",
    )
    english_student_after = student.json(
        "GET", f"/api/domain/edu/assignments/{english_assignment['id']}"
    )
    check(
        english_student_after["title"] == english_v2["title"],
        "English assignment republish did not advance the student snapshot",
    )

    for source in assignment_sources.values():
        in_use = teacher.request(
            "DELETE",
            f"/api/domain/edu/assets/{source['id']}",
            expected=409,
        ).json()
        check(in_use.get("error_code") == "asset_in_use", "referenced asset was deletable")

    teacher.json("POST", f"/api/domain/edu/papers/{paper['id']}/publish")
    english_knowledge = create_questions_and_paper(
        teacher,
        english_course["id"],
        subject_label="高中英语",
        count=4,
        suffix=suffix,
    )
    chinese_knowledge = create_questions_and_paper(
        teacher,
        chinese_course["id"],
        subject_label="小学语文",
        count=3,
        suffix=suffix,
    )

    english_lesson_map = create_mind_map_fixture(
        student,
        english_course["id"],
        title="English lesson evidence map",
        scope_type="lesson",
        lesson_ids=[existing_lessons[0]["id"]],
    )
    chinese_lesson_map = create_mind_map_fixture(
        student,
        chinese_course["id"],
        title="语文课时证据导图",
        scope_type="lesson",
        lesson_ids=[chinese_lessons[0]["id"]],
    )
    chinese_course_map = create_mind_map_fixture(
        student,
        chinese_course["id"],
        title="语文课程总览导图",
        scope_type="course",
        lesson_ids=[],
    )

    for course, lessons, _subject_label, key in course_specs:
        assets = teacher.json(
            "GET",
            f"/api/domain/edu/courses/{course['id']}/assets",
        ).get("items") or []
        purposes = [row.get("purpose") for row in assets]
        check(purposes.count("courseware") >= 2, f"{key} has fewer than two courseware files")
        check("lesson_material" in purposes, f"{key} lesson material is missing")
        check("assignment_source" in purposes, f"{key} assignment attachment is missing")
        resources = teacher.json(
            "GET",
            f"/api/domain/edu/courses/{course['id']}/knowledge-resources",
        ).get("items") or []
        check(resources, f"{key} knowledge resource is missing")

    all_question_count = sum(
        len(
            teacher.json(
                "GET", f"/api/domain/edu/courses/{course['id']}/questions"
            ).get("items")
            or []
        )
        for course in (english_course, chinese_course)
    )
    all_paper_count = sum(
        len(
            teacher.json(
                "GET", f"/api/domain/edu/courses/{course['id']}/papers"
            ).get("items")
            or []
        )
        for course in (english_course, chinese_course)
    )
    check(all_question_count >= 8, "Phase 3 dataset has fewer than eight questions")
    check(all_paper_count >= 2, "Phase 3 dataset has fewer than two papers")

    return {
        "status": "passed",
        "accounts": {"teacher_username": teacher_username, "student_username": student_username},
        "courses": [
            {"id": english_course["id"], "lesson_count": len(existing_lessons)},
            {"id": chinese_course["id"], "lesson_count": len(chinese_lessons)},
        ],
        "assets": {
            "courseware_per_course": 2,
            "lesson_material_ids": {key: value["id"] for key, value in lesson_materials.items()},
            "assignment_source_ids": {key: value["id"] for key, value in assignment_sources.items()},
            "knowledge_resource_ids": {
                key: value["resource"]["id"] for key, value in knowledge_fixtures.items()
            },
            "permission_toggle_and_archive": True,
            "dependency_conflict": True,
        },
        "assignments": {
            "chinese": {
                "id": assignment["id"],
                "published_version": chinese_student_after["published_version"]["version_number"],
            },
            "english_long": {
                "id": english_assignment["id"],
                "published_version": english_student_after["published_version"]["version_number"],
                "html_chars": len(long_html),
            },
        },
        "knowledge": {
            "question_count": all_question_count,
            "paper_count": all_paper_count,
            "english_paper_id": english_knowledge["paper"]["id"],
            "chinese_paper_id": chinese_knowledge["paper"]["id"],
        },
        "mind_maps": {
            "custom_id": mind_map["id"],
            "custom_version": mind_map["current_version"]["version_number"],
            "relation_count": len(mind_map["current_version"]["relations"]),
            "lesson_ids": [english_lesson_map["id"], chinese_lesson_map["id"]],
            "course_id": chinese_course_map["id"],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5002")
    parser.add_argument("--teacher-username", required=True)
    parser.add_argument("--student-username", required=True)
    args = parser.parse_args()
    try:
        result = run(args.base_url, args.teacher_username, args.student_username)
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
