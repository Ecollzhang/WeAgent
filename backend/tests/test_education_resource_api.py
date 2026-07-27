from datetime import timedelta

from flask_jwt_extended import create_access_token

from services.edu.app import create_edu_app
from services.edu.extensions import db


class Config:
    TESTING = True
    SERVICE_NAME = "weagent-edu-resource-test"
    PORT = 5102
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://127.0.0.1:6379/15"
    EDUCATION_FEATURE_ENABLED = True


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


class PipelineProbe:
    def __init__(self):
        self.calls = []

    def research(self, query, *, scope, limit):
        self.calls.append((query, scope, limit))
        return {
            "query": query,
            "provider_index": 0,
            "results": [{"title": "Fetched result", "score": 0.9}],
            "diagnostics": [],
            "fallback_exhausted": False,
        }


def test_resource_search_scope_comes_from_membership_and_has_unconfigured_fallback():
    app = create_edu_app(Config)
    with app.app_context():
        db.create_all()
    client = app.test_client()
    teacher = _headers(app, "resource-teacher")
    outsider = _headers(app, "resource-outsider")
    course = client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "Scoped resources",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
        },
    ).get_json()

    fallback = client.post(
        "/api/edu/resources/search",
        headers=teacher,
        json={"query": "narrative lesson", "course_id": course["id"]},
    )
    assert fallback.status_code == 200
    assert fallback.get_json()["fallback_exhausted"] is True
    assert fallback.get_json()["diagnostics"][0]["status"] == "unconfigured"

    probe = PipelineProbe()
    app.config["EDUCATION_RESOURCE_PIPELINE"] = probe
    result = client.post(
        "/api/edu/resources/search",
        headers=teacher,
        json={
            "query": "narrative lesson",
            "course_id": course["id"],
            "course_ids": ["forged-course"],
            "user_id": "forged-user",
            "domain": "rd",
            "limit": 3,
        },
    )
    assert result.status_code == 200
    query, scope, limit = probe.calls[0]
    assert query == "narrative lesson"
    assert scope.user_id == "resource-teacher"
    assert scope.domain == "edu"
    assert scope.course_ids == (course["id"],)
    assert limit == 3

    assert client.post(
        "/api/edu/resources/search",
        headers=outsider,
        json={"query": "narrative lesson", "course_id": course["id"]},
    ).status_code == 404
    with app.app_context():
        db.session.remove()
        db.drop_all()
