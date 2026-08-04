from types import SimpleNamespace
import json

from app.services.message_service import MessageService, _public_education_workflow
from app.services.agent_output_sanitizer import public_agent_output


def _worker(agent_id, name):
    return SimpleNamespace(
        participant_id=agent_id,
        participant_name=name,
    )


def test_server_defined_workflow_builds_deterministic_dependency_layers():
    workflow = {
        "id": "product.courseware",
        "name": "Agent 课件制作",
        "execution_mode": "server_defined",
        "nodes": [
            {
                "id": "step-1",
                "type": "agent_task",
                "agent_id": "_edu_1",
                "agent_role": "course_designer",
            },
            {
                "id": "step-2",
                "type": "agent_task",
                "agent_id": "_edu_2",
                "agent_role": "courseware_maker",
                "finalizer": {"type": "education_courseware_from_agent_files"},
            },
            {
                "id": "step-3",
                "type": "agent_task",
                "agent_id": "_edu_9",
                "agent_role": "teaching_reviewer",
            },
        ],
        "edges": [
            {"from": "step-1", "to": "step-2"},
            {"from": "step-2", "to": "step-3"},
        ],
        "parallel_groups": [],
    }
    workers = [
        _worker("_edu_1", "课程设计师"),
        _worker("_edu_2", "课件制作师"),
        _worker("_edu_9", "教学审校员"),
    ]

    plan = MessageService._server_defined_workflow_plan(workflow, workers)

    assert plan["type"] == "plan"
    assert plan["source"] == "server_defined_workflow"
    assert plan["parallel_groups"] == [["step-1"], ["step-2"], ["step-3"]]
    assert [task["depends_on"] for task in plan["tasks"]] == [
        [],
        ["step-1"],
        ["step-2"],
    ]
    assert [task["agent_id"] for task in plan["tasks"]] == [
        "_edu_1",
        "_edu_2",
        "_edu_9",
    ]
    assert plan["tasks"][1]["finalizer"] == {
        "type": "education_courseware_from_agent_files"
    }
    assert all("用户原始任务" in task["instruction"] for task in plan["tasks"])


def test_server_defined_workflow_rejects_unknown_worker_or_cycle():
    workers = [_worker("_edu_1", "课程设计师")]
    unknown = {
        "execution_mode": "server_defined",
        "nodes": [
            {"id": "a", "type": "agent_task", "agent_id": "_edu_missing"},
        ],
        "edges": [],
    }
    cyclic = {
        "execution_mode": "server_defined",
        "nodes": [
            {"id": "a", "type": "agent_task", "agent_id": "_edu_1"},
            {"id": "b", "type": "agent_task", "agent_id": "_edu_1"},
        ],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},
        ],
    }

    assert MessageService._server_defined_workflow_plan(unknown, workers) is None
    assert MessageService._server_defined_workflow_plan(cyclic, workers) is None


def test_server_defined_workflow_rejects_untrusted_finalizer():
    workflow = {
        "execution_mode": "server_defined",
        "nodes": [
            {
                "id": "a",
                "type": "agent_task",
                "agent_id": "_edu_1",
                "finalizer": {"type": "run_arbitrary_command"},
            },
        ],
        "edges": [],
    }

    assert MessageService._server_defined_workflow_plan(
        workflow,
        [_worker("_edu_1", "Course designer")],
    ) is None


def test_server_defined_workflow_accepts_bounded_question_finalizer():
    workflow = {
        "execution_mode": "server_defined",
        "nodes": [
            {
                "id": "questions",
                "type": "agent_task",
                "agent_id": "_edu_3",
                "agent_role": "exercise_generator",
                "finalizer": {"type": "education_questions_from_agent_reply"},
            },
        ],
        "edges": [],
    }

    plan = MessageService._server_defined_workflow_plan(
        workflow,
        [_worker("_edu_3", "Exercise generator")],
    )

    assert plan is not None
    assert plan["tasks"][0]["finalizer"] == {
        "type": "education_questions_from_agent_reply"
    }


