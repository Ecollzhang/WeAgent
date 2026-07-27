"""Canonical built-in Tool capability definitions.

These definitions are the single source for platform-owned Tool capabilities.
They feed both the legacy AgentTool compatibility list and the DB-backed
Capability(type="tool") seed path.
"""

from copy import deepcopy


TOOL_STATUSES = {"implemented", "partial", "requires_config", "deferred"}


def _schema(properties=None, required=None):
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _text_output(extra=None):
    properties = {
        "status": {"type": "string"},
        "summary": {"type": "string"},
    }
    properties.update(extra or {})
    return _schema(properties)


def _markdown(title, when, usage, limits, example):
    return (
        f"# {title}\n\n"
        "## When to use\n"
        f"{when}\n\n"
        "## How to use\n"
        f"{usage}\n\n"
        "## Boundaries\n"
        f"{limits}\n\n"
        "## Example tool_call\n"
        "```json\n"
        f"{example}\n"
        "```\n"
    )


def _definition(
    value,
    name,
    category,
    icon,
    color,
    description,
    handler,
    tool_names,
    permissions,
    status,
    input_schema=None,
    output_schema=None,
    markdown=None,
    status_reason="",
    suggested_alternative="",
    visibility="visible",
    configurable=False,
    bindable=None,
    provider_types=None,
    config_schema=None,
):
    if bindable is None:
        bindable = status in {"implemented", "partial"}
    manifest = {
        "schema_version": "weagent.tool/v1",
        "runtime": "builtin",
        "handler": handler,
        "tool_names": list(tool_names),
        "tool": {
            "value": value,
            "name": name,
            "category": category,
            "icon": icon,
            "color": color,
            "description": description,
        },
        "input_schema": input_schema or _schema(),
        "output_schema": output_schema or _text_output(),
        "permissions": permissions,
        "audit": {
            "record_input": True,
            "record_output_summary": True,
            "sensitive_fields": ["headers.authorization", "headers.cookie", "token", "api_key"],
        },
        "ui": {
            "status": status,
            "visibility": visibility,
            "configurable": bool(configurable),
            "bindable": bool(bindable),
            "status_reason": status_reason,
            "suggested_alternative": suggested_alternative,
            "provider_types": list(provider_types or []),
            "config_schema": config_schema or {},
        },
    }
    return {
        "value": value,
        "name": name,
        "category": category,
        "icon": icon,
        "color": color,
        "description": description,
        "handler": handler,
        "tool_names": list(tool_names),
        "permissions": permissions,
        "status": status,
        "visibility": visibility,
        "configurable": bool(configurable),
        "bindable": bool(bindable),
        "manifest": manifest,
        "markdown": markdown or _markdown(
            name,
            description,
            f"Call `{tool_names[0]}` with the parameters described in the manifest.",
            "This is a platform-owned built-in Tool. Users can bind it to Agents but cannot edit its implementation.",
            '{"name":"' + tool_names[0] + '","args":{}}',
        ),
    }


