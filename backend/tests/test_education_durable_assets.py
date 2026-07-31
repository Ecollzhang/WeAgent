from datetime import timedelta
from io import BytesIO

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import inspect, text
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import DataError

from services.edu.extensions import db


class DurableAssetTestConfig:
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
    EDUCATION_MAX_UPLOAD_BYTES = 1024 * 1024


@pytest.fixture()
def app():
    from services.edu.app import create_edu_app

    application = create_edu_app(DurableAssetTestConfig)
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


def headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=user_id)
    return {"Authorization": f"Bearer {token}"}


def create_course(client, teacher):
    return client.post(
        "/api/edu/courses",
        headers=teacher,
        json={
            "title": "Durable English",
            "subject_code": "high_school_english",
            "grade_band": "senior_high",
            "description": "Reading and writing",
        },
    ).get_json()


def add_student(client, teacher, student, course_id):
    invitation = client.post(
        f"/api/edu/courses/{course_id}/invitations",
        headers=teacher,
        json={},
    ).get_json()
    response = client.post(
        "/api/edu/invitations/accept",
        headers=student,
        json={"token": invitation["token"]},
    )
    assert response.status_code == 200


def create_lesson(client, teacher, course_id):
    return client.post(
        f"/api/edu/courses/{course_id}/lessons",
        headers=teacher,
        json={
            "title": "Narrative reading",
            "learning_domain": "reading",
            "theme_code": "growth",
            "text_genre_code": "narrative",
            "lesson_type_code": "reading",
            "duration_minutes": 45,
        },
    ).get_json()


def test_database_asset_upload_download_and_course_visibility(app):
    client = app.test_client()
    teacher = headers(app, "teacher")
    student = headers(app, "student")
    outsider = headers(app, "outsider")
    course = create_course(client, teacher)
    add_student(client, teacher, student, course["id"])

    uploaded = client.post(
        f"/api/edu/courses/{course['id']}/assets",
        headers=teacher,
        data={
            "title": "Source text",
            "purpose": "knowledge_resource",
            "visibility_scope": "course_teacher",
            "file": (BytesIO("A durable text".encode()), "source.txt"),
        },
        content_type="multipart/form-data",
    )

    assert uploaded.status_code == 201
    asset = uploaded.get_json()
    assert asset["storage_backend"] == "database"
    assert asset["byte_size"] == len("A durable text".encode())
    assert len(asset["sha256"]) == 64
    assert "blob_bytes" not in asset

    assert client.get(asset["download_url"], headers=student).status_code == 404
    assert client.get(asset["download_url"], headers=outsider).status_code == 404
    teacher_download = client.get(asset["download_url"], headers=teacher)
    assert teacher_download.status_code == 200
    assert teacher_download.data == "A durable text".encode()

    published = client.patch(
        f"/api/edu/assets/{asset['id']}",
        headers=teacher,
        json={"visibility_scope": "course_published"},
    )
    assert published.status_code == 200
    student_download = client.get(asset["download_url"], headers=student)
    assert student_download.status_code == 200
    assert student_download.data == "A durable text".encode()


def test_asset_binary_column_uses_mysql_longblob():
    from services.edu.asset_models import EducationAsset

    compiled = EducationAsset.__table__.c.blob_bytes.type.compile(
        dialect=mysql.dialect()
    )

    assert compiled.upper() == "LONGBLOB"


