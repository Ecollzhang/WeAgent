import pytest

from app.sandbox.host.manager import DockerContainerManager


def test_agent_workspace_path_resolves_bare_filename_inside_private_workspace():
    assert DockerContainerManager._normalize_agent_workspace_path(
        "_edu_2",
        "slide_document.json",
        "课件制作师",
    ) == "/workspace/agents/课件制作师/slide_document.json"


def test_agent_workspace_path_accepts_its_own_absolute_path_only():
    own_path = "/workspace/agents/课件制作师/preview.html"
    assert DockerContainerManager._normalize_agent_workspace_path(
        "_edu_2",
        own_path,
        "课件制作师",
    ) == own_path

    with pytest.raises(ValueError, match="inside the agent workspace"):
        DockerContainerManager._normalize_agent_workspace_path(
            "_edu_2",
            "/workspace/shared/preview.html",
            "课件制作师",
        )

    with pytest.raises(ValueError, match="inside the agent workspace"):
        DockerContainerManager._normalize_agent_workspace_path(
            "_edu_2",
            "../shared/preview.html",
            "课件制作师",
        )
