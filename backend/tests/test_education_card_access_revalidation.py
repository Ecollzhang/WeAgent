from app.services.message_service import _sanitize_education_card_elements


def test_revoked_course_access_hides_historical_card_identity_and_summary():
    message = {
        "content": "Agent completed the task",
        "elements": [
            {"type": "text", "content": "completed"},
            {
                "type": "education_card",
                "content": "v3 · 8 页",
                "status": "done",
                "data": {
                    "object_type": "courseware",
                    "canonical_ref": {
                        "object_id": "secret-courseware",
                        "version_id": "secret-version",
                    },
                    "title": "Private lesson slides",
                    "summary": "v3 · 8 页",
                    "meta": {"course_id": "course-revoked"},
                },
            },
        ],
    }

    sanitized = _sanitize_education_card_elements(message, allowed=False)

    assert sanitized["elements"][0] == message["elements"][0]
    card = sanitized["elements"][1]
    assert card["data"] == {
        "access_revoked": True,
        "title": "课程访问权限已失效",
        "summary": "重新加入课程后可查看该产物",
    }
    assert "secret-courseware" not in str(sanitized)
    assert "Private lesson slides" not in str(sanitized)


def test_active_course_access_preserves_card_projection():
    message = {
        "elements": [
            {
                "type": "education_card",
                "data": {"title": "Visible slides"},
            }
        ]
    }

    assert _sanitize_education_card_elements(message, allowed=True) == message
