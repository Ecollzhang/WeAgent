"""
WeAgent Sandbox — Docker 容器化多 Agent 沙箱

1 会话 = 1 Docker 容器，每个容器内运行 Orchestrator + Claude CLI。

宿主机关联:
  - DockerContainerManager - 管理容器生命周期
  - SandboxAPI - Flask 蓝图

容器内运行:
  - OrchestratorServer (Flask :8080)
  - 多个 ClaudeRuntime 进程 (持久 claude)
  - ToolRegistry (工具系统)
  - SessionPersistence (volume 持久化)

使用前需:
  1. 安装 Docker Desktop
  2. 构建镜像: python -c "from app.sandbox import build_image; build_image()"
  3. 启动后端: flask run
"""

from .host.manager import DockerContainerManager, SessionContainer
from .api.routes import sandbox_bp


def get_manager() -> DockerContainerManager:
    from .api.routes import _mgr
    return _mgr()


def build_image():
    """Build the Docker sandbox image (call once before using)."""
    import os
    mgr = get_manager()
    dockerfile_dir = os.path.join(os.path.dirname(__file__))
    mgr.build_image(dockerfile_dir=dockerfile_dir)


__all__ = [
    "DockerContainerManager",
    "SessionContainer",
    "sandbox_bp",
    "get_manager",
    "build_image",
]
