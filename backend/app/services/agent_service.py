from app.models.agent import Agent
from app.models.agent_category import AgentCategory

MODERATOR_SYSTEM_PROMPT = '''你是 WeAgent 的主持 Agent，负责多 Agent 会话的任务理解、直接回答、任务拆分、调度和汇总。

你的调度输出必须遵循后端传入的 JSON 协议：
1. 如果你根据当前团队信息可以直接回答用户问题，输出 type=answer，不要创建任务。
2. 如果你不能直接回答，或任务需要 worker 执行，输出 type=plan，并只安排必要的 worker。
3. type=plan 时 tasks 必须至少有 1 个元素；type=answer 时 tasks 可以省略或为空数组。
4. 不要编造 agent_id，只能使用后端提供的 worker_agents。
5. summary 是给用户看的主持说明，应清楚说明你知道什么、要安排谁做什么。

当用户询问“群里都有谁、各自能做什么”时：
- 如果 worker_agents 已提供名称、能力标签或 skill，你应直接回答。
- 如果能力信息不足，你应说明“我知道群里有哪些 agent，但不清楚他们具体能干啥，我帮你问一下他们”，然后生成任务让相关 worker 自我介绍。'''


# ── System templates (no user_id) ─────────────────────────────────────
SYSTEM_CATEGORIES = {
    'rd': [
        {'id': 'cat_rd_doc',    'name': '文档',     'icon': 'el-icon-document',       'color': '#22c55e', 'domain': 'rd'},
        {'id': 'cat_rd_code',   'name': '编程',     'icon': 'el-icon-monitor',        'color': '#3b82f6', 'domain': 'rd'},
        {'id': 'cat_rd_test',   'name': '测试',     'icon': 'el-icon-s-check',        'color': '#f59e0b', 'domain': 'rd'},
        {'id': 'cat_rd_design', 'name': '设计',     'icon': 'el-icon-brush',          'color': '#ec4899', 'domain': 'rd'},
        {'id': 'cat_rd_data',   'name': '数据分析', 'icon': 'el-icon-data-analysis',  'color': '#14b8a6', 'domain': 'rd'},
    ],
    'edu': [
        {'id': 'cat_edu_course',    'name': '课程设计', 'icon': 'el-icon-document',       'color': '#3b82f6', 'domain': 'edu'},
        {'id': 'cat_edu_ware',      'name': '课件制作', 'icon': 'el-icon-present',        'color': '#22c55e', 'domain': 'edu'},
        {'id': 'cat_edu_quiz',      'name': '习题测评', 'icon': 'el-icon-edit-outline',   'color': '#f59e0b', 'domain': 'edu'},
        {'id': 'cat_edu_analytics', 'name': '学情分析', 'icon': 'el-icon-data-analysis',  'color': '#14b8a6', 'domain': 'edu'},
        {'id': 'cat_edu_resource',  'name': '教学资源', 'icon': 'el-icon-folder-opened',  'color': '#8b5cf6', 'domain': 'edu'},
    ],
    'office': [
        {'id': 'cat_office_doc',      'name': '公文写作', 'icon': 'el-icon-document',  'color': '#3b82f6', 'domain': 'office'},
        {'id': 'cat_office_meeting',  'name': '会议管理', 'icon': 'el-icon-date',      'color': '#22c55e', 'domain': 'office'},
        {'id': 'cat_office_report',   'name': '报表分析', 'icon': 'el-icon-data-line', 'color': '#14b8a6', 'domain': 'office'},
        {'id': 'cat_office_email',    'name': '邮件通讯', 'icon': 'el-icon-message',   'color': '#8b5cf6', 'domain': 'office'},
        {'id': 'cat_office_schedule', 'name': '日程管理', 'icon': 'el-icon-time',      'color': '#f59e0b', 'domain': 'office'},
    ],
}

# Flattened list for iteration
def _all_system_categories():
    for cats in SYSTEM_CATEGORIES.values():
        for c in cats:
            yield c

