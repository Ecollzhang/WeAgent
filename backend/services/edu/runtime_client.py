"""Adapter from Education workflow runs to the shared core Agent runtime."""

import json
import os
import re

import requests


class CoreRuntimeError(RuntimeError):
    """Raised when the shared core runtime rejects or cannot serve a run."""


def _validate_lesson_plan_artifact(payload):
    allowed_fields = {
        "subject_code",
        "learning_domain",
        "text_genre_code",
        "lesson_type_code",
        "title",
        "duration_minutes",
        "objectives",
        "stages",
    }
    required_fields = {
        "subject_code",
        "learning_domain",
        "text_genre_code",
        "lesson_type_code",
        "title",
        "objectives",
        "stages",
    }
    if (
        not required_fields.issubset(payload)
        or set(payload) - allowed_fields
        or payload.get("subject_code")
        not in {"high_school_english", "primary_chinese"}
        or payload.get("learning_domain")
        not in {"reading", "writing", "integrated"}
        or payload.get("lesson_type_code")
        not in {"reading", "writing", "reading_writing", "integrated"}
    ):
        raise CoreRuntimeError(
            "lesson plan artifact must use the canonical top-level schema"
        )
    objectives = payload.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        raise CoreRuntimeError(
            "lesson plan artifact objectives must be a non-empty object array"
        )
    for index, objective in enumerate(objectives):
        if (
            not isinstance(objective, dict)
            or set(objective) != {"id", "description"}
            or not str(objective.get("id") or "").strip()
            or not str(objective.get("description") or "").strip()
        ):
            raise CoreRuntimeError(
                "lesson plan artifact "
                f"objectives[{index}] requires only id and description"
            )
    stages = payload.get("stages")
    required_stage_fields = {
        "name",
        "duration_minutes",
        "teacher_activity",
        "student_activity",
        "assessment",
    }
    if not isinstance(stages, list) or not stages:
        raise CoreRuntimeError(
            "lesson plan artifact stages must be a non-empty object array"
        )
    for index, stage in enumerate(stages):
        if (
            not isinstance(stage, dict)
            or set(stage) != required_stage_fields
            or any(
                not str(stage.get(field) or "").strip()
                for field in required_stage_fields - {"duration_minutes"}
            )
        ):
            raise CoreRuntimeError(
                "lesson plan artifact "
                f"stages[{index}] must use the canonical stage fields"
            )
        try:
            if int(stage["duration_minutes"]) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise CoreRuntimeError(
                "lesson plan artifact "
                f"stages[{index}].duration_minutes must be positive"
            )


def _validate_exercise_artifact(payload):
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise CoreRuntimeError(
            "exercise artifact questions must contain at least one renderable question"
        )
    allowed_difficulties = {"easy", "medium", "hard"}
    allowed_types = {
        "single_choice",
        "multiple_choice",
        "fill_blank",
        "short_answer",
        "writing",
    }
    choice_types = {"single_choice", "multiple_choice"}
    for index, question in enumerate(questions):
        path = f"questions[{index}]"
        if not isinstance(question, dict):
            raise CoreRuntimeError(f"{path} must be an object")
        for field in ("id", "type", "prompt", "answer", "difficulty", "score"):
            if question.get(field) in (None, ""):
                raise CoreRuntimeError(f"{path}.{field} is required")
        if question["type"] not in allowed_types:
            raise CoreRuntimeError(f"{path}.type is unsupported")
        if question["difficulty"] not in allowed_difficulties:
            raise CoreRuntimeError(f"{path}.difficulty is unsupported")
        try:
            if float(question["score"]) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise CoreRuntimeError(f"{path}.score must be a positive number")
        if question["type"] in choice_types:
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise CoreRuntimeError(
                    f"{path}.options requires at least two choices"
                )
            for option_index, option in enumerate(options):
                if not isinstance(option, str) or not option.strip():
                    raise CoreRuntimeError(
                        f"{path}.options[{option_index}] must be plain text"
                    )
                if re.match(r"^[A-Z][.)、．:：]\s*", option.strip(), re.IGNORECASE):
                    raise CoreRuntimeError(
                        f"{path}.options[{option_index}] must be plain text "
                        "without A/B labels"
                    )


