"""
container.agent — ClaudeRuntime wrapper using claude -p CLI.

Each agent runs in its own workspace directory with its own .claude/agent.md
for role definition. Uses subprocess to invoke `claude -p` non-interactively.
"""

import os
import queue
import re
import subprocess
import threading
import time
from typing import Optional

from .claude_config import claude_env, trust_projects, write_settings
from .events import push_event
from .logging_utils import log_agent, shorten


class ClaudeRuntime:
    """
    Wraps claude -p CLI calls for task execution.

    Each agent has its own workspace under /workspace/agents/{workspace_name}/
    with .claude/agent.md for role definition.
    """

    def __init__(self, agent_id: str, role: str, system_prompt: str,
                 workspace_name: str = ""):
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.workspace_name = self._safe_workspace_name(workspace_name or role or agent_id)
        self._stop_signaled = False
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._agent_dir = f"/workspace/agents/{self.workspace_name}"
        self._claude_session_marker = os.path.join(self._agent_dir, ".weagent_claude_session")

    def start(self):
        """Set up agent workspace: create dirs, write agent.md, link settings."""
        agent_dir = self._agent_dir
        log_agent(
            self.agent_id,
            "workspace_setup_start",
            role=self.role,
            workspace_name=self.workspace_name,
            work_dir=agent_dir,
        )
        claude_dir = os.path.join(agent_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        write_settings(
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
            os.environ.get("ANTHROPIC_BASE_URL", ""),
            os.environ.get("ANTHROPIC_MODEL", ""),
        )
        trust_projects(["/workspace", agent_dir])

        # Write agent.md — this defines the agent's role for Claude Code
        agent_md_path = os.path.join(claude_dir, "agent.md")
        claude_md_path = os.path.join(agent_dir, "CLAUDE.md")
        for prompt_path in (agent_md_path, claude_md_path):
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(self._format_agent_md())

        # Link or copy shared settings.local.json from workspace root
        settings_src = "/workspace/.claude/settings.local.json"
        settings_dst = os.path.join(claude_dir, "settings.local.json")
        if os.path.exists(settings_src) and not os.path.exists(settings_dst):
            try:
                os.symlink(settings_src, settings_dst)
            except (OSError, NotImplementedError):
                # symlink may fail on some systems, copy instead
                import shutil
                shutil.copy2(settings_src, settings_dst)

        os.makedirs("/workspace/shared", exist_ok=True)
        log_agent(
            self.agent_id,
            "workspace_setup_done",
            role=self.role,
            workspace_name=self.workspace_name,
            work_dir=agent_dir,
        )

    def _format_agent_md(self) -> str:
        """Format the agent.md file from the system prompt."""
        note = f"""

===== WeAgent 工作与实时上报规范 =====
你的私有工作目录是 /workspace/agents/{self.workspace_name}/。
公共协作目录是 /workspace/shared/。
你可以读取 /workspace/agents/ 下其他 Agent 的工作目录内容来协作。

你必须使用 Bash 调用 weagent-report 向前端实时汇报进度和结果。
执行任务前先上报计划；每个步骤开始前上报 progress；步骤完成后上报 result；生成文件后上报 file；生成图片后上报 image；出错时上报 error。

weagent-report 只接受一个 JSON 字符串参数：
weagent-report '{{"type":"progress","title":"分析需求","content":"正在确认任务范围","status":"running","step_id":"step-1"}}'

上报类型：progress、result、text、table、image、code、file、error。
table 固定格式：{{"type":"table","title":"标题","data":{{"headers":["列1"],"rows":[["值1"]]}}}}。
image/file 只允许上报容器内 /workspace/... 路径。
大段代码可以用 code 块上报；如果用户要求生成项目或可运行产物，必须把代码写入文件，再上报 file/image。

文件创建方式：优先使用 Claude Code 的 Write/Edit/Bash 工具直接创建文件。所有正式产物优先写入你的私有工作目录。
如果工具不可用，才使用下面格式输出文件内容，系统会尝试自动写入：

## /workspace/agents/{self.workspace_name}/实际文件名.ext
```
文件内容
```

不要请求批准，系统已自动批准工具调用。写入完成后必须上报对应 file/image。
========================
"""
        return f"# {self.role}\n\n{self.system_prompt}\n{note}"

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
        return self._call_claude(message)

    def send_with_context(self, message: str, context: str = "") -> str:
        """Send message with injected context from other agents."""
        parts = []
        if context:
            parts.append(f"## 其他 Agent 的输出上下文\n{context}\n")
        parts.append(message)
        full_message = "\n\n".join(parts)
        return self._call_claude(full_message)

    def _runtime_instruction(self) -> str:
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
2. 每个关键步骤开始时调用 progress；步骤完成时调用 result；写入文件后调用 file；生成图片后调用 image；出错时调用 error。
3. 用户要求生成前端、脚本、项目、文档或任何可运行产物时，绝大多数情况必须真实写入 /workspace/agents/{self.workspace_name}/ 下的文件，再上报 file/image。
4. image/file 只能上报容器内 /workspace/... 路径，不能上报宿主机路径、base64、data URL。
5. table 只能使用 data.headers 和 data.rows：{{"type":"table","title":"标题","data":{{"headers":["列"],"rows":[["值"]]}}}}。
6. 大段代码可以用 code 上报到消息框；但可运行产物必须写入文件。
7. 如果你不知道下一步是否耗时，也要先上报 progress。

weagent-report 调用示例：
weagent-report '{{"type":"progress","title":"分析需求","content":"正在确认任务范围","status":"running","step_id":"step-1"}}'
weagent-report '{{"type":"result","title":"分析完成","content":"已确认实现范围","status":"done","step_id":"step-1"}}'
weagent-report '{{"type":"file","title":"产物文件","content":"/workspace/agents/{self.workspace_name}/index.html","data":{{"path":"/workspace/agents/{self.workspace_name}/index.html"}}}}'

{moderator_rule}
下面才是用户任务。先上报 progress，再开始处理。
""".strip()


    # ---- claude -p call ----

    def _call_claude(self, message: str, retry_without_continue: bool = True) -> str:
        """Run claude -p with the given message, capturing output.

        Claude Code runs in non-interactive bypass mode because there is no
        frontend path for approving container-local tool prompts.
        """
        self._stop_signaled = False
        start_time = time.time()
        exec_timeout = int(os.environ.get("CLAUDE_EXEC_TIMEOUT_SECONDS", "7200"))
        log_agent(
            self.agent_id,
            "claude_call_start",
            role=self.role,
            workspace_name=self.workspace_name,
            message_len=len(message or ""),
            message_preview=shorten(message, 300),
            timeout=exec_timeout,
        )

        push_event(self.agent_id, "claude_started", {
            "agent_id": self.agent_id,
            "role": self.role,
            "message": "Claude Code started",
        })

        full_message = f"{self._runtime_instruction()}\n\n用户任务：\n{message}"
        use_continue = retry_without_continue and os.path.exists(self._claude_session_marker)
        cmd = ["claude"]
        if use_continue:
            cmd.append("-c")
        cmd.extend([
            "-p",
            full_message,
            "--permission-mode",
            "bypassPermissions",
            "--dangerously-skip-permissions",
        ])
        log_agent(
            self.agent_id,
            "claude_context_mode",
            role=self.role,
            use_continue=use_continue,
            marker=self._claude_session_marker,
        )

        # Disable color/ANSI output for cleaner parsing
        env = os.environ.copy()
        env.update({
            **claude_env(),
            "WEAGENT_AGENT_ID": self.agent_id,
            "WEAGENT_WORKSPACE_NAME": self.workspace_name,
        })

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
                "claude_process_started",
                role=self.role,
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
                    "claude_prompt_marker_seen",
                    level="warning",
                    role=self.role,
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
                    if out_len or err_len:
                        stage = f"Claude Code still running, streamed {out_len} chars"
                    else:
                        stage = "Claude Code is thinking or using tools"
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
                        "claude_heartbeat",
                        role=self.role,
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
                    log_agent(
                        self.agent_id,
                        "claude_stdout_chunk",
                        role=self.role,
                        chunk_len=len(chunk),
                        chunk_preview=shorten(chunk, 200),
                    )
                    push_event(self.agent_id, "claude_output_delta", {
                        "agent_id": self.agent_id,
                        "role": self.role,
                        "chunk": chunk,
                    })
                else:
                    stderr_parts.append(chunk)
                    _maybe_answer_prompt(chunk)
                    log_agent(
                        self.agent_id,
                        "claude_stderr_chunk",
                        level="warning",
                        role=self.role,
                        chunk_len=len(chunk),
                        chunk_preview=shorten(chunk, 200),
                    )
                    push_event(self.agent_id, "claude_error_delta", {
                        "agent_id": self.agent_id,
                        "role": self.role,
                        "chunk": chunk,
                    })

            proc.wait(timeout=5)
            heartbeat_stop.set()
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
            elapsed = time.time() - start_time

            # Clean ANSI escape codes from output
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', stdout or "")

            # Strip shell prompt artifacts
            output = re.sub(r'^>\s*', '', output, flags=re.MULTILINE)
            output = output.strip()
            log_agent(
                self.agent_id,
                "claude_process_finished",
                role=self.role,
                returncode=proc.returncode,
                elapsed=round(elapsed, 2),
                stdout_chars=len(stdout or ""),
                stderr_chars=len(stderr or ""),
                output_chars=len(output or ""),
            )

            if self._stop_signaled:
                push_event(self.agent_id, "claude_stopped", {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "message": "执行已停止",
                    "status": "stopped",
                })
                log_agent(self.agent_id, "claude_call_stopped", level="warning", role=self.role, elapsed=round(elapsed, 2))
                return f"[Stopped] 执行已停止（{elapsed:.0f}s）"

            auth_error_patterns = (
                "Not logged in",
                "Please run /login",
                "Invalid API key",
                "ANTHROPIC_API_KEY",
            )
            if any(pattern in output for pattern in auth_error_patterns):
                msg = f"[AuthError] {output}"
                push_event(self.agent_id, "error", {
                    "agent_id": self.agent_id,
                    "error": msg,
                })
                log_agent(self.agent_id, "claude_auth_error", level="error", role=self.role, error=shorten(msg, 300))
                return msg

            # If output is empty, surface stderr for debugging
            if not output:
                err_msg = stderr.strip() if stderr else ""
                if use_continue and self._should_retry_without_continue(err_msg):
                    log_agent(
                        self.agent_id,
                        "claude_continue_retry",
                        level="warning",
                        role=self.role,
                        stderr=shorten(err_msg, 500),
                    )
                    try:
                        os.remove(self._claude_session_marker)
                    except OSError:
                        pass
                    return self._call_claude(message, retry_without_continue=False)
                if err_msg:
                    push_event(self.agent_id, "error", {
                        "agent_id": self.agent_id,
                        "error": err_msg[:500],
                    })
                    log_agent(self.agent_id, "claude_empty_output_with_stderr", level="error", role=self.role, stderr=shorten(err_msg, 500))
                    return f"[Error] {err_msg[:500]}"
                log_agent(self.agent_id, "claude_empty_output", level="error", role=self.role)
                return "[Error] No output from Claude"

            push_event(self.agent_id, "claude_output", {
                "agent_id": self.agent_id,
                "role": self.role,
                "output": output,
                "elapsed": elapsed,
                "char_count": len(output),
            })
            if stderr and stderr.strip():
                push_event(self.agent_id, "claude_error", {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "output": stderr.strip(),
                })

            try:
                with open(self._claude_session_marker, "w", encoding="utf-8") as f:
                    f.write(str(time.time()))
            except OSError as e:
                log_agent(self.agent_id, "claude_session_marker_failed", level="warning", role=self.role, error=str(e))

            return output

        except subprocess.TimeoutExpired:
            try:
                heartbeat_stop.set()
            except Exception:
                pass
            proc.kill()
            timeout_seconds = getattr(e, "timeout", exec_timeout) or exec_timeout
            msg = f"[Error] Claude execution timed out ({timeout_seconds}s)"
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "error": msg,
            })
            log_agent(self.agent_id, "claude_timeout", level="error", role=self.role, timeout=timeout_seconds)
            return msg
        except FileNotFoundError:
            msg = "[Error] claude CLI not found. Check Docker image."
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "error": msg,
            })
            log_agent(self.agent_id, "claude_not_found", level="error", role=self.role)
            return msg
        except Exception as e:
            msg = f"[Error] {e}"
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "error": msg,
            })
            log_agent(self.agent_id, "claude_call_exception", level="error", role=self.role, error=str(e))
            return msg
        finally:
            try:
                heartbeat_stop.set()
            except Exception:
                pass
            with self._lock:
                self._process = None
            self._stop_signaled = False
            log_agent(self.agent_id, "claude_call_cleanup", role=self.role)

    @staticmethod
    def _should_retry_without_continue(stderr: str) -> bool:
        text = (stderr or "").lower()
        retry_markers = (
            "no conversation",
            "conversation not found",
            "could not continue",
            "cannot continue",
            "no previous",
            "unknown option",
            "invalid option",
        )
        return any(marker in text for marker in retry_markers)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "workspace_name": self.workspace_name,
            "alive": True,
            "work_dir": self._agent_dir,
        }

    @staticmethod
    def _safe_workspace_name(name: str) -> str:
        clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(name or "").strip())
        clean = re.sub(r"\s+", "_", clean).strip("._ ")
        return clean[:80] or "agent"
