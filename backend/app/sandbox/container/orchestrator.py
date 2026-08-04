"""
container.orchestrator — Multi-agent manager and message router.

Runs inside the Docker container, manages multiple ClaudeRuntime agents,
handles message routing between agents, and manages tools.
"""

import base64
import json
import mimetypes
import os
import re
import subprocess
import threading
import time
from typing import Optional

from .agent import AgentRuntime, ClaudeRuntime
from .capabilities import (
    agent_bootstrap_instruction,
    collect_skill_draft_payloads,
    write_projection,
    write_run_snapshot,
)
from .claude_config import clean_base_url, clean_config_value, claude_env, write_settings, trust_projects
from .mcp_runtime import McpRuntime
from .tools import ToolRegistry, register_builtin_tools
from . import session as session_store
from .events import push_event
from .logging_utils import log_agent, log_event, shorten
from .providers import ProviderRunnerFactory
from .service_manager import ServiceManager


class Orchestrator:
    """
    Manages agents and routes messages for a single session.

    One orchestrator per container.
    """

    def __init__(self):
        self.agents: dict[str, AgentRuntime] = {}
        self.tools = ToolRegistry()
        self.mcp_runtime = McpRuntime()
        self.custom_tools_path = "/workspace/.session/tools.json"
        self.capability_projection: Optional[dict] = None
        self._capability_run_counter = 0
        self.services: dict[int, dict] = {}
        self.service_manager = ServiceManager()
        os.makedirs("/workspace/shared", exist_ok=True)
        os.makedirs("/workspace/agents", exist_ok=True)
        os.environ.update(claude_env())
        trust_projects(["/workspace"])
        register_builtin_tools(self.tools)
        self._load_custom_tools()
        log_event("orchestrator_initialized")

    # ---- Capability projection ----

    def apply_capability_projection(self, projection: dict) -> dict:
        """Install the session-local .weagent capability projection."""
        if not isinstance(projection, dict):
            return {"status": "error", "error": "Projection must be an object"}
        self.mcp_runtime.stop_all()
        result = write_projection(projection, workspace_root="/workspace")
        self.capability_projection = projection
        log_event(
            "capability_projection_applied",
            capability_count=len(projection.get("capabilities") or {}),
            agent_count=len(projection.get("agents") or {}),
            file_count=len(result.get("written") or []),
        )
        return result

    def _snapshot_workspace(self) -> dict[str, dict]:
        """Snapshot files in /workspace for created/modified detection."""
        snapshot = {}
        base = "/workspace"
        if not os.path.exists(base):
            return snapshot
        for root, dirs, files in os.walk(base):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in self.LOW_VALUE_FILE_PARTS
            ]
            for f in files:
                full = os.path.join(root, f)
                try:
                    stat = os.stat(full)
                except OSError:
                    continue
                relpath = os.path.relpath(full, base).replace("\\", "/")
                snapshot[relpath] = {"mtime": stat.st_mtime, "size": stat.st_size}
        return snapshot

    # ---- Agent management ----

    def create_agent(self, agent_id: str, role: str, system_prompt: str,
                     workspace_name: str = "", adapter_name: str = "claude") -> dict:
        """Create and start a new agent."""
        adapter_name = (adapter_name or "claude").strip().lower()
        log_agent(
            agent_id,
            "create_requested",
            role=role,
            workspace_name=workspace_name or role or agent_id,
            adapter_name=adapter_name,
            prompt_len=len(system_prompt or ""),
        )
        if agent_id in self.agents:
            log_agent(agent_id, "create_rejected", level="warning", reason="already exists")
            return {"error": f"Agent '{agent_id}' already exists"}

        # Persist original config (for clean replay)
        workspace_name = workspace_name or role or agent_id
        if adapter_name not in ProviderRunnerFactory.providers():
            log_agent(agent_id, "create_rejected", level="warning", reason="unsupported provider", adapter_name=adapter_name)
            return {"error": f"Unsupported provider: {adapter_name}"}
        session_store.save_agent_config(agent_id, role, system_prompt, workspace_name, adapter_name)

        # NOTE: system_prompt is passed to ClaudeRuntime which writes agent.md
        # The agent.md file defines the agent's role for claude -p.
        # Tool instructions are embedded in agent.md, not injected here.

        runtime_prompt = self._with_capability_bootstrap(agent_id, system_prompt)
        agent = AgentRuntime(
            agent_id,
            role,
            runtime_prompt,
            workspace_name,
            provider_name=adapter_name,
        )
        try:
            agent.start()
        except Exception as e:
            log_agent(agent_id, "create_failed", level="error", role=role, error=str(e))
            return {"error": f"Failed to start agent: {e}"}

        self.agents[agent_id] = agent
        log_agent(agent_id, "created", role=role, workspace_name=agent.workspace_name, adapter_name=adapter_name, work_dir=agent.to_dict().get("work_dir"))

        return {"status": "ok", "agent": agent.to_dict()}

    def remove_agent(self, agent_id: str) -> dict:
        """Stop and remove an agent."""
        agent = self.agents.pop(agent_id, None)
        if agent:
            log_agent(agent_id, "remove_requested", role=agent.role)
            agent.stop()
            log_agent(agent_id, "removed", role=agent.role)
        return {"status": "ok"}

    def get_agent(self, agent_id: str) -> Optional[AgentRuntime]:
        return self.agents.get(agent_id)

    def list_agents(self) -> list[dict]:
        return [a.to_dict() for a in self.agents.values()]

    # ---- Message handling ----

    def send_to_agent(self, agent_id: str, message: str) -> dict:
        """Send a message to an agent and get a response."""
        agent = self._get_or_recreate_agent(agent_id)
        if isinstance(agent, dict):
            log_agent(agent_id, "send_rejected", level="error", error=agent.get("error", "Agent not found"))
            push_event(agent_id, "error", {"error": agent.get("error", "Agent not found")})
            return agent  # error dict

        # Build context from other agents' recent outputs
        context = self._build_context(exclude=agent_id)

        # Save user message
        session_store.save_message(agent_id, "user", message)

        role = agent.role or agent_id
        capability_run_id = self._write_capability_run_snapshot(agent_id)
        log_agent(
            agent_id,
            "task_start",
            role=role,
            message_len=len(message or ""),
            message_preview=shorten(message, 300),
            context_len=len(context or ""),
        )
        push_event(agent_id, "agent_task_started", {
            "agent_id": agent_id,
            "role": role,
            "message": message,
        })

        # Workspace snapshot before agent execution (for detecting files
        # written by Claude's native tools)
        fs_baseline = self._snapshot_workspace()

        try:
            # ── Multi-turn loop: feed tool results back to the agent ──
            MAX_TOOL_TURNS = 5
            all_tool_results = []
            final_reply = None
            current_message = message
            current_context = context
            first_turn = True

            for _turn in range(MAX_TOOL_TURNS):
                prompt = self._with_tool_instructions(agent_id, current_message)
                reply = agent.send_with_context(prompt, context=current_context)
                log_agent(
                    agent_id,
                    "task_reply_received",
                    role=role,
                    reply_len=len(reply or ""),
                    reply_preview=shorten(reply, 300),
                )

                # Save assistant reply
                session_store.save_message(agent_id, "assistant", reply)
                final_reply = reply

                if self._is_agent_runtime_error(reply):
                    log_agent(agent_id, "task_runtime_error", level="error", role=role, error=shorten(reply, 500))
                    push_event(agent_id, "error", {
                        "agent_id": agent_id,
                        "error": reply,
                    })
                    return {"status": "error", "agent_id": agent_id, "error": reply, "reply": reply}

                # Parse <tool_call> XML blocks and execute them
                start_parse = time.time()
                turn_tool_results = []
                if self._should_collect_agent_files(agent_id):
                    turn_tool_results = self._execute_tool_calls(
                        agent_id, reply, run_id=capability_run_id
                    )
                all_tool_results.extend(turn_tool_results)

                if turn_tool_results:
                    # Feed tool results back to agent for the next turn
                    fb_parts = ["工具执行结果："]
                    for tr in turn_tool_results:
                        fb_parts.append(
                            f"\n[{tr.get('tool', 'unknown')}]: {tr.get('result', '')}"
                        )
                    current_message = "\n".join(fb_parts)
                    current_context = ""
                    first_turn = False
                    continue  # Next turn with tool feedback

                # No tool calls — extract file artifacts (final turn)
                if self._should_collect_agent_files(agent_id):
                    log_agent(agent_id, "artifact_collection_start", role=role)
                    code_blocks = self._parse_and_write_code_blocks(agent_id, reply)
                    if code_blocks:
                        all_tool_results.extend(code_blocks)
                    else:
                        detected = self._detect_written_files(agent_id, reply, baseline=fs_baseline)
                        if detected:
                            all_tool_results.extend(detected)
                        elif self._reply_mentions_files(reply):
                            log_agent(agent_id, "artifact_second_pass_start", role=role)
                            second_pass = self._second_pass_extract_files(
                                agent_id,
                                message if first_turn else current_message,
                                reply,
                            )
                            if second_pass:
                                all_tool_results.extend(second_pass)
                    log_agent(
                        agent_id,
                        "artifact_collection_done",
                        role=role,
                        file_count=len(all_tool_results or []),
                        files=[t.get("file", "") for t in (all_tool_results or [])],
                    )
                break  # Agent is done

            parse_elapsed = time.time() - start_parse

            # Strip <tool_call> blocks from the final reply for clean display
            clean_reply = self._strip_tool_calls(final_reply or "")

            result = {"status": "ok", "agent_id": agent_id, "reply": clean_reply}
            if capability_run_id:
                result["capability_run_id"] = capability_run_id
            skill_drafts = self.collect_skill_drafts(agent_id)
            if skill_drafts:
                result["skill_drafts"] = skill_drafts
            if all_tool_results:
                result["tool_results"] = all_tool_results

            push_event(agent_id, "agent_task_completed", {
                "agent_id": agent_id,
                "role": role,
                "message": f"{role} 任务完成",
                "file_count": len(all_tool_results) if all_tool_results else 0,
                "files": [t.get("file", "") for t in (all_tool_results or [])],
                "parse_time": round(parse_elapsed, 1),
            })
            log_agent(
                agent_id,
                "task_completed",
                role=role,
                file_count=len(all_tool_results) if all_tool_results else 0,
                parse_time=round(parse_elapsed, 2),
            )
            return result
        except Exception as e:
            log_agent(agent_id, "task_exception", level="error", role=role, error=str(e))
            push_event(agent_id, "error", {
                "agent_id": agent_id,
                "error": str(e),
            })
            return {"status": "error", "error": str(e)}

    def send_to_agent_chain(self, messages: list[dict]) -> list[dict]:
        """
        Send a chain of messages across agents.
        Each message's output becomes context for the next.

        messages: [{"agent_id": "pm", "message": "..."},
                   {"agent_id": "frontend", "message": "..."}]
        """
        results = []
        accumulated_context = ""

        for item in messages:
            agent_id = item["agent_id"]
            msg = item["message"]

            agent = self._get_or_recreate_agent(agent_id)
            if isinstance(agent, dict):
                log_agent(agent_id, "chain_step_rejected", level="error", error=agent.get("error", "Agent not found"))
                push_event(agent_id, "error", {"error": agent.get("error", "Agent not found")})
                results.append({"agent_id": agent_id, "error": agent.get("error")})
                continue

            role = agent.role or agent_id
            log_agent(agent_id, "chain_step_start", role=role, message_len=len(msg or ""))
            push_event(agent_id, "agent_task_started", {
                "agent_id": agent_id, "role": role,
                "message": f"{role} 开始处理链式任务",
            })

            prompted_msg = self._with_tool_instructions(agent_id, msg)
            full_msg = accumulated_context + "\n\n" + prompted_msg if accumulated_context else prompted_msg
            session_store.save_message(agent_id, "user", full_msg)
            capability_run_id = self._write_capability_run_snapshot(agent_id)

            try:
                # Snapshot workspace before each agent in the chain
                chain_baseline = self._snapshot_workspace()

                # ── Multi-turn loop for this chain step ──
                CHAIN_MAX_TOOL_TURNS = 5
                all_step_tool_results = []
                final_step_reply = None
                current_step_msg = full_msg
                chain_step_error = False

                for _cturn in range(CHAIN_MAX_TOOL_TURNS):
                    reply = agent.send(current_step_msg)
                    log_agent(agent_id, "chain_step_reply_received", role=role, reply_len=len(reply or ""))
                    session_store.save_message(agent_id, "assistant", reply)
                    final_step_reply = reply

                    if self._is_agent_runtime_error(reply):
                        push_event(agent_id, "error", {
                            "agent_id": agent_id,
                            "error": reply,
                        })
                        results.append({"status": "error", "agent_id": agent_id, "error": reply, "reply": reply})
                        chain_step_error = True
                        break

                    step_tool_results = []
                    if self._should_collect_agent_files(agent_id):
                        step_tool_results = self._execute_tool_calls(
                            agent_id, reply, run_id=capability_run_id
                        )
                    all_step_tool_results.extend(step_tool_results)

                    if step_tool_results:
                        # Feed tool results back to the agent
                        fb_parts = ["工具执行结果："]
                        for tr in step_tool_results:
                            fb_parts.append(
                                f"\n[{tr.get('tool', 'unknown')}]: {tr.get('result', '')}"
                            )
                        current_step_msg = "\n".join(fb_parts)
                        continue

                    # No tool calls — extract file artifacts (final turn)
                    if self._should_collect_agent_files(agent_id):
                        code_blocks = self._parse_and_write_code_blocks(agent_id, reply)
                        if code_blocks:
                            all_step_tool_results.extend(code_blocks)
                        else:
                            detected = self._detect_written_files(
                                agent_id, reply, baseline=chain_baseline)
                            if detected:
                                all_step_tool_results.extend(detected)
                    break  # Agent is done

                if chain_step_error:
                    continue  # Skip to next chain item

                clean_reply = self._strip_tool_calls(final_step_reply or "")

                entry = {"status": "ok", "agent_id": agent_id, "reply": clean_reply}
                if capability_run_id:
                    entry["capability_run_id"] = capability_run_id
                skill_drafts = self.collect_skill_drafts(agent_id)
                if skill_drafts:
                    entry["skill_drafts"] = skill_drafts
                if all_step_tool_results:
                    entry["tool_results"] = all_step_tool_results

                push_event(agent_id, "agent_task_completed", {
                    "agent_id": agent_id, "role": role,
                    "message": f"{role} 链式任务完成",
                    "file_count": len(all_step_tool_results) if all_step_tool_results else 0,
                    "files": [t.get("file", "") for t in (all_step_tool_results or [])],
                })
                log_agent(agent_id, "chain_step_completed", role=role, file_count=len(all_step_tool_results or []))

                accumulated_context += f"\n\n[{role} 的输出]:\n{clean_reply}"
                results.append(entry)
            except Exception as e:
                log_agent(agent_id, "chain_step_exception", level="error", role=role, error=str(e))
                push_event(agent_id, "error", {
                    "agent_id": agent_id, "error": str(e),
                })
                results.append({"status": "error", "agent_id": agent_id, "error": str(e)})

        return results

    def delegate_task(self, message: str, moderator_id: str = "moderator",
                      target_agent_ids: Optional[list[str]] = None) -> dict:
        """Delegate a task through a moderator agent.

        The moderator first analyzes and plans. Then the plan is sent to target
        agents. If target_agent_ids is omitted, all non-moderator agents are
        used as targets.
        """
        if not self.agents:
            log_event("delegation_rejected", level="warning", reason="no agents")
            return {"status": "error", "error": "No agents available"}

        if moderator_id not in self.agents:
            moderator_id = next(iter(self.agents.keys()))

        moderator = self._get_or_recreate_agent(moderator_id)
        if isinstance(moderator, dict):
            log_agent(moderator_id, "delegation_rejected", level="error", error=moderator.get("error", "Moderator not found"))
            return {"status": "error", "error": moderator.get("error", "Moderator not found")}

        log_agent(
            moderator_id,
            "delegation_start",
            role=moderator.role,
            message_len=len(message or ""),
            target_agent_ids=target_agent_ids,
        )
        push_event(moderator_id, "delegation_started", {
            "agent_id": moderator_id,
            "role": moderator.role,
            "message": "主持 Agent 开始分析和分派任务",
        })

        agent_list = []
        for aid in self.agents:
            if aid == moderator_id:
                continue
            agent = self.agents.get(aid)
            name = agent.role if agent else aid
            ws = agent.workspace_name if agent else aid
            agent_list.append(f"  - agent_id: {aid}, name: {name}, workspace: /workspace/agents/{ws}")
        agent_lines = "\n".join(agent_list) if agent_list else "  (无可用 worker agent)"

        moderator_prompt = (
            "你是主持 Agent。请先分析用户任务，拆解为可执行步骤，"
            "并说明应该由哪些专业 Agent 完成。不要自己写最终产物，"
            "只输出任务分析、分工和执行计划。\n\n"
            "目录策略：每个 Agent 的正式产物必须放在自己的 workspace 目录下，"
            "不能写入其他 Agent 的目录。/workspace/shared/ 只允许放任务分工、"
            "简短协作摘要、接口约定，不允许放完整 HTML/CSS/JS 成品或重复文件。\n\n"
            "可用 worker agents 及其工作目录：\n"
            f"{agent_lines}\n\n"
            f"用户任务：\n{message}"
        )
        moderator_result = self.send_to_agent(moderator_id, moderator_prompt)
        if moderator_result.get("status") == "error":
            log_agent(moderator_id, "delegation_moderator_failed", level="error", error=moderator_result.get("error", "Moderator failed"))
            push_event(moderator_id, "delegation_failed", {
                "agent_id": moderator_id,
                "error": moderator_result.get("error", "Moderator failed"),
            })
            return {
                "status": "error",
                "moderator_id": moderator_id,
                "moderator_result": moderator_result,
                "results": [],
                "error": moderator_result.get("error", "Moderator failed"),
            }
        plan = moderator_result.get("reply", "")

        push_event(moderator_id, "delegation_plan", {
            "agent_id": moderator_id,
            "role": moderator.role,
            "plan": plan,
        })
        log_agent(
            moderator_id,
            "delegation_plan_ready",
            role=moderator.role,
            plan_len=len(plan or ""),
            plan_preview=shorten(plan, 300),
        )

        if target_agent_ids is None:
            target_agent_ids = [aid for aid in self.agents.keys() if aid != moderator_id]
        else:
            target_agent_ids = [aid for aid in target_agent_ids if aid in self.agents and aid != moderator_id]

        results = []
        if not target_agent_ids:
            push_event(moderator_id, "delegation_complete", {
                "agent_id": moderator_id,
                "message": "没有可分派的目标 Agent，仅返回主持分析",
                "target_count": 0,
            })
            return {
                "status": "ok",
                "moderator_id": moderator_id,
                "moderator_result": moderator_result,
                "results": results,
            }

        for target_id in target_agent_ids:
            target = self._get_or_recreate_agent(target_id)
            if isinstance(target, dict):
                log_agent(target_id, "delegation_target_missing", level="error", error=target.get("error"))
                results.append({"status": "error", "agent_id": target_id, "error": target.get("error")})
                continue

            log_agent(target_id, "delegation_target_start", role=target.role, moderator_id=moderator_id)
            push_event(target_id, "delegation_target_started", {
                "agent_id": target_id,
                "role": target.role,
                "message": f"开始执行主持 Agent 分派的任务",
                "moderator_id": moderator_id,
            })

            delegated_message = (
                "## 主持 Agent 的任务分析和分工\n"
                f"{plan}\n\n"
                "## 用户原始任务\n"
                f"{message}\n\n"
                f"{self._role_boundary_prompt(target_id, target.role)}\n\n"
                "请只完成分派给你的部分。"
            )
            target_result = self.send_to_agent(target_id, delegated_message)
            log_agent(
                target_id,
                "delegation_target_done",
                role=target.role,
                status=target_result.get("status"),
                file_count=len(target_result.get("tool_results", []) or []),
            )
            results.append(target_result)

        push_event(moderator_id, "delegation_complete", {
            "agent_id": moderator_id,
            "message": "主持分派任务完成",
            "target_count": len(target_agent_ids),
            "targets": target_agent_ids,
        })
        log_agent(moderator_id, "delegation_complete", role=moderator.role, target_count=len(target_agent_ids), targets=target_agent_ids)

        return {
            "status": "ok",
            "moderator_id": moderator_id,
            "moderator_result": moderator_result,
            "results": results,
        }

    # ---- Context building ----

    def _build_context(self, exclude: str = "") -> str:
        """Build context from other agents' recent history."""
        parts = []
        for aid, agent in self.agents.items():
            if aid == exclude:
                continue
            recent = session_store.get_recent_context(aid, count=3)
            if recent:
                parts.append(f"[{agent.role} ({aid}) 的输出]:\n{recent}")
        return "\n\n".join(parts)

    def _role_boundary_prompt(self, agent_id: str, role: str) -> str:
        role_text = f"{agent_id} {role}".lower()
        work_dir = self._agent_work_dir(agent_id)
        if "writer" in role_text or "文档" in role:
            return (
                "## 角色边界\n"
                "你是文档助手，只负责写开发文档、需求说明、使用说明、接口说明等文档产物。\n"
                "禁止实现 HTML/CSS/JS/Vue/React 等前端代码；如果需要引用页面结构，只能用文字描述。\n"
                f"正式文档只能写入 {work_dir}/，推荐路径 {work_dir}/开发文档.md。\n"
                "/workspace/shared/ 只允许写 1 个简短协作摘要或任务分工，不允许复制完整文档，不允许写代码文件。"
            )
        if "frontend" in role_text or "前端" in role or "编程" in role:
            return (
                "## 角色边界\n"
                "你是前端助手，只负责实现登录界面的 HTML/CSS/JS/Vue 等前端代码和必要静态资源。\n"
                "不要撰写开发文档正文；如需说明，只保留极简运行说明。\n"
                f"正式前端文件只能写入 {work_dir}/，例如 {work_dir}/index.html、{work_dir}/css/style.css、{work_dir}/js/login.js。\n"
                "可以读取 /workspace/shared/ 中的摘要，但禁止把 HTML/CSS/JS/Vue/React 成品或副本写入 /workspace/shared/。"
            )
        return (
            "## 角色边界\n"
            "只完成主持 Agent 分派给你且符合你角色的部分，不要越权替其他 Agent 完成工作。"
            "/workspace/shared/ 只用于简短协作材料，不用于重复保存正式产物。"
        )

    # ---- Tool handling ----

    def execute_tool(self, agent_id: str, tool_name: str, args: dict) -> str:
        """Execute a tool on behalf of an agent."""
        run_id = self._write_capability_run_snapshot(agent_id)
        session_id = (self.capability_projection or {}).get("session_id", "")
        return self.tools.call_from_agent(
            agent_id,
            tool_name,
            args,
            run_id=run_id,
            session_id=session_id,
        )

    def list_tools(self) -> list[dict]:
        return self.tools.list_tools()

    def _agent_tool_index(self, agent_id: str) -> list[dict]:
        projection = self.capability_projection or {}
        agent_view = (projection.get("agents") or {}).get(agent_id) or {}
        return agent_view.get("tool_index") or []

    # ---- MCP runtime ----

    def start_mcp_server(self, agent_id: str, runtime_id: str) -> dict:
        return self.mcp_runtime.start_server(agent_id, runtime_id)

    def list_mcp_tools(self, runtime_id: str) -> dict:
        return self.mcp_runtime.list_tools(runtime_id)

    def call_mcp_tool(self, agent_id: str, runtime_id: str, tool_name: str,
                      args: dict) -> dict:
        run_id = self._write_capability_run_snapshot(agent_id)
        session_id = (self.capability_projection or {}).get("session_id", "")
        return self.mcp_runtime.call_tool(
            agent_id,
            runtime_id,
            tool_name,
            args,
            run_id=run_id,
            session_id=session_id,
        )

    def stop_mcp_server(self, runtime_id: str) -> dict:
        return self.mcp_runtime.stop_server(runtime_id)

    def list_mcp_servers(self) -> dict:
        return {"status": "ok", "servers": self.mcp_runtime.list_running_servers()}

    def collect_skill_drafts(self, agent_id: str = "") -> list[dict]:
        projection = self.capability_projection or {}
        session_id = projection.get("session_id", "")
        if agent_id:
            return collect_skill_draft_payloads(
                agent_id,
                session_id,
                workspace_root="/workspace",
            )
        drafts = []
        for projected_agent_id in (projection.get("agents") or {}).keys():
            drafts.extend(collect_skill_draft_payloads(
                projected_agent_id,
                session_id,
                workspace_root="/workspace",
            ))
        return drafts

    def _load_custom_tools(self):
        """Load persisted command-backed custom tools."""
        if not os.path.exists(self.custom_tools_path):
            return
        try:
            with open(self.custom_tools_path, "r", encoding="utf-8") as f:
                specs = json.load(f)
        except Exception:
            return
        for spec in specs:
            self._register_command_tool(spec)

    def _save_custom_tools(self, specs: list[dict]):
        os.makedirs(os.path.dirname(self.custom_tools_path), exist_ok=True)
        with open(self.custom_tools_path, "w", encoding="utf-8") as f:
            json.dump(specs, f, ensure_ascii=False, indent=2)

    def list_custom_tools(self) -> list[dict]:
        if not os.path.exists(self.custom_tools_path):
            return []
        try:
            with open(self.custom_tools_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _register_command_tool(self, spec: dict):
        name = spec.get("name", "")
        if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", name):
            print(f"[ToolRegistry] skip invalid tool name: '{name}'")
            return
        entrypoint = spec["entrypoint"]
        description = spec.get("description", name)

        def _run_custom_tool(**kwargs):
            safe_cwd, error = self._resolve_workspace_path(kwargs.pop("cwd", "/workspace"))
            if error or not os.path.isdir(safe_cwd):
                raise ValueError(error or "cwd not found")

            result = subprocess.run(
                entrypoint,
                input=json.dumps(kwargs, ensure_ascii=False),
                shell=True,
                capture_output=True,
                text=True,
                timeout=int(spec.get("timeout", 300)),
                cwd=safe_cwd,
            )
            output = result.stdout or ""
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            return {
                "returncode": result.returncode,
                "output": output,
            }

        self.tools.register(name, _run_custom_tool, description)

    def install_tool(self, spec: dict) -> dict:
        """Install a base64-encoded script as a command-backed tool."""
        name = spec.get("name", "")
        if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", name):
            return {"status": "error", "error": "Invalid tool name"}

        filename = os.path.basename(spec.get("filename", f"{name}.py"))
        content_base64 = spec.get("content_base64", "")
        if not content_base64:
            return {"status": "error", "error": "content_base64 required"}

        tool_dir = os.path.join("/workspace/tools", name)
        os.makedirs(tool_dir, exist_ok=True)
        file_path = os.path.join(tool_dir, filename)

        try:
            content = base64.b64decode(content_base64)
        except Exception as e:
            return {"status": "error", "error": f"Invalid base64 content: {e}"}

        with open(file_path, "wb") as f:
            f.write(content)

        entrypoint = spec.get("entrypoint") or f"python {file_path}"
        installed = {
            "name": name,
            "description": spec.get("description", name),
            "filename": filename,
            "path": file_path,
            "entrypoint": entrypoint,
            "timeout": int(spec.get("timeout", 300)),
        }

        specs = [t for t in self.list_custom_tools() if t.get("name") != name]
        specs.append(installed)
        self._save_custom_tools(specs)
        self._register_command_tool(installed)

        push_event("system", "tool_installed", {"tool": installed})
        return {"status": "ok", "tool": installed}

    def remove_custom_tool(self, name: str) -> dict:
        specs = [t for t in self.list_custom_tools() if t.get("name") != name]
        self._save_custom_tools(specs)
        return {"status": "ok", "tool": name}

    # ---- Tool call parsing & execution ----

    TOOL_CALL_PATTERN = re.compile(
        r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL
    )

    @staticmethod
    def _strip_tool_calls(text: str) -> str:
        """Remove <tool_call> XML blocks from agent reply for clean display."""
        if not text:
            return text
        return re.sub(
            r"<tool_call>\s*\{.*?\}\s*</tool_call>",
            "",
            text,
            flags=re.DOTALL,
        ).strip()

    def _execute_tool_calls(self, agent_id: str, response: str,
                            run_id: str = None) -> list[dict]:
        """Parse <tool_call> blocks from agent response and execute them."""
        results = []
        session_id = (self.capability_projection or {}).get("session_id", "")
        for match in self.TOOL_CALL_PATTERN.finditer(response):
            raw = match.group(1)
            try:
                call = json.loads(raw)
                tool_name = call.get("name", "")
                args = call.get("args", {})
                if not tool_name:
                    results.append({"error": "Missing 'name' in tool_call"})
                    continue
                result = self.tools.call_from_agent(
                    agent_id,
                    tool_name,
                    args,
                    run_id=run_id,
                    session_id=session_id,
                )
                results.append({"tool": tool_name, "result": result})
                # Push RAG search results as a structured card element (both old and new tool names)
                if tool_name in ("rag_search", "call_service_api") and isinstance(result, dict):
                    if tool_name == "call_service_api":
                        # Check if this is a rag search call
                        if args.get("service_name") == "rag" and "/api/rag/search" in str(args.get("path", "")):
                            body = args.get("body") or {}
                            self._push_rag_result_card(agent_id, body.get("query", ""), result)
                    else:
                        self._push_rag_result_card(agent_id, args.get("query", ""), result)
            except json.JSONDecodeError as e:
                results.append({"error": f"Invalid JSON in tool_call: {e}"})
        return results

    @staticmethod
    def _push_rag_result_card(agent_id: str, query: str, result: dict):
        """Push RAG search results as a collapsible card element in the chat."""
        search_results = result.get("results") or []
        total = result.get("total", 0)
        if not search_results:
            push_event(agent_id, "agent_report_element", {
                "type": "result",
                "title": f'知识库检索: {query[:50]}{"..." if len(query) > 50 else ""}',
                "content": "未找到相关文档",
                "status": "done",
                "data": {"title": "知识库检索结果", "empty": True},
            })
            return
        # Build a table of results
        headers = ["#", "文档", "相关度", "内容摘要"]
        rows = []
        for i, item in enumerate(search_results[:10], 1):
            doc_name = (item.get("document") or {}).get("name") or item.get("metadata", {}).get("source") or "-"
            score = item.get("score", 0)
            score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
            content = (item.get("content") or "")[:150].replace("\n", " ")
            rows.append([str(i), str(doc_name), score_str, content])
        push_event(agent_id, "agent_report_element", {
            "type": "table",
            "title": f'知识库检索: {query[:50]}{"..." if len(query) > 50 else ""}',
            "content": f'共找到 {total} 条相关结果',
            "status": "done",
            "data": {
                "title": f'知识库检索结果 ({total}条)',
                "headers": headers,
                "rows": rows,
                "query": query,
                "total": total,
            },
        })

    def _tool_instructions(self, agent_id: str) -> str:
        """Generate tool usage instructions for the system prompt."""
        tool_index = self._agent_tool_index(agent_id)
        if tool_index:
            tool_lines = []
            seen_tools = set()
            for item in tool_index:
                names = ", ".join(item.get("tool_names") or [])
                status = item.get("status") or "deferred"
                doc_path = item.get("doc_path") or ""
                description = item.get("description") or item.get("name") or ""
                tool_lines.append(
                    f"  - {item.get('name')}: {description} "
                    f"(status: {status}; tools: {names}; doc: {doc_path})"
                )
                for n in (item.get("tool_names") or []):
                    seen_tools.add(n)
            # 始终包含微服务调用工具（list_services / call_service_api）
            if "list_services" not in seen_tools and "list_services" in self.tools._tools:
                tool_lines.append(
                    "  - 列出微服务: 列出所有可用的后端微服务及其访问地址\n"
                    "    (status: implemented; tools: list_services)"
                )
            if "call_service_api" not in seen_tools and "call_service_api" in self.tools._tools:
                tool_lines.append(
                    "  - 调用服务API: 通用微服务API调用工具，可调用任何已注册服务的接口\n"
                    "    参数: service_name(必填,服务名如rag/rd), method(默认GET), path(必填,如/api/rag/search),\n"
                    "    body(可选,POST/PUT的JSON请求体), query_params(可选,URL查询参数)\n"
                    "    每个服务都有 /api/{service}/spec 端点可查询所有可用接口\n"
                    "    (status: implemented; tools: call_service_api)"
                )
            tool_list = "\n".join(tool_lines)
            tool_hint = (
                "只调用上面列出的 Tool。需要更多说明时，先读取对应 doc 路径中的 TOOL.md。\n"
                "微服务调用提示：先用 list_services 查看服务，再用 call_service_api 访问 /api/{service}/spec 了解接口，最后调用具体接口。\n"
            )
        else:
            tools = self.tools.list_tools()
            if not tools:
                return ""
            tool_list = "\n".join(f"  - {t['name']}: {t['description']}" for t in tools)
            tool_hint = "当前是 legacy 工具模式；优先遵守主持 Agent 的授权范围。\n微服务调用提示：先用 list_services 查看服务，再用 call_service_api 访问 /api/{service}/spec 了解接口，最后调用具体接口。\n"
        work_dir = self._agent_work_dir(agent_id)
        return (
            "\n\n===== 沙箱协作和工具说明 =====\n"
            "工作区：\n"
            f"  - 你的私有目录：{work_dir}/\n"
            "  - 公共协作目录：/workspace/shared/\n"
            "  - 可读取其他 Agent 目录进行协作：/workspace/agents/<Agent名称>/\n\n"
            "可用工具：\n"
            f"{tool_list}\n"
            f"{tool_hint}\n"
            "如需调用系统注册工具，输出如下格式，系统会在回复后执行：\n"
            "<tool_call>{\"name\":\"工具名\",\"args\":{\"参数名\":\"参数值\"}}</tool_call>\n\n"
            "如需输出文件内容，使用如下格式，系统会自动写入：\n"
            f"## {work_dir}/实际文件名.ext\n"
            "```\n"
            "文件完整内容\n"
            "```\n"
            "不要复述上述示例格式；只有在确实要创建文件时才输出文件块。\n"
            "==========================="
        )

    def _with_tool_instructions(self, agent_id: str, message: str) -> str:
        return f"{message}\n\n{self._role_boundary_prompt(agent_id, self.agents.get(agent_id).role if agent_id in self.agents else agent_id)}" + self._tool_instructions(agent_id)

    # ---- Session ----

    def get_history(self, agent_id: str, limit: int = 0) -> list[dict]:
        return session_store.get_history(agent_id, limit=limit)

    def get_session_info(self) -> dict:
        return {
            "agents": [a.to_dict() for a in self.agents.values()],
            "tools": self.tools.list_tools(),
            "agent_count": len(self.agents),
        }

    # ---- File extraction (code block parsing) ----

    CODE_BLOCK_RE = re.compile(
        r"```(\w*)\n(.*?)```", re.DOTALL
    )
    FILENAME_HEADER_RE = re.compile(
        r"^#{1,3}\s+(/workspace/[\w./-]+)\s*$",
        re.MULTILINE,
    )
    FILE_MENTION_RE = re.compile(
        r"`?/workspace/[\w./-]+`?",
        re.IGNORECASE,
    )
    # Detect file references without /workspace/ prefix (e.g. README.md, docs/guide.md)
    FILE_REF_RE = re.compile(
        r"(?:[a-zA-Z0-9_\-]+/)*[a-zA-Z0-9_\-]+\.(?:md|html?|css|js|json|txt|xml|svg|py|jsx|tsx?|vue)\b",
        re.IGNORECASE,
    )
    FRONTEND_FILE_EXTS = {".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svg"}
    DOC_FILE_EXTS = {".md", ".txt"}
    LOW_VALUE_FILE_PARTS = {
        ".git",
        ".next",
        ".nuxt",
        ".output",
        ".parcel-cache",
        ".turbo",
        ".vite",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "vendor",
    }

    @staticmethod
    def _agent_kind(agent_id: str, role: str = "") -> str:
        role_text = f"{agent_id} {role}".lower()
        if "writer" in role_text or "文档" in role:
            return "writer"
        if "frontend" in role_text or "前端" in role or "编程" in role:
            return "frontend"
        if "moderator" in role_text or "主持" in role:
            return "moderator"
        return "generic"

    def _agent_workspace_name(self, agent_id: str) -> str:
        agent = self.agents.get(agent_id)
        if agent:
            return agent.workspace_name
        config = session_store.load_agent_config(agent_id) or {}
        name = config.get("workspace_name") or config.get("role") or agent_id
        return ClaudeRuntime._safe_workspace_name(name)

    def _agent_workspace_rel(self, agent_id: str) -> str:
        return f"agents/{self._agent_workspace_name(agent_id)}"

    def _agent_work_dir(self, agent_id: str) -> str:
        return f"/workspace/{self._agent_workspace_rel(agent_id)}"

    def _path_policy(self, agent_id: str, relpath: str) -> tuple[Optional[str], Optional[str]]:
        """Return the allowed relative path for an agent output.

        The path can be rewritten to the agent's private directory or rejected
        with a reason. This is deliberately stricter than prompts because
        Claude's native Write tool can ignore instructions.
        """
        agent = self.agents.get(agent_id)
        role = agent.role if agent else ""
        kind = self._agent_kind(agent_id, role)
        agent_root = self._agent_workspace_rel(agent_id)
        agent_prefix = agent_root + "/"
        clean = re.sub(r"^/workspace/", "", relpath).lstrip("/").replace("\\", "/")
        clean = os.path.normpath(clean).replace("\\", "/")
        if clean == "." or clean.startswith("../") or clean.startswith("/"):
            return None, "path outside workspace"

        if clean == agent_root:
            return clean, None
        if clean.startswith(agent_prefix + "agents/"):
            clean = agent_prefix + clean[len(agent_prefix + "agents/"):].split("/", 1)[-1]

        _, ext = os.path.splitext(clean.lower())
        basename = os.path.basename(clean).lower()

        if kind == "frontend":
            if ext in self.DOC_FILE_EXTS and not clean.startswith(agent_prefix):
                return None, "frontend agent cannot write docs outside its private directory"
            if ext in self.FRONTEND_FILE_EXTS:
                if clean.startswith(agent_prefix):
                    return clean, None
                if clean.startswith("shared/"):
                    return f"{agent_root}/{clean[len('shared/'):].lstrip('/')}", "rewritten from shared to agent workspace"
                if clean.startswith("agents/"):
                    return f"{agent_root}/{basename}", "rewritten from another agent workspace"
                return f"{agent_root}/{clean}", "rewritten to agent workspace"
            if clean.startswith("shared/"):
                return None, "frontend agent cannot write non-coordination files to shared"
            return clean if clean.startswith(agent_prefix) else f"{agent_root}/{clean}", "rewritten to agent workspace"

        if kind == "writer":
            if ext in self.FRONTEND_FILE_EXTS:
                return None, "writer agent cannot write frontend code"
            if clean.startswith(agent_prefix):
                return clean, None
            if clean.startswith("shared/"):
                allowed_shared = any(token in basename for token in ("summary", "摘要", "分工", "协作", "coordination"))
                if allowed_shared:
                    return clean, None
                return f"{agent_root}/{basename}", "rewritten from shared to agent workspace"
            if clean.startswith("agents/"):
                return f"{agent_root}/{basename}", "rewritten from another agent workspace"
            return f"{agent_root}/{clean}", "rewritten to agent workspace"

        if kind == "moderator":
            if ext in self.FRONTEND_FILE_EXTS:
                return None, "moderator agent cannot write frontend code"
            if clean.startswith("shared/"):
                return clean, None
            if ext in self.DOC_FILE_EXTS:
                return f"shared/{basename}", "moderator docs go to shared"
            return None, "moderator agent cannot write final artifacts"

        if clean.startswith("shared/") and ext in self.FRONTEND_FILE_EXTS:
            return None, "shared cannot contain frontend final artifacts"
        if clean.startswith(agent_prefix):
            return clean, None
        if clean.startswith("agents/"):
            return f"{agent_root}/{basename}", "rewritten from another agent workspace"
        if clean.startswith("shared/"):
            return clean, None
        return f"{agent_root}/{clean}", "rewritten to agent workspace"

    def _is_low_value_file_path(self, relpath: str) -> bool:
        path = str(relpath or "").replace("\\", "/").strip("/")
        if path.startswith("workspace/"):
            path = path[len("workspace/"):]
        parts = {part for part in path.split("/") if part}
        return bool(parts & self.LOW_VALUE_FILE_PARTS)

    def _should_collect_agent_files(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        role = agent.role if agent else ""
        return self._agent_kind(agent_id, role) != "moderator"

    def _apply_native_file_policy(self, agent_id: str, relpath: str) -> tuple[Optional[str], Optional[str]]:
        """Move or delete files created by Claude native tools if they violate role paths."""
        allowed_path, note = self._path_policy(agent_id, relpath)
        clean = re.sub(r"^/workspace/", "", relpath).lstrip("/").replace("\\", "/")
        clean = os.path.normpath(clean).replace("\\", "/")
        src, src_error = self._resolve_workspace_path(clean)
        if src_error or not os.path.isfile(src):
            return None, src_error or "file not found"
        if allowed_path is None:
            try:
                os.remove(src)
            except OSError:
                pass
            return None, note or "rejected by role path policy"
        if allowed_path != clean:
            dst, dst_error = self._resolve_workspace_path(allowed_path)
            if dst_error:
                try:
                    os.remove(src)
                except OSError:
                    pass
                return None, dst_error
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.abspath(src) != os.path.abspath(dst):
                if os.path.exists(dst):
                    try:
                        with open(src, "rb") as a, open(dst, "rb") as b:
                            same_content = a.read() == b.read()
                    except OSError:
                        same_content = False
                    if same_content:
                        os.remove(src)
                    else:
                        os.replace(src, dst)
                else:
                    os.replace(src, dst)
            return allowed_path, note
        return clean, note

    def _reply_mentions_files(self, reply: str) -> bool:
        """Check if reply mentions creating/writing files."""
        if self.FILE_MENTION_RE.search(reply):
            return True
        # Also check for file references without /workspace/ prefix
        matches = self.FILE_REF_RE.findall(reply)
        if matches:
            # Filter out false positives (URLs, code snippets mentioning file extensions)
            # Keep matches in context of file creation keywords
            file_keywords = ["readme", "document", "file", "组件", "文档", "页面",
                             "guide", "spec", "index", "main", "app", "config",
                             "component", "style", "script"]
            for m in matches:
                name = m.lower().rsplit("/", 1)[-1].rsplit(".", 1)[0]
                if any(kw in name for kw in file_keywords):
                    return True
                # Common document/page names
                if name in ("readme", "index", "main", "app", "guide", "style", "script"):
                    return True
        return False

    def _second_pass_extract_files(self, agent_id: str, original_msg: str,
                                    first_reply: str) -> list[dict]:
        """Ask agent to output full file content so we can write it server-side."""
        agent = self.agents.get(agent_id)
        if not agent:
            return []

        # Extract all file references (with and without /workspace/)
        filenames = set()
        for m in self.FILE_MENTION_RE.findall(first_reply):
            candidate = m.strip("`").strip()
            if self._looks_like_reportable_file(candidate):
                filenames.add(candidate)
        for m in self.FILE_REF_RE.findall(first_reply):
            candidate = m.strip("`").strip()
            if self._looks_like_reportable_file(candidate):
                filenames.add(candidate)

        # Sort and prefix with /workspace/ if missing
        sorted_files = sorted(filenames)
        if not sorted_files:
            log_agent(agent_id, "artifact_second_pass_skipped", reason="no concrete file paths")
            return []
        files_list_lines = []
        for f in sorted_files:
            if f.startswith("/workspace/"):
                files_list_lines.append(f"  - {f}")
            else:
                files_list_lines.append(f"  - /workspace/{f}")

        files_list = "\n".join(files_list_lines) if files_list_lines else "  - (the file you mentioned)"

        followup = (
            f"Output the COMPLETE content of each file now. Use this EXACT format:\n\n"
            f"## /workspace/filename\n"
            f"```\n"
            f"full file content here\n"
            f"```\n\n"
            f"Files to output:\n{files_list}\n\n"
            f"IMPORTANT: Do NOT ask for permission. Do NOT describe. Just output each file."
        )
        try:
            followup_reply = agent.send(followup)
            session_store.save_message(agent_id, "user", followup)
            session_store.save_message(agent_id, "assistant", followup_reply)

            # Parse code blocks from the followup reply
            return self._parse_and_write_code_blocks(agent_id, followup_reply)
        except Exception:
            return []

    @staticmethod
    def _looks_like_reportable_file(path: str) -> bool:
        clean = str(path or "").strip().strip("`").rstrip("/")
        if not clean:
            return False
        basename = clean.rsplit("/", 1)[-1]
        if "." not in basename:
            return False
        ext = os.path.splitext(basename)[1].lower()
        return ext in {".md", ".html", ".htm", ".css", ".js", ".json", ".txt", ".xml", ".svg", ".py", ".jsx", ".ts", ".tsx", ".vue"}

    def _detect_written_files(self, agent_id: str, reply: str,
                               baseline: dict[str, dict] = None) -> list[dict]:
        """Detect files that were written by Claude's native tools.

        Compares the current workspace state against a baseline snapshot.
        Also parses the reply for file path mentions to confirm naming.
        Reports all new files found on disk.
        """
        results = []

        # Collect newly created files by scanning filesystem delta
        if baseline is not None:
            current = self._snapshot_workspace()
            changed_files = []
            for relpath, meta in current.items():
                if self._is_low_value_file_path(relpath):
                    continue
                old = baseline.get(relpath)
                if not old:
                    changed_files.append((relpath, "created"))
                elif old.get("mtime") != meta.get("mtime") or old.get("size") != meta.get("size"):
                    changed_files.append((relpath, "modified"))
            for relpath, change_type in sorted(changed_files):
                policy_path, policy_note = self._apply_native_file_policy(agent_id, relpath)
                if policy_path is None:
                    log_agent(
                        agent_id,
                        "file_policy_rejected",
                        level="warning",
                        file=relpath.replace("\\", "/"),
                        reason=policy_note,
                    )
                    push_event(agent_id, "file_policy", {
                        "agent_id": agent_id,
                        "file": relpath.replace("\\", "/"),
                        "action": "rejected",
                        "reason": policy_note,
                    })
                    continue
                relpath = policy_path
                full_path = os.path.join("/workspace", relpath)
                try:
                    size = os.path.getsize(full_path)
                    log_agent(
                        agent_id,
                        "file_detected",
                        file=relpath.replace("\\", "/"),
                        change_type=change_type,
                        size=size,
                        method="filesystem_scan",
                        policy_note=policy_note,
                    )
                    results.append({
                        "tool": "write_file",
                        "file": relpath.replace("\\", "/"),
                        "change_type": change_type,
                        "method": "filesystem_scan",
                        "size": size,
                        "policy_note": policy_note,
                    })
                    push_event(agent_id, "file_write", {
                        "agent_id": agent_id,
                        "file": relpath.replace("\\", "/"),
                        "change_type": change_type,
                        "size": size,
                        "policy_note": policy_note,
                    })
                except OSError:
                    pass

        # If no delta found, try to verify files mentioned in the reply
        if not results:
            mentioned = set()
            for m in self.FILE_MENTION_RE.findall(reply):
                path = m.strip("`").strip()
                clean = re.sub(r"^/workspace/", "", path)
                mentioned.add(clean.lstrip("/"))
            for m in self.FILE_REF_RE.findall(reply):
                clean = m.strip("`").strip()
                mentioned.add(clean.lstrip("/"))

            for relpath in mentioned:
                policy_path, policy_note = self._apply_native_file_policy(agent_id, relpath)
                if policy_path is None:
                    continue
                relpath = policy_path
                full_path = os.path.join("/workspace", relpath)
                if os.path.isfile(full_path):
                    try:
                        size = os.path.getsize(full_path)
                        log_agent(
                            agent_id,
                            "file_verified_from_reply",
                            file=relpath.replace("\\", "/"),
                            size=size,
                            method="verify_mention",
                            policy_note=policy_note,
                        )
                        results.append({
                            "tool": "write_file",
                            "file": relpath.replace("\\", "/"),
                            "method": "verify_mention",
                            "size": size,
                            "policy_note": policy_note,
                        })
                        push_event(agent_id, "file_write", {
                            "agent_id": agent_id,
                            "file": relpath.replace("\\", "/"),
                            "size": size,
                            "policy_note": policy_note,
                        })
                    except OSError:
                        pass

        return results

    def _parse_and_write_code_blocks(self, agent_id: str, text: str) -> list[dict]:
        """Parse markdown sections with ## /workspace/path headers.

        Unlike the old approach (regex for code blocks), this takes ALL content
        between a ## /workspace/path header and the next header, then strips
        optional outer ``` markers. This handles files with embedded code blocks
        correctly.
        """
        results = []

        # Find all filename headers with their positions
        header_positions = []
        for m in self.FILENAME_HEADER_RE.finditer(text):
            header_positions.append((m.start(), m.end(), m.group(1)))

        if not header_positions:
            return results

        for i, (h_start, h_end, path) in enumerate(header_positions):
            next_h_start = header_positions[i + 1][0] if i + 1 < len(header_positions) else len(text)

            clean_path = re.sub(r"^/workspace/", "", path)
            clean_path, policy_note = self._path_policy(agent_id, clean_path)
            if clean_path is None:
                log_agent(agent_id, "file_policy_rejected", level="warning", file=path, reason=policy_note)
                results.append({"error": f"Rejected {path}: {policy_note}"})
                push_event(agent_id, "file_policy", {
                    "agent_id": agent_id,
                    "file": path,
                    "action": "rejected",
                    "reason": policy_note,
                })
                continue

            # Everything between header end and next header (or end of text)
            raw = text[h_end:next_h_start].strip()

            if not raw:
                continue

            # Strip outer ``` markers if present
            content = raw
            if content.startswith("```"):
                # Find the first newline after opening ```
                first_nl = content.find("\n")
                if first_nl != -1:
                    content = content[first_nl + 1:]
                else:
                    content = content[3:]
                # Strip trailing ```
                if content.endswith("```"):
                    content = content[:-3]
                elif "```" in content:
                    content = content.rsplit("```", 1)[0]
                content = content.strip()

            try:
                full_path, _ = self._resolve_workspace_path(clean_path)
                existed = os.path.exists(full_path)
                self.tools.execute("write_file", path=clean_path, content=content)
                change_type = "modified" if existed else "created"
                log_agent(
                    agent_id,
                    "file_written_from_codeblock",
                    file=clean_path,
                    change_type=change_type,
                    size=len(content),
                    policy_note=policy_note,
                )
                results.append({
                    "tool": "write_file",
                    "file": clean_path,
                    "change_type": change_type,
                    "method": "codeblock",
                    "policy_note": policy_note,
                })
                # Push file_write event
                push_event(agent_id, "file_write", {
                    "agent_id": agent_id,
                    "file": clean_path,
                    "change_type": change_type,
                    "size": len(content),
                    "policy_note": policy_note,
                })
            except Exception as e:
                log_agent(agent_id, "file_write_failed", level="error", file=clean_path, error=str(e))
                results.append({"error": f"Failed to write {clean_path}: {e}"})

        return results

    # ---- Internal ----

    # ---- File operations ----

    def _resolve_workspace_path(self, path: str) -> tuple[str, Optional[str]]:
        """Resolve a path and ensure it stays inside /workspace."""
        if path.startswith("/workspace"):
            full_path = path
        else:
            full_path = os.path.join("/workspace", path.lstrip("/"))

        real_path = os.path.realpath(full_path)
        workspace_root = os.path.realpath("/workspace")
        if real_path != workspace_root and not real_path.startswith(workspace_root + os.sep):
            return "", "Access denied: path outside workspace"
        return real_path, None

    def read_file(self, agent_id: str, path: str) -> dict:
        """Read a file or list directory contents within /workspace.

        Args:
            agent_id: Agent making the request (for context)
            path: File path, can be relative to /workspace or absolute

        Returns:
            dict with file content or directory listing
        """
        real_path, error = self._resolve_workspace_path(path)
        if error:
            return {"error": error}

        if not os.path.exists(real_path):
            return {"error": f"File not found: {path}"}

        if os.path.isdir(real_path):
            # List directory contents recursively
            files = []
            for root, dirs, filenames in os.walk(real_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in filenames:
                    filepath = os.path.join(root, f)
                    rel_path = os.path.relpath(filepath, "/workspace")
                    try:
                        files.append({
                            "path": f"/workspace/{rel_path.replace(os.sep, '/')}",
                            "name": f,
                            "size": os.path.getsize(filepath),
                        })
                    except OSError:
                        pass
            return {"type": "directory", "path": path, "files": files, "count": len(files)}

        # Read file content
        try:
            with open(real_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "type": "file",
                "path": path,
                "content": content,
                "size": len(content),
                "language": os.path.splitext(path)[1].lstrip("."),
            }
        except UnicodeDecodeError:
            return {"error": "Binary file - cannot display as text"}
        except IOError as e:
            return {"error": f"Failed to read file: {e}"}

    def start_service(self, payload: dict) -> dict:
        """Start a preview service inside the sandbox container."""
        try:
            result = self.service_manager.start_service(
                agent_id=payload.get("agent_id", ""),
                name=payload.get("name", ""),
                cwd=payload.get("cwd", ""),
                command=payload.get("command", ""),
                port=int(payload.get("port") or 0),
                service_type=payload.get("type") or payload.get("service_type") or "custom",
                env=payload.get("env") or {},
            )
            log_event("service_start_requested", result_status=result.get("status"))
            return result
        except Exception as exc:
            log_event("service_start_exception", level="error", error=str(exc))
            return {"error": str(exc)}

    def stop_service(self, service_id: str) -> dict:
        return self.service_manager.stop_service(service_id)

    def restart_service(self, service_id: str) -> dict:
        return self.service_manager.restart_service(service_id)

    def list_services(self) -> dict:
        return {"services": self.service_manager.list_services()}

    def get_service(self, service_id: str) -> dict:
        service = self.service_manager.get_service(service_id)
        if not service:
            return {"error": "service not found"}
        return {"service": service}

    def get_service_logs(self, service_id: str, tail_bytes: int = 65536) -> dict:
        return self.service_manager.get_logs(service_id, tail_bytes=tail_bytes)

    def read_raw_file(self, path: str) -> tuple[bytes, str, str]:
        """Read raw bytes from a workspace file with MIME type."""
        real_path, error = self._resolve_workspace_path(path)
        if error:
            raise ValueError(error)
        if not os.path.isfile(real_path):
            raise FileNotFoundError(path)

        with open(real_path, "rb") as f:
            content = f.read()

        mime_type = mimetypes.guess_type(real_path)[0] or "application/octet-stream"
        filename = os.path.basename(real_path)
        return content, mime_type, filename

    REPORT_TYPES = {"progress", "result", "summary", "text", "table", "image", "code", "file", "error", "service", "requirement_card", "bug_card", "iteration_card", "project_card", "office_card"}
    REPORT_STATUSES = {"running", "done", "error", "stopped", "starting", "stopping", "failed", "exited"}
    REPORT_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}

    def report_element(self, agent_id: str, report: dict) -> dict:
        """Validate and emit a structured report element from an agent."""
        log_agent(
            agent_id,
            "report_received",
            report_type=report.get("type") if isinstance(report, dict) else None,
            title=report.get("title") if isinstance(report, dict) else None,
            content_preview=shorten(report.get("content", ""), 200) if isinstance(report, dict) else "",
        )
        if agent_id not in self.agents:
            log_agent(agent_id, "report_rejected", level="warning", reason="agent not found")
            return {"status": "error", "error": f"Agent '{agent_id}' not found"}
        if not isinstance(report, dict):
            log_agent(agent_id, "report_rejected", level="warning", reason="report must be object")
            return {"status": "error", "error": "report must be an object"}

        element, error = self._normalize_report_element(report)
        if error:
            log_agent(agent_id, "report_invalid", level="warning", error=error)
            push_event(agent_id, "agent_report_element", {
                "type": "error",
                "title": "进度上报失败",
                "content": error,
                "status": "error",
                "data": {"raw": report},
            })
            return {"status": "error", "error": error}

        push_event(agent_id, "agent_report_element", element)
        log_agent(
            agent_id,
            "report_emitted",
            report_type=element.get("type"),
            status=element.get("status"),
            title=(element.get("data") or {}).get("title"),
        )
        return {"status": "ok", "element": element}

    def _normalize_report_element(self, report: dict) -> tuple[dict, Optional[str]]:
        element_type = str(report.get("type") or "").strip().lower()
        if not element_type:
            return {}, self._report_usage_error("missing required field: type")
        if element_type not in self.REPORT_TYPES:
            return {}, self._report_usage_error(
                f"invalid report type: {element_type}; allowed: {', '.join(sorted(self.REPORT_TYPES))}"
            )

        status = str(report.get("status") or ("running" if element_type == "progress" else "done")).strip().lower()
        if status not in self.REPORT_STATUSES:
            return {}, self._report_usage_error(
                f"invalid report status: {status}; allowed: {', '.join(sorted(self.REPORT_STATUSES))}"
            )

        if "data" in report and report.get("data") is not None and not isinstance(report.get("data"), dict):
            return {}, self._report_usage_error("field data must be an object when provided")
        data = report.get("data") if isinstance(report.get("data"), dict) else {}
        content = report.get("content", "")
        if content is None:
            content = ""
        content = str(content)
        title = str(report.get("title") or "").strip()

        # 领域卡片类型：title/content 从 data 中提取，content 可选
        DOMAIN_CARD_TYPES = {"requirement_card", "bug_card", "iteration_card", "project_card", "office_card"}
        if element_type in DOMAIN_CARD_TYPES:
            if not title:
                title = str(data.get("title") or "").strip()
            if not content.strip():
                content = str(data.get("summary") or data.get("description") or title)
        if not title:
            return {}, self._report_usage_error("missing required non-empty string field: title")
        step_id = str(report.get("step_id") or data.get("step_id") or "").strip()

        if element_type != "table" and element_type not in DOMAIN_CARD_TYPES and not content.strip():
            return {}, self._report_usage_error("missing required non-empty string field: content")

        normalized = {
            "type": element_type,
            "content": content,
            "status": status,
            "data": {
                **data,
                "title": title,
            },
        }
        if step_id:
            normalized["step_id"] = step_id
            normalized["data"]["step_id"] = step_id

        if element_type == "table":
            headers = data.get("headers")
            rows = data.get("rows")
            if not isinstance(headers, list) or not headers or not all(isinstance(h, str) and h.strip() for h in headers):
                return {}, self._report_usage_error("table requires data.headers as a non-empty string array")
            if not isinstance(rows, list):
                return {}, self._report_usage_error("table requires data.rows as an array")
            if any(not isinstance(row, list) for row in rows):
                return {}, self._report_usage_error("table data.rows must contain row arrays")
            normalized["data"]["headers"] = [str(h) for h in headers]
            normalized["data"]["rows"] = [
                [str(cell) if cell is not None else "" for cell in row]
                for row in rows if isinstance(row, list)
            ]
            normalized["content"] = content or title

        if element_type in {"file", "image"}:
            path = data.get("path") or content
            if not str(path or "").strip():
                return {}, self._report_usage_error(f"{element_type} requires data.path or content as /workspace/... path")
            if not str(path).startswith("/workspace/"):
                return {}, self._report_usage_error(f"{element_type} path must start with /workspace/: {path}")
            real_path, error = self._resolve_workspace_path(str(path or ""))
            if error:
                return {}, self._report_usage_error(error)
            if not os.path.exists(real_path):
                return {}, self._report_usage_error(f"reported path not found: {path}")
            rel_path = os.path.relpath(real_path, "/workspace").replace(os.sep, "/")
            workspace_path = f"/workspace/{rel_path}"
            ext = os.path.splitext(real_path)[1].lower()
            if element_type == "image" and ext not in self.REPORT_IMAGE_EXTS:
                return {}, self._report_usage_error(f"reported image must be one of: {', '.join(sorted(self.REPORT_IMAGE_EXTS))}")
            normalized["content"] = content or os.path.basename(real_path)
            normalized["data"].update({
                "path": workspace_path,
                "name": os.path.basename(real_path),
                "size": os.path.getsize(real_path) if os.path.isfile(real_path) else None,
            })

        if element_type == "code":
            normalized["data"]["language"] = str(data.get("language") or report.get("language") or "text")

        if element_type == "service":
            service_data = data.get("service") if isinstance(data.get("service"), dict) else data
            service_id = str(service_data.get("service_id") or service_data.get("id") or "").strip()
            if not service_id:
                return {}, self._report_usage_error("service requires data.service_id as a non-empty string")
            normalized["data"].update(service_data)
            normalized["data"]["service_id"] = service_id
            normalized["data"]["id"] = service_data.get("id") or service_id
            if service_data.get("port") is not None:
                try:
                    normalized["data"]["port"] = int(service_data.get("port"))
                except (TypeError, ValueError):
                    return {}, self._report_usage_error("service data.port must be a positive integer")
            normalized["content"] = content or title

        if element_type in {"progress", "result", "summary", "text", "error"}:
            normalized["content"] = content or title

        return normalized, None

    @staticmethod
    def _report_usage_error(message: str) -> str:
        return (
            f"WEAGENT_REPORT_VALIDATION_ERROR: {message}\n"
            "weagent-report 只接受一个 JSON 对象字符串。\n"
            "必填字段：type、title；除 table 外还必须有非空 content。\n"
            "type 只能是 progress/result/summary/text/table/image/code/file/error/service/requirement_card/bug_card/iteration_card/project_card/office_card。\n"
            "status 可选，只能是 running/done/error/stopped/starting/stopping/failed/exited。\n"
            "table 格式：{\"type\":\"table\",\"title\":\"任务分派计划\",\"data\":{\"headers\":[\"Agent\",\"任务\",\"产出\"],\"rows\":[[\"frontend\",\"实现登录页\",\"index.html\"]]}}\n"
            "file 格式：{\"type\":\"file\",\"title\":\"前端页面\",\"content\":\"/workspace/agents/frontend/index.html\",\"data\":{\"path\":\"/workspace/agents/frontend/index.html\"}}\n"
            "service 格式：{\"type\":\"service\",\"title\":\"前端预览\",\"content\":\"服务已启动\",\"status\":\"running\",\"data\":{\"service_id\":\"svc_xxx\",\"port\":5173}}\n"
            "progress 格式：{\"type\":\"progress\",\"title\":\"分析需求\",\"content\":\"正在确认任务范围\",\"status\":\"running\",\"step_id\":\"step-1\"}"
        )

    def write_binary_file(self, agent_id: str, path: str, content: bytes) -> dict:
        """Write uploaded bytes into the agent workspace userInput directory."""
        real_path, error = self._resolve_workspace_path(path)
        if error:
            return {"error": error}

        allowed_root = os.path.realpath(f"{self._agent_work_dir(agent_id)}/userInput")
        target = os.path.realpath(real_path)
        if target != allowed_root and not target.startswith(allowed_root + os.sep):
            return {"error": "Uploads must stay inside agent userInput directory"}

        os.makedirs(os.path.dirname(real_path), exist_ok=True)
        with open(real_path, "wb") as f:
            f.write(content)

        rel_path = os.path.relpath(real_path, "/workspace").replace(os.sep, "/")
        return {
            "status": "ok",
            "path": f"/workspace/{rel_path}",
            "size": len(content),
        }

    def delete_file(self, agent_id: str, path: str) -> dict:
        """Delete a file from the agent workspace userInput directory."""
        real_path, error = self._resolve_workspace_path(path)
        if error:
            return {"error": error}

        allowed_root = os.path.realpath(f"{self._agent_work_dir(agent_id)}/userInput")
        target = os.path.realpath(real_path)
        if target != allowed_root and not target.startswith(allowed_root + os.sep):
            return {"error": "Can only delete files inside agent userInput directory"}
        if not os.path.isfile(real_path):
            return {"error": "File not found"}

        os.remove(real_path)
        return {"status": "ok", "path": path}

    def list_tree(self, root: str = "/workspace", include_hidden: bool = False,
                  max_depth: int = 8) -> dict:
        """Return a tree of files under a workspace path."""
        started_at = time.time()
        real_root, error = self._resolve_workspace_path(root)
        resolve_ms = round((time.time() - started_at) * 1000, 1)
        if error:
            log_event("list_tree_error", root=root, resolve_ms=resolve_ms, error=error)
            return {"error": error}
        if not os.path.exists(real_root):
            log_event("list_tree_missing", root=root, real_root=real_root, resolve_ms=resolve_ms)
            return {"error": f"Path not found: {root}"}

        workspace_root = os.path.realpath("/workspace")
        stats = {
            "dirs": 0,
            "files": 0,
            "listdir_ms": 0.0,
            "sort_ms": 0.0,
            "file_meta_ms": 0.0,
        }

        def build_node(path: str, depth: int) -> dict:
            rel_path = os.path.relpath(path, workspace_root)
            node_path = "/workspace" if rel_path == "." else f"/workspace/{rel_path.replace(os.sep, '/')}"
            name = os.path.basename(path) or "workspace"

            if os.path.isdir(path):
                stats["dirs"] += 1
                node = {
                    "name": name,
                    "path": node_path,
                    "type": "directory",
                    "children": [],
                }
                if depth >= max_depth:
                    node["truncated"] = True
                    return node

                try:
                    listdir_started = time.time()
                    entries = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
                    listdir_elapsed = (time.time() - listdir_started) * 1000
                    stats["listdir_ms"] += listdir_elapsed
                except OSError:
                    return node

                for entry in entries:
                    if not include_hidden and entry.startswith("."):
                        continue
                    child_path = os.path.join(path, entry)
                    node["children"].append(build_node(child_path, depth + 1))
                return node

            size = 0
            try:
                file_meta_started = time.time()
                size = os.path.getsize(path)
                stats["file_meta_ms"] += (time.time() - file_meta_started) * 1000
            except OSError:
                pass
            stats["files"] += 1
            mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            return {
                "name": name,
                "path": node_path,
                "type": "file",
                "size": size,
                "mime_type": mime_type,
                "extension": os.path.splitext(path)[1].lstrip("."),
            }

        tree = build_node(real_root, 0)
        total_ms = round((time.time() - started_at) * 1000, 1)
        log_event(
            "list_tree_timing",
            root=root,
            real_root=real_root,
            resolve_ms=resolve_ms,
            total_ms=total_ms,
            dirs=stats["dirs"],
            files=stats["files"],
            listdir_ms=round(stats["listdir_ms"], 1),
            file_meta_ms=round(stats["file_meta_ms"], 1),
            max_depth=max_depth,
            include_hidden=include_hidden,
        )
        return {"root": root, "tree": tree}

    # ---- Stop agent ----

    def stop_agent(self, agent_id: str) -> dict:
        """Stop an agent's current execution."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent '{agent_id}' not found"}
        agent.stop()
        return {"status": "ok"}

    def restart_agent(self, agent_id: str) -> dict:
        """Restart one agent runtime while keeping workspace and session history."""
        agent = self.agents.pop(agent_id, None)
        if agent:
            agent.stop()
        recreated = self._get_or_recreate_agent(agent_id)
        if isinstance(recreated, dict):
            return recreated
        return {"status": "ok", "agent": recreated.to_dict()}

    def update_model_config(self, config: dict) -> dict:
        """Update shared Claude Code settings used by all agent workspaces."""
        api_key = (
            config.get("api_key")
            or config.get("ANTHROPIC_API_KEY")
            or config.get("DEEPSEEK_API_KEY")
            or ""
        )
        base_url = (
            config.get("base_url")
            or config.get("ANTHROPIC_BASE_URL")
            or config.get("DEEPSEEK_BASE_URL")
            or ""
        )
        model_name = (
            config.get("model")
            or config.get("ANTHROPIC_MODEL")
            or config.get("DEEPSEEK_MODEL")
            or ""
        )
        api_key = clean_config_value(api_key)
        base_url = clean_base_url(base_url)
        model_name = clean_config_value(model_name)
        if not api_key:
            return {"error": "api_key required"}

        write_settings(api_key, base_url, model_name)
        os.environ["ANTHROPIC_API_KEY"] = api_key
        if base_url:
            os.environ["ANTHROPIC_BASE_URL"] = base_url
        if model_name:
            os.environ["ANTHROPIC_MODEL"] = model_name
        os.environ.update(claude_env())

        provider_env_keys = [
            "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
            "CODEX_API_KEY", "CODEX_BASE_URL", "CODEX_MODEL",
            "CODEX_AUTH_JSON", "CODEX_CONFIG_TOML", "CODEX_USE_RELAY",
            "OPENCODE_API_KEY", "OPENCODE_BASE_URL", "OPENCODE_MODEL",
        ]
        for key in provider_env_keys:
            value = config.get(key)
            if value is None:
                continue
            if key.endswith("BASE_URL"):
                value = clean_base_url(value)
            elif key.endswith("API_KEY") or key.endswith("MODEL"):
                value = clean_config_value(value)
            if value:
                os.environ[key] = value

        for agent in self.agents.values():
            agent.start()
        return {
            "status": "ok",
            "model": model_name,
            "base_url": base_url,
            "codex_base_url": os.environ.get("CODEX_BASE_URL", ""),
            "agents": list(self.agents.keys()),
        }

    # ---- Internal ----

    def _with_capability_bootstrap(self, agent_id: str, system_prompt: str) -> str:
        projection = self.capability_projection or {}
        if agent_id not in (projection.get("agents") or {}):
            return system_prompt or ""
        bootstrap = agent_bootstrap_instruction(agent_id)
        prompt = system_prompt or ""
        if bootstrap in prompt:
            return prompt
        return f"{prompt}\n\n{bootstrap}".strip()

    def _write_capability_run_snapshot(self, agent_id: str) -> Optional[str]:
        projection = self.capability_projection or {}
        if agent_id not in (projection.get("agents") or {}):
            return None
        self._capability_run_counter += 1
        run_id = f"{agent_id}-{int(time.time() * 1000)}-{self._capability_run_counter}"
        result = write_run_snapshot(projection, run_id, workspace_root="/workspace")
        return result.get("run_id")

    def _get_or_recreate_agent(self, agent_id: str):
        """Get agent, or recreate from saved config if missing."""
        agent = self.agents.get(agent_id)
        if agent is not None and agent.is_alive:
            return agent

        # Try to recreate from persisted config
        config = session_store.load_agent_config(agent_id)
        if not config:
            return {"error": f"Agent '{agent_id}' not found and no saved config"}

        # Use saved system prompt (agent.md handles role definition)
        runtime_prompt = self._with_capability_bootstrap(agent_id, config["system_prompt"])

        agent = AgentRuntime(
            agent_id,
            config["role"],
            runtime_prompt,
            config.get("workspace_name") or config.get("role") or agent_id,
            provider_name=config.get("adapter_name") or config.get("provider") or "claude",
        )
        try:
            agent.start()
        except Exception as e:
            return {"error": f"Failed to recreate agent: {e}"}

        self.agents[agent_id] = agent

        # Replay recent history to restore context
        history = session_store.get_history(agent_id, limit=10)
        for msg in history:
            agent.send(msg["content"])

        return agent

    @staticmethod
    def _is_agent_runtime_error(reply: str) -> bool:
        if not reply:
            return False
        error_prefixes = ("[Error]", "[AuthError]")
        if reply.startswith(error_prefixes):
            return True
        text = reply.lower()
        error_markers = (
            "failed to authenticate",
            "api error",
            "unexpected status",
            "insufficient balance",
            "invalid api key",
            "missing or invalid",
            "unauthorized",
            "permission denied",
            "rate limit",
        )
        return any(marker in text for marker in error_markers)