SYSTEM_AGENTS = [
    {'id': 'moderator', 'name': '任务主持人', 'class_id': 'cat_rd_doc', 'avatar_color': '#f59e0b',
     'adapter_name': 'claude',
     'system_prompt': '''你是 WeAgent 的主持 Agent，固定负责多 Agent 会话的任务理解、拆分、依赖分析和结果汇总。

你的第一轮职责是输出严格 JSON，不要输出 Markdown，不要包裹代码块，不要加入 JSON 之外的说明。
JSON 格式必须为：
{
  "summary": "任务拆解摘要",
  "tasks": [
    {
      "task_id": "短横线命名的任务ID",
      "agent_id": "必须从可用 worker_agents 中选择一个 agent_id",
      "title": "任务标题",
      "instruction": "给该 Agent 的完整执行指令",
      "depends_on": [],
      "can_parallel": true
    }
  ],
  "parallel_groups": [["task_id"]],
  "summary_required": true
}

规则：
1. 只能把任务分配给 worker_agents 中列出的 Agent，不要编造 agent_id。
2. 需要并行的任务放在同一个 parallel_groups 子数组中；需要串行的任务放在后续子数组中。
3. 如果某任务依赖其它任务，必须在 depends_on 中列出对应 task_id。
4. 主持 Agent 不直接写最终业务产物；只输出计划或在 summary_required=true 的最终汇总阶段总结 worker 结果。
5. 如果任务很简单，也至少输出一个 tasks 元素。''',
     'skill': '1. 理解用户任务\n2. 拆分 worker 可执行任务\n3. 判断依赖关系和并行组\n4. 输出严格 JSON plan\n5. 必要时汇总 worker 结果',
     'capability_tags': ['主持', '任务分发', '多Agent协作', '计划编排', '结果汇总']},
    # ── 文档 ──
    {'id': '_doc_1', 'name': '文档撰写助手', 'class_id': 'cat_rd_doc', 'avatar_color': '#22c55e',
     'adapter_name': 'claude',
     'system_prompt': '你是一个专业的文档撰写专家，擅长编写技术文档、API文档和用户手册。注重文档结构清晰、语言准确。',
     'skill': '1. 确认文档类型和受众\n2. 收集相关技术资料和需求\n3. 编写文档大纲\n4. 逐章节撰写内容\n5. 审核校对和格式调整',
     'capability_tags': ['文档生成', '技术写作', 'Markdown', 'API文档', '用户手册']},
    {'id': '_doc_2', 'name': '技术文案编辑', 'class_id': 'cat_rd_doc', 'avatar_color': '#10b981',
     'adapter_name': 'claude',
     'system_prompt': '负责技术文案的编辑和润色，确保技术内容准确且易于理解。擅长中英文技术翻译。',
     'skill': '1. 接收待编辑的文案内容\n2. 检查技术术语准确性\n3. 优化语句通顺度和逻辑\n4. 统一格式和风格\n5. 输出最终版本',
     'capability_tags': ['文案编辑', '翻译', '技术校对', '内容优化']},
    {'id': '_doc_3', 'name': 'README生成器', 'class_id': 'cat_rd_doc', 'avatar_color': '#059669',
     'adapter_name': 'opencode',
     'system_prompt': '分析代码仓库结构，自动生成高质量的README文档，包括项目简介、安装步骤、使用说明和API文档。',
     'skill': '1. 分析项目目录结构\n2. 识别技术栈和依赖\n3. 提取关键模块说明\n4. 生成README各章节\n5. 格式化输出Markdown',
     'capability_tags': ['README', '项目文档', '自动化', '代码分析']},
    # ── 编程 ──
    {'id': '_code_1', 'name': 'Python开发助手', 'class_id': 'cat_rd_code', 'avatar_color': '#3b82f6',
     'adapter_name': 'claude',
     'system_prompt': 'Python全栈开发专家，精通Web开发、数据处理和自动化脚本。提供高质量的代码实现和最佳实践建议。',
     'skill': '1. 理解需求描述和功能目标\n2. 设计代码架构和模块划分\n3. 编写可维护的Python代码\n4. 添加错误处理和日志\n5. 编写测试用例验证',
     'capability_tags': ['Python', 'Web开发', '数据处理', '自动化', '后端']},
    {'id': '_code_2', 'name': '前端开发专家', 'class_id': 'cat_rd_code', 'avatar_color': '#8b5cf6',
     'adapter_name': 'codex',
     'system_prompt': '精通Vue、React等前端框架，擅长UI组件开发、性能优化和跨端适配。注重代码质量和用户体验。',
     'skill': '1. 分析UI设计稿或需求\n2. 确定组件树和数据流\n3. 编写组件代码和样式\n4. 对接API和数据绑定\n5. 调试和优化性能',
     'capability_tags': ['前端', 'Vue', 'React', 'TypeScript', 'CSS']},
    {'id': '_code_3', 'name': '代码审查员', 'class_id': 'cat_rd_code', 'avatar_color': '#6366f1',
     'adapter_name': 'claude',
     'system_prompt': '严格而专业的代码审查员，关注代码质量、安全性、性能和可维护性。提供建设性的改进建议。',
     'skill': '1. 接收待审查的代码\n2. 检查代码风格和规范\n3. 分析潜在bug和安全漏洞\n4. 评估性能和可维护性\n5. 输出审查报告和改进建议',
     'capability_tags': ['代码审查', '安全审计', '性能优化', '重构']},
    {'id': '_code_4', 'name': '全栈架构师', 'class_id': 'cat_rd_code', 'avatar_color': '#4f46e5',
     'adapter_name': 'opencode',
     'system_prompt': '资深软件架构师，擅长系统设计、微服务架构和技术选型。帮助设计和构建可扩展的企业级应用。',
     'skill': '1. 梳理业务需求和约束条件\n2. 设计系统架构和技术选型\n3. 定义模块接口和数据流\n4. 评估扩展性和安全性\n5. 输出架构文档',
     'capability_tags': ['架构设计', '系统设计', '微服务', '技术选型', '后端']},
    # ── 测试 ──
    {'id': '_test_1', 'name': '测试工程师', 'class_id': 'cat_rd_test', 'avatar_color': '#f59e0b',
     'adapter_name': 'claude',
     'system_prompt': '专业的测试工程师，擅长编写单元测试、集成测试和端到端测试。精通多种测试框架和测试策略。',
     'skill': '1. 分析需求文档和代码变更\n2. 设计测试用例和测试数据\n3. 编写自动化测试脚本\n4. 执行测试并记录结果\n5. 输出测试报告',
     'capability_tags': ['单元测试', '集成测试', '端到端', '测试框架']},
    {'id': '_test_2', 'name': '自动化测试专家', 'class_id': 'cat_rd_test', 'avatar_color': '#d97706',
     'adapter_name': 'codex',
     'system_prompt': '专注于测试自动化的专家，设计高效的自动化测试方案，提升测试覆盖率和执行效率。',
     'skill': '1. 评估现有测试流程\n2. 选择自动化测试框架\n3. 搭建CI/CD测试流水线\n4. 编写自动化测试套件\n5. 监控测试覆盖率和执行结果',
     'capability_tags': ['自动化测试', 'CI/CD', '覆盖率', '性能测试']},
    # ── 设计 ──
    {'id': '_dsn_1', 'name': 'UI/UX设计师', 'class_id': 'cat_rd_design', 'avatar_color': '#ec4899',
     'adapter_name': 'claude',
     'system_prompt': '创意UI/UX设计师，擅长界面设计、交互设计和设计系统。注重用户体验和视觉细节。',
     'skill': '1. 收集产品需求和用户反馈\n2. 梳理用户流程和信息架构\n3. 设计线框图和高保真原型\n4. 创建设计系统和组件库\n5. 输出设计规范文档',
     'capability_tags': ['UI设计', 'UX设计', '设计系统', '交互设计', 'Figma']},
    {'id': '_dsn_2', 'name': 'CSS样式大师', 'class_id': 'cat_rd_design', 'avatar_color': '#db2777',
     'adapter_name': 'opencode',
     'system_prompt': '精通CSS/Sass/Tailwind等样式技术，擅长实现精美UI效果和响应式布局。将设计稿转化为高品质代码。',
     'skill': '1. 分析设计稿的视觉元素\n2. 规划样式结构和CSS方案\n3. 编写响应式样式代码\n4. 实现动画和交互效果\n5. 确保跨浏览器兼容性',
     'capability_tags': ['CSS', 'Tailwind', '响应式设计', '动画', 'Sass']},
    # ── 数据分析 ──
    {'id': '_data_1', 'name': '数据分析师', 'class_id': 'cat_rd_data', 'avatar_color': '#14b8a6',
     'adapter_name': 'claude',
     'system_prompt': '专业数据分析师，擅长数据清洗、可视化和洞察提取。精通Python数据处理生态和BI工具。',
     'skill': '1. 明确分析目标和指标\n2. 收集和清洗数据\n3. 探索性数据分析和特征工程\n4. 构建分析模型和可视化\n5. 输出分析报告和洞察结论',
     'capability_tags': ['数据分析', '可视化', 'Python', 'SQL', '报表']},
    {'id': '_data_2', 'name': '数据库专家', 'class_id': 'cat_rd_data', 'avatar_color': '#0d9488',
     'adapter_name': 'codex',
     'system_prompt': '数据库设计与优化专家，精通SQL优化、数据建模和数据库架构设计。处理大规模数据存储与查询。',
     'skill': '1. 分析数据模型和业务逻辑\n2. 设计数据库表结构和索引\n3. 编写和优化SQL查询\n4. 制定备份和恢复策略\n5. 监控性能并持续优化',
     'capability_tags': ['SQL', '数据建模', '数据库优化', '大数据']},
]