def test_server_defined_workflow_accepts_bounded_student_insight_finalizer():
    workflow = {
        "execution_mode": "server_defined",
        "nodes": [
            {
                "id": "refresh",
                "type": "agent_task",
                "agent_id": "_edu_4",
                "agent_role": "learning_analyst",
                "finalizer": {
                    "type": "education_student_insight_refresh_from_agent_reply"
                },
            },
        ],
        "edges": [],
    }

    plan = MessageService._server_defined_workflow_plan(
        workflow,
        [_worker("_edu_4", "Learning analyst")],
    )

    assert plan is not None
    assert plan["tasks"][0]["finalizer"] == {
        "type": "education_student_insight_refresh_from_agent_reply"
    }


def test_education_natural_language_courseware_intent_builds_trusted_plan():
    conversation = SimpleNamespace(kb_domain="edu")
    workers = [
        _worker("_edu_1", "Course designer"),
        _worker("_edu_2", "Courseware maker"),
        _worker("_edu_9", "Teaching reviewer"),
    ]

    plan = MessageService._education_natural_language_plan(
        conversation,
        "根据当前教案帮我生成一套 8 页左右、paper_annotation 风格的 PPT。",
        workers,
    )

    assert plan["source"] == "education_natural_language_intent"
    assert plan["intent"] == "courseware_create"
    assert [task["agent_id"] for task in plan["tasks"]] == [
        "_edu_1",
        "_edu_2",
        "_edu_9",
    ]
    maker = plan["tasks"][1]
    assert maker["finalizer"] == {
        "type": "education_courseware_from_agent_files"
    }
    assert "slide_document.json" in maker["instruction"]
    assert "preview.html" in maker["instruction"]
    assert "paper_annotation" in maker["instruction"]


def test_education_natural_language_revision_takes_precedence_over_create():
    conversation = SimpleNamespace(kb_domain="edu")
    workers = [
        _worker("_edu_2", "Courseware maker"),
        _worker("_edu_9", "Teaching reviewer"),
    ]

    plan = MessageService._education_natural_language_plan(
        conversation,
        "把第三页改成证据—推理—结论结构，并保存新版本。",
        workers,
    )

    assert plan["intent"] == "courseware_version"
    assert plan["tasks"][0]["finalizer"] == {
        "type": "education_courseware_version_from_agent_files"
    }
    assert "edu.course.context.get" in plan["tasks"][0]["instruction"]


def test_education_natural_language_lesson_update_uses_bounded_finalizer():
    conversation = SimpleNamespace(kb_domain="edu")
    workers = [_worker("_edu_1", "Course designer")]

    plan = MessageService._education_natural_language_plan(
        conversation,
        "把当前课时时长改成 50 分钟。",
        workers,
    )

    assert plan["intent"] == "lesson_update"
    assert plan["tasks"][0]["finalizer"] == {
        "type": "education_lesson_update_from_agent_reply"
    }
    assert "changes" in plan["tasks"][0]["instruction"]


def test_education_workflow_projection_hides_private_instruction_and_ids():
    plan = MessageService._education_natural_language_plan(
        SimpleNamespace(kb_domain="edu"),
        "把当前课时时长改成 50 分钟。",
        [_worker("_edu_1", "课程设计师")],
    )

    workflow = MessageService._workflow_from_plan(plan)
    summary = MessageService._format_plan_summary(plan)

    assert workflow["nodes"][0]["title"] == "课程设计师"
    assert "instruction" not in workflow["nodes"][0]
    assert "agent_id" not in workflow["nodes"][0]
    assert "_edu_1" not in summary
    assert "edu-intent-lesson_update-1" not in summary
    assert "课程设计师" in summary


def test_public_agent_output_removes_provider_and_private_tool_trace():
    raw = (
        'Reading additional input from stdin...我将先探测当前服务。\n'
        '<tool_call>{"name":"list_services","args":{}}</tool_call>\n'
        'This will show me the available endpoints.\n'
        '{"changes":{"duration_minutes":50},"summary":"已调整",'
        '"workspace":"be6e11ee-4d3d-45bc-be70-76a83f1c25cf"}'
    )

    projected = public_agent_output(raw)

    assert projected == (
        '{"changes":{"duration_minutes":50},"summary":"已调整",'
        '"workspace":"[内部标识已隐藏]"}'
    )
    assert "tool_call" not in projected


