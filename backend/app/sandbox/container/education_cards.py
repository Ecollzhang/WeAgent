"""Pure projection of verified Education tool results into chat cards.

This module is shipped in both the host backend and the sandbox image.  It
must not import Flask, database models, or any module from the host ``app``
package.
"""


def education_card_from_tool_result(action, envelope):
    """Return one canonical Education card, or ``None`` when not applicable."""
    if not isinstance(envelope, dict):
        return None
    payload = (
        envelope.get("result")
        if isinstance(envelope.get("result"), dict)
        else envelope
    )
    action = str(action or envelope.get("tool_name") or "").strip()
    object_type = ""
    object_id = ""
    version_id = ""
    title = ""
    status = ""
    preview_kind = ""
    meta = {}

    if action in {"edu.course.create", "edu.course.context.get"}:
        course = (
            payload.get("course")
            if isinstance(payload.get("course"), dict)
            else payload
        )
        object_type = "course"
        object_id = str(course.get("id") or "")
        title = str(course.get("title") or "课程")
        status = str(course.get("status") or "active")
        meta = {"course_id": course.get("id")}
    elif action in {"edu.lesson.create", "edu.lesson.update"}:
        object_type = "lesson"
        object_id = str(payload.get("id") or "")
        title = str(payload.get("title") or "课时")
        status = str(payload.get("status") or "draft")
        meta = {
            "course_id": payload.get("course_id"),
            "duration_minutes": payload.get("duration_minutes"),
            "lesson_type_code": payload.get("lesson_type_code"),
        }
    elif action in {
        "edu.courseware.create",
        "edu.courseware.get",
        "edu.courseware.version.create",
    }:
        content = (
            payload.get("content")
            if isinstance(payload.get("content"), dict)
            else {}
        )
        version = (
            payload.get("version")
            if isinstance(payload.get("version"), dict)
            else {}
        )
        source = (
            version.get("source_json")
            if isinstance(version.get("source_json"), dict)
            else {}
        )
        kind = str(content.get("kind") or "")
        object_type = "lesson_plan" if kind == "lesson_plan" else "courseware"
        object_id = str(content.get("id") or "")
        version_id = str(
            version.get("id") or content.get("current_version_id") or ""
        )
        title = str(
            payload.get("title")
            or content.get("title")
            or source.get("title")
            or ("教案" if object_type == "lesson_plan" else "课件")
        )
        status = str(content.get("status") or "draft")
        preview_kind = kind
        meta = {
            "course_id": content.get("course_id"),
            "lesson_id": content.get("lesson_id"),
            "version_number": version.get("version_number"),
            "version_created_at": (
                version.get("created_at") or version.get("updated_at")
            ),
            "schema_name": version.get("schema_name"),
            "generated_formats": ["html", "pptx", "pdf"],
        }
        if source:
            slides = source.get("slides")
            theme = source.get("theme")
            if isinstance(slides, list):
                meta["slide_count"] = len(slides)
            if isinstance(theme, dict):
                meta["theme"] = theme.get("style")
    elif action == "edu.question_bank.upsert":
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        first = items[0] if items and isinstance(items[0], dict) else {}
        object_type = "question_bank"
        object_id = str(
            payload.get("batch_id")
            or first.get("id")
            or envelope.get("call_id")
            or ""
        )
        version_id = str(
            first.get("current_version_id")
            or first.get("version_id")
            or envelope.get("call_id")
            or ""
        )
        title = "题库内容"
        status = "draft"
        meta = {
            "course_id": first.get("course_id"),
            "question_count": len(items),
            "stimulus_count": len(payload.get("stimuli") or []),
        }
    elif action in {"edu.paper.compose", "edu.mock_exam.create"}:
        object_type = "assessment_paper"
        object_id = str(payload.get("id") or "")
        version_id = str(
            payload.get("current_version_id") or payload.get("version_id") or ""
        )
        title = str(payload.get("title") or "试卷")
        status = str(payload.get("status") or "draft")
        meta = {
            "course_id": payload.get("course_id"),
            "question_count": len(
                payload.get("items") or payload.get("questions") or []
            ),
        }
    elif action in {"edu.asset.attach", "edu.knowledge.resource.adopt"}:
        object_type = "knowledge_resource"
        object_id = str(payload.get("id") or "")
        version_id = str(
            payload.get("current_version_id") or payload.get("version_id") or ""
        )
        title = str(
            payload.get("title")
            or payload.get("original_filename")
            or "课程资料"
        )
        status = str(payload.get("status") or "ready")
        preview_kind = str(payload.get("media_type") or "")
        meta = {
            "course_id": payload.get("course_id"),
            "lesson_id": payload.get("lesson_id"),
        }
    elif action == "edu.submission_review.analysis.create":
        object_type = "assignment"
        object_id = str(payload.get("assignment_id") or "")
        version_id = str(
            payload.get("submission_version_id") or payload.get("version_id") or ""
        )
        title = "作业批改与反馈"
        status = str(payload.get("status") or "ready")
        meta = {
            "course_id": payload.get("course_id"),
            "submission_id": payload.get("submission_id"),
        }
    elif action in {"edu.student_insight.refresh", "edu.weakness.analyze"}:
        refresh = (
            payload.get("refresh")
            if isinstance(payload.get("refresh"), dict)
            else payload
        )
        items = refresh.get("items") if isinstance(refresh.get("items"), list) else []
        first = items[0] if items and isinstance(items[0], dict) else {}
        object_type = "student_insight"
        object_id = str(
            first.get("id")
            or refresh.get("snapshot_id")
            or refresh.get("id")
            or envelope.get("call_id")
            or ""
        )
        version_id = str(
            first.get("version_id")
            or refresh.get("version_id")
            or envelope.get("call_id")
            or ""
        )
        title = (
            "作业弱点分析"
            if action == "edu.weakness.analyze"
            else "学生画像与学情报告"
        )
        status = str(refresh.get("status") or "ready")
        meta = {
            "course_id": first.get("course_id") or refresh.get("course_id"),
            "student_count": len(items),
        }
    elif action == "edu.mind_map.create":
        object_type = "mind_map"
        object_id = str(payload.get("id") or "")
        version_id = str(
            payload.get("current_version_id") or payload.get("version_id") or ""
        )
        title = str(payload.get("title") or "课程思维导图")
        status = str(payload.get("status") or "draft")
        meta = {
            "course_id": payload.get("course_id"),
            "lesson_id": payload.get("lesson_id"),
        }

    if not object_type or not object_id:
        return None
    summary_bits = []
    if meta.get("version_number"):
        summary_bits.append(f"v{meta['version_number']}")
    if meta.get("slide_count") is not None:
        summary_bits.append(f"{meta['slide_count']} 页")
    if meta.get("question_count") is not None:
        summary_bits.append(f"{meta['question_count']} 题")
    if meta.get("duration_minutes"):
        summary_bits.append(f"{meta['duration_minutes']} 分钟")
    summary = " · ".join(summary_bits)
    return {
        "type": "education_card",
        "content": summary or "已写入智慧教育业务数据",
        "status": "done",
        "data": {
            "schema_version": "1.0",
            "object_type": object_type,
            "canonical_ref": {
                "object_id": object_id,
                "version_id": version_id or None,
            },
            "title": title,
            "summary": summary,
            "status": status,
            "meta": {
                key: value for key, value in meta.items()
                if value not in (None, "")
            },
            "preview_kind": preview_kind,
            "source_action": action,
        },
    }
