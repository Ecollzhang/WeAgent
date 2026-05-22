from app.models.agent import Agent
from app.models.agent_category import AgentCategory


# ── System templates (no user_id) ─────────────────────────────────────
SYSTEM_CATEGORIES = [
    {'id': 'cat_doc',    'name': '文档',     'icon': 'el-icon-document',       'color': '#22c55e'},
    {'id': 'cat_code',   'name': '编程',     'icon': 'el-icon-monitor',        'color': '#3b82f6'},
    {'id': 'cat_test',   'name': '测试',     'icon': 'el-icon-s-check',        'color': '#f59e0b'},
    {'id': 'cat_design', 'name': '设计',     'icon': 'el-icon-brush',          'color': '#ec4899'},
    {'id': 'cat_data',   'name': '数据分析', 'icon': 'el-icon-data-analysis',  'color': '#14b8a6'},
]

SYSTEM_AGENTS = [
    # ── 文档 ──
    {'id': '_doc_1', 'name': '文档撰写助手', 'class_id': 'cat_doc', 'avatar_color': '#22c55e',
     'adapter_name': 'claude',
     'system_prompt': '你是一个专业的文档撰写专家，擅长编写技术文档、API文档和用户手册。注重文档结构清晰、语言准确。',
     'skill': '1. 确认文档类型和受众\n2. 收集相关技术资料和需求\n3. 编写文档大纲\n4. 逐章节撰写内容\n5. 审核校对和格式调整',
     'capability_tags': ['文档生成', '技术写作', 'Markdown', 'API文档', '用户手册']},
    {'id': '_doc_2', 'name': '技术文案编辑', 'class_id': 'cat_doc', 'avatar_color': '#10b981',
     'adapter_name': 'claude',
     'system_prompt': '负责技术文案的编辑和润色，确保技术内容准确且易于理解。擅长中英文技术翻译。',
     'skill': '1. 接收待编辑的文案内容\n2. 检查技术术语准确性\n3. 优化语句通顺度和逻辑\n4. 统一格式和风格\n5. 输出最终版本',
     'capability_tags': ['文案编辑', '翻译', '技术校对', '内容优化']},
    {'id': '_doc_3', 'name': 'README生成器', 'class_id': 'cat_doc', 'avatar_color': '#059669',
     'adapter_name': 'opencode',
     'system_prompt': '分析代码仓库结构，自动生成高质量的README文档，包括项目简介、安装步骤、使用说明和API文档。',
     'skill': '1. 分析项目目录结构\n2. 识别技术栈和依赖\n3. 提取关键模块说明\n4. 生成README各章节\n5. 格式化输出Markdown',
     'capability_tags': ['README', '项目文档', '自动化', '代码分析']},
    # ── 编程 ──
    {'id': '_code_1', 'name': 'Python开发助手', 'class_id': 'cat_code', 'avatar_color': '#3b82f6',
     'adapter_name': 'claude',
     'system_prompt': 'Python全栈开发专家，精通Web开发、数据处理和自动化脚本。提供高质量的代码实现和最佳实践建议。',
     'skill': '1. 理解需求描述和功能目标\n2. 设计代码架构和模块划分\n3. 编写可维护的Python代码\n4. 添加错误处理和日志\n5. 编写测试用例验证',
     'capability_tags': ['Python', 'Web开发', '数据处理', '自动化', '后端']},
    {'id': '_code_2', 'name': '前端开发专家', 'class_id': 'cat_code', 'avatar_color': '#8b5cf6',
     'adapter_name': 'codex',
     'system_prompt': '精通Vue、React等前端框架，擅长UI组件开发、性能优化和跨端适配。注重代码质量和用户体验。',
     'skill': '1. 分析UI设计稿或需求\n2. 确定组件树和数据流\n3. 编写组件代码和样式\n4. 对接API和数据绑定\n5. 调试和优化性能',
     'capability_tags': ['前端', 'Vue', 'React', 'TypeScript', 'CSS']},
    {'id': '_code_3', 'name': '代码审查员', 'class_id': 'cat_code', 'avatar_color': '#6366f1',
     'adapter_name': 'claude',
     'system_prompt': '严格而专业的代码审查员，关注代码质量、安全性、性能和可维护性。提供建设性的改进建议。',
     'skill': '1. 接收待审查的代码\n2. 检查代码风格和规范\n3. 分析潜在bug和安全漏洞\n4. 评估性能和可维护性\n5. 输出审查报告和改进建议',
     'capability_tags': ['代码审查', '安全审计', '性能优化', '重构']},
    {'id': '_code_4', 'name': '全栈架构师', 'class_id': 'cat_code', 'avatar_color': '#4f46e5',
     'adapter_name': 'opencode',
     'system_prompt': '资深软件架构师，擅长系统设计、微服务架构和技术选型。帮助设计和构建可扩展的企业级应用。',
     'skill': '1. 梳理业务需求和约束条件\n2. 设计系统架构和技术选型\n3. 定义模块接口和数据流\n4. 评估扩展性和安全性\n5. 输出架构文档',
     'capability_tags': ['架构设计', '系统设计', '微服务', '技术选型', '后端']},
    # ── 测试 ──
    {'id': '_test_1', 'name': '测试工程师', 'class_id': 'cat_test', 'avatar_color': '#f59e0b',
     'adapter_name': 'claude',
     'system_prompt': '专业的测试工程师，擅长编写单元测试、集成测试和端到端测试。精通多种测试框架和测试策略。',
     'skill': '1. 分析需求文档和代码变更\n2. 设计测试用例和测试数据\n3. 编写自动化测试脚本\n4. 执行测试并记录结果\n5. 输出测试报告',
     'capability_tags': ['单元测试', '集成测试', '端到端', '测试框架']},
    {'id': '_test_2', 'name': '自动化测试专家', 'class_id': 'cat_test', 'avatar_color': '#d97706',
     'adapter_name': 'codex',
     'system_prompt': '专注于测试自动化的专家，设计高效的自动化测试方案，提升测试覆盖率和执行效率。',
     'skill': '1. 评估现有测试流程\n2. 选择自动化测试框架\n3. 搭建CI/CD测试流水线\n4. 编写自动化测试套件\n5. 监控测试覆盖率和执行结果',
     'capability_tags': ['自动化测试', 'CI/CD', '覆盖率', '性能测试']},
    # ── 设计 ──
    {'id': '_dsn_1', 'name': 'UI/UX设计师', 'class_id': 'cat_design', 'avatar_color': '#ec4899',
     'adapter_name': 'claude',
     'system_prompt': '创意UI/UX设计师，擅长界面设计、交互设计和设计系统。注重用户体验和视觉细节。',
     'skill': '1. 收集产品需求和用户反馈\n2. 梳理用户流程和信息架构\n3. 设计线框图和高保真原型\n4. 创建设计系统和组件库\n5. 输出设计规范文档',
     'capability_tags': ['UI设计', 'UX设计', '设计系统', '交互设计', 'Figma']},
    {'id': '_dsn_2', 'name': 'CSS样式大师', 'class_id': 'cat_design', 'avatar_color': '#db2777',
     'adapter_name': 'opencode',
     'system_prompt': '精通CSS/Sass/Tailwind等样式技术，擅长实现精美UI效果和响应式布局。将设计稿转化为高品质代码。',
     'skill': '1. 分析设计稿的视觉元素\n2. 规划样式结构和CSS方案\n3. 编写响应式样式代码\n4. 实现动画和交互效果\n5. 确保跨浏览器兼容性',
     'capability_tags': ['CSS', 'Tailwind', '响应式设计', '动画', 'Sass']},
    # ── 数据分析 ──
    {'id': '_data_1', 'name': '数据分析师', 'class_id': 'cat_data', 'avatar_color': '#14b8a6',
     'adapter_name': 'claude',
     'system_prompt': '专业数据分析师，擅长数据清洗、可视化和洞察提取。精通Python数据处理生态和BI工具。',
     'skill': '1. 明确分析目标和指标\n2. 收集和清洗数据\n3. 探索性数据分析和特征工程\n4. 构建分析模型和可视化\n5. 输出分析报告和洞察结论',
     'capability_tags': ['数据分析', '可视化', 'Python', 'SQL', '报表']},
    {'id': '_data_2', 'name': '数据库专家', 'class_id': 'cat_data', 'avatar_color': '#0d9488',
     'adapter_name': 'codex',
     'system_prompt': '数据库设计与优化专家，精通SQL优化、数据建模和数据库架构设计。处理大规模数据存储与查询。',
     'skill': '1. 分析数据模型和业务逻辑\n2. 设计数据库表结构和索引\n3. 编写和优化SQL查询\n4. 制定备份和恢复策略\n5. 监控性能并持续优化',
     'capability_tags': ['SQL', '数据建模', '数据库优化', '大数据']},
]