def test_public_agent_output_hides_project_ids_and_private_workflow_task_keys():
    raw = (
        "课程 ID：1821bf81-485d-4c1a-94e3-b90936bceb8d\n"
        "前置任务未成功完成：edu-intent-courseware_create-2"
    )

    projected = public_agent_output(raw)

    assert "1821bf81-485d-4c1a-94e3-b90936bceb8d" not in projected
    assert "edu-intent-courseware_create-2" not in projected
    assert "[内部标识已隐藏]" in projected
    assert "前置步骤" in projected


def test_existing_education_workflow_is_projected_without_private_fields():
    conversation = SimpleNamespace(
        kb_domain="edu",
        participants=[
            SimpleNamespace(
                participant_type="agent",
                participant_id="_edu_1",
                participant_name="课程设计师",
            )
        ],
    )
    element = {
        "type": "workflow",
        "content": "internal",
        "data": {
            "id": "private-id",
            "name": "课时修改",
            "summary": "正在修改课时",
            "source": "moderator_plan",
            "raw_plan": {"token": "must-not-leak"},
            "nodes": [
                {
                    "id": "edu-intent-lesson_update-1",
                    "agent_id": "_edu_1",
                    "instruction": "private system instruction",
                    "title": "internal title",
                    "depends_on": [],
                }
            ],
            "edges": [],
            "parallel_groups": [["edu-intent-lesson_update-1"]],
        },
    }

    projected = _public_education_workflow(element, conversation)
    serialized = json.dumps(projected, ensure_ascii=False)

    assert projected["data"]["nodes"][0]["title"] == "课程设计师"
    assert projected["data"]["nodes"][0]["id"] == "step-1"
    assert "instruction" not in serialized
    assert "_edu_1" not in serialized
    assert "private-id" not in serialized
    assert "must-not-leak" not in serialized


def test_education_natural_language_router_does_not_capture_general_chat():
    workers = [_worker("_edu_2", "Courseware maker")]

    assert MessageService._education_natural_language_plan(
        SimpleNamespace(kb_domain="rd"),
        "生成一套 PPT",
        workers,
    ) is None
    assert MessageService._education_natural_language_plan(
        SimpleNamespace(kb_domain="edu"),
        "请解释 CER 推理支架是什么。",
        workers,
    ) is None


def test_courseware_finalizer_adopts_the_designated_agents_validated_files():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def get_agent_raw_file(self, session_id, agent_id, path):
            assert session_id == "session-1"
            assert agent_id == "_edu_2"
            if path == "slide_document.json":
                return (
                    b'{"title":"Evidence and Voice","theme":{"style":"paper_annotation"},'
                    b'"slides":[]}',
                    "application/json",
                )
            if path == "preview.html":
                return (
                    b"<!doctype html><html><body><main>validated preview "
                    b"with complete classroom content and learning activity"
                    b"</main></body></html>",
                    "text/html",
                )
            raise AssertionError(path)

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            return {
                "status": "ok",
                "result": {
                    "status": "ok",
                    "result": {"content": {"id": "content-1"}},
                },
            }

    manager = FakeManager()
    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_2",
        {"type": "education_courseware_from_agent_files"},
    )

    assert result["status"] == "ok"
    _, agent_id, tool_name, args = manager.executed[0]
    assert agent_id == "_edu_2"
    assert tool_name == "education_action"
    assert args["action"] == "edu.courseware.create"
    assert args["arguments"]["kind"] == "slide_document"
    assert args["arguments"]["source_json"]["theme"]["style"] == "paper_annotation"
    assert args["idempotency_key"].startswith("product-courseware-slide-")
    assert len(args["idempotency_key"]) == len("product-courseware-slide-") + 16


