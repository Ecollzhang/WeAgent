"""Run the final Education MVP business-loop and live-model UAT.

The script intentionally prints only de-identified evidence. It never prints
tokens, request headers, raw model responses, invitation tokens, or student
answers.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(REPOSITORY_ROOT / ".env", override=False)

from services.edu.app import create_edu_app
from services.edu.extensions import db


class UATConfig:
    TESTING = True
    SERVICE_NAME = "weagent-edu-uat"
    PORT = 5102
    SECRET_KEY = "education-uat-secret"
    JWT_SECRET_KEY = "education-uat-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://127.0.0.1:6379/15"
    EDUCATION_FEATURE_ENABLED = True


def expect(response, status: int, label: str) -> dict[str, Any]:
    if response.status_code != status:
        body = response.get_json(silent=True)
        raise AssertionError(f"{label}: expected {status}, got {response.status_code}: {body}")
    return response.get_json() or {}


def live_model_probe() -> dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1").strip().rstrip("/")
    endpoint = (
        base_url
        if base_url.endswith("/chat/completions")
        else f"{base_url}/chat/completions"
    )
    model = os.getenv("TEXT2IFC_DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a lesson-design agent. Return concise JSON only, with keys "
                        "objectives, reading_activity, writing_activity, and assessment."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Design one high-school English narrative reading-to-writing lesson. "
                        "Keep it suitable for a teacher to review before publishing."
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        },
        timeout=(10, 90),
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []
    content = (
        ((choices[0].get("message") or {}).get("content") or "").strip()
        if choices
        else ""
    )
    if len(content) < 20:
        raise AssertionError("live model returned no usable lesson content")
    return {
        "provider": "openai-compatible",
        "model": str(payload.get("model") or model),
        "http_status": response.status_code,
        "output_chars": len(content),
        "output_sha256_12": hashlib.sha256(content.encode("utf-8")).hexdigest()[:12],
    }


def run_business_loop() -> dict[str, Any]:
    app = create_edu_app(UATConfig)
    with app.app_context():
        db.create_all()
        client = app.test_client()

        def auth(user_id: str) -> dict[str, str]:
            token = create_access_token(identity=user_id)
            return {"Authorization": f"Bearer {token}"}

        teacher = auth("uat-teacher")
        students = {
            "student-a": auth("uat-student-a"),
            "student-b": auth("uat-student-b"),
        }
        outsider = auth("uat-outsider")
        course_specs = [
            {
                "title": "高中英语：叙事阅读与写作",
                "subject_code": "high_school_english",
                "grade_band": "senior_high",
                "genre": "narrative",
                "theme": "growth_and_choices",
                "answers": [
                    "The turning point is supported by the character's final decision.",
                    "Evidence and reflection make the revised ending convincing.",
                ],
            },
            {
                "title": "小学语文：寓言阅读与表达",
                "subject_code": "primary_chinese",
                "grade_band": "primary",
                "genre": "fable",
                "theme": "wisdom_and_choices",
                "answers": [
                    "人物的行动和结果共同说明了寓意。",
                    "我用另一人物的视角重写结尾并保留寓意。",
                ],
            },
        ]
        counters = {
            "courses": 0,
            "memberships": 0,
            "lessons": 0,
            "published_lessons": 0,
            "assignments": 0,
            "submissions": 0,
            "feedback": 0,
            "draft_recoveries": 0,
            "isolation_checks": 0,
        }
        analytics_summary = []

        for course_index, spec in enumerate(course_specs, start=1):
            course = expect(
                client.post(
                    "/api/edu/courses",
                    headers=teacher,
                    json={
                        "title": spec["title"],
                        "subject_code": spec["subject_code"],
                        "grade_band": spec["grade_band"],
                    },
                ),
                201,
                "create course",
            )
            course_id = course["id"]
            counters["courses"] += 1

            invitation = expect(
                client.post(
                    f"/api/edu/courses/{course_id}/invitations",
                    headers=teacher,
                    json={"max_uses": 2, "expires_in_hours": 24},
                ),
                201,
                "create invitation",
            )
            for student_headers in students.values():
                expect(
                    client.post(
                        "/api/edu/invitations/accept",
                        headers=student_headers,
                        json={"token": invitation["token"]},
                    ),
                    200,
                    "join course",
                )
                counters["memberships"] += 1

            members = expect(
                client.get(f"/api/edu/courses/{course_id}/members", headers=teacher),
                200,
                "list members",
            )["items"]
            assert sorted(item["role"] for item in members) == ["student", "student", "teacher"]
            expect(
                client.get(f"/api/edu/courses/{course_id}/members", headers=outsider),
                404,
                "outsider member isolation",
            )
            counters["isolation_checks"] += 1

            unit = expect(
                client.post(
                    f"/api/edu/courses/{course_id}/units",
                    headers=teacher,
                    json={"title": "阅读与写作任务群", "position": 1},
                ),
                201,
                "create unit",
            )

            for lesson_index, domain in enumerate(("reading", "writing"), start=1):
                lesson = expect(
                    client.post(
                        f"/api/edu/courses/{course_id}/lessons",
                        headers=teacher,
                        json={
                            "unit_id": unit["id"],
                            "title": f"{spec['title']} · {domain}",
                            "learning_domain": domain,
                            "theme_code": spec["theme"],
                            "text_genre_code": spec["genre"],
                            "lesson_type_code": domain,
                            "duration_minutes": 45,
                            "position": lesson_index,
                        },
                    ),
                    201,
                    "create lesson",
                )
                lesson_id = lesson["id"]
                counters["lessons"] += 1
                plan = {
                    "subject_code": spec["subject_code"],
                    "learning_domain": domain,
                    "text_genre_code": spec["genre"],
                    "objectives": [
                        {
                            "id": f"{domain}-objective",
                            "description": (
                                "Locate evidence and explain meaning"
                                if domain == "reading"
                                else "Write a focused response using textual evidence"
                            ),
                        }
                    ],
                    "stages": [
                        {
                            "name": "Model, practise, reflect",
                            "duration_minutes": 35,
                            "teacher_activity": "Model the genre-specific strategy",
                            "student_activity": "Read, discuss, draft, and revise",
                            "assessment": "Exit response against the visible rubric",
                        }
                    ],
                }
                content = expect(
                    client.post(
                        f"/api/edu/lessons/{lesson_id}/contents",
                        headers=teacher,
                        json={
                            "kind": "lesson_plan",
                            "schema_name": "lesson_plan_json",
                            "source_json": plan,
                            "rendered_html": (
                                "<article><h1>Learning task</h1>"
                                "<p>Read closely, then write from evidence.</p></article>"
                            ),
                        },
                    ),
                    201,
                    "create lesson plan",
                )
                expect(
                    client.post(
                        f"/api/edu/lessons/{lesson_id}/activities",
                        headers=teacher,
                        json={
                            "activity_type": domain,
                            "title": f"{domain.title()} workshop",
                            "position": 1,
                            "content_version_id": content["version"]["id"],
                            "student_payload": {
                                "prompt": "Complete the visible reading-to-writing task."
                            },
                            "teacher_payload": {
                                "answer_key": "Private exemplar",
                                "rubric": {"evidence": 5, "expression": 5},
                            },
                        },
                    ),
                    201,
                    "create activity",
                )
                publication = expect(
                    client.post(
                        f"/api/edu/lessons/{lesson_id}/publish",
                        headers={
                            **teacher,
                            "Idempotency-Key": f"uat-{course_index}-{lesson_index}",
                        },
                        json={},
                    ),
                    201,
                    "publish lesson",
                )
                counters["published_lessons"] += 1

                release = expect(
                    client.get(
                        f"/api/edu/lessons/{lesson_id}/release",
                        headers=students["student-a"],
                    ),
                    200,
                    "student lesson release",
                )
                assert publication["teacher_evaluation_manifest"]
                assert "teacher_evaluation_manifest" not in release
                assert "answer_key" not in json.dumps(release)
                expect(
                    client.get(f"/api/edu/lessons/{lesson_id}/release", headers=outsider),
                    404,
                    "outsider lesson isolation",
                )
                counters["isolation_checks"] += 2

                assignment = expect(
                    client.post(
                        f"/api/edu/lessons/{lesson_id}/assignments",
                        headers=teacher,
                        json={
                            "title": f"{domain.title()} evidence task",
                            "kind": "quiz" if domain == "reading" else "writing",
                            "instruction_json": {
                                "prompt": "Respond with evidence from the learning material.",
                                "student_rubric": ["evidence", "clear expression"],
                            },
                            "evaluation_json": {
                                "answer_key": ["Private teacher criterion"],
                                "rubric": {"evidence": 5, "expression": 5},
                            },
                            "max_attempts": 2,
                        },
                    ),
                    201,
                    "create assignment",
                )
                assignment_id = assignment["id"]
                counters["assignments"] += 1
                expect(
                    client.post(
                        f"/api/edu/assignments/{assignment_id}/publish",
                        headers=teacher,
                    ),
                    200,
                    "publish assignment",
                )
                student_assignment = expect(
                    client.get(
                        f"/api/edu/assignments/{assignment_id}",
                        headers=students["student-a"],
                    ),
                    200,
                    "student assignment",
                )
                assert "evaluation_json" not in student_assignment
                counters["isolation_checks"] += 1

                for student_index, (student_name, student_headers) in enumerate(
                    students.items()
                ):
                    answer = {
                        "text": (
                            f"{spec['answers'][student_index]} "
                            f"[{domain}:{student_name}]"
                        )
                    }
                    expect(
                        client.put(
                            f"/api/edu/assignments/{assignment_id}/submission/draft",
                            headers=student_headers,
                            json={"answer_json": answer},
                        ),
                        200,
                        "save draft",
                    )
                    recovery = expect(
                        client.get(
                            f"/api/edu/assignments/{assignment_id}/submission",
                            headers=student_headers,
                        ),
                        200,
                        "recover draft",
                    )
                    assert recovery["draft"]["answer_json"] == answer
                    counters["draft_recoveries"] += 1
                    submitted = expect(
                        client.post(
                            f"/api/edu/assignments/{assignment_id}/submissions",
                            headers=student_headers,
                            json={},
                        ),
                        201,
                        "submit assignment",
                    )
                    counters["submissions"] += 1
                    expect(
                        client.post(
                            f"/api/edu/submissions/{submitted['submission']['id']}/feedback",
                            headers=teacher,
                            json={
                                "feedback_json": {
                                    "strengths": ["Uses relevant evidence"],
                                    "next_steps": ["Revise expression for precision"],
                                },
                                "score": 8 + student_index,
                            },
                        ),
                        201,
                        "release feedback",
                    )
                    own_feedback = expect(
                        client.get(
                            f"/api/edu/submissions/{submitted['submission']['id']}/feedback",
                            headers=student_headers,
                        ),
                        200,
                        "student feedback",
                    )
                    assert len(own_feedback["items"]) == 1
                    other_headers = students[
                        "student-b" if student_name == "student-a" else "student-a"
                    ]
                    expect(
                        client.get(
                            f"/api/edu/submissions/{submitted['submission']['id']}/feedback",
                            headers=other_headers,
                        ),
                        404,
                        "cross-student feedback isolation",
                    )
                    counters["feedback"] += 1
                    counters["isolation_checks"] += 1

            analytics = expect(
                client.get(f"/api/edu/courses/{course_id}/analytics", headers=teacher),
                200,
                "course analytics",
            )
            assert analytics["active_students"] == 2
            assert analytics["published_assignments"] == 2
            assert analytics["submitted_students"] == 2
            assert analytics["completion_rate"] == 1.0
            assert analytics["learning_domain_counts"] == {"reading": 1, "writing": 1}
            analytics_summary.append(
                {
                    "subject_code": spec["subject_code"],
                    "completion_rate": analytics["completion_rate"],
                    "average_score": analytics["average_score"],
                }
            )

        db.session.remove()
        db.drop_all()
    return {**counters, "analytics": analytics_summary}


def main() -> int:
    evidence = {
        "business_loop": run_business_loop(),
        "live_model": live_model_probe(),
    }
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
