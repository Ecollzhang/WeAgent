"""Seed and verify an authentic Phase 4 high-school English UAT course.

The password is supplied through WEAGENT_UAT_PASSWORD and is never persisted.
The script exercises the real core authentication and Education HTTP services.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


CORE_URL = os.getenv("WEAGENT_CORE_URL", "http://127.0.0.1:5002")
EDU_URL = os.getenv("WEAGENT_EDU_URL", "http://127.0.0.1:5102/api/edu")
PASSWORD = os.getenv("WEAGENT_UAT_PASSWORD", "")
RUN_KEY = os.getenv("WEAGENT_UAT_RUN_KEY", "phase4_0802_authentic")


class ApiError(RuntimeError):
    pass


def request_json(method, url, *, token=None, payload=None, headers=None, expected=(200,)):
    body = None
    request_headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request_headers.update(headers or {})
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            if response.status not in expected:
                raise ApiError(f"{method} {url} returned {response.status}: {data}")
            return data
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw[:1000]
        if error.code in expected:
            return data
        raise ApiError(f"{method} {url} returned {error.code}: {data}") from error


def core(method, path, **kwargs):
    return request_json(method, f"{CORE_URL}{path}", **kwargs)


def edu(method, path, **kwargs):
    return request_json(method, f"{EDU_URL}{path}", **kwargs)


def ensure_account(username, email):
    registered = core(
        "POST",
        "/api/auth/register",
        payload={"username": username, "email": email, "password": PASSWORD},
        expected=(201, 400),
    )
    if registered.get("success") is True:
        data = registered["data"]
    else:
        logged_in = core(
            "POST",
            "/api/auth/login",
            payload={"username": username, "password": PASSWORD},
        )
        data = logged_in["data"]
    return {
        "username": username,
        "user_id": data["user"]["id"],
        "token": data["access_token"],
    }


def lesson_plan(title, objective):
    return {
        "subject_code": "high_school_english",
        "learning_domain": "integrated",
        "text_genre_code": "narrative",
        "title": title,
        "objectives": [
            {"id": "objective-evidence", "description": objective},
            {
                "id": "objective-transfer",
                "description": "Transfer textual evidence into a coherent analytical or narrative paragraph.",
            },
        ],
        "stages": [
            {
                "name": "Evidence noticing",
                "duration_minutes": 12,
                "teacher_activity": "Model how a concrete detail supports an inference.",
                "student_activity": "Underline a detail and annotate what it implies.",
                "assessment": "Share one evidence–reasoning sentence.",
            },
            {
                "name": "Guided interpretation",
                "duration_minutes": 18,
                "teacher_activity": "Use follow-up questions to test alternative interpretations.",
                "student_activity": "Compare evidence and refine a claim with a partner.",
                "assessment": "Complete an evidence–reasoning organizer.",
            },
            {
                "name": "Writing transfer",
                "duration_minutes": 15,
                "teacher_activity": "Give one focused revision prompt.",
                "student_activity": "Draft or revise a short paragraph.",
                "assessment": "Submit a two-sentence exit response.",
            },
        ],
    }


def publishable_lesson(teacher_token, course_id, position, title, objective):
    lesson = edu(
        "POST",
        f"/courses/{course_id}/lessons",
        token=teacher_token,
        payload={
            "title": title,
            "learning_domain": "integrated",
            "theme_code": "choices_and_values",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading_writing",
            "duration_minutes": 45,
            "position": position,
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/lessons/{lesson['id']}/contents",
        token=teacher_token,
        payload={
            "kind": "lesson_plan",
            "visibility_scope": "course_teacher",
            "schema_name": "weagent.education.lesson-plan",
            "source_json": lesson_plan(title, objective),
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/lessons/{lesson['id']}/activities",
        token=teacher_token,
        payload={
            "activity_type": "reading",
            "title": "Evidence ladder",
            "position": 1,
            "student_payload": {
                "prompt": "Select one detail, state what it shows, and explain why it matters."
            },
            "teacher_payload": {
                "look_for": "A traceable detail followed by inference, not plot summary."
            },
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/lessons/{lesson['id']}/publish",
        token=teacher_token,
        headers={"Idempotency-Key": f"{RUN_KEY}-lesson-{position}"},
        expected=(201,),
    )
    return lesson


def create_assignment(teacher_token, lesson, title, kind, prompt):
    assignment = edu(
        "POST",
        f"/lessons/{lesson['id']}/assignments",
        token=teacher_token,
        payload={
            "title": title,
            "kind": kind,
            "instruction_json": {
                "html": f"<h3>{title}</h3><p>{prompt}</p>",
                "prompt": prompt,
            },
            "evaluation_json": {},
            "max_score": 100,
            "max_attempts": 2,
            "allow_revision_after_feedback": True,
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/assignments/{assignment['id']}/publish",
        token=teacher_token,
    )
    return assignment


def feedback_comment(assignment_index, score):
    if assignment_index == 0:
        return (
            "能准确定位情节转折，但引用后还需要解释这个细节怎样体现人物的牺牲。"
            if score < 80
            else "情节证据定位准确，能够把金钱细节与人物选择联系起来。"
        )
    if assignment_index == 1:
        return (
            "观点已经明确；下一步请把引文嵌入句子，并补足‘证据为什么支持观点’这一层推理。"
            if score < 80
            else "中心观点清晰，引文与反讽主题之间的推理链完整。"
        )
    return (
        "叙事视角基本稳定，但 Jim 的语气和内心冲突还缺少来自原文的语言依据。"
        if score < 80
        else "Jim 的视角保持稳定，改写保留了原作反讽并增加了合理的内心活动。"
    )


def verify_and_write_report(teacher, students, course):
    course_id = course["id"]
    structure = edu(
        "GET", f"/courses/{course_id}/structure", token=teacher["token"]
    )
    lessons = list(structure.get("ungrouped_lessons") or [])
    for unit in structure.get("units") or []:
        lessons.extend(unit.get("lessons") or [])
    assignments = edu(
        "GET", f"/courses/{course_id}/assignments", token=teacher["token"]
    )["items"]
    questions = edu(
        "GET", f"/courses/{course_id}/questions", token=teacher["token"]
    )
    papers = edu(
        "GET", f"/courses/{course_id}/papers", token=teacher["token"]
    )["items"]
    mind_maps = edu(
        "GET", f"/courses/{course_id}/mind-maps", token=students[0]["token"]
    )["items"]
    insights = edu(
        "POST",
        f"/courses/{course_id}/student-insights/refresh",
        token=teacher["token"],
        expected=(201,),
    )
    grade_overviews = [
        edu(
            "GET",
            f"/courses/{course_id}/grade-overview?assignment_id={assignment['id']}",
            token=teacher["token"],
        )
        for assignment in assignments
    ]
    weakness = edu(
        "GET",
        f"/courses/{course_id}/weakness-analysis",
        token=students[0]["token"],
    )
    preview_paper = max(
        papers,
        key=lambda row: len((row.get("current_version") or {}).get("item_version_ids") or []),
    )
    student_preview = edu(
        "GET",
        f"/papers/{preview_paper['id']}/preview?mode=student",
        token=students[0]["token"],
    )

    assert len(lessons) == 3
    assert len(assignments) == 3
    assert len(questions["stimuli"]) >= 1
    assert questions["stimuli"][0]["question_count"] >= 6
    assert {row["current_version"]["question_type"] for row in questions["items"]} >= {
        "single_choice",
        "multiple_choice",
        "true_false",
        "fill_blank",
        "short_answer",
        "writing",
    }
    assert len(student_preview["questions"]) >= 7
    assert all("answer" not in row for row in student_preview["questions"])
    assert grade_overviews[0]["submitted_count"] == 6
    assert grade_overviews[0]["student_count"] == 7
    assert len(grade_overviews[0]["course_assignment_trend"]) == 3
    assert len(insights["items"]) == 7
    assert weakness["data_state"] == "ready"
    assert len(weakness["weaknesses"]) >= 3
    assert mind_maps[0]["current_version"]["document"]["root"]["color_token"] == "teal"
    assert len(mind_maps[0]["current_version"]["relations"]) == 3

    report = {
        "course": {
            "id": course_id,
            "title": course["title"],
            "url": f"http://127.0.0.1:8080/education/courses/{course_id}",
        },
        "teacher": {key: teacher[key] for key in ("username", "user_id")},
        "student": {
            "username": students[0]["username"],
            "user_id": students[0]["user_id"],
            "display_name": students[0]["display_name"],
        },
        "counts": {
            "students": len(students),
            "lessons": len(lessons),
            "assignments": len(assignments),
            "submissions": sum(row["submitted_count"] for row in grade_overviews),
            "stimuli": len(questions["stimuli"]),
            "questions": len(questions["items"]),
            "paper_questions": len(student_preview["questions"]),
            "profiles": len(insights["items"]),
            "weaknesses_for_uat_student": len(weakness["weaknesses"]),
        },
        "ids": {
            "lesson_ids": [lesson["id"] for lesson in lessons],
            "assignment_ids": [assignment["id"] for assignment in assignments],
            "stimulus_id": questions["stimuli"][0]["id"],
            "paper_id": preview_paper["id"],
            "mind_map_id": mind_maps[0]["id"],
        },
        "source": {
            "title": "The Gift of the Magi",
            "author": "O. Henry",
            "url": "https://www.gutenberg.org/ebooks/7256",
            "rights": "Public domain in the USA; Project Gutenberg eBook #7256",
        },
        "checks": {
            "six_question_types": True,
            "student_answer_keys_hidden": True,
            "assignment_specific_grade_overview": True,
            "three_assignment_trend": True,
            "feedback_to_weakness_projection": True,
            "colored_versioned_mind_map": True,
        },
    }
    output = Path(__file__).resolve().parents[2] / ".runtime" / "phase4-authentic-uat.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def seed():
    if len(PASSWORD) < 8:
        raise ApiError("WEAGENT_UAT_PASSWORD must contain at least 8 characters")

    teacher = ensure_account(
        f"edu_teacher_{RUN_KEY}",
        f"edu_teacher_{RUN_KEY}@example.test",
    )
    student_names = ["陈雨桐", "周子涵", "林思远", "王可欣", "赵一诺", "孙嘉航", "许安然"]
    students = [
        {
            **ensure_account(
                f"edu_student_{index + 1}_{RUN_KEY}",
                f"edu_student_{index + 1}_{RUN_KEY}@example.test",
            ),
            "display_name": display_name,
        }
        for index, display_name in enumerate(student_names)
    ]

    existing_courses = edu("GET", "/courses", token=teacher["token"])["items"]
    existing = next(
        (
            row
            for row in existing_courses
            if row["title"] == "高一英语·叙事阅读与写作（真实案例）"
        ),
        None,
    )
    if existing:
        verify_and_write_report(teacher, students, existing)
        return

    course = edu(
        "POST",
        "/courses",
        token=teacher["token"],
        payload={
            "title": "高一英语·叙事阅读与写作（真实案例）",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
            "description": (
                "以 O. Henry 公共领域短篇 The Gift of the Magi 为核心，"
                "训练文本证据、反讽分析与叙事改写。"
            ),
        },
        expected=(201,),
    )
    course_id = course["id"]
    edu(
        "PUT",
        f"/courses/{course_id}/me/profile",
        token=teacher["token"],
        payload={"display_name": "林老师"},
    )
    invitation = edu(
        "POST",
        f"/courses/{course_id}/invitations",
        token=teacher["token"],
        payload={"max_uses": 20, "expires_in_hours": 168},
        expected=(201,),
    )
    for student in students:
        edu(
            "POST",
            "/invitations/accept",
            token=student["token"],
            payload={"token": invitation["token"]},
        )
        edu(
            "PUT",
            f"/courses/{course_id}/me/profile",
            token=student["token"],
            payload={"display_name": student["display_name"]},
        )

    lesson_specs = [
        (
            "The Gift of the Magi：证据与反讽",
            "Infer Della's motivation and explain situational irony with traceable textual evidence.",
        ),
        (
            "分析段落：Wise or Foolish?",
            "Build a claim–evidence–reasoning paragraph about the narrator's final judgment.",
        ),
        (
            "视角改写：Jim at the Door",
            "Rewrite the turning point from Jim's point of view while preserving textual constraints.",
        ),
    ]
    lessons = [
        publishable_lesson(
            teacher["token"], course_id, index + 1, title, objective
        )
        for index, (title, objective) in enumerate(lesson_specs)
    ]

    assignments = [
        create_assignment(
            teacher["token"],
            lessons[0],
            "阅读证据检查：Della 的选择",
            "quiz",
            (
                "阅读课内节选，完成四个问题：概括 Della 的处境；找出一处金钱细节；"
                "解释该细节如何推动她的决定；用一句话说明结尾的反讽。"
            ),
        ),
        create_assignment(
            teacher["token"],
            lessons[1],
            "分析写作：他们是 Wise 还是 Foolish？",
            "writing",
            (
                "写一个 180–220 词的分析段落，回应 ‘Della and Jim are both foolish and wise.’ "
                "必须整合两处原文证据，并解释叙述者在结尾为什么称他们为 the magi。"
            ),
        ),
        create_assignment(
            teacher["token"],
            lessons[2],
            "叙事改写：Jim 进门的三分钟",
            "writing",
            (
                "从 Jim 的第一人称视角改写他进门到两人收起礼物的片段，220–280 词。"
                "保留原作的三个事实约束，并通过动作、内心独白与对话呈现他的情绪变化。"
            ),
        ),
    ]

    score_rows = [
        [68, 92, 84, 76, 88, 61, None],
        [65, 90, 82, 73, 86, None, None],
        [62, 94, 79, 70, None, None, None],
    ]
    answer_rows = [
        (
            "Della has only $1.87 after months of saving. The repeated counting makes the shortage concrete "
            "and explains why selling her hair becomes a meaningful sacrifice."
        ),
        (
            "Della and Jim appear foolish because each destroys the practical use of the other's gift, "
            "yet the narrator calls them wise because their choices reveal selfless love rather than material value."
        ),
        (
            "I stopped at the door because Della's hair was gone. For one breath I thought I had entered "
            "the wrong room; then I saw her anxious eyes and understood that she had given up something precious."
        ),
    ]
    for assignment_index, assignment in enumerate(assignments):
        for student_index, score in enumerate(score_rows[assignment_index]):
            if score is None:
                continue
            student = students[student_index]
            submitted = edu(
                "POST",
                f"/assignments/{assignment['id']}/submissions",
                token=student["token"],
                payload={
                    "answer_json": {
                        "writing": answer_rows[assignment_index],
                        "reflection": (
                            "I used a detail from the text and checked whether my explanation answered why it matters."
                        ),
                    }
                },
                expected=(201,),
            )
            submission_id = submitted["submission"]["id"]
            edu(
                "POST",
                f"/submissions/{submission_id}/feedback",
                token=teacher["token"],
                payload={
                    "feedback_json": {
                        "comment": feedback_comment(assignment_index, score)
                    },
                    "score": score,
                },
                expected=(201,),
            )

    source_url = "https://www.gutenberg.org/ebooks/7256"
    stimulus = edu(
        "POST",
        f"/courses/{course_id}/stimuli",
        token=teacher["token"],
        payload={
            "title": "The Gift of the Magi — evidence and irony excerpt",
            "lesson_id": lessons[0]["id"],
            "stimulus_type": "reading_passage",
            "language": "en",
            "content": {
                "paragraphs": [
                    (
                        "One dollar and eighty-seven cents. That was all. And sixty cents of it was in pennies. "
                        "Pennies saved one and two at a time by bargaining with the grocer, the vegetable man, "
                        "and the butcher. Three times Della counted it. One dollar and eighty-seven cents. "
                        "And the next day would be Christmas."
                    ),
                    (
                        "There was clearly nothing to do but sit down on the shabby little couch and cry. "
                        "So Della did it. Then she stood by the window and looked out dully at a gray cat "
                        "walking along a gray fence in a gray backyard."
                    ),
                    (
                        "Jim had not yet seen his beautiful present. She held it out to him eagerly. "
                        "The dull precious metal seemed to flash with a reflection of her bright and ardent spirit."
                    ),
                    (
                        "Jim smiled and said that he had sold the watch to buy her combs. The narrator closes by "
                        "calling these two seemingly foolish young people the wisest of all who give and receive gifts."
                    ),
                ],
                "teacher_note": (
                    "Classroom excerpt lightly modernizes two lexical items while preserving the source sequence; "
                    "teachers can open the source record for the complete public-domain text."
                ),
            },
            "source_refs": [
                {
                    "title": "The Gift of the Magi",
                    "author": "O. Henry",
                    "url": source_url,
                    "rights": "Public domain in the USA; Project Gutenberg eBook #7256",
                }
            ],
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/stimuli/{stimulus['id']}/publish",
        token=teacher["token"],
    )
    stimulus_version_id = stimulus["current_version_id"]
    question_payloads = [
        {
            "title": "Repeated counting and motivation",
            "question_type": "single_choice",
            "prompt": "What does Della's repeated counting most strongly reveal?",
            "options": [
                "She enjoys handling coins.",
                "Her limited money makes the gift problem urgent.",
                "She distrusts Jim's arithmetic.",
                "She plans to return the groceries.",
            ],
            "correct_answer": "B",
            "explanation": "The repeated exact sum foregrounds scarcity before her decision.",
            "difficulty": "easy",
            "score": 5,
            "knowledge_points": ["detail inference", "character motivation"],
        },
        {
            "title": "Evidence of sacrifice",
            "question_type": "multiple_choice",
            "prompt": "Which TWO details best establish the couple's sacrifice?",
            "options": [
                "The backyard fence is gray.",
                "Della gives up her hair to buy Jim's gift.",
                "Christmas is the next day.",
                "Jim sells his watch to buy Della's combs.",
            ],
            "correct_answer": ["B", "D"],
            "explanation": "Both characters surrender their most valued possession for the other.",
            "difficulty": "easy",
            "score": 6,
            "knowledge_points": ["text evidence", "parallel structure"],
        },
        {
            "title": "Sequence check",
            "question_type": "true_false",
            "prompt": "Both gifts become temporarily unusable because each character sells a treasured possession.",
            "correct_answer": True,
            "explanation": "The chain needs Jim's sold watch; the combs need Della's sold hair.",
            "difficulty": "easy",
            "score": 3,
            "knowledge_points": ["plot sequence", "situational irony"],
        },
        {
            "title": "Exact-detail recall",
            "question_type": "fill_blank",
            "prompt": "Complete the amount: Della has only ________ before Christmas.",
            "correct_answer": ["one dollar and eighty-seven cents", "$1.87", "1.87 dollars"],
            "explanation": "The exact amount is repeated to make her poverty concrete.",
            "difficulty": "easy",
            "score": 3,
            "knowledge_points": ["key detail"],
        },
        {
            "title": "Gray imagery",
            "question_type": "short_answer",
            "prompt": "How does the repeated word ‘gray’ support the mood before Della acts? Use one detail.",
            "correct_answer": "It mirrors Della's dull, discouraged mood and makes her later decision feel like a change.",
            "explanation": "A strong response links imagery, mood, and the coming decision.",
            "rubric": {"textual_detail": 3, "inference": 3},
            "difficulty": "medium",
            "score": 6,
            "knowledge_points": ["imagery", "mood", "evidence reasoning"],
        },
        {
            "title": "Foolish and wise",
            "question_type": "writing",
            "prompt": "In 120–150 words, explain how the ending makes Della and Jim both foolish and wise.",
            "correct_answer": "A defensible paragraph should explain practical foolishness and selfless wisdom with two details.",
            "explanation": "The task assesses claim, evidence integration, reasoning, and concise academic language.",
            "rubric": {"claim": 4, "evidence": 6, "reasoning": 6, "language": 4},
            "difficulty": "hard",
            "score": 20,
            "knowledge_points": ["situational irony", "theme", "analytical writing"],
        },
    ]
    question_ids = []
    for order, payload in enumerate(question_payloads, start=1):
        question = edu(
            "POST",
            f"/courses/{course_id}/questions",
            token=teacher["token"],
            payload={
                **payload,
                "grade_band": "senior_high",
                "source_context": {
                    "source_title": "The Gift of the Magi",
                    "source_url": source_url,
                    "rights": "Public domain in the USA",
                },
                "stimulus_version_id": stimulus_version_id,
                "stimulus_order": order,
            },
            expected=(201,),
        )
        edu(
            "POST",
            f"/questions/{question['id']}/publish",
            token=teacher["token"],
        )
        question_ids.append(question["id"])

    standalone = edu(
        "POST",
        f"/courses/{course_id}/questions",
        token=teacher["token"],
        payload={
            "title": "Transition revision",
            "lesson_id": lessons[1]["id"],
            "question_type": "single_choice",
            "prompt": "Which transition best introduces a contrasting interpretation?",
            "options": ["For example", "However", "Similarly", "As a result"],
            "correct_answer": "B",
            "explanation": "However signals contrast between practical foolishness and emotional wisdom.",
            "difficulty": "easy",
            "score": 4,
            "knowledge_points": ["cohesion", "contrast transition"],
            "grade_band": "senior_high",
            "source_context": {"basis": "writing transfer from the reading lesson"},
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/questions/{standalone['id']}/publish",
        token=teacher["token"],
    )
    question_ids.append(standalone["id"])

    paper = edu(
        "POST",
        f"/courses/{course_id}/papers/compose",
        token=teacher["token"],
        payload={
            "title": "The Gift of the Magi 单元诊断卷",
            "purpose": "diagnostic",
            "duration_minutes": 40,
            "item_ids": question_ids,
            "sections": [
                {"title": "Reading evidence", "question_count": 5},
                {"title": "Interpretation and writing", "question_count": 2},
            ],
        },
        expected=(201,),
    )
    edu(
        "POST",
        f"/papers/{paper['id']}/publish",
        token=teacher["token"],
    )

    mind_map_document = {
        "schema_name": "education_mind_map_v2",
        "scope_type": "course",
        "lesson_ids": [lesson["id"] for lesson in lessons],
        "root": {
            "id": "gift-root",
            "label": "The Gift of the Magi",
            "color_token": "teal",
            "children": [
                {
                    "id": "plot",
                    "label": "Plot and turning points",
                    "color_token": "blue",
                    "children": [
                        {"id": "money", "label": "$1.87 problem", "color_token": "blue", "children": []},
                        {"id": "hair", "label": "Della sells her hair", "color_token": "violet", "children": []},
                        {"id": "watch", "label": "Jim sells his watch", "color_token": "violet", "children": []},
                    ],
                },
                {
                    "id": "characters",
                    "label": "Character choices",
                    "color_token": "indigo",
                    "children": [
                        {"id": "della", "label": "Della: urgency → resolve", "color_token": "indigo", "children": []},
                        {"id": "jim", "label": "Jim: shock → understanding", "color_token": "indigo", "children": []},
                    ],
                },
                {
                    "id": "irony",
                    "label": "Situational irony",
                    "color_token": "amber",
                    "children": [
                        {"id": "unusable", "label": "Useful gifts become unusable", "color_token": "amber", "children": []},
                        {"id": "magi", "label": "Foolish actions, wise giving", "color_token": "orange", "children": []},
                    ],
                },
                {
                    "id": "transfer",
                    "label": "Writing transfer",
                    "color_token": "rose",
                    "children": [
                        {"id": "cer", "label": "Claim–evidence–reasoning", "color_token": "rose", "children": []},
                        {"id": "pov", "label": "Jim's point of view", "color_token": "slate", "children": []},
                    ],
                },
            ],
        },
        "relations": [
            {"id": "rel-1", "from": "hair", "to": "unusable", "label": "creates", "type": "cross_link"},
            {"id": "rel-2", "from": "watch", "to": "magi", "label": "supports theme", "type": "cross_link"},
            {"id": "rel-3", "from": "cer", "to": "magi", "label": "explains", "type": "cross_link"},
        ],
        "view": {"direction": "right", "theme": "education_clear"},
    }
    mind_map = edu(
        "POST",
        f"/courses/{course_id}/mind-maps",
        token=students[0]["token"],
        payload={
            "title": "我的《麦琪的礼物》证据图",
            "scope_type": "course",
            "document": mind_map_document,
            "source_refs": [lesson["id"] for lesson in lessons],
            "change_summary": "基于三节已发布课时整理情节、反讽与写作迁移。",
        },
        expected=(201,),
    )

    verify_and_write_report(teacher, students, course)


if __name__ == "__main__":
    try:
        seed()
    except Exception as error:
        print(f"UAT FAILED: {error}", file=sys.stderr)
        raise
