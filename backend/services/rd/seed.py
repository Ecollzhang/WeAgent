"""
种子数据脚本 — 将第一个演示项目（用户反馈系统）的数据写入数据库。

用法：
    cd backend/services/rd
    python seed.py

会清空已有数据后重新插入。
使用真实用户 UUID（从 weagent 主库查询或创建）。
"""
import sys
import os
import uuid
import hashlib
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# 初始化 database 模块
import database
database.init_db(db)

# 导入全部 RD 模型
from models import (
    RdProject, RdProjectMember, RdIteration, RdRequirement,
    RdRequirementAssignee, RdBug, RdBugAssignee, RdComment,
    RdBranch, RdActivityLog
)

NOW = datetime.utcnow()


def _make_pw_hash(password):
    """生成与 Werkzeug 兼容的密码哈希."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)


def _make_uuid(seed):
    """从种子字符串生成确定性 UUID."""
    return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))


def ensure_users(main_db_conn):
    """确保 weagent 主库中存在所需用户，返回 user_id -> user_info 映射."""
    import pymysql
    cursor = main_db_conn.cursor(pymysql.cursors.DictCursor)

    # 需要确保存在的用户
    desired_users = [
        ('Ecoll', 'ecoll@weagent.dev', 'admin'),
        ('张三', 'zhangsan@weagent.dev', 'user'),
        ('李四', 'lisi@weagent.dev', 'user'),
        ('王五', 'wangwu@weagent.dev', 'user'),
        ('赵六', 'zhaoliu@weagent.dev', 'user'),
        ('陈测试', 'chentest@weagent.dev', 'user'),
        ('周审查', 'zhoushencha@weagent.dev', 'user'),
    ]

    users = {}
    for username, email, role in desired_users:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row:
            uid = row['id']
            print(f"  [EXISTS] User: {username} ({uid})")
        else:
            uid = str(uuid.uuid4())
            pw_hash = _make_pw_hash('weagent123')
            cursor.execute(
                "INSERT INTO users (id, username, email, password_hash, role, avatar_url, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, '', NOW(), NOW())",
                (uid, username, email, pw_hash, role)
            )
            print(f"  [CREATED] User: {username} ({uid})")
        users[username] = {'id': uid, 'username': username, 'role': role}
    main_db_conn.commit()
    cursor.close()
    return users


def seed():
    import pymysql
    from config import Config as Cfg

    # ── 连接主库 weagent（用户表所在）──
    print("连接主库 weagent...")
    main_conn = pymysql.connect(
        host=Cfg.MYSQL_HOST,
        port=Cfg.MYSQL_PORT,
        user=Cfg.MYSQL_USER,
        password=Cfg.MYSQL_PASSWORD,
        database='weagent',
        charset='utf8mb4',
    )
    users = ensure_users(main_conn)
    main_conn.close()

    ecoll_id = users['Ecoll']['id']
    dev_ids = {
        'ecoll': ecoll_id,
        'dev1': users['张三']['id'],
        'dev2': users['李四']['id'],
        'dev3': users['王五']['id'],
        'dev4': users['赵六']['id'],
        'tester': users['陈测试']['id'],
        'reviewer': users['周审查']['id'],
    }

    with app.app_context():
        db.create_all()

        # ── 清空已有数据 ──
        print("\n清空已有 RD 数据...")
        for model in [
            RdActivityLog, RdBranch, RdComment, RdBugAssignee, RdBug,
            RdRequirementAssignee, RdRequirement, RdIteration,
            RdProjectMember, RdProject,
        ]:
            db.session.query(model).delete()
        db.session.commit()

        # ── 1. 创建项目 ──
        print("\n创建项目：用户反馈系统 (owner=Ecoll)")
        project_id = 'proj-1'
        project = RdProject(
            id=project_id,
            workspace_id='ws-default',
            user_id=ecoll_id,
            name='用户反馈系统',
            description='收集和管理用户反馈的全栈应用，支持反馈提交、分类、处理和数据分析',
            tech_stack={
                'frontend': 'Vue 3 + Element Plus',
                'backend': 'Flask',
                'database': 'MySQL',
                'deployment': 'Docker',
            },
            coding_standards=(
                '1. ESLint (airbnb-base) 代码规范\n'
                '2. Prettier 统一格式化\n'
                '3. Git Commit 遵循 Conventional Commits\n'
                '4. 组件必须包含 Props 类型定义\n'
                '5. API 接口必须有 Swagger 文档'
            ),
            status='active',
            visibility='private',
        )
        db.session.add(project)
        db.session.flush()  # 确保 project 写入数据库，后续的 activity_log 等外键才能引用

        # ── 2. 创建项目成员 ──
        print("创建项目成员...")
        members_data = [
            {'user_id': dev_ids['ecoll'], 'role': 'owner'},
            {'user_id': dev_ids['dev2'], 'role': 'admin'},
            {'user_id': dev_ids['dev4'], 'role': 'developer'},
            {'user_id': dev_ids['tester'], 'role': 'viewer'},
        ]
        for m in members_data:
            db.session.add(RdProjectMember(
                project_id=project_id,
                user_id=m['user_id'],
                role=m['role'],
            ))

        # ── 3. 创建迭代 ──
        print("创建迭代...")
        iterations_data = [
            {
                'id': 'iter-1', 'name': 'Sprint 1 — 反馈提交与展示',
                'goal': '**核心目标：打通用户反馈闭环**\n\n- **反馈表单页** — 支持类型选择、富文本输入、图片拖拽上传、联系方式校验\n- **反馈数据 API** — RESTful 接口，支持分页查询、条件筛选、状态流转\n- **管理员列表页** — 表格展示 + 行内编辑 + 批量操作 + 导出 CSV\n\n`预计工时 80h` | `优先级 P0`',
                'start_date': '2026-07-13', 'end_date': '2026-07-27',
                'status': 'active', 'sort_order': 1,
            },
            {
                'id': 'iter-2', 'name': 'Sprint 2 — 反馈处理工作流',
                'goal': '**目标：构建智能反馈处理引擎**\n\n- **智能分类** — 基于关键词 + NLP 模型自动归类 Bug / 建议 / 咨询\n- **自动指派** — 按模块负责人 + 负载均衡策略自动分配处理人\n- **状态流转** — 待处理 → 处理中 → 已解决 → 已关闭，支持驳回和转派\n- **邮件通知** — 状态变更、新评论、即将超时时自动发送提醒邮件\n\n`预计工时 60h` | `优先级 P1` | `依赖 Sprint 1`',
                'start_date': '2026-07-28', 'end_date': '2026-08-10',
                'status': 'planning', 'sort_order': 2,
            },
            {
                'id': 'iter-3', 'name': 'Sprint 0 — 项目初始化',
                'goal': '**目标：从零搭建工程化基础设施**\n\n- **项目骨架** — Monorepo 结构 + ESLint/Prettier 统一规范 + Git Hooks 提交检查\n- **CI/CD 流水线** — GitHub Actions 自动化: `lint → test → build → deploy`\n- **开发环境** — Docker Compose 一键启动，含 MySQL / Redis / Nginx\n- **技术栈定型** — 前端 Vue2 + Element UI | 后端 Flask | 数据库 MySQL\n\n`实际工时 72h` | `状态: 已完成`',
                'start_date': '2026-06-28', 'end_date': '2026-07-11',
                'status': 'completed', 'sort_order': 0,
            },
        ]
        for it in iterations_data:
            db.session.add(RdIteration(
                id=it['id'],
                project_id=project_id,
                name=it['name'],
                goal=it['goal'],
                start_date=it['start_date'],
                end_date=it['end_date'],
                status=it['status'],
                sort_order=it['sort_order'],
            ))

        # ── 4. 创建需求 ──
        print("创建需求...")
        requirements_data = [
            {
                'id': 'req-1', 'iteration_id': 'iter-1',
                'title': '反馈提交表单页面',
                'description': '用户可以在前端页面提交反馈，包含反馈类型选择、文本输入、图片上传、联系方式填写等字段。表单需做前端校验。',
                'acceptance_criteria': '1. 用户可选择反馈类型（Bug/建议/咨询/投诉）并成功提交\n2. 表单前端校验提示准确，必填项未填时不可提交\n3. 图片上传支持 jpg/png/gif 格式，单张不超过 5MB\n4. 联系方式邮箱格式校验正确\n5. 提交成功后显示成功提示并清空表单',
                'type': 'feature', 'priority': 'p1', 'status': 'in_review',
                'story_points': 5, 'labels': ['前端', '表单', '用户体验'],
                'start_date': '2026-07-13', 'due_date': '2026-07-22',
                'created_by': dev_ids['ecoll'],
                'assignees': [
                    {'user_id': dev_ids['ecoll'], 'role': 'primary'},
                    {'user_id': dev_ids['dev4'], 'role': 'reviewer'},
                ],
            },
            {
                'id': 'req-1-1', 'iteration_id': 'iter-1', 'parent_id': 'req-1',
                'title': '反馈类型选择器组件',
                'description': '抽取反馈类型选择为独立可复用组件，支持图标+文字展示，支持搜索过滤。',
                'acceptance_criteria': '1. 组件支持 4 种反馈类型的展示和选择\n2. 可选择显示为下拉框或单选按钮组两种模式\n3. 键盘导航支持（上下箭头选择，回车确认）',
                'type': 'feature', 'priority': 'p1', 'status': 'done',
                'story_points': 2, 'labels': ['前端', '组件'],
                'start_date': '2026-07-13', 'due_date': '2026-07-16',
                'created_by': dev_ids['ecoll'],
                'assignees': [{'user_id': dev_ids['ecoll'], 'role': 'primary'}],
            },
            {
                'id': 'req-1-2', 'iteration_id': 'iter-1', 'parent_id': 'req-1',
                'title': '图片上传与预览组件',
                'description': '实现图片多图上传、拖拽排序、缩略图预览、删除确认等功能。上传前自动压缩。',
                'acceptance_criteria': '1. 支持一次性选择最多 5 张图片\n2. 上传前自动压缩至最大宽度 1920px\n3. 拖拽调整图片顺序\n4. 点击缩略图可全屏预览\n5. 单张超过 5MB 时给出提示',
                'type': 'feature', 'priority': 'p2', 'status': 'in_progress',
                'story_points': 3, 'labels': ['前端', '组件', '图片'],
                'start_date': '2026-07-17', 'due_date': '2026-07-21',
                'created_by': dev_ids['ecoll'],
                'assignees': [
                    {'user_id': dev_ids['ecoll'], 'role': 'primary'},
                    {'user_id': dev_ids['dev4'], 'role': 'reviewer'},
                ],
            },
            {
                'id': 'req-2', 'iteration_id': 'iter-1',
                'title': '反馈数据 API',
                'description': '设计和实现反馈数据的 CRUD RESTful API，支持分页查询、按类型/状态筛选、排序功能。需要添加 JWT 鉴权。',
                'acceptance_criteria': '1. POST /api/feedback 创建反馈返回 201 和完整数据\n2. GET /api/feedback?page=1&per_page=20&type=bug 正确分页筛选\n3. GET /api/feedback/:id 返回单条完整数据\n4. PATCH /api/feedback/:id 更新状态并验证状态流转合法性\n5. DELETE /api/feedback/:id 仅管理员可执行\n6. 未携带有效 JWT 的请求返回 401\n7. API 响应时间 p95 < 200ms',
                'type': 'feature', 'priority': 'p1', 'status': 'in_progress',
                'story_points': 3, 'labels': ['后端', 'API', '数据库'],
                'start_date': '2026-07-13', 'due_date': '2026-07-20',
                'created_by': dev_ids['dev2'],
                'assignees': [
                    {'user_id': dev_ids['dev2'], 'role': 'primary'},
                    {'user_id': dev_ids['dev3'], 'role': 'reviewer'},
                ],
            },
            {
                'id': 'req-3', 'iteration_id': 'iter-1',
                'title': '管理员反馈列表页',
                'description': '管理员可以查看所有用户提交的反馈，支持表格展示、高级筛选（类型/状态/日期范围）、批量操作（标记已处理/删除）。',
                'acceptance_criteria': '1. 表格展示所有反馈记录，支持按创建时间倒序排列\n2. 高级筛选面板支持类型、状态、日期范围的组合筛选\n3. 支持批量勾选并执行"标记已处理"或"批量删除"\n4. 操作需要有二次确认弹窗\n5. 分页切换时筛选条件不丢失',
                'type': 'feature', 'priority': 'p2', 'status': 'todo',
                'story_points': 3, 'labels': ['前端', '管理后台', '表格'],
                'start_date': '2026-07-20', 'due_date': '2026-07-27',
                'created_by': dev_ids['ecoll'],
                'assignees': [
                    {'user_id': dev_ids['ecoll'], 'role': 'primary'},
                    {'user_id': dev_ids['tester'], 'role': 'tester'},
                ],
            },
            {
                'id': 'req-4', 'iteration_id': 'iter-2',
                'title': '反馈自动分类引擎',
                'description': '基于 NLP 模型自动识别反馈类型（Bug/建议/咨询/投诉），减少人工分类工作量。准确率目标 > 85%。',
                'acceptance_criteria': '1. 文本分类准确率在测试集上 > 85%\n2. 单条反馈分类耗时 < 100ms\n3. 支持人工修正分类结果并反馈给模型\n4. 分类结果记录置信度分数\n5. 低置信度（< 0.6）的反馈标记为待人工审核',
                'type': 'enhancement', 'priority': 'p2', 'status': 'backlog',
                'story_points': 8, 'labels': ['后端', 'AI', 'NLP'],
                'start_date': '2026-07-28', 'due_date': '2026-08-10',
                'created_by': dev_ids['dev3'],
                'assignees': [{'user_id': dev_ids['dev3'], 'role': 'primary'}],
            },
            {
                'id': 'req-5', 'iteration_id': 'iter-2',
                'title': '邮件通知服务',
                'description': '当反馈状态变更时（新建/处理中/已解决），自动发送邮件通知给提交者和相关处理人。支持邮件模板自定义。',
                'acceptance_criteria': '1. 反馈状态变更时自动触发邮件发送\n2. 邮件包含反馈标题、状态变更、处理人信息\n3. 支持 HTML 邮件模板，管理员可在线编辑模板\n4. 发送失败时自动重试 3 次，间隔 5 分钟\n5. 记录所有邮件发送日志供排查',
                'type': 'feature', 'priority': 'p2', 'status': 'backlog',
                'story_points': 3, 'labels': ['后端', '通知', '邮件'],
                'start_date': '2026-08-01', 'due_date': '2026-08-07',
                'created_by': dev_ids['dev2'],
                'assignees': [{'user_id': dev_ids['dev2'], 'role': 'primary'}],
            },
            {
                'id': 'req-6', 'iteration_id': None,
                'title': '反馈数据分析仪表盘',
                'description': '可视化展示反馈数据：时间趋势图、类型分布饼图、处理效率统计、热门反馈词云等。',
                'acceptance_criteria': '1. 时间趋势图展示近 30 天反馈数量变化\n2. 类型分布饼图支持点击钻取\n3. 处理效率统计展示平均处理时长\n4. 仪表盘数据每日凌晨自动刷新\n5. 支持导出统计报表为 PDF',
                'type': 'enhancement', 'priority': 'p3', 'status': 'backlog',
                'story_points': 5, 'labels': ['前端', '数据分析', '可视化'],
                'created_by': dev_ids['ecoll'],
                'assignees': [],
            },
        ]
        for req in requirements_data:
            assignees = req.pop('assignees', [])
            r = RdRequirement(
                project_id=project_id,
                **req,
            )
            db.session.add(r)
            for a in assignees:
                db.session.add(RdRequirementAssignee(
                    requirement_id=r.id,
                    user_id=a['user_id'],
                    role=a['role'],
                ))

        # ── 5. 创建 Bug ──
        print("创建 Bug...")
        db.session.flush()  # 确保需求和迭代已写入，Bug 的外键才能引用
        bugs_data = [
            {
                'id': 'bug-1', 'iteration_id': 'iter-1', 'requirement_id': 'req-1',
                'title': '反馈提交按钮在 Safari 下点击无响应',
                'description': '在 Safari 17.0 浏览器中，填写完反馈表单后点击"提交"按钮没有任何反应，控制台无报错。Chrome/Firefox 正常。',
                'expected_behavior': '点击提交按钮后，表单数据发送到后端，显示提交成功提示',
                'actual_behavior': '点击按钮后页面无任何响应，网络请求未发出',
                'severity': 'critical', 'priority': 'p0', 'status': 'in_progress',
                'environment': 'macOS 14.0, Safari 17.0',
                'browser_info': 'Safari 17.0', 'os_info': 'macOS 14.0 Sonoma',
                'labels': ['前端', '浏览器兼容', 'Safari'],
                'created_by': dev_ids['tester'],
                'assignees': [
                    {'user_id': dev_ids['ecoll'], 'role': 'fixer'},
                    {'user_id': dev_ids['tester'], 'role': 'tester'},
                ],
            },
            {
                'id': 'bug-2', 'iteration_id': 'iter-1', 'requirement_id': 'req-2',
                'title': '反馈内容超过 1000 字时 API 返回 500',
                'description': '当用户提交的反馈内容超过 1000 个字符时，POST /api/feedback 返回 500 Internal Server Error。数据库字段可能长度不足。',
                'expected_behavior': '支持最多 5000 字符的反馈内容',
                'actual_behavior': '超过 1000 字符时返回 500 错误',
                'severity': 'major', 'priority': 'p1', 'status': 'fixed',
                'environment': '全平台',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['后端', 'API', '数据库'],
                'created_by': dev_ids['tester'],
                'assignees': [
                    {'user_id': dev_ids['dev2'], 'role': 'fixer'},
                    {'user_id': dev_ids['tester'], 'role': 'tester'},
                ],
            },
            {
                'id': 'bug-3', 'iteration_id': 'iter-1', 'requirement_id': 'req-3',
                'title': '管理员列表页分页切换后筛选条件丢失',
                'description': '在管理员反馈列表页，先选择"类型=Bug"筛选，然后点击第2页，筛选条件被重置为全部。',
                'expected_behavior': '切换分页时保持当前筛选条件',
                'actual_behavior': '分页后筛选条件丢失，显示全部数据',
                'severity': 'minor', 'priority': 'p2', 'status': 'confirmed',
                'environment': 'Chrome 120, Windows 11',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['前端', '分页', '状态管理'],
                'created_by': dev_ids['tester'],
                'assignees': [
                    {'user_id': dev_ids['dev4'], 'role': 'fixer'},
                    {'user_id': dev_ids['ecoll'], 'role': 'reviewer'},
                ],
            },
            {
                'id': 'bug-4', 'iteration_id': None, 'requirement_id': 'req-1',
                'title': '首页加载速度慢，首屏时间超过 3 秒',
                'description': 'Chrome DevTools Lighthouse 报告首页 Performance 评分仅 45 分。首屏内容渲染时间 3.2s。',
                'expected_behavior': '首屏时间 < 1.5s，Performance 评分 > 80',
                'actual_behavior': '首屏时间 3.2s，Performance 45 分',
                'severity': 'major', 'priority': 'p2', 'status': 'open',
                'environment': 'Chrome 120, Fast 3G throttling',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['前端', '性能优化'],
                'created_by': dev_ids['dev3'],
                'assignees': [],
            },
        ]
        for bug in bugs_data:
            assignees = bug.pop('assignees', [])
            b = RdBug(project_id=project_id, **bug)
            db.session.add(b)
            for a in assignees:
                db.session.add(RdBugAssignee(
                    bug_id=b.id,
                    user_id=a['user_id'],
                    role=a['role'],
                ))

        # ── 6. 创建评论 ──
        print("创建评论...")
        comments_data = [
            {
                'id': 'comment-1', 'target_type': 'requirement', 'target_id': 'req-1',
                'content': '表单校验规则已经写好，大家看一下 `FeedbackForm.vue` 里的 `rules` 对象，有什么遗漏的校验项吗？',
                'author_id': dev_ids['ecoll'], 'is_pinned': False,
                'days_ago': 10,
            },
            {
                'id': 'comment-2', 'target_type': 'requirement', 'target_id': 'req-1',
                'parent_id': 'comment-1',
                'content': '我看了下，建议加上**联系方式去重校验**，同一个邮箱重复提交时需要提示用户"该邮箱已有反馈记录"。',
                'author_id': dev_ids['dev4'], 'is_pinned': False,
                'days_ago': 9,
            },
            {
                'id': 'comment-3', 'target_type': 'requirement', 'target_id': 'req-1',
                'parent_id': 'comment-1',
                'content': '还有图片上传的大小也需要前端校验一下，后端已经做了 5MB 限制，前端也加一下避免用户传了才发现。',
                'author_id': dev_ids['dev2'], 'is_pinned': False,
                'days_ago': 8,
            },
            {
                'id': 'comment-4', 'target_type': 'requirement', 'target_id': 'req-2',
                'content': 'API 设计文档已更新到 Swagger，接口路径统一使用 `/api/v1/feedback`，请大家 review。',
                'author_id': dev_ids['dev2'], 'is_pinned': True,
                'days_ago': 7,
            },
            {
                'id': 'comment-5', 'target_type': 'requirement', 'target_id': 'req-2',
                'parent_id': 'comment-4',
                'content': '建议把反馈更新接口的权限粒度细化一下，不是所有字段都能被普通用户修改。',
                'author_id': dev_ids['dev3'], 'is_pinned': False,
                'days_ago': 6,
            },
            {
                'id': 'comment-6', 'target_type': 'bug', 'target_id': 'bug-1',
                'content': '已定位问题：Safari 对 `button[type="submit"]` 在 shadow DOM 中的行为有差异。修复中。',
                'author_id': dev_ids['ecoll'], 'is_pinned': False,
                'days_ago': 4,
            },
            {
                'id': 'comment-7', 'target_type': 'requirement', 'target_id': 'req-3',
                'content': '列表页需要考虑移动端响应式，屏幕宽度小于 768px 时切换为卡片视图。',
                'author_id': dev_ids['dev4'], 'is_pinned': False,
                'days_ago': 3,
            },
        ]
        for c in comments_data:
            db.session.add(RdComment(
                id=c['id'],
                project_id=project_id,
                target_type=c['target_type'],
                target_id=c['target_id'],
                parent_id=c.get('parent_id'),
                content=c['content'],
                content_type='markdown',
                author_id=c['author_id'],
                is_pinned=c['is_pinned'],
                created_at=NOW - timedelta(days=c['days_ago']),
            ))

        # ── 7. 创建分支 ──
        print("创建分支...")
        branches_data = [
            {
                'id': 'br-1', 'repo_id': 'repo-1',
                'branch_name': 'feature/REQ-001-feedback-form',
                'base_branch': 'develop',
                'source_type': 'requirement', 'source_id': 'req-1',
                'status': 'active', 'created_by': dev_ids['ecoll'],
                'days_ago': 13,
            },
            {
                'id': 'br-2', 'repo_id': 'repo-1',
                'branch_name': 'feature/REQ-002-feedback-api',
                'base_branch': 'develop',
                'source_type': 'requirement', 'source_id': 'req-2',
                'status': 'active', 'created_by': dev_ids['dev2'],
                'days_ago': 12,
            },
            {
                'id': 'br-3', 'repo_id': 'repo-1',
                'branch_name': 'fix/BUG-001-safari-submit',
                'base_branch': 'develop',
                'source_type': 'bug', 'source_id': 'bug-1',
                'status': 'active', 'created_by': dev_ids['ecoll'],
                'days_ago': 4,
            },
            {
                'id': 'br-4', 'repo_id': 'repo-1',
                'branch_name': 'feature/REQ-003-admin-list',
                'base_branch': 'develop',
                'source_type': 'requirement', 'source_id': 'req-3',
                'status': 'active', 'created_by': dev_ids['ecoll'],
                'days_ago': 6,
            },
        ]
        for br in branches_data:
            db.session.add(RdBranch(
                id=br['id'],
                project_id=project_id,
                repo_id=br['repo_id'],
                branch_name=br['branch_name'],
                base_branch=br['base_branch'],
                source_type=br['source_type'],
                source_id=br['source_id'],
                status=br['status'],
                created_by=br['created_by'],
                created_at=NOW - timedelta(days=br['days_ago']),
            ))

        # ── 8. 创建活动日志 ──
        print("创建活动日志...")
        activities_data = [
            {'target_type': 'project', 'target_id': project_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了项目', 'days_ago': 30},
            {'target_type': 'iteration', 'target_id': 'iter-3', 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了 Sprint 0', 'days_ago': 30},
            {'target_type': 'iteration', 'target_id': 'iter-3', 'action': 'status_changed',
             'actor_id': dev_ids['ecoll'], 'detail': 'Sprint 0 已完成', 'days_ago': 16},
            {'target_type': 'iteration', 'target_id': 'iter-1', 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了 Sprint 1', 'days_ago': 15},
            {'target_type': 'requirement', 'target_id': 'req-1', 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了需求：反馈提交表单页面', 'days_ago': 14},
            {'target_type': 'requirement', 'target_id': 'req-2', 'action': 'created',
             'actor_id': dev_ids['dev2'], 'detail': '创建了需求：反馈数据 API', 'days_ago': 14},
            {'target_type': 'requirement', 'target_id': 'req-1-1', 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了子需求：反馈类型选择器组件', 'days_ago': 14},
            {'target_type': 'requirement', 'target_id': 'req-1-2', 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了子需求：图片上传与预览组件', 'days_ago': 14},
            {'target_type': 'requirement', 'target_id': 'req-1-1', 'action': 'status_changed',
             'actor_id': dev_ids['ecoll'], 'detail': '反馈类型选择器组件 → 已完成', 'days_ago': 7},
            {'target_type': 'requirement', 'target_id': 'req-1', 'action': 'status_changed',
             'actor_id': dev_ids['ecoll'], 'detail': '反馈提交表单页面 → 审查中', 'days_ago': 2},
            {'target_type': 'bug', 'target_id': 'bug-1', 'action': 'created',
             'actor_id': dev_ids['tester'], 'detail': '提交了Bug：Safari 下提交按钮无响应', 'days_ago': 5},
            {'target_type': 'bug', 'target_id': 'bug-2', 'action': 'created',
             'actor_id': dev_ids['tester'], 'detail': '提交了Bug：API 500 错误', 'days_ago': 8},
            {'target_type': 'bug', 'target_id': 'bug-2', 'action': 'status_changed',
             'actor_id': dev_ids['dev2'], 'detail': 'Bug 已修复', 'days_ago': 3},
            {'target_type': 'requirement', 'target_id': 'req-4', 'action': 'created',
             'actor_id': dev_ids['dev3'], 'detail': '创建了需求：反馈自动分类引擎', 'days_ago': 1},
            {'target_type': 'requirement', 'target_id': 'req-5', 'action': 'created',
             'actor_id': dev_ids['dev2'], 'detail': '创建了需求：邮件通知服务', 'days_ago': 1},
            {'target_type': 'iteration', 'target_id': 'iter-2', 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了 Sprint 2', 'days_ago': 1},
        ]
        for a in activities_data:
            db.session.add(RdActivityLog(
                project_id=project_id,
                target_type=a['target_type'],
                target_id=a['target_id'],
                action=a['action'],
                actor_id=a['actor_id'],
                new_value={'detail': a['detail']},
                created_at=NOW - timedelta(days=a['days_ago']),
            ))

        db.session.commit()
        print("\n[SUCCESS] Seed data written!")
        print(f"  项目: 1 (用户反馈系统) — 属于 Ecoll ({ecoll_id})")
        print(f"  成员: {len(members_data)}")
        print(f"  迭代: {len(iterations_data)}")
        print(f"  需求: {len(requirements_data)}")
        print(f"  Bug: {len(bugs_data)}")
        print(f"  评论: {len(comments_data)}")
        print(f"  分支: {len(branches_data)}")
        print(f"  活动日志: {len(activities_data)}")
        print(f"\n  Ecoll ({dev_ids['ecoll']}) — 项目所有者")
        print(f"  张三 ({dev_ids['dev1']}) — 前端开发")
        print(f"  李四 ({dev_ids['dev2']}) — 后端开发")
        print(f"  王五 ({dev_ids['dev3']}) — 全栈开发")
        print(f"  赵六 ({dev_ids['dev4']}) — 前端开发")
        print(f"  陈测试 ({dev_ids['tester']}) — 测试工程师")
        print(f"  周审查 ({dev_ids['reviewer']}) — 代码审查")
        print(f"\n  所有用户密码: weagent123")


if __name__ == '__main__':
    seed()
