import builtins
import os
import stat

from unittest.mock import MagicMock, patch

import app.sandbox.container.orchestrator as orchestrator_module
import app.sandbox.container.tools as tools_module
from app.sandbox.container.orchestrator import Orchestrator


def test_controlled_file_write_replaces_read_only_rehydrated_artifact(tmp_path):
    workspace = tmp_path / "workspace"
    target = workspace / "agents" / "courseware" / "slide_document.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"version": 1}', encoding="utf-8")
    os.chmod(target, stat.S_IREAD)
    previous_root = tools_module.WORKSPACE_ROOT
    tools_module.WORKSPACE_ROOT = str(workspace)
    try:
        tools_module._write_file(
            "agents/courseware/slide_document.json",
            '{"version": 2}',
        )
        assert target.read_text(encoding="utf-8") == '{"version": 2}'
    finally:
        tools_module.WORKSPACE_ROOT = previous_root
        if target.exists():
            os.chmod(target, stat.S_IWRITE | stat.S_IREAD)


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


def test_send_to_agent_collects_controlled_files_after_read_tool_call():
    orchestrator = Orchestrator.__new__(Orchestrator)
    agent = MagicMock()
    agent.role = "courseware maker"
    final_reply = (
        "## /workspace/agents/maker/slide_document.json\n"
        "```json\n{\"title\":\"Revised deck\"}\n```"
    )
    agent.send_with_context.side_effect = [
        '<tool_call>{"name":"education_action","args":{"action":"edu.course.context.get"}}</tool_call>',
        final_reply,
    ]
    orchestrator.agents = {"maker": agent}
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()
    orchestrator.tools.call_from_agent.return_value = {
        "status": "ok",
        "result": {"slide_documents": [{"content_id": "deck-1"}]},
    }
    written = [{
        "tool": "write_file",
        "file": "agents/maker/slide_document.json",
        "change_type": "modified",
    }]

    with (
        patch.object(orchestrator, "_get_or_recreate_agent", return_value=agent),
        patch.object(orchestrator, "_build_context", return_value=""),
        patch.object(orchestrator, "_write_capability_run_snapshot", return_value="run-1"),
        patch.object(orchestrator, "_snapshot_workspace", return_value={}),
        patch.object(orchestrator, "_should_collect_agent_files", return_value=True),
        patch.object(orchestrator, "_parse_and_write_code_blocks", return_value=written) as collect,
        patch.object(orchestrator, "collect_skill_drafts", return_value=[]),
        patch("app.sandbox.container.orchestrator.session_store.save_message"),
        patch("app.sandbox.container.orchestrator.log_agent"),
        patch("app.sandbox.container.orchestrator.push_event"),
    ):
        result = orchestrator.send_to_agent("maker", "Revise slide 3")

    collect.assert_called_once_with("maker", final_reply)
    assert [item["tool"] for item in result["tool_results"]] == [
        "education_action",
        "write_file",
    ]
    assert result["tool_results"][-1]["file"] == "agents/maker/slide_document.json"


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

    with patch.dict("os.environ", {}, clear=False), patch(
        "app.sandbox.container.orchestrator.session_store.save_message"
    ):
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


def test_text_tool_loop_rejects_non_object_arguments_without_crashing():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()

    results = orchestrator._execute_tool_calls(
        "researcher",
        '<tool_call>{"name":"rag_search","args":"not-an-object"}</tool_call>',
        run_id="run-1",
    )

    assert results == [{
        "tool": "rag_search",
        "error": "Tool arguments must be a JSON object",
    }]
    orchestrator.tools.call_from_agent.assert_not_called()