def _validate_slide_document(payload):
    allowed_root = {"title", "theme", "slides"}
    if (
        not isinstance(payload, dict)
        or set(payload) - allowed_root
        or not str(payload.get("title") or "").strip()
        or not isinstance(payload.get("theme"), dict)
        or not isinstance(payload.get("slides"), list)
        or not payload["slides"]
        or len(payload["slides"]) > 60
    ):
        raise CoreRuntimeError(
            "slide document requires only title, theme and 1-60 slides"
        )
    allowed_slide = {"id", "title", "layout", "blocks", "speaker_notes"}
    allowed_block = {
        "type",
        "content",
        "emphasis",
        "source_ref",
        "asset_id",
        "alt_text",
    }
    allowed_types = {
        "text",
        "bullets",
        "heading",
        "subheading",
        "quote",
        "key-point",
        "question",
        "tip",
        "image",
        "table",
        "timeline",
        "comparison",
        "vocabulary",
        "activity",
    }
    for index, slide in enumerate(payload["slides"]):
        path = f"slides[{index}]"
        if (
            not isinstance(slide, dict)
            or set(slide) - allowed_slide
            or any(
                not str(slide.get(field) or "").strip()
                for field in ("id", "title", "layout")
            )
            or not isinstance(slide.get("blocks"), list)
            or not slide["blocks"]
            or len(slide["blocks"]) > 30
        ):
            raise CoreRuntimeError(
                f"{path} requires id, title, layout, non-empty blocks and optional speaker_notes"
            )
        for block_index, block in enumerate(slide["blocks"]):
            block_path = f"{path}.blocks[{block_index}]"
            if (
                not isinstance(block, dict)
                or set(block) - allowed_block
                or block.get("type") not in allowed_types
                or "content" not in block
                or not isinstance(
                    block.get("content"),
                    (str, list, dict, int, float),
                )
            ):
                raise CoreRuntimeError(
                    f"{block_path} must use a supported type and renderable content"
                )


def validate_education_artifact(artifact_role, payload):
    if artifact_role == "course_designer":
        _validate_lesson_plan_artifact(payload)
    elif artifact_role == "exercise_generator":
        _validate_exercise_artifact(payload)
    elif artifact_role == "courseware_maker":
        _validate_slide_document(payload)
    return payload