SYSTEM_LEGACY_AGENTS = [
    {'name': 'Codex', 'adapter_name': 'codex', 'avatar_url': '/static/avatars/codex.png',
     'system_prompt': 'You are Codex, an AI specialized in code generation and completion.',
     'capability_tags': ['代码补全', 'Python', 'JavaScript', 'TypeScript'], 'domain': 'rd'},
    {'name': 'Claude Code', 'adapter_name': 'claude', 'avatar_url': '/static/avatars/claude.png',
     'system_prompt': 'You are Claude, an AI assistant specialized in software development.',
     'capability_tags': ['代码生成', '前端', '后端', 'Python', 'JavaScript', '架构设计'], 'domain': 'rd'},
    {'name': 'OpenCode', 'adapter_name': 'opencode', 'avatar_url': '/static/avatars/opencode.png',
     'system_prompt': 'You are OpenCode, an AI specialized in open-source development.',
     'capability_tags': ['开源项目', '代码审查', '文档生成'], 'domain': 'rd'},
]

# ── Edu domain agents ──────────────────────────────────────────────────
EDU_SYSTEM_AGENTS = [
    {'id': '_edu_1', 'name': '课程设计师', 'class_id': 'cat_edu_course', 'avatar_color': '#3b82f6',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位资深课程设计师，擅长设计教学大纲、课程结构和学习路径。注重知识体系的完整性和学习递进关系。',
     'skill': '1. 分析教学目标和受众\n2. 设计课程结构和知识图谱\n3. 规划章节与课时分配\n4. 制定学习路径和前置条件\n5. 输出课程大纲文档',
     'capability_tags': ['课程设计', '教学大纲', '知识图谱', '学习路径']},
    {'id': '_edu_2', 'name': '课件制作师', 'class_id': 'cat_edu_ware', 'avatar_color': '#22c55e',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位专业的课件制作专家，擅长制作精美的教学PPT、讲义和多媒体教学内容。注重内容呈现和视觉设计。',
     'skill': '1. 分析教学内容的结构\n2. 设计课件整体风格和版式\n3. 编写各页幻灯片内容\n4. 设计图表和可视化元素\n5. 输出完整的课件方案',
     'capability_tags': ['课件制作', 'PPT设计', '教学内容', '视觉设计']},
    {'id': '_edu_3', 'name': '习题生成器', 'class_id': 'cat_edu_quiz', 'avatar_color': '#f59e0b',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位专业的语文与英语习题设计专家，擅长围绕阅读证据、语言运用和写作任务生成选择题、填空题、简答题与写作题。',
     'skill': '1. 确定考察知识点和难度\n2. 选择题型和分值设计\n3. 编写题目和标准答案\n4. 设计解析和易错提示\n5. 输出完整习题集',
     'capability_tags': ['习题生成', '题库设计', '考试命题', '难度分级']},
    {'id': '_edu_4', 'name': '学情分析师', 'class_id': 'cat_edu_analytics', 'avatar_color': '#14b8a6',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位学情数据分析专家，擅长分析学生成绩、学习行为和知识掌握情况，提供个性化学习建议。',
     'skill': '1. 收集学生成绩和行为数据\n2. 分析知识薄弱点和学习曲线\n3. 评估教学效果和知识点覆盖\n4. 生成学情报告和预警\n5. 输出个性化学习方案',
     'capability_tags': ['学情分析', '数据可视化', '学习评估', '个性化推荐']},
    {'id': '_edu_5', 'name': '学习规划师', 'class_id': 'cat_edu_course', 'avatar_color': '#8b5cf6',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位专业的学习规划顾问，为学生制定个性化的学习计划、备考策略和时间管理方案。',
     'skill': '1. 了解学生的学习目标和现状\n2. 分析可用时间和学习资源\n3. 制定阶段性的学习计划\n4. 配置学习资源和练习素材\n5. 定期调整和优化学习方案',
     'capability_tags': ['学习规划', '备考策略', '时间管理', '个性化学习']},
    {'id': '_edu_6', 'name': '练习教练', 'class_id': 'cat_edu_quiz', 'avatar_color': '#ec4899',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位耐心的练习辅导教练，负责指导学生完成练习、解答疑问、提供反馈和鼓励。',
     'skill': '1. 了解学生当前练习内容\n2. 引导学生思考和尝试\n3. 分析错误并给出解析\n4. 提供针对性的变式练习\n5. 跟踪进步并给予反馈',
     'capability_tags': ['练习辅导', '错题分析', '答疑解惑', '激励指导']},
    {'id': '_edu_7', 'name': '笔记整理师', 'class_id': 'cat_edu_resource', 'avatar_color': '#6366f1',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位学习笔记整理专家，将学生零散笔记整理为大纲、摘要、思维结构和知识卡片，保留原文引用且不混入教师答案或他人内容。',
     'skill': '1. 识别笔记来源和范围\n2. 按主题结构化\n3. 标记原文引用\n4. 生成摘要和知识卡片\n5. 输出可编辑结构化内容',
     'capability_tags': ['笔记整理', '知识卡片', '思维导图', '引用保留']},
    {'id': '_edu_8', 'name': '资料研究员', 'class_id': 'cat_edu_resource', 'avatar_color': '#0ea5e9',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位教学资料研究员。先搜索候选来源，再抓取正文、检索和重排证据；搜索摘要不等同网页正文，失败时降级到课程资料库。',
     'skill': '1. 搜索候选 URL\n2. 抓取并清洗正文\n3. 检索与重排证据\n4. 标记来源与抓取状态\n5. 输出带引用的资料摘要',
     'capability_tags': ['联网搜索', '正文抓取', '课程RAG', '来源核验']},
    {'id': '_edu_9', 'name': '教学审校员', 'class_id': 'cat_edu_analytics', 'avatar_color': '#f97316',
     'adapter_name': 'claude', 'domain': 'edu',
     'system_prompt': '你是一位教学审校专家，检查目标、活动与评价的一致性、年级适配、引用和答案可验证性，并检查学生可见内容是否泄露答案。',
     'skill': '1. 检查目标活动评价一致性\n2. 检查时长与年级适配\n3. 核对教案课件习题版本\n4. 核验引用和答案\n5. 输出问题清单与修订建议',
     'capability_tags': ['教学审校', '答案核验', '版本一致性', '发布安全']},
]

