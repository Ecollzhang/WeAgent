from app.models.agent_tool import AgentTool
from app.services.builtin_tool_definitions import builtin_tools_for_legacy_view


# ── Built-in tool templates ────────────────────────────────────────────
BUILTIN_TOOLS = builtin_tools_for_legacy_view()

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
