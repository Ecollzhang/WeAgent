from unittest.mock import MagicMock, patch

from app.sandbox.container.orchestrator import Orchestrator


def test_send_to_agent_returns_answer_after_tool_result_is_fed_back():
    orchestrator = Orchestrator.__new__(Orchestrator)
    agent = MagicMock()
    agent.role = "researcher"
    agent.send_with_context.side_effect = [
        '<tool_call>{"name":"rag_search","args":{"query":"photosynthesis"}}</tool_call>',
        "Plants turn light into stored chemical energy.",
    ]
    orchestrator.agents = {"researcher": agent}
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()
    orchestrator.tools.call_from_agent.return_value = (
        '{"status":"ok","result":{"results":[{"content":"Plants convert light."}]}}'
    )

    with (
        patch.object(orchestrator, "_get_or_recreate_agent", return_value=agent),
        patch.object(orchestrator, "_build_context", return_value=""),
        patch.object(orchestrator, "_write_capability_run_snapshot", return_value="run-1"),
        patch.object(orchestrator, "_snapshot_workspace", return_value={}),
        patch.object(orchestrator, "_should_collect_agent_files", return_value=False),
        patch.object(orchestrator, "collect_skill_drafts", return_value=[]),
        patch("app.sandbox.container.orchestrator.session_store.save_message"),
        patch("app.sandbox.container.orchestrator.log_agent"),
        patch("app.sandbox.container.orchestrator.push_event"),
    ):
        result = orchestrator.send_to_agent("researcher", "Explain photosynthesis")

    assert result["status"] == "ok"
    assert result["reply"] == "Plants turn light into stored chemical energy."
    assert len(agent.send_with_context.call_args_list) == 2
    follow_up = agent.send_with_context.call_args_list[1].args[0]
    assert "rag_search" in follow_up
    assert "Plants convert light." in follow_up


def test_send_to_agent_stops_tool_loop_at_configured_limit():
    orchestrator = Orchestrator.__new__(Orchestrator)
    agent = MagicMock()
    agent.role = "researcher"
    agent.send_with_context.return_value = (
        '<tool_call>{"name":"rag_search","args":{"query":"again"}}</tool_call>'
    )
    orchestrator.agents = {"researcher": agent}
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()
    orchestrator.tools.call_from_agent.return_value = '{"status":"ok","result":{}}'

    with (
        patch.object(orchestrator, "_get_or_recreate_agent", return_value=agent),
        patch.object(orchestrator, "_build_context", return_value=""),
        patch.object(orchestrator, "_write_capability_run_snapshot", return_value="run-1"),
        patch.object(orchestrator, "_snapshot_workspace", return_value={}),
        patch.object(orchestrator, "_should_collect_agent_files", return_value=False),
        patch.object(orchestrator, "collect_skill_drafts", return_value=[]),
        patch("app.sandbox.container.orchestrator.session_store.save_message"),
        patch("app.sandbox.container.orchestrator.log_agent"),
        patch("app.sandbox.container.orchestrator.push_event"),
        patch.dict("os.environ", {"WEAGENT_TOOL_LOOP_MAX_ROUNDS": "2"}),
    ):
        result = orchestrator.send_to_agent("researcher", "Keep searching")

    assert result["status"] == "error"
    assert "maximum tool rounds" in result["error"].lower()
    assert agent.send_with_context.call_count == 3


def test_tool_loop_default_allows_bounded_schema_repair_rounds():
    orchestrator = Orchestrator.__new__(Orchestrator)
    agent = MagicMock()
    agent.role = "courseware maker"
    agent.send_with_context.side_effect = [
        '<tool_call>{"name":"education_action","args":{"action":"read","arguments":{}}}</tool_call>',
        '<tool_call>{"name":"education_action","args":{"action":"write","arguments":{"invalid":true}}}</tool_call>',
        '<tool_call>{"name":"education_action","args":{"action":"schema","arguments":{}}}</tool_call>',
        '<tool_call>{"name":"education_action","args":{"action":"write","arguments":{"still_invalid":true}}}</tool_call>',
        '<tool_call>{"name":"education_action","args":{"action":"write","arguments":{"valid":true}}}</tool_call>',
        "Canonical courseware was persisted.",
    ]
    orchestrator.agents = {"maker": agent}
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()
    orchestrator.tools.call_from_agent.side_effect = [
        {"course": "context"},
        RuntimeError("invalid_slide_document: unsupported block type"),
        {"courseware_id": "deck-1"},
    ]

    # ToolRegistry normally returns a structured failed result rather than
    # raising. Keep this test focused on the number of permitted repair rounds.
    orchestrator.tools.call_from_agent.side_effect = [
        {"course": "context"},
        {"status": "error", "error": "invalid_slide_document"},
        {"allowed_types": ["text", "bullets"]},
        {"status": "error", "error": "visual_quality_failed"},
        {"courseware_id": "deck-1"},
    ]

    with patch.dict("os.environ", {}, clear=False):
        reply, results, error = orchestrator._complete_tool_calls(
            agent,
            "maker",
            agent.send_with_context("start"),
            run_id="run-1",
        )

    assert error is None
    assert reply == "Canonical courseware was persisted."
    assert len(results) == 5


def test_rag_tool_result_json_is_projected_as_structured_card():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()
    orchestrator.tools.call_from_agent.return_value = (
        '{"status":"ok","result":{"results":[{"content":"source"}],"total":1}}'
    )

    with patch.object(orchestrator, "_push_rag_result_card") as push_card:
        results = orchestrator._execute_tool_calls(
            "researcher",
            '<tool_call>{"name":"rag_search","args":{"query":"lesson"}}</tool_call>',
            run_id="run-1",
        )

    assert results[0]["tool"] == "rag_search"
    push_card.assert_called_once()
    assert push_card.call_args.args[2]["total"] == 1
def test_large_artifact_protocol_suppresses_generic_tool_instructions():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.agents = {
        "_edu_2": type("Agent", (), {"role": "Courseware maker"})()
    }
    orchestrator._role_boundary_prompt = lambda *_args: "ROLE_BOUNDARY"
    orchestrator._tool_instructions = lambda *_args: (_ for _ in ()).throw(
        AssertionError("generic tool instructions must be suppressed")
    )

    prompt = orchestrator._with_tool_instructions(
        "_edu_2",
        "[Education large-artifact finalizer protocol]\nCreate the deck.",
    )

    assert "ROLE_BOUNDARY" in prompt
    assert "Do not emit tool calls" in prompt
    assert "slide_document.json" in prompt
