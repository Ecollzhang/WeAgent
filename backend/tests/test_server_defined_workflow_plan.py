from types import SimpleNamespace
import json

from app.services.message_service import MessageService


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