def test_courseware_version_finalizer_updates_latest_lesson_object():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def get_agent_raw_file(self, session_id, agent_id, path):
            if path == "slide_document.json":
                return (
                    b'{"title":"Evidence and Reasoning","theme":{"style":"paper_annotation"},'
                    b'"slides":[]}',
                    "application/json",
                )
            if path == "preview.html":
                return (
                    b"<!doctype html><html><body><main>updated complete classroom "
                    b"preview with evidence reasoning and conclusion</main></body></html>",
                    "text/html",
                )
            raise AssertionError(path)

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            if args["action"] == "edu.course.context.get":
                result = {
                    "courseware_context": {
                        "slide_documents": [
                            {
                                "content_id": "content-1",
                                "version_id": "version-1",
                                "version_number": 1,
                            }
                        ]
                    }
                }
            else:
                result = {
                    "content": {"id": "content-1", "kind": "slide_document"},
                    "version": {"id": "version-2", "version_number": 2},
                }
            return {
                "status": "ok",
                "result": {
                    "status": "ok",
                    "result": {
                        "call_id": "call-1",
                        "tool_name": args["action"],
                        "replayed": False,
                        "result": result,
                    },
                },
            }

    manager = FakeManager()
    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_2",
        {"type": "education_courseware_version_from_agent_files"},
    )

    assert result["status"] == "ok"
    assert [entry[3]["action"] for entry in manager.executed] == [
        "edu.course.context.get",
        "edu.courseware.version.create",
    ]
    version_call = manager.executed[1][3]
    assert version_call["arguments"]["content_id"] == "content-1"
    assert version_call["idempotency_key"].startswith(
        "chat-courseware-version-content-1-"
    )


def test_lesson_update_finalizer_resolves_scoped_lesson_and_updates_only_changes():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            if args["action"] == "edu.course.context.get":
                result = {
                    "courseware_context": {
                        "lesson": {
                            "id": "lesson-1",
                            "title": "Old title",
                            "duration_minutes": 45,
                        }
                    }
                }
            else:
                result = {
                    "id": "lesson-1",
                    "course_id": "course-1",
                    "title": "Old title",
                    "duration_minutes": 50,
                }
            return {
                "status": "ok",
                "result": {"status": "ok", "result": result},
            }

    manager = FakeManager()
    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_1",
        {"type": "education_lesson_update_from_agent_reply"},
        reply=json.dumps(
            {
                "changes": {"duration_minutes": 50},
                "summary": "Extend guided practice by five minutes.",
            }
        ),
    )

    assert result["status"] == "ok"
    assert [entry[3]["action"] for entry in manager.executed] == [
        "edu.course.context.get",
        "edu.lesson.update",
    ]
    update_call = manager.executed[1][3]
    assert update_call["arguments"] == {
        "lesson_id": "lesson-1",
        "duration_minutes": 50,
    }
    assert update_call["idempotency_key"].startswith(
        "chat-lesson-update-lesson-1-"
    )


def test_submission_review_finalizer_adopts_strict_agent_json():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            return {
                "status": "ok",
                "result": {
                    "status": "ok",
                    "result": {"id": "analysis-1", "status": "ready"},
                },
            }

    analysis = {
        "summary": "The response identifies the turning point.",
        "strengths": ["Uses a clear sequence"],
        "issues": [
            {
                "evidence": "Then she chose to return.",
                "concern": "The reason is under-explained.",
                "suggestion": "Add one causal sentence.",
            }
        ],
        "next_steps": ["Explain cause and effect"],
        "evidence_refs": ["Then she chose to return."],
    }
    manager = FakeManager()

    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_4",
        {"type": "education_submission_review_from_agent_reply"},
        reply=json.dumps(analysis),
    )

    assert result["status"] == "ok"
    _, agent_id, tool_name, args = manager.executed[0]
    assert agent_id == "_edu_4"
    assert tool_name == "education_action"
    assert args["action"] == "edu.submission_review.analysis.create"
    assert args["arguments"] == {"analysis": analysis}
    assert args["idempotency_key"].startswith("product-submission-review-analysis-")