def test_education_tool_result_is_projected_as_trusted_unified_card():
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator.capability_projection = {"session_id": "session-1"}
    orchestrator.tools = MagicMock()
    orchestrator.tools.call_from_agent.return_value = (
        '{"status":"ok","result":{"call_id":"call-1",'
        '"tool_name":"edu.courseware.create","result":{'
        '"content":{"id":"deck-1","lesson_id":"lesson-1",'
        '"kind":"slide_document","status":"draft"},'
        '"version":{"id":"version-2","version_number":2,'
        '"source_json":{"title":"The Gift of the Magi",'
        '"theme":{"style":"paper_annotation"},"slides":[{},{}]}}}}}'
    )

    with patch("app.sandbox.container.orchestrator.push_event") as push_event:
        orchestrator._execute_tool_calls(
            "_edu_2",
            '<tool_call>{"name":"education_action","args":{'
            '"action":"edu.courseware.create","arguments":{},'
            '"idempotency_key":"deck-write-1"}}</tool_call>',
            run_id="run-1",
        )

    card = push_event.call_args.args[2]
    assert push_event.call_args.args[:2] == (
        "_edu_2",
        "agent_report_element",
    )
    assert card["type"] == "education_card"
    assert card["data"]["object_type"] == "courseware"
    assert card["data"]["canonical_ref"] == {
        "object_id": "deck-1",
        "version_id": "version-2",
    }
    assert card["data"]["title"] == "The Gift of the Magi"
    assert card["data"]["summary"] == "v2 · 2 页"
    assert "education_card" not in Orchestrator.REPORT_TYPES


def test_education_card_projection_does_not_import_core_app_package():
    """The container image has no host Flask ``app`` package at runtime."""
    real_import = builtins.__import__

    def reject_core_app(name, *args, **kwargs):
        if name == "app" or name.startswith("app."):
            raise ModuleNotFoundError("No module named 'app'")
        return real_import(name, *args, **kwargs)

    envelope = {
        "result": {
            "course": {
                "id": "course-1",
                "title": "English reading",
                "status": "active",
            }
        }
    }
    with (
        patch.object(orchestrator_module, "push_event") as push_event,
        patch("builtins.__import__", side_effect=reject_core_app),
    ):
        Orchestrator._push_education_result_card(
            "_edu_1",
            "edu.course.context.get",
            envelope,
        )

    assert push_event.call_args.args[2]["type"] == "education_card"


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


def test_literal_tool_provider_is_told_not_to_probe_native_or_mcp_tools():
    orchestrator = Orchestrator.__new__(Orchestrator)
    provider = type("Provider", (), {"requires_literal_tool_calls": True})()
    agent = type(
        "Agent",
        (),
        {
            "role": "Researcher",
            "workspace_name": "researcher",
            "provider_runner": provider,
        },
    )()
    orchestrator.agents = {"researcher": agent}
    orchestrator.capability_projection = {
        "agents": {
            "researcher": {
                "tool_index": [{
                    "name": "Knowledge search",
                    "description": "Course-scoped retrieval",
                    "tool_names": ["rag_search"],
                    "status": "implemented",
                }]
            }
        }
    }

    prompt = orchestrator._tool_instructions("researcher")

    assert "do not issue provider-native function calls" in prompt
    assert "do not probe MCP servers or resources" in prompt
    assert "exact English tool name" in prompt


def test_literal_tool_provider_receives_exact_authorized_tool_contracts():
    orchestrator = Orchestrator.__new__(Orchestrator)
    provider = type("Provider", (), {"requires_literal_tool_calls": True})()
    agent = type(
        "Agent",
        (),
        {
            "role": "Course designer",
            "workspace_name": "course-designer",
            "provider_runner": provider,
        },
    )()
    orchestrator.agents = {"_edu_1": agent}
    orchestrator.capability_projection = {
        "agents": {
            "_edu_1": {
                "tool_index": [{
                    "name": "Education operations",
                    "description": "Course-scoped actions",
                    "tool_names": [
                        "education_action",
                        "rag_search",
                        "list_services",
                        "call_service_api",
                    ],
                    "status": "implemented",
                }]
            }
        }
    }

    prompt = orchestrator._tool_instructions("_edu_1")

    assert '"name":"education_action","args":{"action":"edu.course.context.get"}' in prompt
    assert '"arguments":{}' in prompt
    assert '"name":"rag_search","args":{"query":"...","top_k":5}' in prompt
    assert '"name":"list_services","args":{}' in prompt
    assert '"service_name":"edu"' in prompt
    assert '"query_params":{}' in prompt
    assert "Never invent payload, params, service, workspaceId" in prompt
