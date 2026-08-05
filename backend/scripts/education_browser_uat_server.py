"""Local-only browser harness for the compiled Education UI.

It serves the production frontend bundle and the real Education Flask API from
one disposable in-memory process. The bootstrap token is test-only and expires
with the process; no repository or environment credential is exposed.
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

from flask import jsonify, request, send_from_directory
from flask_jwt_extended import create_access_token


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
FRONTEND_DIST = REPOSITORY_ROOT / "frontend" / "dist"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.edu.app import create_edu_app
from services.edu.extensions import db


class BrowserUATConfig:
    TESTING = False
    SERVICE_NAME = "weagent-edu-browser-uat"
    PORT = 5182
    SECRET_KEY = "browser-uat-secret"
    JWT_SECRET_KEY = "browser-uat-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = "redis://127.0.0.1:6379/15"
    EDUCATION_FEATURE_ENABLED = True


class EducationPrefixRewrite:
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        prefix = "/api/domain/edu"
        if path == prefix or path.startswith(f"{prefix}/"):
            environ["PATH_INFO"] = f"/api/edu{path[len(prefix):]}"
        return self.application(environ, start_response)


app = create_edu_app(BrowserUATConfig)
app.wsgi_app = EducationPrefixRewrite(app.wsgi_app)


@app.get("/api/grayscale/config")
def grayscale_config():
    domain = request.args.get("domain", "")
    rows = []
    if domain == "edu":
        rows.append(
            {
                "config_key": "feature.education.enabled",
                "enabled": True,
                "visible": True,
                "domains": ["edu"],
            }
        )
    return jsonify({"code": 200, "data": rows})


@app.get("/uat/bootstrap")
def bootstrap():
    with app.app_context():
        token = create_access_token(identity="browser-uat-teacher")
    return jsonify(
        {
            "access_token": token,
            "user": {"id": "browser-uat-teacher", "username": "UAT Teacher"},
        }
    )


@app.get("/", defaults={"asset_path": ""})
@app.get("/<path:asset_path>")
def frontend(asset_path):
    candidate = FRONTEND_DIST / asset_path
    if asset_path and candidate.is_file():
        return send_from_directory(FRONTEND_DIST, asset_path)
    return send_from_directory(FRONTEND_DIST, "index.html")


def seed_courses():
    client = app.test_client()
    with app.app_context():
        db.create_all()
        token = create_access_token(identity="browser-uat-teacher")
    headers = {"Authorization": f"Bearer {token}"}
    for payload in (
        {
            "title": "高中英语：叙事阅读与写作",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
            "description": "阅读证据、结构分析与续写表达。",
        },
        {
            "title": "小学语文：寓言阅读与表达",
            "subject_code": "primary_chinese",
            "grade_band": "primary",
            "description": "按寓言文体组织阅读、复述和改写。",
        },
    ):
        response = client.post("/api/edu/courses", headers=headers, json=payload)
        if response.status_code != 201:
            raise RuntimeError(f"failed to seed browser UAT course: {response.status_code}")


if __name__ == "__main__":
    if not (FRONTEND_DIST / "index.html").is_file():
        raise SystemExit("frontend/dist/index.html is missing; run the production build first")
    seed_courses()
    app.run(host="127.0.0.1", port=5182, debug=False, use_reloader=False)