class CoreRuntimeClient:
    """Small interface over core Conversation, sandbox and Message endpoints."""

    def __init__(self, base_url=None, timeout=180, agent_adapter=None):
        self.base_url = (
            base_url or os.getenv("CORE_SERVICE_URL", "http://127.0.0.1:5002")
        ).rstrip("/")
        self.timeout = timeout
        self.agent_adapter = agent_adapter or os.getenv(
            "EDUCATION_AGENT_ADAPTER", "codex"
        )

    @staticmethod
    def _payload(response):
        try:
            body = response.json()
        except ValueError as exc:
            raise CoreRuntimeError("core runtime returned a non-JSON response") from exc
        if response.status_code >= 400:
            message = body.get("message") or body.get("error") or "core runtime rejected request"
            raise CoreRuntimeError(message)
        if isinstance(body, dict) and "code" in body and "data" in body:
            return body["data"]
        return body

    def _request(self, method, path, authorization, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        if authorization:
            headers["Authorization"] = authorization
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise CoreRuntimeError(f"core runtime is unavailable: {exc}") from exc
        return self._payload(response)

    def start_workflow(
        self,
        *,
        authorization,
        title,
        prompt,
        agent_ids,
        workflow,
        education_run_grant=None,
    ):
        agent_configs = {}
        for agent_id in [*agent_ids, "moderator"]:
            config = {"adapter_name": self.agent_adapter}
            if education_run_grant:
                config["education_tool_context"] = {
                    "run_grant": education_run_grant
                }
            agent_configs[agent_id] = config
        conversation = self._request(
            "POST",
            "/api/conversations",
            authorization,
            json={
                "title": title,
                "type": "group",
                "participant_ids": [f"agent_{agent_id}" for agent_id in agent_ids],
                "kb_domain": "edu",
                "agent_configs": agent_configs,
            },
        )
        preflight = self._request(
            "GET",
            f"/api/conversations/{conversation['id']}/runtime-preflight",
            authorization,
            params={
                "required_tools": "education_action",
                "agent_ids": ",".join(agent_ids),
            },
        )
        if not preflight.get("ready"):
            try:
                self._request(
                    "DELETE",
                    f"/api/conversations/{conversation['id']}",
                    authorization,
                )
            except CoreRuntimeError:
                pass
            missing = ", ".join(preflight.get("missing_tools") or [])
            raise CoreRuntimeError(
                "Education Agent tool preflight failed"
                + (f": missing {missing}" if missing else "")
            )
        message = self._request(
            "POST",
            "/api/messages",
            authorization,
            json={
                "conversation_id": conversation["id"],
                "content": prompt,
                "workflow": workflow,
            },
        )
        return {
            "conversation_id": conversation["id"],
            "sandbox_session_id": conversation.get("sandbox_session_id"),
            "message_id": message["id"],
            "runtime_generation": (
                conversation.get("sandbox_runtime", {}).get("generation")
                or conversation.get("sandbox_generation")
                or 1
            ),
        }

    def get_snapshot(self, *, authorization, conversation_id):
        payload = self._request(
            "GET",
            f"/api/messages/conversation/{conversation_id}?page=1&per_page=100",
            authorization,
        )
        agent_runs = []
        for message in payload.get("items", []):
            if message.get("sender_type") != "agent":
                continue
            agent_runs.append(
                {
                    "agent_id": message.get("sender_id"),
                    "status": message.get("status"),
                    "content": message.get("content") or "",
                    "run_id": message.get("run_id"),
                    "elements": message.get("elements") or [],
                    "error": (message.get("meta") or {}).get("error"),
                }
            )
        return {"status": "running", "agent_runs": agent_runs}

    def get_user_profiles(self, *, authorization, user_ids):
        payload = self._request(
            "POST",
            "/api/auth/profiles",
            authorization,
            json={"user_ids": list(user_ids)},
        )
        return {
            item["id"]: item
            for item in payload.get("items", [])
            if isinstance(item, dict) and item.get("id")
        }

    def get_workspace_json(
        self, *, authorization, sandbox_session_id, path, artifact_role=None
    ):
        if not str(path or "").startswith("/workspace/shared/"):
            raise CoreRuntimeError("education artifacts must be read from /workspace/shared")
        headers = {"Authorization": authorization} if authorization else {}
        try:
            response = requests.request(
                "GET",
                f"{self.base_url}/api/sandbox/sessions/{sandbox_session_id}/files/raw",
                headers=headers,
                params={"path": path},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise CoreRuntimeError(f"core runtime is unavailable: {exc}") from exc
        if response.status_code >= 400:
            raise CoreRuntimeError(f"education artifact is unavailable: {path}")
        try:
            payload = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise CoreRuntimeError(f"education artifact is not valid JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise CoreRuntimeError(f"education artifact must contain a JSON object: {path}")
        return validate_education_artifact(artifact_role, payload)

    def repair_workspace_json(
        self,
        *,
        authorization,
        sandbox_session_id,
        agent_id,
        path,
        validation_error,
        artifact_role=None,
    ):
        """Ask the producing Agent to repair its own invalid structured artifact once."""
        self._request(
            "POST",
            f"/api/sandbox/sessions/{sandbox_session_id}/send",
            authorization,
            json={
                "agent_id": agent_id,
                "message": (
                    "结构化输出校验器发现你生成的 JSON 无法解析。\n"
                    f"文件：{path}\n"
                    f"错误：{validation_error}\n"
                    "请修复 JSON（包括未转义引号、尾逗号或截断内容），"
                    "覆盖写回同一路径。不要改变字段语义；完成后只简短确认。"
                ),
            },
        )
        return self.get_workspace_json(
            authorization=authorization,
            sandbox_session_id=sandbox_session_id,
            path=path,
            artifact_role=artifact_role,
        )