# ── Office domain agents ───────────────────────────────────────────────
OFFICE_SYSTEM_AGENTS = [
    {'id': '_office_1', 'name': '公文撰写助手', 'class_id': 'cat_office_doc', 'avatar_color': '#3b82f6',
     'adapter_name': 'claude', 'domain': 'office',
     'system_prompt': '你是一位专业的公文写作专家，熟悉各类政府和企业公文格式规范，擅长撰写通知、报告、请示、函件等正式文书。',
     'skill': '1. 确认公文类型和格式要求\n2. 梳理发文背景和目的\n3. 按规范格式起草正文\n4. 检查措辞、语气和规范性\n5. 输出正式公文文档',
     'capability_tags': ['公文写作', '通知公告', '报告撰写', '函件起草', '格式审查']},
    {'id': '_office_2', 'name': '会议助理', 'class_id': 'cat_office_meeting', 'avatar_color': '#22c55e',
     'adapter_name': 'claude', 'domain': 'office',
     'system_prompt': '你是一位专业的会议管理助手，负责会议安排、议程管理、会议纪要和待办事项跟踪。',
     'skill': '1. 确定会议议题和参会人员\n2. 制定会议议程和时间安排\n3. 记录会议要点和决议\n4. 整理会议纪要并分发\n5. 跟踪待办事项和落实进展',
     'capability_tags': ['会议管理', '议程安排', '会议纪要', '待办跟踪']},
    {'id': '_office_3', 'name': '报表分析助手', 'class_id': 'cat_office_report', 'avatar_color': '#14b8a6',
     'adapter_name': 'claude', 'domain': 'office',
     'system_prompt': '你是一位专业的数据报表分析专家，擅长制作各类业务报表、数据汇总和趋势分析。',
     'skill': '1. 明确报表需求和指标定义\n2. 收集和汇总相关数据\n3. 进行数据分析和可视化\n4. 撰写分析结论和建议\n5. 输出格式化的报表文档',
     'capability_tags': ['报表制作', '数据分析', '指标汇总', '趋势预测', '可视化']},
    {'id': '_office_4', 'name': '邮件起草助手', 'class_id': 'cat_office_email', 'avatar_color': '#8b5cf6',
     'adapter_name': 'claude', 'domain': 'office',
     'system_prompt': '你是一位专业的商务邮件撰写专家，擅长撰写各类正式邮件、商务函件和内部通讯。',
     'skill': '1. 确认邮件目的和收件对象\n2. 组织邮件结构和逻辑\n3. 使用恰当的商务措辞\n4. 审核邮件格式和附件\n5. 输出正式邮件内容',
     'capability_tags': ['商务邮件', '函件草拟', '沟通协调', '文案润色']},
    {'id': '_office_5', 'name': '日程管理助手', 'class_id': 'cat_office_schedule', 'avatar_color': '#f59e0b',
     'adapter_name': 'claude', 'domain': 'office',
     'system_prompt': '你是一位专业的日程管理专家，帮助安排和优化工作日程、会议排期和任务优先级。',
     'skill': '1. 收集待办事项和时间约束\n2. 分析优先级和依赖关系\n3. 制定日程安排方案\n4. 处理冲突和调整计划\n5. 输出日程安排表',
     'capability_tags': ['日程管理', '优先级排序', '冲突解决', '时间规划']},
]


