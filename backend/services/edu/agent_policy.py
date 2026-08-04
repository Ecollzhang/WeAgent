"""Trusted Education Agent role and service policy."""

from copy import deepcopy


EDUCATION_AGENT_MANIFESTS = {
    "_edu_1": {
        "allowed_education_roles": ["teacher"],
        "required_services": ["edu"],
        "optional_services": ["rag"],
        "capability_summary": ["课程读取", "课时与教案写入", "课程知识检索"],
    },
    "_edu_2": {
        "allowed_education_roles": ["teacher"],
        "required_services": ["edu"],
        "optional_services": ["rag"],
        "capability_summary": ["课件读取", "课件版本写入", "课程知识检索"],
    },
    "_edu_3": {
        "allowed_education_roles": ["teacher"],
        "required_services": ["edu"],
        "optional_services": ["rag"],
        "capability_summary": ["题库写入", "试卷组卷", "课程知识检索"],
    },
    "_edu_4": {
        "allowed_education_roles": ["teacher"],
        "required_services": ["edu"],
        "optional_services": [],
        "capability_summary": ["成绩读取", "学情刷新", "学生画像分析"],
    },
    "_edu_5": {
        "allowed_education_roles": ["student"],
        "required_services": ["edu"],
        "optional_services": [],
        "capability_summary": ["学习证据读取", "学习计划建议"],
    },
    "_edu_6": {
        "allowed_education_roles": ["student"],
        "required_services": ["edu"],
        "optional_services": [],
        "capability_summary": ["练习读取", "弱点分析", "模拟测评"],
    },
    "_edu_7": {
        "allowed_education_roles": ["student"],
        "required_services": ["edu"],
        "optional_services": ["rag"],
        "capability_summary": ["课程内容读取", "知识检索", "思维导图写入"],
    },
    "_edu_8": {
        "allowed_education_roles": ["teacher"],
        "required_services": ["edu", "rag"],
        "optional_services": [],
        "capability_summary": ["课程资料读取", "知识检索", "资料采纳"],
    },
    "_edu_9": {
        "allowed_education_roles": ["teacher"],
        "required_services": ["edu"],
        "optional_services": [],
        "capability_summary": ["教学内容读取", "目标—活动—评价一致性审校"],
    },
}

EDUCATION_AGENT_DISPLAY = {
    "_edu_1": {
        "name": "课程设计师",
        "category_id": "cat_edu_course",
        "category_name": "课程设计",
        "category_icon": "el-icon-document",
        "avatar_color": "#3b82f6",
        "adapter_name": "claude",
    },
    "_edu_2": {
        "name": "课件制作师",
        "category_id": "cat_edu_ware",
        "category_name": "课件制作",
        "category_icon": "el-icon-present",
        "avatar_color": "#22c55e",
        "adapter_name": "claude",
    },
    "_edu_3": {
        "name": "习题生成器",
        "category_id": "cat_edu_quiz",
        "category_name": "习题测评",
        "category_icon": "el-icon-edit-outline",
        "avatar_color": "#f59e0b",
        "adapter_name": "claude",
    },
    "_edu_4": {
        "name": "学情分析师",
        "category_id": "cat_edu_analytics",
        "category_name": "学情分析",
        "category_icon": "el-icon-data-analysis",
        "avatar_color": "#14b8a6",
        "adapter_name": "claude",
    },
    "_edu_5": {
        "name": "学习规划师",
        "category_id": "cat_edu_course",
        "category_name": "课程设计",
        "category_icon": "el-icon-document",
        "avatar_color": "#8b5cf6",
        "adapter_name": "claude",
    },
    "_edu_6": {
        "name": "练习教练",
        "category_id": "cat_edu_quiz",
        "category_name": "习题测评",
        "category_icon": "el-icon-edit-outline",
        "avatar_color": "#ec4899",
        "adapter_name": "claude",
    },
    "_edu_7": {
        "name": "笔记整理师",
        "category_id": "cat_edu_resource",
        "category_name": "教学资源",
        "category_icon": "el-icon-folder-opened",
        "avatar_color": "#6366f1",
        "adapter_name": "claude",
    },
    "_edu_8": {
        "name": "资料研究员",
        "category_id": "cat_edu_resource",
        "category_name": "教学资源",
        "category_icon": "el-icon-folder-opened",
        "avatar_color": "#0ea5e9",
        "adapter_name": "claude",
    },
    "_edu_9": {
        "name": "教学审校员",
        "category_id": "cat_edu_analytics",
        "category_name": "学情分析",
        "category_icon": "el-icon-data-analysis",
        "avatar_color": "#f97316",
        "adapter_name": "claude",
    },
}


class EducationAgentPolicyError(ValueError):
    def __init__(self, message, error_code="invalid_agent"):
        super().__init__(message)
        self.error_code = error_code


def agent_manifest(agent_id):
    manifest = EDUCATION_AGENT_MANIFESTS.get(str(agent_id or "").strip())
    return deepcopy(manifest) if manifest else None


def agents_for_role(role):
    return [
        {
            "id": agent_id,
            **deepcopy(EDUCATION_AGENT_DISPLAY[agent_id]),
            **deepcopy(manifest),
        }
        for agent_id, manifest in EDUCATION_AGENT_MANIFESTS.items()
        if role in manifest["allowed_education_roles"]
    ]


def resolve_agent_service_views(
    agent_ids,
    *,
    role,
    material_policy="course_only",
    rag_enabled=True,
):
    normalized = []
    for raw_id in agent_ids or []:
        agent_id = str(raw_id or "").strip()
        if agent_id and agent_id not in normalized:
            normalized.append(agent_id)
    if not normalized:
        raise EducationAgentPolicyError(
            "at least one Education Agent is required",
            "agent_required",
        )
    if len(normalized) > 9:
        raise EducationAgentPolicyError(
            "too many Education Agents selected",
            "agent_limit_exceeded",
        )
    allow_rag = (
        bool(rag_enabled)
        and material_policy in {"course_only", "authorized_knowledge"}
    )
    result = {}
    for agent_id in normalized:
        manifest = EDUCATION_AGENT_MANIFESTS.get(agent_id)
        if not manifest:
            raise EducationAgentPolicyError(
                f"Education Agent is not available: {agent_id}",
                "agent_not_available",
            )
        if role not in manifest["allowed_education_roles"]:
            raise EducationAgentPolicyError(
                f"Education Agent {agent_id} is not available for {role}",
                "agent_role_mismatch",
            )
        services = list(manifest["required_services"])
        if allow_rag:
            services.extend(manifest["optional_services"])
        if not rag_enabled:
            services = [name for name in services if name != "rag"]
        # Education is the only primary domain. RD/Office are never inferred.
        result[agent_id] = [
            name
            for name in ("edu", "rag")
            if name in services
        ]
    return result


def union_services(agent_service_views):
    return [
        name
        for name in ("edu", "rag")
        if any(
            name in services
            for services in (agent_service_views or {}).values()
        )
    ]
