"""
container.agent — ClaudeRuntime wrapper using claude -p CLI.

Each agent runs in its own workspace directory with its own .claude/agent.md
for role definition. Uses subprocess to invoke `claude -p` non-interactively.
"""

import json
import os
import queue
import re
import subprocess
import threading
import time
from typing import Optional

from .events import push_event
from .logging_utils import log_agent, shorten
from .providers import ProviderRunnerFactory


class AgentRuntime:
    """
    Wraps claude -p CLI calls for task execution.

    Each agent has its own workspace under /workspace/agents/{workspace_name}/
    with .claude/agent.md for role definition.
    """

    def __init__(self, agent_id: str, role: str, system_prompt: str,
                 workspace_name: str = "", provider_name: str = "claude"):
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.provider_name = (provider_name or "claude").strip().lower()
        self.workspace_name = self._safe_workspace_name(workspace_name or role or agent_id)
        self._stop_signaled = False
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._agent_dir = f"/workspace/agents/{self.workspace_name}"
        self._claude_session_marker = os.path.join(self._agent_dir, ".weagent_claude_session")
        self.provider_runner = ProviderRunnerFactory.create(self.provider_name, self)

    def start(self):
        """Set up agent workspace: create dirs, write agent.md, link settings."""
        agent_dir = self._agent_dir
        log_agent(
            self.agent_id,
            "workspace_setup_start",
            role=self.role,
            workspace_name=self.workspace_name,
            work_dir=agent_dir,
            provider=self.provider_runner.provider_name,
        )
        os.makedirs(agent_dir, exist_ok=True)
        self.provider_runner.setup()
        os.makedirs("/workspace/shared", exist_ok=True)
        log_agent(
            self.agent_id,
            "workspace_setup_done",
            role=self.role,
            workspace_name=self.workspace_name,
            work_dir=agent_dir,
            provider=self.provider_runner.provider_name,
        )

    def bound_tool_names(self) -> list[str]:
        """Read the server-projected tool catalog for this Agent."""
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(self.agent_id or "").strip())
        path = os.path.join(
            os.environ.get("WEAGENT_WORKSPACE_ROOT", "/workspace"),
            ".weagent",
            "agents",
            safe_id.strip(".-") or "item",
            "capabilities.json",
        )
        try:
            with open(path, encoding="utf-8") as stream:
                payload = json.load(stream)
        except (OSError, ValueError):
            return []
        names = set()
        for capability in payload.get("capabilities") or []:
            if capability.get("type") != "tool":
                continue
            if (capability.get("status") or "implemented") not in {
                "implemented",
                "partial",
            }:
                continue
            manifest = capability.get("manifest") or {}
            for name in capability.get("tool_names") or manifest.get("tool_names") or []:
                clean = str(name or "").strip()
                if clean:
                    names.add(clean)
        return sorted(names)

    def tool_preflight(self, required_tools=None) -> dict:
        return self.provider_runner.tool_preflight(required_tools or [])

    def _format_agent_md(self) -> str:
        """Format the agent.md file from the system prompt."""
        capability_note = self._capability_instruction()
        note = f"""

===== WeAgent 工作与实时上报规范 =====
你的私有工作目录是 /workspace/agents/{self.workspace_name}/。
公共协作目录是 /workspace/shared/。
你可以读取 /workspace/agents/ 下其他 Agent 的工作目录内容来协作。

你必须使用 Bash 调用 weagent-report 向前端实时汇报进度和结果。
执行任务前先上报计划；每个步骤开始前上报 progress；步骤完成后上报 result；生成文件后上报 file；生成图片后上报 image；出错时上报 error；结束前上报 summary。

weagent-report 只接受一个 JSON 字符串参数：
weagent-report '{{"type":"progress","title":"分析需求","content":"正在确认任务范围","status":"running","step_id":"step-1"}}'

服务预览工具：
- 当用户要求运行、部署、预览或暴露生成的项目时，必须使用 weagent-service。
- weagent-service 会在沙箱内启动进程、登记端口，并自动向前端上报 service 卡片。
- 严禁直接在 Bash 中前台执行 npm run dev / npm run serve / vue-cli-service serve / next dev / flask run / uvicorn 等长时间运行命令。
- 如果需要启动这类长运行服务，只能通过 weagent-service start 启动，让服务在后台运行，然后继续上报 summary 并结束本轮回复。
- 示例：
  weagent-service start --name "前端预览" --cwd "/workspace/agents/{self.workspace_name}" --command "npm run dev -- --host 0.0.0.0 --port 5173" --port 5173 --type vite

上报类型：progress、result、summary、text、table、image、code、file、error、service、requirement_card、bug_card、iteration_card、project_card、office_card。
table 固定格式：{{"type":"table","title":"标题","data":{{"headers":["列1"],"rows":[["值1"]]}}}}。
image/file 只允许上报容器内 /workspace/... 路径。
service 产物优先使用 weagent-service start 自动上报；手动上报时必须包含 data.service_id。
大段代码可以用 code 块上报；如果用户要求生成项目或可运行产物，必须把代码写入文件，再上报 file/image。

领域卡片（requirement_card/bug_card/iteration_card/project_card）用于展示研发管理数据，title/content 放在 data 里，不需要顶层字段：
weagent-report '{{"type":"project_card","data":{{"id":"<id>","title":"项目名","summary":"描述","project_id":"<id>","meta":{{"requirement_count":5,"bug_count":3}}}}}}'
weagent-report '{{"type":"requirement_card","data":{{"id":"<id>","title":"需求标题","project_id":"项目ID","priority":"p0/p1/p2/p3","status":"backlog/todo/in_progress/in_review/done","meta":{{"assignee":"负责人","iteration_name":"迭代名"}}}}}}'
RD 服务数据展示优先级：领域卡片 > table > 纯文本。
查询到需求/缺陷/迭代/项目列表时，**必须逐条发送对应卡片**，这是第一优先级。
只在卡片无法表达汇总/对比信息时，才用 table 作为补充（如"本次共查询到 5 条需求，汇总如下"后面跟一个 table）。
禁止用卡片类型能覆盖的数据去写大段 Markdown 列表或表格来替代卡片。

智慧办公数据使用 office_card，上报会议、行动项、公文或审批记录：
weagent-report '{{"type":"office_card","data":{{"id":"<id>","kind":"meeting/action_item/document/approval","title":"标题","status":"状态","summary":"摘要","meta":{{"assignee":"负责人","due_date":"截止时间"}}}}}}'

文件创建方式：优先使用 Claude Code 的 Write/Edit/Bash 工具直接创建文件。所有正式产物优先写入你的私有工作目录。
如果工具不可用，才使用下面格式输出文件内容，系统会尝试自动写入：

## /workspace/agents/{self.workspace_name}/实际文件名.ext
```
文件内容
```

不要请求批准，系统已自动批准工具调用。写入完成后必须上报对应 file/image，结束前用 summary 上报给用户看的简短结论。
========================
"""
        if capability_note:
            note = note.replace("\n========================", f"{capability_note}\n========================")
        return f"# {self.role}\n\n{self.system_prompt}\n{note}"

    def _capability_instruction(self) -> str:
        """Return the toolset projection note if the capability module is present."""
        try:
            from .capabilities import agent_bootstrap_instruction
            bootstrap = agent_bootstrap_instruction(self.agent_id)
            if bootstrap in (self.system_prompt or ""):
                return ""
            return "\n" + bootstrap
        except Exception:
            return ""

    def stop(self):
        """Signal the currently running process to stop."""
        self._stop_signaled = True
        log_agent(self.agent_id, "stop_requested", role=self.role)
        with self._lock:
            if self._process:
                try:
                    self._process.terminate()
                except Exception:
                    pass

    @property
    def is_alive(self) -> bool:
        return True

    def send(self, message: str) -> str:
        """Send a single message with system prompt (via agent.md)."""
        if not self.provider_runner.runnable:
            return self._provider_not_implemented()
        return self._call_claude(message)

    def send_with_context(self, message: str, context: str = "") -> str:
        """Send message with injected context from other agents."""
        parts = []
        if context:
            parts.append(f"## 其他 Agent 的输出上下文\n{context}\n")
        parts.append(message)
        full_message = "\n\n".join(parts)
        if not self.provider_runner.runnable:
            return self._provider_not_implemented()
        return self._call_claude(full_message)

    def _provider_not_implemented(self) -> str:
        msg = f"[Error] {self.provider_runner.unavailable_message()}"
        push_event(self.agent_id, "error", {
            "agent_id": self.agent_id,
            "role": self.role,
            "provider": self.provider_runner.provider_name,
            "error": msg,
        })
        log_agent(
            self.agent_id,
            "provider_not_implemented",
            level="error",
            role=self.role,
            provider=self.provider_runner.provider_name,
        )
        return msg

    def _runtime_instruction(self) -> str:
        if not self.provider_runner.supports_native_shell:
            capability_note = self._capability_instruction()
            moderator_rule = ""
            if self.agent_id == "moderator":
                moderator_rule = (
                    "\nAs the moderator, coordinate the assigned roles in plain text. "
                    "Do not invent tool calls or executable commands.\n"
                )
            return f"""
You are the WeAgent conversation Agent {self.role} (agent_id={self.agent_id}).

This provider has no executable shell or native progress tools. The runtime reports
heartbeats automatically. Do not call bash, run_command, run_command_safe,
weagent-report, update_plan, request_user_input, or any invented tool.

When the task requires files, return each complete artifact as one controlled file
block using this exact format:

## /workspace/agents/{self.workspace_name}/actual-filename.ext
```text
complete file content
```

The trusted runtime writes controlled file blocks into the private workspace and
reports them to the product. Never claim that you executed or persisted a file
yourself. Finish with a short user-facing summary after all required file blocks.
{moderator_rule}
{capability_note}
The user task follows below.
""".strip()
        capability_note = self._capability_instruction()
        moderator_rule = ""
        if self.agent_id == "moderator":
            moderator_rule = """
主持 Agent 额外要求：
- 你生成“任务分派计划”时，也必须先调用 weagent-report 上报。
- 分派计划优先用 table，上报格式为 {"type":"table","title":"任务分派计划","data":{"headers":["Agent","任务","产出"],"rows":[["agent_id","任务说明","预期产物"]]}}。
- 分派完成后继续用 result 上报分派结果。
"""
        return f"""
你是 WeAgent 会话中的 Agent：{self.role}（agent_id={self.agent_id}）。

强制实时上报规则：
1. 执行任何任务前，必须先用 Bash 调用 weagent-report 上报 progress。不要只在最终回复里描述进度。
2. 每个关键步骤开始时调用 progress；步骤完成时调用 result；写入文件后调用 file；生成图片后调用 image；出错时调用 error；所有任务结束前必须调用 summary。
3. 用户要求生成前端、脚本、项目、文档或任何可运行产物时，绝大多数情况必须真实写入 /workspace/agents/{self.workspace_name}/ 下的文件，再上报 file/image。
4. image/file 只能上报容器内 /workspace/... 路径，不能上报宿主机路径、base64、data URL。
5. table 只能使用 data.headers 和 data.rows：{{"type":"table","title":"标题","data":{{"headers":["列"],"rows":[["值"]]}}}}。
6. 大段代码可以用 code 上报到消息框；但可运行产物必须写入文件。
7. 如果你不知道下一步是否耗时，也要先上报 progress。

weagent-report 调用示例：
weagent-report '{{"type":"progress","title":"分析需求","content":"正在确认任务范围","status":"running","step_id":"step-1"}}'
weagent-report '{{"type":"result","title":"分析完成","content":"已确认实现范围","status":"done","step_id":"step-1"}}'
weagent-report '{{"type":"file","title":"产物文件","content":"/workspace/agents/{self.workspace_name}/index.html","data":{{"path":"/workspace/agents/{self.workspace_name}/index.html"}}}}'
weagent-report '{{"type":"summary","title":"完成摘要","content":"已完成用户请求，生成的文件位于 /workspace/agents/{self.workspace_name}/index.html","status":"done"}}'

领域卡片示例（RD服务查询结果优先用卡片，汇总对比可补充table）：
weagent-report '{{"type":"project_card","data":{{"id":"<id>","title":"项目名","summary":"描述","project_id":"<id>","meta":{{"requirement_count":5,"bug_count":3}}}}}}'
weagent-report '{{"type":"requirement_card","data":{{"id":"<id>","title":"需求标题","project_id":"项目ID","priority":"p0","status":"todo","meta":{{"assignee":"张三"}}}}}}'
weagent-report '{{"type":"bug_card","data":{{"id":"<id>","title":"缺陷标题","project_id":"项目ID","severity":"critical","status":"open"}}}}'
weagent-report '{{"type":"iteration_card","data":{{"id":"<id>","title":"迭代名称","project_id":"项目ID","status":"active","meta":{{"start_date":"2026-08-01","end_date":"2026-08-14"}},"progress":50}}}}'

服务预览命令：
- 如果需要运行或部署生成的 Vue/Vite/React/Next/Flask/FastAPI 项目，使用 weagent-service。
- 服务必须绑定到 0.0.0.0，并使用你上报的同一个端口。
- 不要直接运行会常驻前台的 dev server 命令；直接运行会导致本轮任务无法结束、前端一直转圈。
- 启动服务后必须继续调用 weagent-report 上报 summary，说明文件位置和预览服务。
- 示例：
weagent-service start --name "前端预览" --cwd "/workspace/agents/{self.workspace_name}" --command "npm run dev -- --host 0.0.0.0 --port 5173" --port 5173 --type vite

{moderator_rule}
{capability_note}
下面才是用户任务。先上报 progress，再开始处理。
""".strip()


    # ---- claude -p call ----

    def _call_claude(self, message: str, retry_without_continue: bool = True) -> str:
        """Run claude -p with the given message, capturing output.

        Claude Code runs in non-interactive bypass mode because there is no
        frontend path for approving container-local tool prompts.
        """
        runner = self.provider_runner
        self._stop_signaled = False
        start_time = time.time()
        exec_timeout = runner.timeout_seconds()
        log_agent(
            self.agent_id,
            f"{runner.log_prefix}_call_start",
            role=self.role,
            workspace_name=self.workspace_name,
            provider=runner.provider_name,
            message_len=len(message or ""),
            message_preview=shorten(message, 300),
            timeout=exec_timeout,
        )

        push_event(self.agent_id, runner.started_event, runner.started_payload())

        cmd, use_continue = runner.build_command(message, retry_with_resume=retry_without_continue)
        log_agent(
            self.agent_id,
            f"{runner.log_prefix}_context_mode",
            role=self.role,
            provider=runner.provider_name,
            **runner.context_log_fields(use_continue),
        )

        # Disable color/ANSI output for cleaner parsing
        env = runner.environment()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self._agent_dir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            with self._lock:
                self._process = proc
            log_agent(
                self.agent_id,
                f"{runner.log_prefix}_process_started",
                role=self.role,
                provider=runner.provider_name,
                pid=proc.pid,
                cwd=self._agent_dir,
            )

            stdout_parts = []
            stderr_parts = []
            output_queue = queue.Queue()
            heartbeat_stop = threading.Event()

            def _maybe_answer_prompt(chunk: str):
                text = (chunk or "").lower()
                prompt_markers = (
                    "do you want to proceed",
                    "do you want to continue",
                    "permission",
                    "allow this command",
                    "allow this tool",
                    "trust",
                    "confirm",
                    "yes/no",
                    "(y/n)",
                    "press enter",
                )
                if not any(marker in text for marker in prompt_markers):
                    return
                log_agent(
                    self.agent_id,
                    f"{runner.log_prefix}_prompt_marker_seen",
                    level="warning",
                    role=self.role,
                    provider=runner.provider_name,
                    chunk_preview=shorten(chunk, 200),
                )

            def _reader(stream, name):
                try:
                    buf = []
                    last_flush = time.time()
                    while True:
                        ch = stream.read(1)
                        if ch == "":
                            if buf:
                                output_queue.put((name, "".join(buf)))
                            break
                        buf.append(ch)
                        now = time.time()
                        if ch in ("\n", "\r") or len(buf) >= 256 or now - last_flush >= 0.1:
                            output_queue.put((name, "".join(buf)))
                            buf = []
                            last_flush = now
                finally:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    output_queue.put((name, None))

            def _heartbeat():
                last_stage = ""
                while not heartbeat_stop.wait(15):
                    if proc.poll() is not None:
                        break
                    elapsed = int(time.time() - start_time)
                    out_len = sum(len(part) for part in stdout_parts)
                    err_len = sum(len(part) for part in stderr_parts)
                    stage = runner.heartbeat_message(out_len, err_len)
                    if stage == last_stage and elapsed < 30:
                        continue
                    last_stage = stage
                    push_event(self.agent_id, "agent_progress", {
                        "agent_id": self.agent_id,
                        "role": self.role,
                        "message": stage,
                        "elapsed": elapsed,
                        "stdout_chars": out_len,
                        "stderr_chars": err_len,
                    })
                    log_agent(
                        self.agent_id,
                        f"{runner.log_prefix}_heartbeat",
                        role=self.role,
                        provider=runner.provider_name,
                        elapsed=elapsed,
                        stdout_chars=out_len,
                        stderr_chars=err_len,
                        message=stage,
                    )

            threading.Thread(target=_reader, args=(proc.stdout, "stdout"), daemon=True).start()
            threading.Thread(target=_reader, args=(proc.stderr, "stderr"), daemon=True).start()
            threading.Thread(target=_heartbeat, daemon=True).start()

            deadline = time.time() + exec_timeout
            closed = set()
            while len(closed) < 2:
                if time.time() > deadline:
                    proc.kill()
                    raise subprocess.TimeoutExpired(cmd, exec_timeout)
                try:
                    name, chunk = output_queue.get(timeout=0.2)
                except queue.Empty:
                    if proc.poll() is not None and len(closed) >= 2:
                        break
                    continue
                if chunk is None:
                    closed.add(name)
                    continue
                if name == "stdout":
                    stdout_parts.append(chunk)
                    _maybe_answer_prompt(chunk)
                    event_chunk = runner.stream_chunk(chunk, "stdout")
                    log_agent(
                        self.agent_id,
                        f"{runner.log_prefix}_stdout_chunk",
                        role=self.role,
                        provider=runner.provider_name,
                        chunk_len=len(chunk),
                        chunk_preview=shorten(chunk, 200),
                    )
                    if event_chunk:
                        push_event(self.agent_id, runner.stdout_delta_event, {
                            "agent_id": self.agent_id,
                            "role": self.role,
                            "provider": runner.provider_name,
                            "chunk": event_chunk,
                        })
                else:
                    stderr_parts.append(chunk)
                    _maybe_answer_prompt(chunk)
                    event_chunk = runner.stream_chunk(chunk, "stderr")
                    log_agent(
                        self.agent_id,
                        f"{runner.log_prefix}_stderr_chunk",
                        level="warning",
                        role=self.role,
                        provider=runner.provider_name,
                        chunk_len=len(chunk),
                        chunk_preview=shorten(chunk, 200),
                    )
                    if event_chunk:
                        push_event(self.agent_id, runner.stderr_delta_event, {
                            "agent_id": self.agent_id,
                            "role": self.role,
                            "provider": runner.provider_name,
                            "chunk": event_chunk,
                        })

            proc.wait(timeout=5)
            heartbeat_stop.set()
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
            clean_stderr = runner.clean_error_output(stderr)
            elapsed = time.time() - start_time

            output = runner.clean_output(stdout or "")
            if not output:
                output = runner.fallback_output(stdout or "", clean_stderr)
            log_agent(
                self.agent_id,
                f"{runner.log_prefix}_process_finished",
                role=self.role,
                provider=runner.provider_name,
                returncode=proc.returncode,
                elapsed=round(elapsed, 2),
                stdout_chars=len(stdout or ""),
                stderr_chars=len(stderr or ""),
                output_chars=len(output or ""),
            )

            if self._stop_signaled:
                push_event(self.agent_id, runner.stopped_event, {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "provider": runner.provider_name,
                    "message": "执行已停止",
                    "status": "stopped",
                })
                log_agent(self.agent_id, f"{runner.log_prefix}_call_stopped", level="warning", role=self.role, provider=runner.provider_name, elapsed=round(elapsed, 2))
                return runner.stopped_message(elapsed)

            if runner.is_auth_error(output):
                msg = runner.auth_error_message(output)
                push_event(self.agent_id, "error", {
                    "agent_id": self.agent_id,
                    "provider": runner.provider_name,
                    "error": msg,
                })
                log_agent(self.agent_id, f"{runner.log_prefix}_auth_error", level="error", role=self.role, provider=runner.provider_name, error=shorten(msg, 300))
                return msg

            # If output is empty, surface stderr for debugging
            if not output:
                err_msg = clean_stderr
                if use_continue and runner.should_retry_without_resume(err_msg):
                    log_agent(
                        self.agent_id,
                        f"{runner.log_prefix}_continue_retry",
                        level="warning",
                        role=self.role,
                        provider=runner.provider_name,
                        stderr=shorten(err_msg, 500),
                    )
                    runner.clear_resume_state()
                    return self._call_claude(message, retry_without_continue=False)
                if err_msg:
                    push_event(self.agent_id, "error", {
                        "agent_id": self.agent_id,
                        "provider": runner.provider_name,
                        "error": err_msg[:500],
                    })
                    log_agent(self.agent_id, f"{runner.log_prefix}_empty_output_with_stderr", level="error", role=self.role, provider=runner.provider_name, stderr=shorten(err_msg, 500))
                    return f"[Error] {err_msg[:500]}"
                log_agent(self.agent_id, f"{runner.log_prefix}_empty_output", level="error", role=self.role, provider=runner.provider_name)
                return runner.empty_output_message()

            push_event(self.agent_id, runner.output_event, {
                "agent_id": self.agent_id,
                "role": self.role,
                "provider": runner.provider_name,
                "output": output,
                "elapsed": elapsed,
                "char_count": len(output),
            })
            if clean_stderr:
                push_event(self.agent_id, runner.error_event, {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "provider": runner.provider_name,
                    "output": clean_stderr,
                })

            runner.mark_success()

            return output

        except subprocess.TimeoutExpired as e:
            try:
                heartbeat_stop.set()
            except Exception:
                pass
            proc.kill()
            timeout_seconds = getattr(e, "timeout", exec_timeout) or exec_timeout
            msg = runner.timeout_message(timeout_seconds)
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "provider": runner.provider_name,
                "error": msg,
            })
            log_agent(self.agent_id, f"{runner.log_prefix}_timeout", level="error", role=self.role, provider=runner.provider_name, timeout=timeout_seconds)
            return msg
        except FileNotFoundError:
            msg = runner.not_found_message()
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "provider": runner.provider_name,
                "error": msg,
            })
            log_agent(self.agent_id, f"{runner.log_prefix}_not_found", level="error", role=self.role, provider=runner.provider_name)
            return msg
        except Exception as e:
            msg = f"[Error] {e}"
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "provider": runner.provider_name,
                "error": msg,
            })
            log_agent(self.agent_id, f"{runner.log_prefix}_call_exception", level="error", role=self.role, provider=runner.provider_name, error=str(e))
            return msg
        finally:
            try:
                heartbeat_stop.set()
            except Exception:
                pass
            with self._lock:
                self._process = None
            self._stop_signaled = False
            log_agent(self.agent_id, f"{runner.log_prefix}_call_cleanup", role=self.role, provider=runner.provider_name)

    @staticmethod
    def _should_retry_without_continue(stderr: str) -> bool:
        from .providers.claude_code import ClaudeCodeRunner

        return ClaudeCodeRunner._should_retry_without_continue(stderr)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "workspace_name": self.workspace_name,
            "provider": self.provider_runner.provider_name,
            "adapter_name": self.provider_runner.provider_name,
            "alive": True,
            "work_dir": self._agent_dir,
        }

    @staticmethod
    def _safe_workspace_name(name: str) -> str:
        clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(name or "").strip())
        clean = re.sub(r"\s+", "_", clean).strip("._ ")
        return clean[:80] or "agent"


class ClaudeRuntime(AgentRuntime):
    """Backward-compatible Claude runtime facade."""

    def __init__(self, agent_id: str, role: str, system_prompt: str,
                 workspace_name: str = ""):
        super().__init__(agent_id, role, system_prompt, workspace_name, provider_name="claude")