def test_submission_review_reviewer_finalizer_requires_a_real_conclusion():
    valid = {
        "verdict": "approved",
        "rubric_alignment": "The advice follows all three rubric dimensions.",
        "evidence_check": "Every quoted phrase occurs in the submitted response.",
        "labeling_check": "The wording describes evidence rather than labeling the student.",
        "required_changes": [],
    }

    accepted = MessageService._execute_trusted_task_finalizer(
        object(),
        "session-1",
        "_edu_9",
        {"type": "education_submission_review_reviewer_from_agent_reply"},
        reply=json.dumps(valid),
    )
    progress_only = MessageService._execute_trusted_task_finalizer(
        object(),
        "session-1",
        "_edu_9",
        {"type": "education_submission_review_reviewer_from_agent_reply"},
        reply="weagent-report '{\"type\":\"progress\",\"status\":\"running\"}'",
    )

    assert accepted == {"status": "ok", "result": valid}
    assert progress_only["status"] == "error"
    assert "not adoptable" in progress_only["error"]


def test_question_finalizer_validates_json_and_adopts_draft_questions():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            return {
                "status": "ok",
                "result": {
                    "status": "ok",
                    "result": {"items": [{"id": "question-1", "status": "draft"}]},
                },
            }

    questions = {
        "stimuli": [],
        "questions": [
            {
                "title": "Evidence and inference",
                "question_type": "single_choice",
                "prompt": "Which detail best supports the inference?",
                "options": ["Detail one", "Detail two", "Detail three"],
                "correct_answer": "B",
                "explanation": "Detail two directly supports the inference.",
                "difficulty": "medium",
                "score": 5,
                "knowledge_points": ["text evidence"],
                "grade_band": "senior_high",
                "source_context": {"kind": "teacher_requirement"},
            }
        ]
    }
    manager = FakeManager()

    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_3",
        {"type": "education_questions_from_agent_reply"},
        reply=json.dumps(questions),
    )

    assert result["status"] == "ok"
    _, agent_id, tool_name, args = manager.executed[0]
    assert agent_id == "_edu_3"
    assert tool_name == "education_action"
    assert args["action"] == "edu.question_bank.upsert"
    assert args["arguments"] == {
        "stimuli": [],
        "questions": questions["questions"],
        "publish": False,
    }
    assert args["idempotency_key"].startswith("product-question-generation-")


def test_student_insight_finalizer_lists_members_then_refreshes_real_evidence():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            if args["action"] == "edu.course.members.list":
                result = {"items": [{"user_id": "student-1", "role": "student"}]}
            else:
                result = {
                    "items": [
                        {
                            "student_user_id": "student-1",
                            "data_state": "ready",
                        }
                    ]
                }
            return {
                "status": "ok",
                "result": {"status": "ok", "result": result},
            }

    manager = FakeManager()

    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_4",
        {"type": "education_student_insight_refresh_from_agent_reply"},
        reply='{"refresh":true}',
    )

    assert result["status"] == "ok"
    assert [entry[3]["action"] for entry in manager.executed] == [
        "edu.course.members.list",
        "edu.student_insight.refresh",
    ]
    assert manager.executed[1][3]["idempotency_key"].startswith(
        "product-student-insight-refresh-"
    )
    assert result["result"]["member_count"] == 1
    assert result["result"]["refresh"]["items"][0]["data_state"] == "ready"

    rejected = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_4",
        {"type": "education_student_insight_refresh_from_agent_reply"},
        reply='{"refresh":false}',
    )
    assert rejected["status"] == "error"


