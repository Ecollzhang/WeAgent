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

from .events import push_event


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

    def start(self):
        """Set up agent workspace: create dirs, write agent.md, link settings."""
        agent_dir = self._agent_dir
        claude_dir = os.path.join(agent_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)

        # Write agent.md — this defines the agent's role for Claude Code
        agent_md_path = os.path.join(claude_dir, "agent.md")
        if not os.path.exists(agent_md_path):
            with open(agent_md_path, "w") as f:
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

    def _format_agent_md(self) -> str:
        """Format the agent.md file from the system prompt."""
        note = (
            "\n\n===== 文件创建方式 =====\n"
            "本系统允许你使用 Write 工具直接创建文件，"
            "所有工具调用已被设置为自动批准，无需请求权限。\n\n"
            f"你的私有工作目录是 /workspace/agents/{self.workspace_name}/。\n"
            "公共协作目录是 /workspace/shared/。\n"
            "请优先把自己的产出写入你的私有工作目录；需要给其他 Agent 共享的材料写入公共协作目录。\n"
            "你可以读取 /workspace/agents/ 下其他 Agent 的工作目录内容来协作。\n"
            "如果工具不可用，用以下格式输出：\n\n"
            f"## /workspace/agents/{self.workspace_name}/实际文件名.ext\n"
            "```\n"
            "文件内容\n"
            "```\n\n"
            "注意：\n"
            "- 不要请求批准——系统已自动批准\n"
            "- 输出完整的文件内容，不要截断\n"
            "- 写入完成后，在回复中说明已创建的文件\n"
            "========================"
        )
        return f"# {self.role}\n\n{self.system_prompt}\n{note}"

    def stop(self):
        """Signal the currently running process to stop."""
        self._stop_signaled = True
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

    # ---- claude -p call ----

    def _call_claude(self, message: str) -> str:
        """Run claude -p with the given message, capturing output.

        NOTE: No --print flag! Without --print, Claude can execute tools.
        Permissions in settings.local.json are set to 'allow': 'all',
        so tool calls (including Write) are auto-approved.
        """
        self._stop_signaled = False
        start_time = time.time()

        push_event(self.agent_id, "claude_started", {
            "agent_id": self.agent_id,
            "role": self.role,
            "message": "Claude Code started",
        })

        cmd = ["claude", "-p", message, "--dangerously-skip-permissions"]

        # Disable color/ANSI output for cleaner parsing
        env = os.environ.copy()
        env.update({
            "CLICOLOR": "0",
            "TERM": "dumb",
            "NO_COLOR": "1",
            "CLAUDE_NO_COLOR": "1",
            "FORCE_COLOR": "0",
        })

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self._agent_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            with self._lock:
                self._process = proc

            if proc.stdin:
                proc.stdin.close()

            stdout_parts = []
            stderr_parts = []
            output_queue = queue.Queue()

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

            threading.Thread(target=_reader, args=(proc.stdout, "stdout"), daemon=True).start()
            threading.Thread(target=_reader, args=(proc.stderr, "stderr"), daemon=True).start()

            deadline = time.time() + 600
            closed = set()
            while len(closed) < 2:
                if time.time() > deadline:
                    proc.kill()
                    raise subprocess.TimeoutExpired(cmd, 600)
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
                    push_event(self.agent_id, "claude_output_delta", {
                        "agent_id": self.agent_id,
                        "role": self.role,
                        "chunk": chunk,
                    })
                else:
                    stderr_parts.append(chunk)
                    push_event(self.agent_id, "claude_error_delta", {
                        "agent_id": self.agent_id,
                        "role": self.role,
                        "chunk": chunk,
                    })

            proc.wait(timeout=5)
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
            elapsed = time.time() - start_time

            # Clean ANSI escape codes from output
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', stdout or "")

            # Strip shell prompt artifacts
            output = re.sub(r'^>\s*', '', output, flags=re.MULTILINE)
            output = output.strip()

            if self._stop_signaled:
                push_event(self.agent_id, "claude_stopped", {
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "message": "执行已停止",
                    "status": "stopped",
                })
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
                return msg

            # If output is empty, surface stderr for debugging
            if not output:
                err_msg = stderr.strip() if stderr else ""
                if err_msg:
                    push_event(self.agent_id, "error", {
                        "agent_id": self.agent_id,
                        "error": err_msg[:500],
                    })
                    return f"[Error] {err_msg[:500]}"
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

            return output

        except subprocess.TimeoutExpired:
            proc.kill()
            msg = "[Error] Claude execution timed out (600s)"
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "error": msg,
            })
            return msg
        except FileNotFoundError:
            msg = "[Error] claude CLI not found. Check Docker image."
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "error": msg,
            })
            return msg
        except Exception as e:
            msg = f"[Error] {e}"
            push_event(self.agent_id, "error", {
                "agent_id": self.agent_id,
                "error": msg,
            })
            return msg
        finally:
            with self._lock:
                self._process = None
            self._stop_signaled = False

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
