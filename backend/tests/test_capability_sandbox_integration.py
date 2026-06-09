from app import create_app, db
from app.models.agent import Agent
from app.models.user import User
from app.sandbox.host import manager as manager_module
from app.sandbox.host.manager import DockerContainerManager
from app.services.capability_service import capability_service


def test_manager_projects_capabilities_before_creating_container_agents(monkeypatch):
    app = create_app("testing")
    events = []

    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            id="user-1",
            username="toolset-user",
            email="toolset@example.com",
            password_hash="hash",
        )
        agent = Agent(
            id="agent-1",
            name="Reviewer",
            agent_type="custom",
            adapter_name="claude",
            user_id=user.id,
            created_by=user.id,
        )
        db.session.add_all([user, agent])
        db.session.commit()
        skill, error = capability_service.create_skill(
            user_id=user.id,
            name="Runtime Skill",
            markdown="# Runtime Skill",
        )
        assert error is None
        result, error = capability_service.bind_to_agent(
            agent_id=agent.id,
            capability_version_id=skill["latest_version"]["id"],
            granted_permissions=[],
        )
        assert error is None

        class FakeContainer:
            id = "container-1234567890"
            labels = {}
            attrs = {"NetworkSettings": {"Ports": {}}}

        class FakeContainers:
            def run(self, **_kwargs):
                return FakeContainer()

            def list(self, **_kwargs):
                return []

        class FakeDocker:
            containers = FakeContainers()

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def health_check(self):
                return {"status": "ok"}

            def apply_capability_projection(self, projection):
                events.append(("projection", projection))
                return {"status": "ok"}

        manager = DockerContainerManager()
        manager._docker = FakeDocker()
        monkeypatch.setattr(manager, "ensure_image", lambda: True)
        monkeypatch.setattr(manager, "_wait_for_ready", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(
            manager,
            "_create_agent_in_container",
            lambda _port, cfg: events.append(("create_agent", cfg["agent_id"])),
        )
        monkeypatch.setattr(manager_module, "OrchestratorClient", FakeClient)
        ports = iter([18080, 13000, 15173, 18000, 18081, 19000])
        monkeypatch.setattr(manager, "_find_free_port", lambda: next(ports))

        session = manager.create_session(
            "session-1",
            [{"agent_id": agent.id, "role": agent.name, "system_prompt": ""}],
            env_vars={},
        )

        assert session.session_id == "session-1"
        assert events[0][0] == "projection"
        assert events[0][1]["agents"][agent.id]["skill_index"][0]["capability_id"] == skill["id"]
        assert events[1] == ("create_agent", agent.id)

        db.session.remove()
        db.drop_all()