def test_paper_finalizer_searches_real_published_questions_before_composing():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            if args["action"] == "edu.question_bank.search":
                return {
                    "status": "ok",
                    "result": {
                        "status": "ok",
                        "result": {
                            "items": [
                                {
                                    "id": "question-1",
                                    "status": "published",
                                    "current_version": {
                                        "difficulty": "medium",
                                        "knowledge_points": ["text evidence"],
                                    },
                                },
                                {
                                    "id": "question-2",
                                    "status": "published",
                                    "current_version": {
                                        "difficulty": "medium",
                                        "knowledge_points": ["inference"],
                                    },
                                },
                            ]
                        },
                    },
                }
            return {
                "status": "ok",
                "result": {
                    "status": "ok",
                    "result": {"id": "paper-1", "status": "draft"},
                },
            }

    request = {
        "title": "Reading diagnostic",
        "question_count": 2,
        "duration_minutes": 30,
        "purpose": "diagnostic",
        "difficulty": "medium",
        "knowledge_points": [],
    }
    manager = FakeManager()

    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_3",
        {"type": "education_paper_from_agent_reply"},
        reply=json.dumps(request),
    )

    assert result["status"] == "ok"
    assert [entry[3]["action"] for entry in manager.executed] == [
        "edu.question_bank.search",
        "edu.paper.compose",
    ]
    compose_args = manager.executed[1][3]
    assert compose_args["arguments"]["item_ids"] == ["question-1", "question-2"]
    assert compose_args["arguments"]["purpose"] == "diagnostic"


def test_knowledge_finalizer_researches_then_refetches_selected_source():
    class FakeManager:
        def __init__(self):
            self.executed = []

        def execute_tool(self, session_id, agent_id, tool_name, args):
            self.executed.append((session_id, agent_id, tool_name, args))
            if args["action"] == "edu.web.research":
                return {
                    "status": "ok",
                    "result": {
                        "status": "ok",
                        "result": {
                            "results": [
                                {
                                    "url": "https://example.org/evidence",
                                    "title": "Evidence-based reading",
                                    "search_excerpt": "A teaching reference",
                                    "score": 0.9,
                                }
                            ]
                        },
                    },
                }
            return {
                "status": "ok",
                "result": {
                    "status": "ok",
                    "result": {"id": "resource-1", "status": "active"},
                },
            }

    request = {
        "query": "evidence-based reading instruction",
        "license_note": "CC BY-SA 4.0; teacher verified classroom use",
        "teacher_confirmed_rights": True,
    }
    manager = FakeManager()

    result = MessageService._execute_trusted_task_finalizer(
        manager,
        "session-1",
        "_edu_8",
        {"type": "education_knowledge_from_agent_reply"},
        reply=json.dumps(request),
    )

    assert result["status"] == "ok"
    assert [entry[3]["action"] for entry in manager.executed] == [
        "edu.web.research",
        "edu.knowledge.resource.adopt",
    ]
    adoption = manager.executed[1][3]["arguments"]
    assert adoption["url"] == "https://example.org/evidence"
    assert adoption["teacher_confirmed_rights"] is True


def test_dependency_context_contains_only_completed_predecessor_replies():
    task = {"depends_on": ["step-1", "missing"]}
    results = {
        "step-1": {"status": "done", "reply": '{"summary":"analysis"}'},
        "missing": {"status": "error", "reply": "do not include"},
    }

    context = MessageService._trusted_dependency_context(task, results)

    assert "step-1" in context
    assert '{"summary":"analysis"}' in context
    assert "do not include" not in context


def test_dependency_context_includes_bounded_trusted_finalizer_result():
    task = {"depends_on": ["step-1"]}
    results = {
        "step-1": {
            "status": "done",
            "reply": '{"questions":[]}',
            "finalizer_result": {
                "status": "ok",
                "result": {"items": [{"id": "question-1", "status": "draft"}]},
            },
        }
    }

    context = MessageService._trusted_dependency_context(task, results)

    assert "trusted_finalizer_result" in context
    assert "question-1" in context


def test_insufficient_balance_does_not_trigger_misleading_model_config_retry():
    service = MessageService.__new__(MessageService)
    original = {
        "status": "error",
        "error": "stream disconnected: Insufficient Balance",
    }

    returned = service._retry_agent_after_model_error(
        SimpleNamespace(owner_id="owner-1", sandbox_session_id="sandbox-1"),
        "_edu_1",
        "generate slides",
        original,
    )

    assert returned is original