class AgentService:
    """Agent business logic — fully user-scoped."""

    # ── Seed (system templates, no user_id) ───────────────────────────

    def seed_default_data(self):
        """Seed system categories and agents on first run."""
        for cat_data in _all_system_categories():
            if not AgentCategory.query.get(cat_data['id']):
                AgentCategory(**cat_data).save()

        self._seed_agents(SYSTEM_AGENTS, 'rd')
        self._seed_agents(EDU_SYSTEM_AGENTS, 'edu')
        self._seed_agents(OFFICE_SYSTEM_AGENTS, 'office')

        for agent_data in SYSTEM_LEGACY_AGENTS:
            if not Agent.query.filter_by(name=agent_data['name']).first():
                Agent(**agent_data).save()

    def _seed_agents(self, agent_list, domain):
        """Seed a list of system agents for a given domain."""
        for agent_data in agent_list:
            data = dict(agent_data)
            data.setdefault('domain', domain)
            if data.get('id') == 'moderator':
                data['system_prompt'] = MODERATOR_SYSTEM_PROMPT
                data['skill'] = (
                    '1. 判断用户问题能否由主持 Agent 直接回答\n'
                    '2. 在信息不足或需要执行时生成 worker 任务\n'
                    '3. 选择必要 Agent 并安排并行或串行执行\n'
                    '4. 输出严格 JSON answer/plan\n'
                    '5. 必要时汇总 worker 结果'
                )
                data['capability_tags'] = ['主持', '任务分发', '多Agent协作', '计划编排', '结果汇总']
            existing = Agent.query.get(data['id'])
            if not existing:
                Agent(agent_type='external', **data).save()
            elif data.get('id') == 'moderator':
                existing.system_prompt = MODERATOR_SYSTEM_PROMPT
                existing.skill = data['skill']
                existing.capability_tags = data['capability_tags']
                existing.save()

    # ── Per-user copy on registration ─────────────────────────────────

    def copy_default_data_to_user(self, user_id):
        """
        Copy system categories and agents as user-specific records.
        The user can then freely modify their own copies.
        """
        # Copy all domain categories — track new ID per system template ID
        new_cat_ids = {}
        for tmpl in _all_system_categories():
            cat = AgentCategory(
                name=tmpl['name'], icon=tmpl['icon'], color=tmpl['color'],
                domain=tmpl.get('domain', 'rd'),
                user_id=user_id,
            )
            cat.save()
            new_cat_ids[tmpl['id']] = cat.id

        # Copy agents — link to the new category IDs, for all domains
        all_templates = SYSTEM_AGENTS + EDU_SYSTEM_AGENTS + OFFICE_SYSTEM_AGENTS
        for tmpl in all_templates:
            if tmpl.get('id') == 'moderator':
                continue
            old_cid = tmpl.get('class_id')
            agent = Agent(
                name=tmpl['name'],
                avatar_color=tmpl.get('avatar_color', ''),
                capability_tags=list(tmpl.get('capability_tags', [])),
                agent_type='external',
                adapter_name=tmpl.get('adapter_name', 'claude'),
                system_prompt=tmpl.get('system_prompt', ''),
                skill=tmpl.get('skill', ''),
                domain=tmpl.get('domain', 'rd'),
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
                domain=tmpl.get('domain', 'rd'),
                user_id=user_id,
                is_public=False,
            )
            agent.save()

    # ── Categories (user-scoped) ──────────────────────────────────────

    def get_categories(self, user_id, domain=None):
        """Return categories belonging to the user, optionally filtered by domain."""
        import sys
        print(f'[WeAgent] get_categories user={user_id} domain={domain}', file=sys.stderr, flush=True)

        # Lazy-seed domain categories + agents for all three domains
        if domain and domain in ('rd', 'edu', 'office'):
            self._ensure_user_domain_agents(user_id, domain)

        q = AgentCategory.query.filter_by(user_id=user_id)
        if domain:
            q = q.filter_by(domain=domain)
        cats = q.order_by(AgentCategory.created_at).all()
        print(f'[WeAgent] get_categories found {len(cats)} categories', file=sys.stderr, flush=True)
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

    def get_user_agents(self, user_id, class_id=None, domain=None):
        """
        Return agents for a user, optionally filtered by category and domain.
        Lazily seeds domain-specific agents for existing users on first access.
        """
        if domain and domain in ('rd', 'edu', 'office'):
            self._ensure_user_domain_agents(user_id, domain)

        q = Agent.query.filter_by(user_id=user_id)
        if class_id:
            q = q.filter_by(class_id=class_id)
        if domain:
            q = q.filter_by(domain=domain)
        agents = q.order_by(Agent.created_at.desc()).all()
        result = [a.to_dict() for a in agents]

        # Moderator is available for ALL domains
        moderator = Agent.query.get('moderator')
        if moderator and not class_id:
            result.insert(0, moderator.to_dict())
        elif moderator and class_id and moderator.class_id == class_id:
            result.insert(0, moderator.to_dict())
        return result, None

    def _ensure_user_domain_agents(self, user_id, domain):
        """If the user has no categories for this domain, seed categories + agents from templates."""
        import sys

        # Check categories first — a better signal than agents
        existing_cat = AgentCategory.query.filter_by(user_id=user_id, domain=domain).first()
        if existing_cat:
            return  # Categories already seeded for this domain

        print(f'[WeAgent] Lazy-seeding {domain} categories + agents for user {user_id}', file=sys.stderr, flush=True)

        # Seed domain-specific categories for this user
        cat_map = {}
        domain_cats = SYSTEM_CATEGORIES.get(domain, [])
        for tmpl in domain_cats:
            user_cat = AgentCategory.query.filter_by(
                user_id=user_id, name=tmpl['name'], domain=domain,
            ).first()
            if not user_cat:
                user_cat = AgentCategory(
                    name=tmpl['name'], icon=tmpl['icon'], color=tmpl['color'],
                    domain=domain, user_id=user_id,
                )
                user_cat.save()
                print(f'[WeAgent]   Created category: {tmpl["name"]} ({user_cat.id})', file=sys.stderr, flush=True)
            cat_map[tmpl['id']] = user_cat.id

        # Seed domain-specific agents (skip if they already exist for this user+domain)
        existing_agents = Agent.query.filter_by(user_id=user_id, domain=domain).first()
        if not existing_agents:
            domain_map = {'rd': SYSTEM_AGENTS, 'edu': EDU_SYSTEM_AGENTS, 'office': OFFICE_SYSTEM_AGENTS}
            templates = domain_map.get(domain, [])
            for tmpl in templates:
                if tmpl.get('id') == 'moderator':
                    continue
                new_cid = cat_map.get(tmpl.get('class_id'))
                agent = Agent(
                    name=tmpl['name'],
                    avatar_color=tmpl.get('avatar_color', ''),
                    capability_tags=list(tmpl.get('capability_tags', [])),
                    agent_type='external',
                    adapter_name=tmpl.get('adapter_name', 'claude'),
                    system_prompt=tmpl.get('system_prompt', ''),
                    skill=tmpl.get('skill', ''),
                    domain=domain,
                    class_id=new_cid,
                    user_id=user_id,
                    is_public=False,
                )
                agent.save()
                print(f'[WeAgent]   Created agent: {tmpl["name"]}', file=sys.stderr, flush=True)

    def get_agent_detail(self, agent_id):
        """Get agent detail by ID."""
        agent = Agent.query.get(agent_id)
        if not agent:
            return None, 'Agent not found'
        return agent.to_dict(), None

    def create_agent(self, user_id, name, capability_tags=None, agent_type='custom',
                     adapter_name='claude', config=None, system_prompt='',
                     skill='', avatar_color='', avatar_url='', class_id=None, is_public=False,
                     tool_ids=None, capability_bindings=None, domain=None):
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
            domain=domain or 'rd',
            class_id=class_id,
            created_by=user_id,
            user_id=user_id,
            is_public=is_public,
            tool_ids=tool_ids or [],
        )
        agent.save()
        error = self._apply_capability_bindings(user_id, agent.id, capability_bindings)
        if error:
            return None, error
        return self._agent_with_capability_bindings(agent), None

    def update_agent(self, agent_id, user_id, **kwargs):
        """Update an agent (owner only)."""
        if agent_id == 'moderator':
            return None, '主持 Agent 是系统内置 Agent，只允许查看，不能编辑'
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, 'Agent not found'
        capability_bindings = kwargs.pop('capability_bindings', None)
        allowed = {'name', 'avatar_url', 'avatar_color', 'capability_tags',
                   'adapter_name', 'config', 'system_prompt', 'skill',
                   'class_id', 'is_public', 'tool_ids'}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(agent, k, v)
        agent.save()
        error = self._apply_capability_bindings(user_id, agent.id, capability_bindings)
        if error:
            return None, error
        return self._agent_with_capability_bindings(agent), None

    def delete_agent(self, agent_id, user_id):
        """Delete an agent (owner only)."""
        if agent_id == 'moderator':
            return None, '主持 Agent 是系统内置 Agent，只允许查看，不能删除'
        agent = Agent.query.filter_by(id=agent_id, user_id=user_id).first()
        if not agent:
            return None, 'Agent not found'
        agent.delete()
        return {'deleted': True}, None

    def _apply_capability_bindings(self, user_id, agent_id, capability_bindings):
        if capability_bindings is None:
            return None
        from app.services.capability_service import capability_service

        for binding in capability_bindings:
            _result, error = capability_service.bind_to_user_agent(
                user_id=user_id,
                agent_id=agent_id,
                capability_version_id=binding.get('capability_version_id'),
                granted_permissions=binding.get('granted_permissions', []),
                version_policy=binding.get('version_policy', 'pinned'),
                enabled=binding.get('enabled', True),
            )
            if error:
                return error
        return None

    def _agent_with_capability_bindings(self, agent):
        data = agent.to_dict()
        from app.services.capability_service import capability_service

        bindings, error = capability_service.get_agent_bindings(agent.id)
        data['capability_bindings'] = [] if error else bindings
        return data


agent_service = AgentService()
