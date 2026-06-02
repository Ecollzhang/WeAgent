from app import create_app, db
from app.models.user import User
from app.models.user_model_config import UserModelConfig
from app.services.settings_service import settings_service


class FakeSandboxManager:
    def update_model_config_for_user_sessions(self, _user_id, _env_vars):
        return {"status": "ok", "updated": []}


def _create_user():
    user = User(
        id="user-model-config",
        username="model-config",
        email="model-config@example.com",
        password_hash="hash",
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_custom_model_name_is_persisted_and_injected_as_effective_model(monkeypatch):
    app = create_app("testing")
    with app.app_context():
        monkeypatch.setattr("app.sandbox.get_manager", lambda: FakeSandboxManager())
        db.drop_all()
        db.create_all()
        user = _create_user()

        result, error = settings_service.save_model_config(
            user.id,
            {
                "api_key": "sk-test-custom-model-key",
                "model": "custom",
                "custom_model": "deepseek-v4-pro",
                "base_url": "https://api.example.com/v1/",
                "temperature": 0.2,
                "max_tokens": 8192,
            },
        )

        assert error is None
        saved = UserModelConfig.query.filter_by(user_id=user.id).one()
        assert saved.model == "custom"
        assert saved.custom_model == "deepseek-v4-pro"
        assert result["model"] == "custom"
        assert result["custom_model"] == "deepseek-v4-pro"
        assert result["effective_model"] == "deepseek-v4-pro"

        env_vars, env_error = settings_service.get_container_env_vars(user.id)
        assert env_error is None
        assert env_vars["ANTHROPIC_MODEL"] == "deepseek-v4-pro"
        assert env_vars["ANTHROPIC_BASE_URL"] == "https://api.example.com/v1"

        db.session.remove()
        db.drop_all()


def test_preset_model_ignores_custom_model_for_container_injection(monkeypatch):
    app = create_app("testing")
    with app.app_context():
        monkeypatch.setattr("app.sandbox.get_manager", lambda: FakeSandboxManager())
        db.drop_all()
        db.create_all()
        user = _create_user()

        result, error = settings_service.save_model_config(
            user.id,
            {
                "api_key": "sk-test-preset-model-key",
                "model": "qwen-plus",
                "custom_model": "deepseek-v4-pro",
            },
        )

        assert error is None
        assert result["model"] == "qwen-plus"
        assert result["custom_model"] == "deepseek-v4-pro"
        assert result["effective_model"] == "qwen-plus"

        env_vars, env_error = settings_service.get_container_env_vars(user.id)
        assert env_error is None
        assert env_vars["ANTHROPIC_MODEL"] == "qwen-plus"

        db.session.remove()
        db.drop_all()