BUILTIN_TOOL_DEFINITIONS = [
    _definition(
        value="code_generator",
        name="代码生成",
        category="tool_code",
        icon="el-icon-monitor",
        color="#3b82f6",
        description="AI 代码生成需要模型编排，当前不作为确定性内置 Tool 执行",
        handler="code.generate",
        tool_names=["code_generator"],
        permissions={"required": [], "optional": []},
        status="deferred",
        status_reason="需要模型/provider 编排，后续更适合做 Skill 或 Agent workflow。",
        suggested_alternative="使用代码类 Skill 指导 Agent 编写代码。",
        visibility="hidden",
        bindable=False,
    ),
    _definition(
        value="code_search",
        name="代码搜索",
        category="tool_code",
        icon="el-icon-search",
        color="#3b82f6",
        description="在 workspace 内搜索代码或文本片段",
        handler="code.search",
        tool_names=["code_search"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="implemented",
        input_schema=_schema(
            {
                "query": {"type": "string"},
                "path": {"type": "string", "default": ""},
                "max_results": {"type": "integer", "default": 50},
            },
            ["query"],
        ),
        output_schema=_schema({"matches": {"type": "array"}}),
        markdown=_markdown(
            "代码搜索",
            "当 Agent 需要定位函数、TODO、关键字、错误文本或配置项时使用。",
            "调用 `code_search`，传入 `query` 和可选 `path`。返回匹配文件、行号和文本片段。",
            "只读取 workspace 内文本文件；不会修改文件，也不会搜索 `.git`、`node_modules` 或 `.weagent` 缓存目录。",
            '{"name":"code_search","args":{"query":"TODO","path":"src","max_results":20}}',
        ),
    ),
    _definition(
        value="code_review",
        name="代码审查",
        category="tool_code",
        icon="el-icon-s-check",
        color="#6366f1",
        description="对单个文件执行确定性风险扫描",
        handler="code.review_scan",
        tool_names=["code_review_scan"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="implemented",
        input_schema=_schema({"path": {"type": "string"}}, ["path"]),
        output_schema=_schema({"findings": {"type": "array"}}),
        markdown=_markdown(
            "代码审查扫描",
            "当 Agent 需要快速检查一个文件里明显的 TODO、密钥样式文本或危险 API 时使用。",
            "调用 `code_review_scan`，传入 workspace 内文件路径。",
            "这是确定性扫描，不是 LLM 代码审查；它只报告规则命中的风险项。",
            '{"name":"code_review_scan","args":{"path":"src/app.py"}}',
        ),
    ),
    _definition(
        value="file_operations",
        name="文件操作",
        category="tool_file",
        icon="el-icon-document",
        color="#22c55e",
        description="读取、写入和列举 workspace 文件",
        handler="workspace.files",
        tool_names=["read_file", "write_file", "list_files"],
        permissions={"required": ["read_workspace"], "optional": ["write_workspace"]},
        status="implemented",
        input_schema=_schema({"path": {"type": "string"}}),
        output_schema=_text_output({"path": {"type": "string"}}),
        markdown=_markdown(
            "文件操作",
            "当 Agent 需要读取、创建、更新或列出 workspace 文件时使用。",
            "`read_file` 和 `list_files` 需要 `read_workspace`；`write_file` 需要 `write_workspace`。",
            "路径必须留在 workspace 内；写入只应发生在 Agent 被授权修改文件时。",
            '{"name":"read_file","args":{"path":"README.md"}}',
        ),
    ),
    _definition(
        value="document_parse",
        name="文档解析",
        category="tool_file",
        icon="el-icon-reading",
        color="#10b981",
        description="提取文本类文档内容",
        handler="document.text_extract",
        tool_names=["document_text_extract"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="implemented",
        input_schema=_schema({"path": {"type": "string"}, "max_chars": {"type": "integer"}}, ["path"]),
        output_schema=_schema({"text": {"type": "string"}, "truncated": {"type": "boolean"}}),
        markdown=_markdown(
            "文档文本提取",
            "当 Agent 需要读取 Markdown、TXT、JSON、CSV 等文本类资料时使用。",
            "调用 `document_text_extract`，传入文件路径和可选最大字符数。",
            "v1 不解析 PDF/Word 二进制文档；这些格式后续接专门依赖或 MCP。",
            '{"name":"document_text_extract","args":{"path":"docs/spec.md","max_chars":4000}}',
        ),
    ),
    _definition(
        value="web_search",
        name="网页搜索",
        category="tool_web",
        icon="el-icon-search",
        color="#8b5cf6",
        description="通用网页搜索需要搜索 provider 或 MCP 配置",
        handler="web.search",
        tool_names=["web_search"],
        permissions={"required": ["network"], "optional": []},
        status="requires_config",
        status_reason="缺少搜索 provider/MCP 配置时不能直接调用。",
        suggested_alternative="绑定一个搜索 MCP，或使用 http_fetch 抓取已知 URL。",
        configurable=True,
        bindable=False,
        provider_types=["http", "mcp"],
        config_schema=_schema(
            {
                "provider_type": {"type": "string", "enum": ["mcp", "http"]},
                "endpoint": {"type": "string"},
                "mcp_runtime_id": {"type": "string"},
                "tool_name": {"type": "string"},
                "secret_alias": {"type": "string"},
            }
        ),
    ),
    _definition(
        value="web_fetch",
        name="网页抓取",
        category="tool_web",
        icon="el-icon-download",
        color="#a855f7",
        description="抓取指定 HTTP/HTTPS URL 的文本预览",
        handler="web.http_fetch",
        tool_names=["http_fetch"],
        permissions={"required": ["network"], "optional": []},
        status="implemented",
        input_schema=_schema({"url": {"type": "string"}, "max_bytes": {"type": "integer"}}, ["url"]),
        output_schema=_schema({"status_code": {"type": "integer"}, "body_preview": {"type": "string"}}),
        markdown=_markdown(
            "网页抓取",
            "当 Agent 已经知道一个 URL 并需要读取其文本内容时使用。",
            "调用 `http_fetch`，传入 `url` 和可选 `max_bytes`。",
            "只允许 HTTP/HTTPS；输出会截断；不要把 token 放进 URL query。",
            '{"name":"http_fetch","args":{"url":"https://example.com","max_bytes":20000}}',
        ),
    ),
    _definition(
        value="api_client",
        name="API调用",
        category="tool_web",
        icon="el-icon-connection",
        color="#7c3aed",
        description="调用明确指定的 HTTP API",
        handler="web.api_request",
        tool_names=["api_request"],
        permissions={"required": ["network"], "optional": ["use_secret"]},
        status="implemented",
        input_schema=_schema(
            {
                "url": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "headers": {"type": "object"},
                "body": {"type": "string"},
            },
            ["url"],
        ),
        output_schema=_schema({"status_code": {"type": "integer"}, "body_preview": {"type": "string"}}),
        markdown=_markdown(
            "API 调用",
            "当 Agent 需要调用一个明确 URL 的 GET/POST API 时使用。",
            "调用 `api_request`，默认 GET。需要密钥时必须额外授权 `use_secret`。",
            "审计只记录脱敏摘要；不要在普通参数里直接写入密钥。",
            '{"name":"api_request","args":{"url":"https://api.example.com/items","method":"GET"}}',
        ),
    ),
    _definition(
        value="data_analysis",
        name="数据分析",
        category="tool_data",
        icon="el-icon-data-analysis",
        color="#14b8a6",
        description="对 CSV、JSON、SQLite 文件执行轻量只读分析",
        handler="data.local_profile",
        tool_names=["csv_profile", "json_query", "sqlite_query_readonly"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="implemented",
        input_schema=_schema({"path": {"type": "string"}}),
        output_schema=_schema({"summary": {"type": "object"}}),
        markdown=_markdown(
            "本地数据分析",
            "当 Agent 需要查看 CSV 列、JSON 字段或 SQLite 只读查询时使用。",
            "根据文件类型调用 `csv_profile`、`json_query` 或 `sqlite_query_readonly`。",
            "只读取 workspace 文件；SQLite 仅允许 SELECT 和 PRAGMA table_info。",
            '{"name":"csv_profile","args":{"path":"data/users.csv"}}',
        ),
    ),
    _definition(
        value="database_query",
        name="数据库查询",
        category="tool_data",
        icon="el-icon-coin",
        color="#0d9488",
        description="外部数据库查询需要 DB profile 和只读权限配置",
        handler="data.database_query",
        tool_names=["database_query"],
        permissions={"required": ["read_workspace"], "optional": ["use_secret"]},
        status="requires_config",
        status_reason="外部数据库连接需要 DB profile、secret 管理和只读策略。",
        suggested_alternative="对 workspace 内 SQLite 文件使用 sqlite_query_readonly。",
        configurable=True,
        bindable=False,
        provider_types=["database"],
        config_schema=_schema(
            {
                "driver": {"type": "string", "enum": ["sqlite", "mysql", "postgres"]},
                "connection_alias": {"type": "string"},
                "readonly": {"type": "boolean"},
                "allowed_schemas": {"type": "array"},
                "allowed_tables": {"type": "array"},
                "max_rows": {"type": "integer"},
                "timeout_seconds": {"type": "integer"},
                "secret_alias": {"type": "string"},
            }
        ),
    ),
    _definition(
        value="image_info",
        name="图像信息",
        category="tool_image",
        icon="el-icon-picture",
        color="#ec4899",
        description="读取本地图像文件的格式、大小和尺寸",
        handler="image.info",
        tool_names=["image_info"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="implemented",
        input_schema=_schema({"path": {"type": "string"}}, ["path"]),
        output_schema=_schema({"format": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}}),
        markdown=_markdown(
            "图像信息",
            "当 Agent 需要确认 workspace 内图像文件格式、大小或宽高时使用。",
            "调用 `image_info`，传入图像路径。",
            "v1 不做 OCR、物体识别或图像理解；这些应由模型或 MCP 提供。",
            '{"name":"image_info","args":{"path":"assets/logo.png"}}',
        ),
    ),
    _definition(
        value="image_analysis",
        name="图像分析",
        category="tool_image",
        icon="el-icon-picture",
        color="#ec4899",
        description="AI 图像理解需要模型或专用 MCP",
        handler="image.analysis",
        tool_names=["image_analysis"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="requires_config",
        status_reason="图像理解需要视觉模型 provider 或 MCP 配置。",
        suggested_alternative="配置视觉模型/MCP；仅需元信息时使用 image_info。",
        configurable=True,
        bindable=False,
        provider_types=["mcp", "model"],
        config_schema=_schema(
            {
                "provider_type": {"type": "string", "enum": ["mcp", "model"]},
                "model": {"type": "string"},
                "mcp_runtime_id": {"type": "string"},
                "tool_name": {"type": "string"},
                "secret_alias": {"type": "string"},
            }
        ),
    ),
    _definition(
        value="image_generation",
        name="图像生成",
        category="tool_image",
        icon="el-icon-picture-outline",
        color="#db2777",
        description="AI 图像生成需要模型 provider 或专用 MCP 配置",
        handler="image.generate",
        tool_names=["image_generate"],
        permissions={"required": ["write_workspace"], "optional": ["network", "use_secret"]},
        status="requires_config",
        status_reason="图像生成需要 provider/MCP 配置和输出文件写入权限。",
        suggested_alternative="配置图像生成 provider/MCP；仅需查看图片元信息时使用 image_info。",
        configurable=True,
        bindable=False,
        provider_types=["mcp", "model"],
        config_schema=_schema(
            {
                "provider_type": {"type": "string", "enum": ["mcp", "model"]},
                "model": {"type": "string"},
                "mcp_runtime_id": {"type": "string"},
                "tool_name": {"type": "string"},
                "output_format": {"type": "string", "enum": ["png", "jpg", "webp"]},
                "secret_alias": {"type": "string"},
            }
        ),
    ),
    _definition(
        value="terminal",
        name="终端执行",
        category="tool_sys",
        icon="el-icon-monitor",
        color="#f59e0b",
        description="执行受限安全命令",
        handler="system.run_command_safe",
        tool_names=["run_command_safe"],
        permissions={"required": ["run_command"], "optional": ["read_workspace"]},
        status="implemented",
        input_schema=_schema({"command": {"type": "string"}, "timeout": {"type": "integer"}}, ["command"]),
        output_schema=_schema({"exit_code": {"type": "integer"}, "stdout": {"type": "string"}, "stderr": {"type": "string"}}),
        markdown=_markdown(
            "受限终端执行",
            "当 Agent 需要执行明确、安全、短时的诊断命令时使用。",
            "调用 `run_command_safe`。v1 只允许 allowlist 命令，并限制 timeout、cwd 和输出长度。",
            "不能执行 shell 链接符、删除、移动、网络下载或包安装等高风险命令。",
            '{"name":"run_command_safe","args":{"command":"echo hello","timeout":10}}',
        ),
    ),
    _definition(
        value="git_operations",
        name="Git操作",
        category="tool_sys",
        icon="el-icon-share",
        color="#d97706",
        description="读取 Git 状态、差异和日志",
        handler="git.readonly",
        tool_names=["git_status", "git_diff", "git_log"],
        permissions={"required": ["read_workspace"], "optional": []},
        status="implemented",
        input_schema=_schema({"path": {"type": "string"}}),
        output_schema=_schema({"stdout": {"type": "string"}, "exit_code": {"type": "integer"}}),
        markdown=_markdown(
            "Git 只读操作",
            "当 Agent 需要检查当前修改、diff 或最近提交时使用。",
            "调用 `git_status`、`git_diff` 或 `git_log`。",
            "v1 只读；不支持 commit、push、checkout、branch mutation。",
            '{"name":"git_status","args":{}}',
        ),
    ),
    _definition(
        value="rag_search",
        name="知识库检索",
        category="tool_web",
        icon="el-icon-collection",
        color="#06b6d4",
        description="搜索知识库中的文档内容，返回相关文本片段",
        handler="rag.search",
        tool_names=["rag_search"],
        permissions={"required": ["network"], "optional": []},
        status="implemented",
        input_schema=_schema(
            {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "domain": {"type": "string", "default": ""},
                "workspace_id": {"type": "string", "default": ""},
                "score_threshold": {"type": "number", "default": 0.0},
            },
            ["query"],
        ),
        output_schema=_schema({
            "query": {"type": "string"},
            "results": {"type": "array"},
            "total": {"type": "integer"},
        }),
        markdown=_markdown(
            "知识库检索",
            "当 Agent 需要从知识库中查找相关文档、参考资料或技术方案时使用。用户上传的文档、网页等内容会被分块存储，本工具通过语义搜索找到最相关的文本片段。",
            "调用 `rag_search`，传入 `query` 和可选的 `domain`（领域过滤）、`workspace_id`（工作空间过滤）、`top_k`（返回数量）、`score_threshold`（最低相似度阈值）。",
            "只搜索已确认存储（status=ready）的文档；domain 可选值为 rd(研发)、edu(教育)、office(办公)；结果按相似度降序排列。",
            '{"name":"rag_search","args":{"query":"微服务架构最佳实践","top_k":3,"domain":"rd"}}',
        ),
    ),
]


def get_builtin_tool_definitions():
    return deepcopy(BUILTIN_TOOL_DEFINITIONS)


def get_builtin_tool_definition(value):
    for item in BUILTIN_TOOL_DEFINITIONS:
        if item["value"] == value:
            return deepcopy(item)
    return None


def builtin_tools_for_legacy_view():
    tools = []
    for item in BUILTIN_TOOL_DEFINITIONS:
        if item.get("visibility") == "hidden":
            continue
        tool = item["manifest"]["tool"]
        tools.append({
            "value": item["value"],
            "name": item["name"],
            "category": item["category"],
            "icon": tool["icon"],
            "color": tool["color"],
            "description": item["description"],
        })
    return tools