SYSTEM_LEGACY_AGENTS = [
    {'name': 'Codex', 'adapter_name': 'codex', 'avatar_url': '/static/avatars/codex.png',
     'system_prompt': 'You are Codex, an AI specialized in code generation and completion.',
     'capability_tags': ['代码补全', 'Python', 'JavaScript', 'TypeScript']},
    {'name': 'Claude Code', 'adapter_name': 'claude', 'avatar_url': '/static/avatars/claude.png',
     'system_prompt': 'You are Claude, an AI assistant specialized in software development.',
     'capability_tags': ['代码生成', '前端', '后端', 'Python', 'JavaScript', '架构设计']},
    {'name': 'OpenCode', 'adapter_name': 'opencode', 'avatar_url': '/static/avatars/opencode.png',
     'system_prompt': 'You are OpenCode, an AI specialized in open-source development.',
     'capability_tags': ['开源项目', '代码审查', '文档生成']},
]


class AgentService:
    """Agent business logic — fully user-scoped."""

    # ── Seed (system templates, no user_id) ───────────────────────────

    def seed_default_data(self):
        """Seed system categories and agents on first run."""
        for cat_data in SYSTEM_CATEGORIES:
            if not AgentCategory.query.get(cat_data['id']):
                AgentCategory(**cat_data).save()

        for agent_data in SYSTEM_AGENTS:
            if not Agent.query.get(agent_data['id']):
                Agent(agent_type='external', **agent_data).save()

        for agent_data in SYSTEM_LEGACY_AGENTS:
            if not Agent.query.filter_by(name=agent_data['name']).first():
                Agent(**agent_data).save()

    # ── Per-user copy on registration ─────────────────────────────────

    def copy_default_data_to_user(self, user_id):
        """
        Copy system categories and agents as user-specific records.
        The user can then freely modify their own copies.
        """
        # Copy categories
        new_cat_ids = {}
        for tmpl in SYSTEM_CATEGORIES:
            cat = AgentCategory(
                name=tmpl['name'], icon=tmpl['icon'], color=tmpl['color'],
                user_id=user_id,
            )
            cat.save()
            new_cat_ids[tmpl['id']] = cat.id

        # Copy agents — link to the new category IDs
        for tmpl in SYSTEM_AGENTS:
            old_cid = tmpl.get('class_id')
            agent = Agent(
                name=tmpl['name'],
                avatar_color=tmpl.get('avatar_color', ''),
                capability_tags=list(tmpl.get('capability_tags', [])),
                agent_type='external',
                adapter_name=tmpl.get('adapter_name', 'claude'),
                system_prompt=tmpl.get('system_prompt', ''),
                skill=tmpl.get('skill', ''),
                class_id=new_cat_ids.get(old_cid) if old_cid else None,
                user_id=user_id,
                is_public=False,
            )
            agent.save()

        # Copy legacy agents (no category)
        for tmpl in SYSTEM_LEGACY_AGENTS:
            existing = Agent.query.filter_by(name=tmpl['name'], user_id=user_id).first()
            if existing:
                continue
            agent = Agent(
                name=tmpl['name'],
                avatar_url=tmpl.get('avatar_url', ''),
                capability_tags=list(tmpl.get('capability_tags', [])),
                agent_type='external',
                adapter_name=tmpl.get('adapter_name', 'claude'),
                system_prompt=tmpl.get('system_prompt', ''),
                user_id=user_id,
                is_public=False,
            )
            agent.save()

    # ── Categories (user-scoped) ──────────────────────────────────────

    def get_categories(self, user_id):
        """Return categories belonging to the user."""
        cats = AgentCategory.query.filter_by(user_id=user_id).order_by(AgentCategory.created_at).all()
        result = []
        for cat in cats:
            d = cat.to_dict()
            d['agent_count'] = Agent.query.filter_by(class_id=cat.id, user_id=user_id).count()
            result.append(d)
        return result, None

    def create_category(self, user_id, name, icon=None, color=None):
        """Create a new category for the user."""
        cat = AgentCategory(
            name=name, icon=icon or 'el-icon-folder',
            color=color or '#a0aec0', user_id=user_id,
        )
        cat.save()
        return cat.to_dict(), None

    def update_category(self, category_id, user_id, **kwargs):
        """Update a category (owner only)."""
        cat = AgentCategory.query.filter_by(id=category_id, user_id=user_id).first()
        if not cat:
            return None, 'Category not found'
        allowed = {'name', 'icon', 'color'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(cat, k, v)
        cat.save()
        return cat.to_dict(), None

    def delete_category(self, category_id, user_id):
        """Delete a category (owner only); detach its agents."""
        cat = AgentCategory.query.filter_by(id=category_id, user_id=user_id).first()
        if not cat:
            return None, 'Category not found'
        Agent.query.filter_by(class_id=category_id, user_id=user_id).update({'class_id': None})
        cat.delete()
        return {'deleted': True}, None

    # ── Agents (user-scoped) ──────────────────────────────────────────

    def get_user_agents(self, user_id, class_id=None):
        """
        Return agents for a user, optionally filtered by category.
        """
        q = Agent.query.filter_by(user_id=user_id)
        if class_id:
            q = q.filter_by(class_id=class_id)
        agents = q.order_by(Agent.created_at.desc()).all()
        return [a.to_dict() for a in agents], None

    def get_agent_detail(self, agent_id):
        """Get agent detail by ID."""
        agent = Agent.query.get(agent_id)
        if not agent:
            return None, 'Agent not found'
        return agent.to_dict(), None

    def create_agent(self, user_id, name, capability_tags=None, agent_type='custom',
                     adapter_name='claude', config=None, system_prompt='',
                     skill='', avatar_color='', avatar_url='', class_id=None, is_public=False,
                     tool_ids=None):
        """Create a custom agent for a user."""
        agent = Agent(
            name=name,
            capability_tags=capability_tags or [],
            agent_type=agent_type,
            adapter_name=adapter_name,
            config=config or {},
            system_prompt=system_prompt,
            skill=skill,
            avatar_color=avatar_color,
            avatar_url=avatar_url,
            class_id=class_id,
            created_by=user_id,
            user_id=user_id,
            is_public=is_public,
            tool_ids=tool_ids or [],
        )
        agent.save()
        return agent.to_dict(), None

    def update_agent(self, agent_id, user_id, **kwargs):
        """Update an agent (owner only)."""
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, 'Agent not found'
        allowed = {'name', 'avatar_url', 'avatar_color', 'capability_tags',
                   'adapter_name', 'config', 'system_prompt', 'skill',
                   'class_id', 'is_public', 'tool_ids'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(agent, k, v)
        agent.save()
        return agent.to_dict(), None

    def delete_agent(self, agent_id, user_id):
        """Delete an agent (owner only)."""
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, 'Agent not found'
        agent.delete()
        return {'deleted': True}, None


agent_service = AgentService()
