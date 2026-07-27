from datetime import timedelta


class EducationTestConfig:
    TESTING = True
    SERVICE_NAME = "weagent-edu-test"
    PORT = 5102
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://127.0.0.1:6379/15"
    EDUCATION_FEATURE_ENABLED = True


def test_education_service_health_is_available():
    from services.edu.app import create_edu_app

    app = create_edu_app(EducationTestConfig)
    response = app.test_client().get("/api/edu/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "domain": "edu",
        "port": 5102,
        "service": "weagent-edu-test",
        "status": "ok",
    }


def test_education_business_routes_require_a_token():
    from services.edu.app import create_edu_app

    app = create_edu_app(EducationTestConfig)
    response = app.test_client().get("/api/edu/courses")

    assert response.status_code == 401


def test_education_service_rejects_business_routes_when_feature_is_disabled():
    from services.edu.app import create_edu_app

    class DisabledEducationConfig(EducationTestConfig):
        EDUCATION_FEATURE_ENABLED = False

    app = create_edu_app(DisabledEducationConfig)
    response = app.test_client().get("/api/edu/courses")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Education feature is disabled"


def test_core_proxy_does_not_forward_disabled_education_requests(monkeypatch):
    from flask_jwt_extended import create_access_token

    from app import create_app, db
    from app.models.grayscale_config import GrayscaleConfig
    import app.controllers.domain_proxy_controller as proxy_controller

    core_app = create_app("testing")
    with core_app.app_context():
        feature = GrayscaleConfig.query.filter_by(
            config_key="feature.education.enabled",
            domain="edu",
        ).one()
        feature.enabled = False
        db.session.commit()
        token = create_access_token(identity="teacher-1")

    def unexpected_forward(*args, **kwargs):
        raise AssertionError("disabled Education traffic must not be forwarded")

    monkeypatch.setattr(proxy_controller.requests, "request", unexpected_forward)
    response = core_app.test_client().get(
        "/api/domain/edu/courses",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