def test_asset_upload_maps_database_capacity_error_to_stable_business_error(
    app, monkeypatch
):
    client = app.test_client()
    teacher = headers(app, "teacher")
    course = create_course(client, teacher)

    def fail_with_database_capacity_error(**_kwargs):
        raise DataError(
            "INSERT INTO edu_assets",
            {},
            RuntimeError("Data too long for column 'blob_bytes'"),
        )

    monkeypatch.setattr(
        "services.edu.asset_routes.create_database_asset",
        fail_with_database_capacity_error,
    )

    response = client.post(
        f"/api/edu/courses/{course['id']}/assets",
        headers=teacher,
        data={"file": (BytesIO(b"x" * 70000), "normal-size.html")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert response.get_json() == {
        "error": "asset storage could not persist the uploaded file",
        "error_code": "asset_storage_capacity_exceeded",
    }


def test_agent_asset_write_maps_database_capacity_error_to_stable_business_error():
    from services.edu.tool_gateway import _error_parts

    error = DataError(
        "INSERT INTO edu_assets",
        {},
        RuntimeError("Data too long for column 'blob_bytes'"),
    )
    message, status_code, error_code = _error_parts(error)

    assert "storage" in message.lower()
    assert status_code == 422
    assert error_code == "asset_storage_capacity_exceeded"


def test_material_upload_is_database_owned_and_survives_source_path_loss(app):
    from services.edu.content_models import EducationMaterial
    from services.edu.asset_models import EducationAsset

    client = app.test_client()
    teacher = headers(app, "teacher")
    course = create_course(client, teacher)
    lesson = create_lesson(client, teacher, course["id"])

    response = client.post(
        f"/api/edu/lessons/{lesson['id']}/materials",
        headers=teacher,
        data={"file": (BytesIO(b"pptx-bytes"), "lesson.pptx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    material_payload = response.get_json()
    assert material_payload["asset_id"]
    with app.app_context():
        material = EducationMaterial.query.get(material_payload["id"])
        asset = EducationAsset.query.get(material.asset_id)
        assert asset.blob_bytes == b"pptx-bytes"
        assert not material.storage_path

    download = client.get(material_payload["download_url"], headers=teacher)
    assert download.status_code == 200
    assert download.data == b"pptx-bytes"


def test_legacy_material_can_be_adopted_then_opened_after_file_deletion(app, tmp_path):
    from services.edu.content_models import EducationMaterial
    from services.edu.asset_models import EducationAsset

    client = app.test_client()
    teacher = headers(app, "teacher")
    course = create_course(client, teacher)
    lesson = create_lesson(client, teacher, course["id"])
    legacy_path = tmp_path / "legacy.pdf"
    legacy_path.write_bytes(b"legacy-document")

    with app.app_context():
        material = EducationMaterial(
            course_id=course["id"],
            lesson_id=lesson["id"],
            owner_user_id="teacher",
            title="Legacy",
            original_filename="legacy.pdf",
            extension="pdf",
            mime_type="application/pdf",
            storage_path=str(legacy_path),
            file_size=legacy_path.stat().st_size,
        )
        db.session.add(material)
        db.session.commit()
        material_id = material.id

    adopted = client.post(
        f"/api/edu/materials/{material_id}/adopt",
        headers=teacher,
    )
    assert adopted.status_code == 200
    assert adopted.get_json()["asset_id"]
    legacy_path.unlink()

    download = client.get(
        f"/api/edu/materials/{material_id}/download",
        headers=teacher,
    )
    assert download.status_code == 200
    assert download.data == b"legacy-document"
    with app.app_context():
        assert EducationAsset.query.count() == 1


def test_existing_material_table_schema_upgrade_is_idempotent():
    from services.edu.app import create_edu_app
    from services.edu.schema_maintenance import migrate_existing_education_schema

    application = create_edu_app(DurableAssetTestConfig)
    with application.app_context():
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE edu_materials ("
                    "id VARCHAR(36) PRIMARY KEY, "
                    "storage_path VARCHAR(1000) NOT NULL"
                    ")"
                )
            )
        db.create_all()

        first = migrate_existing_education_schema()
        second = migrate_existing_education_schema()
        columns = {
            column["name"] for column in inspect(db.engine).get_columns("edu_materials")
        }

        assert first == [
            "edu_materials.asset_id",
            "edu_materials.asset_id_index",
        ]
        assert second == []
        assert "asset_id" in columns
