"""Repair and enrich the fixed Phase 4 Education demo through public APIs."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from uat_phase4_authentic_english import CORE_URL, EDU_URL, PASSWORD, edu


ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / "output" / "pdf" / "gift-of-the-magi-reading-writing-assignment.pdf"
TEACHER_USERNAME = "edu_teacher_phase4_0802_authentic"
STUDENT_USERNAME = "edu_student_1_phase4_0802_authentic"
COURSE_TITLE = "高一英语·叙事阅读与写作（真实案例）"


def core_login(username):
    request = urllib.request.Request(
        f"{CORE_URL}/api/auth/login",
        data=json.dumps({"username": username, "password": PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["data"]["access_token"]


def multipart_upload(url, token, fields, file_path, *, content_type="application/pdf"):
    boundary = f"weagent-{uuid.uuid4().hex}"
    chunks = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = urllib.request.Request(
        url,
        data=b"".join(chunks),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"File upload failed ({error.code}): {body[:1000]}") from error


def download_bytes(url, token):
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read(), response.headers.get_content_type()


def flattened_lessons(course_id, token):
    structure = edu("GET", f"/courses/{course_id}/structure", token=token)
    lessons = list(structure.get("ungrouped_lessons") or [])
    for unit in structure.get("units") or []:
        lessons.extend(unit.get("lessons") or [])
    return sorted(lessons, key=lambda row: row.get("position") or 0)


def question_payload(question, *, lesson_id):
    version = question["current_version"]
    answer = version.get("answer") or {}
    return {
        "title": question["title"],
        "lesson_id": lesson_id,
        "question_type": version["question_type"],
        "prompt": version["prompt"],
        "options": version.get("options") or [],
        "difficulty": version["difficulty"],
        "score": version["score"],
        "knowledge_points": version.get("knowledge_points") or [],
        "grade_band": version.get("grade_band"),
        "source_context": version.get("source_context") or {},
        "stimulus_version_id": version.get("stimulus_version_id"),
        "stimulus_order": version.get("stimulus_order"),
        "correct_answer": answer.get("correct_answer"),
        "explanation": answer.get("explanation") or "",
        "rubric": answer.get("rubric") or {},
    }


def normalize_assignments(course_id, token, asset_id):
    assignments = edu("GET", f"/courses/{course_id}/assignments", token=token)["items"]
    for index, row in enumerate(assignments):
        detail = edu("GET", f"/assignments/{row['id']}", token=token)
        instruction = dict(detail.get("instruction_json") or {})
        instruction.pop("student_rubric", None)
        source_ids = [asset_id] if index == 0 else [
            asset["id"] for asset in detail.get("source_assets") or []
        ]
        edu(
            "PATCH",
            f"/assignments/{row['id']}",
            token=token,
            payload={
                "current_version_id": detail["current_version"]["id"],
                "title": detail["title"],
                "kind": detail["kind"],
                "instruction_json": instruction,
                "evaluation_json": {},
                "source_asset_ids": source_ids,
                "max_score": 100,
                "max_attempts": detail["max_attempts"],
                "allow_revision_after_feedback": detail["allow_revision_after_feedback"],
            },
        )
        edu("POST", f"/assignments/{row['id']}/publish", token=token)
    return assignments


def ensure_pdf_case(course_id, first_lesson, token):
    assignments = edu("GET", f"/courses/{course_id}/assignments", token=token)["items"]
    for assignment in assignments:
        for asset in assignment.get("source_assets") or []:
            if asset.get("original_filename") == PDF_PATH.name:
                return {"status": "existing", "source_asset": asset, "extractor_code": "pdf_text"}
    if not PDF_PATH.is_file():
        raise RuntimeError(f"Generate the PDF first: {PDF_PATH}")
    created = multipart_upload(
        f"{EDU_URL}/courses/{course_id}/assignment-imports",
        token,
        {
            "lesson_id": first_lesson["id"],
            "mode": "editable",
            "title": "The Gift of the Magi - Reading and Writing Assignment",
        },
        PDF_PATH,
    )
    processed = edu(
        "POST",
        f"/assignment-imports/{created['id']}/process",
        token=token,
    )
    if processed.get("status") != "review_required":
        raise RuntimeError(f"PDF did not reach teacher review: {processed}")
    if processed.get("extractor_code") != "pdf_text":
        raise RuntimeError(f"Unexpected PDF extractor: {processed.get('extractor_code')}")
    if "Della and Jim are both foolish and wise" not in processed.get("extracted_text", ""):
        raise RuntimeError("Extracted PDF text is missing the writing prompt")
    return processed


def ensure_knowledge_resource(course_id, token, asset):
    resources = edu(
        "GET", f"/courses/{course_id}/knowledge-resources", token=token
    )["items"]
    existing = next((row for row in resources if row["asset_id"] == asset["id"]), None)
    if existing:
        return existing
    return edu(
        "POST",
        f"/courses/{course_id}/knowledge-resources",
        token=token,
        payload={
            "asset_id": asset["id"],
            "title": "The Gift of the Magi - close-reading worksheet",
            "resource_type": "worksheet",
            "visibility_scope": "course_published",
            "metadata": {
                "source": "Project Gutenberg eBook #7256",
                "rights": "Public domain in the USA",
            },
        },
        expected=(201,),
    )


def ensure_lesson_question_bank(course_id, lessons, token):
    bank = edu("GET", f"/courses/{course_id}/questions", token=token)
    stimuli = bank.get("stimuli") or []
    if stimuli:
        stimulus = stimuli[0]
        if stimulus.get("lesson_id") != lessons[0]["id"]:
            version = stimulus["current_version"]
            edu(
                "POST",
                f"/stimuli/{stimulus['id']}/versions",
                token=token,
                payload={
                    "title": stimulus["title"],
                    "lesson_id": lessons[0]["id"],
                    "content": version["content"],
                    "source_refs": version.get("source_refs") or [],
                    "language": version.get("language"),
                },
                expected=(201,),
            )
            edu("POST", f"/stimuli/{stimulus['id']}/publish", token=token)

    bank = edu("GET", f"/courses/{course_id}/questions", token=token)
    by_title = {row["title"]: row for row in bank["items"]}
    transition = by_title.get("Transition revision")
    if transition and transition.get("lesson_id") != lessons[1]["id"]:
        updated = edu(
            "POST",
            f"/questions/{transition['id']}/versions",
            token=token,
            payload=question_payload(transition, lesson_id=lessons[1]["id"]),
            expected=(201,),
        )
        edu("POST", f"/questions/{updated['id']}/publish", token=token)

    additions = [
        {
            "title": "Embedded quotation repair",
            "lesson_id": lessons[1]["id"],
            "question_type": "short_answer",
            "prompt": "Revise this sentence so the quotation is grammatically embedded: Della is poor. ‘One dollar and eighty-seven cents.’",
            "correct_answer": "The repeated statement that Della has ‘one dollar and eighty-seven cents’ makes her poverty concrete.",
            "explanation": "A successful revision integrates the quotation into the student's own syntax and explains its purpose.",
            "difficulty": "medium",
            "score": 15,
            "knowledge_points": ["quotation integration", "evidence explanation"],
        },
        {
            "title": "Counterclaim bridge",
            "lesson_id": lessons[1]["id"],
            "question_type": "multiple_choice",
            "prompt": "Which TWO sentence openings can introduce a qualified counterclaim?",
            "options": ["Admittedly, their gifts become impractical,", "For example, the flat is small,", "Although the plan appears foolish,", "Therefore, Della counts the money."],
            "correct_answer": ["A", "C"],
            "explanation": "Both openings concede another view before the writer refines the central claim.",
            "difficulty": "medium",
            "score": 10,
            "knowledge_points": ["counterclaim", "cohesion"],
        },
        {
            "title": "Point-of-view boundary",
            "lesson_id": lessons[2]["id"],
            "question_type": "true_false",
            "prompt": "In a first-person rewrite from Jim's viewpoint, the writer may state Della's private thoughts as facts.",
            "correct_answer": False,
            "explanation": "Jim may infer Della's feelings from visible evidence, but he cannot directly know her private thoughts.",
            "difficulty": "easy",
            "score": 10,
            "knowledge_points": ["point of view", "narrative constraint"],
        },
        {
            "title": "Jim at the door micro-rewrite",
            "lesson_id": lessons[2]["id"],
            "question_type": "writing",
            "prompt": "Rewrite Jim's first ten seconds at the door in 80-100 words. Preserve the sold watch, the cut hair, and his initial silence.",
            "correct_answer": "A defensible response stays in Jim's first-person viewpoint and preserves all three source constraints.",
            "explanation": "The response is judged as one whole for viewpoint control, source fidelity, and precise emotional detail.",
            "difficulty": "hard",
            "score": 15,
            "knowledge_points": ["first-person narration", "source fidelity", "showing emotion"],
        },
    ]
    for payload in additions:
        if payload["title"] in by_title:
            continue
        created = edu(
            "POST",
            f"/courses/{course_id}/questions",
            token=token,
            payload={
                **payload,
                "options": payload.get("options") or [],
                "grade_band": "senior_high",
                "source_context": {"basis": "The Gift of the Magi lesson sequence"},
                "rubric": {},
            },
            expected=(201,),
        )
        edu("POST", f"/questions/{created['id']}/publish", token=token)

    bank = edu("GET", f"/courses/{course_id}/questions", token=token)
    by_title = {row["title"]: row for row in bank["items"]}
    paper_title = "课时 2-3：论证与视角迁移练习"
    papers = edu("GET", f"/courses/{course_id}/papers", token=token)["items"]
    if not any(row["title"] == paper_title for row in papers):
        selected = [by_title[payload["title"]]["id"] for payload in additions]
        paper = edu(
            "POST",
            f"/courses/{course_id}/papers/compose",
            token=token,
            payload={
                "title": paper_title,
                "purpose": "practice",
                "duration_minutes": 35,
                "item_ids": selected,
                "sections": [
                    {"title": "Analytical writing tools", "question_count": 2},
                    {"title": "Narrative point of view", "question_count": 2},
                ],
            },
            expected=(201,),
        )
        edu("POST", f"/papers/{paper['id']}/publish", token=token)
    return edu("GET", f"/courses/{course_id}/questions", token=token)


def ensure_courseware_assets(course_id, lesson, token):
    assets = edu(
        "GET",
        f"/courses/{course_id}/assets?purpose=courseware",
        token=token,
    )["items"]
    by_filename = {row["original_filename"]: row for row in assets}
    contents = edu("GET", f"/lessons/{lesson['id']}/contents", token=token)["items"]
    slide_documents = [row for row in contents if row["kind"] == "slide_document"]
    if not slide_documents:
        raise RuntimeError("The demo lesson needs a structured slide document")
    source_content = slide_documents[-1]
    specs = [
        {
            "format": "pptx",
            "filename": "wise-or-foolish-storybook-courseware.pptx",
            "title": "Wise or Foolish? - Storybook courseware",
            "visibility_scope": "course_published",
            "content_type": (
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
        },
        {
            "format": "html",
            "filename": "wise-or-foolish-storybook-preview.html",
            "title": "Wise or Foolish? - HTML preview",
            "visibility_scope": "course_teacher",
            "content_type": "text/html",
        },
    ]
    runtime_dir = ROOT / ".runtime" / "phase4-courseware-assets"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        existing = by_filename.get(spec["filename"])
        if existing:
            if existing["visibility_scope"] != spec["visibility_scope"]:
                existing = edu(
                    "PATCH",
                    f"/assets/{existing['id']}",
                    token=token,
                    payload={"visibility_scope": spec["visibility_scope"]},
                )
            by_filename[spec["filename"]] = existing
            continue
        exported, response_type = download_bytes(
            (
                f"{EDU_URL}/contents/{source_content['id']}/export"
                f"?format={spec['format']}"
            ),
            token,
        )
        if not exported:
            raise RuntimeError(f"Empty courseware export: {spec['format']}")
        temp_path = runtime_dir / spec["filename"]
        temp_path.write_bytes(exported)
        created = multipart_upload(
            f"{EDU_URL}/courses/{course_id}/assets",
            token,
            {
                "lesson_id": lesson["id"],
                "title": spec["title"],
                "purpose": "courseware",
                "visibility_scope": spec["visibility_scope"],
            },
            temp_path,
            content_type=response_type or spec["content_type"],
        )
        by_filename[spec["filename"]] = created
    return [by_filename[spec["filename"]] for spec in specs]


def ensure_student_mock_exam(course_id, teacher_token, student_token, papers):
    attempts = edu(
        "GET",
        f"/courses/{course_id}/mock-exams",
        token=student_token,
    )["items"]
    completed = next(
        (
            row
            for row in attempts
            if row["status"] in {"submitted", "pending_review"}
            and any(
                "The irony makes" in str(answer)
                for answer in (row.get("answers") or {}).values()
            )
        ),
        None,
    )
    if completed:
        return completed
    attempt = next(
        (row for row in attempts if row["status"] == "in_progress"),
        None,
    )

    paper = next(
        (row for row in papers if row.get("purpose") == "diagnostic"),
        papers[0] if papers else None,
    )
    if not paper:
        raise RuntimeError("A published paper is required for the mock-exam demo")
    if attempt is None:
        attempt = edu(
            "POST",
            f"/courses/{course_id}/mock-exams",
            token=student_token,
            payload={"paper_id": paper["id"]},
            expected=(201,),
        )

    frozen_paper = next(
        (
            row
            for row in papers
            if row.get("published_version_id") == attempt["paper_version_id"]
            or row.get("current_version_id") == attempt["paper_version_id"]
        ),
        paper,
    )
    preview = edu(
        "GET",
        (
            f"/papers/{frozen_paper['id']}/preview?mode=teacher"
            f"&version_id={attempt['paper_version_id']}"
        ),
        token=teacher_token,
    )
    answers_by_version = {
        question["id"]: (question.get("answer") or {}).get("correct_answer")
        for question in preview["questions"]
        if (question.get("answer") or {}).get("correct_answer") is not None
    }

    answers = {}
    for question in attempt.get("questions") or []:
        question_id = question["id"]
        if question["question_type"] == "short_answer":
            answers[question_id] = (
                "The repeated gray details create a bleak mood before Della acts, "
                "so her decision feels both desperate and loving."
            )
        elif question["question_type"] == "writing":
            answers[question_id] = (
                "Della and Jim may look foolish because each gift becomes unusable, "
                "but their choices reveal generosity rather than carelessness. Della "
                "sells her hair to buy Jim a chain, while Jim sells his watch to buy "
                "her combs. The irony makes the gifts impractical, yet it also proves "
                "that both characters value the other person above a possession."
            )
        elif question_id in answers_by_version:
            answers[question_id] = answers_by_version[question_id]
        else:
            raise RuntimeError(
                f"Missing a teacher answer key for mock-exam question {question_id}"
            )
    if len(answers) != len(attempt.get("questions") or []):
        raise RuntimeError("Every mock-exam question must receive a demo answer")
    edu(
        "PUT",
        f"/mock-exams/{attempt['id']}/answers",
        token=student_token,
        payload={"answers": answers},
    )
    return edu(
        "POST",
        f"/mock-exams/{attempt['id']}/submit",
        token=student_token,
    )


def main():
    if len(PASSWORD) < 8:
        raise RuntimeError("WEAGENT_UAT_PASSWORD must contain at least 8 characters")
    token = core_login(TEACHER_USERNAME)
    student_token = core_login(STUDENT_USERNAME)
    courses = edu("GET", "/courses", token=token)["items"]
    course = next((row for row in courses if row["title"] == COURSE_TITLE), None)
    if not course:
        raise RuntimeError("Fixed Phase 4 demo course is missing")
    lessons = flattened_lessons(course["id"], token)
    if len(lessons) != 3:
        raise RuntimeError(f"Expected three lessons, received {len(lessons)}")
    imported = ensure_pdf_case(course["id"], lessons[0], token)
    asset = imported["source_asset"]
    assignments = normalize_assignments(course["id"], token, asset["id"])
    resource = ensure_knowledge_resource(course["id"], token, asset)
    bank = ensure_lesson_question_bank(course["id"], lessons, token)
    courseware_assets = ensure_courseware_assets(course["id"], lessons[1], token)
    papers = edu("GET", f"/courses/{course['id']}/papers", token=token)["items"]
    mock_exam = ensure_student_mock_exam(
        course["id"], token, student_token, papers
    )
    mock_exams = edu(
        "GET",
        f"/courses/{course['id']}/mock-exams",
        token=student_token,
    )["items"]
    report = {
        "course_id": course["id"],
        "pdf_import": {
            "asset_id": asset["id"],
            "status": imported["status"],
            "extractor_code": imported["extractor_code"],
            "byte_size": asset["byte_size"],
        },
        "assignment_count": len(assignments),
        "assignments_use_overall_100": True,
        "question_count": len(bank["items"]),
        "questions_by_lesson": {
            lesson["title"]: sum(1 for row in bank["items"] if row.get("lesson_id") == lesson["id"])
            for lesson in lessons
        },
        "paper_count": len(papers),
        "courseware_assets": [
            {
                "id": row["id"],
                "filename": row["original_filename"],
                "visibility_scope": row["visibility_scope"],
                "byte_size": row["byte_size"],
            }
            for row in courseware_assets
        ],
        "mock_exam_count": len(mock_exams),
        "mock_exam": {
            "id": mock_exam["id"],
            "status": mock_exam["status"],
            "question_count": len(mock_exam.get("questions") or []),
            "score": mock_exam.get("score"),
            "max_score": mock_exam.get("max_score"),
            "accuracy": mock_exam.get("accuracy"),
        },
        "knowledge_resource_id": resource["id"],
    }
    if min(report["questions_by_lesson"].values()) < 2:
        raise RuntimeError(f"Each lesson needs at least two questions: {report}")
    output = ROOT / ".runtime" / "phase4-demo-enrichment.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"DEMO ENRICHMENT FAILED: {error}", file=sys.stderr)
        raise
