from app.models.agent_tool import AgentTool


# ── Built-in tool templates ────────────────────────────────────────────
BUILTIN_TOOLS = [
    {'value': 'code_generator', 'name': '代码生成', 'category': 'tool_code',
     'icon': 'el-icon-monitor', 'color': '#3b82f6',
     'description': '根据需求自动生成高质量代码，支持多种编程语言'},
    {'value': 'code_review', 'name': '代码审查', 'category': 'tool_code',
     'icon': 'el-icon-s-check', 'color': '#6366f1',
     'description': '对代码进行静态分析，发现潜在问题和安全漏洞'},
    {'value': 'file_operations', 'name': '文件操作', 'category': 'tool_file',
     'icon': 'el-icon-document', 'color': '#22c55e',
     'description': '创建、读取、编辑和管理文件与目录'},
    {'value': 'document_parse', 'name': '文档解析', 'category': 'tool_file',
     'icon': 'el-icon-reading', 'color': '#10b981',
     'description': '解析 PDF、Word、Excel 等多种格式文档'},
    {'value': 'web_search', 'name': '网页搜索', 'category': 'tool_web',
     'icon': 'el-icon-search', 'color': '#8b5cf6',
     'description': '搜索互联网信息并返回结果摘要'},
    {'value': 'web_fetch', 'name': '网页抓取', 'category': 'tool_web',
     'icon': 'el-icon-download', 'color': '#a855f7',
     'description': '抓取指定网页内容并分析'},
    {'value': 'api_client', 'name': 'API调用', 'category': 'tool_web',
     'icon': 'el-icon-connection', 'color': '#7c3aed',
     'description': '发送 HTTP 请求调用外部 API'},
    {'value': 'data_analysis', 'name': '数据分析', 'category': 'tool_data',
     'icon': 'el-icon-data-analysis', 'color': '#14b8a6',
     'description': '对结构化数据进行统计、分析和可视化'},
    {'value': 'database_query', 'name': '数据库查询', 'category': 'tool_data',
     'icon': 'el-icon-coin', 'color': '#0d9488',
     'description': '执行 SQL 查询和操作数据库'},
    {'value': 'image_analysis', 'name': '图像分析', 'category': 'tool_image',
     'icon': 'el-icon-picture', 'color': '#ec4899',
     'description': '识别和分析图像中的物体、文字和场景'},
    {'value': 'terminal', 'name': '终端执行', 'category': 'tool_sys',
     'icon': 'el-icon-console', 'color': '#f59e0b',
     'description': '在系统终端中执行命令和脚本'},
    {'value': 'git_operations', 'name': 'Git操作', 'category': 'tool_sys',
     'icon': 'el-icon-share', 'color': '#d97706',
     'description': '执行 Git 版本控制操作'},
]

TOOL_CATEGORIES = [
    {'id': 'tool_code', 'name': '代码工具', 'icon': 'el-icon-monitor', 'color': '#3b82f6'},
    {'id': 'tool_file', 'name': '文件处理', 'icon': 'el-icon-document', 'color': '#22c55e'},
    {'id': 'tool_web',  'name': '网络工具', 'icon': 'el-icon-connection', 'color': '#8b5cf6'},
    {'id': 'tool_data', 'name': '数据工具', 'icon': 'el-icon-data-analysis', 'color': '#14b8a6'},
    {'id': 'tool_image','name': '图像工具', 'icon': 'el-icon-picture', 'color': '#ec4899'},
    {'id': 'tool_sys',  'name': '系统工具', 'icon': 'el-icon-setting', 'color': '#f59e0b'},
    {'id': 'tool_custom','name': '自定义工具', 'icon': 'el-icon-plus', 'color': '#a0aec0'},
]


class ToolService:
    """Tool business logic."""

    def seed_default_tools(self):
        """Seed built-in tools (no user_id)."""
        for tpl in BUILTIN_TOOLS:
            exist = AgentTool.query.filter_by(value=tpl['value'], is_builtin=True).first()
            if not exist:
                AgentTool(is_builtin=True, **tpl).save()

    def get_tools(self, user_id=None):
        """Return all tools visible to a user: builtins + user's custom tools."""
        q = AgentTool.query.filter(
            (AgentTool.is_builtin == True) | (AgentTool.user_id == user_id)
        )
        tools = q.order_by(AgentTool.is_builtin.desc(), AgentTool.created_at).all()
        return [t.to_dict() for t in tools], None

    def get_tool_detail(self, tool_id):
        """Get single tool by ID."""
        tool = AgentTool.query.get(tool_id)
        if not tool:
            return None, 'Tool not found'
        return tool.to_dict(), None

    def create_tool(self, user_id, name, value, category='tool_custom',
                    icon='el-icon-setting', color='#a0aec0',
                    description='', params=None):
        """Create a custom tool for the user."""
        exist = AgentTool.query.filter_by(value=value, user_id=user_id).first()
        if exist:
            return None, 'Tool value already exists'
        tool = AgentTool(
            name=name, value=value, category=category,
            icon=icon, color=color, description=description or '',
            params=params or {}, user_id=user_id, is_builtin=False,
        )
        tool.save()
        return tool.to_dict(), None

    def update_tool(self, tool_id, user_id, **kwargs):
        """Update a custom tool (owner only)."""
        tool = AgentTool.query.filter_by(id=tool_id, user_id=user_id).first()
        if not tool:
            return None, 'Tool not found or is built-in'
        allowed = {'name', 'value', 'category', 'icon', 'color', 'description', 'params'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(tool, k, v)
        tool.save()
        return tool.to_dict(), None

    def delete_tool(self, tool_id, user_id):
        """Delete a custom tool (owner only)."""
        tool = AgentTool.query.filter_by(id=tool_id, user_id=user_id).first()
        if not tool:
            return None, 'Tool not found or is built-in'
        tool.delete()
        return {'deleted': True}, None

    def resolve_tool_names(self, tool_ids):
        """Given a list of tool IDs, return list of {id, name, value} dicts."""
        if not tool_ids:
            return []
        tools = AgentTool.query.filter(AgentTool.id.in_(tool_ids)).all()
        tool_map = {t.id: t for t in tools}
        result = []
        for tid in tool_ids:
            t = tool_map.get(tid)
            if t:
                result.append({'id': t.id, 'name': t.name, 'value': t.value,
                               'icon': t.icon, 'color': t.color})
            else:
                result.append({'id': tid, 'name': tid, 'value': tid})
        return result


tool_service = ToolService()
