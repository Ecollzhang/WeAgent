"""
教学管理系统 — 种子数据脚本.
用法: cd backend/services/rd && python seed_edu.py
只新增数据，不清空已有数据。
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

import database
database.init_db(db)

from models import (
    RdProject, RdProjectMember, RdIteration, RdRequirement,
    RdRequirementAssignee, RdBug, RdBugAssignee, RdComment,
    RdBranch, RdActivityLog
)

NOW = datetime.utcnow()


def _make_pw_hash(password):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)


def _make_uuid(seed):
    return str(uuid.UUID(hashlib.md5(seed.encode()).hexdigest()))


def ensure_users(main_db_conn):
    """确保 weagent 主库中存在所需用户."""
    import pymysql
    cursor = main_db_conn.cursor(pymysql.cursors.DictCursor)

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

    print("连接主库 weagent...")
    main_conn = pymysql.connect(
        host=Cfg.MYSQL_HOST, port=Cfg.MYSQL_PORT,
        user=Cfg.MYSQL_USER, password=Cfg.MYSQL_PASSWORD,
        database='weagent', charset='utf8mb4',
    )
    users = ensure_users(main_conn)
    main_conn.close()

    ecoll_id = users['Ecoll']['id']
    dev_ids = {
        'ecoll': ecoll_id,
        'frontend_lead': users['张三']['id'],
        'backend_lead': users['李四']['id'],
        'fullstack': users['王五']['id'],
        'frontend_dev': users['赵六']['id'],
        'tester': users['陈测试']['id'],
        'reviewer': users['周审查']['id'],
    }

    project_id = _make_uuid('edu-project-2026')

    with app.app_context():
        db.create_all()

        # ════════════════════════════════════════════════════════
        #  0. 检查是否已存在，存在则先删除
        # ════════════════════════════════════════════════════════
        existing = RdProject.query.get(project_id)
        if existing:
            print(f"\n项目 '教学管理系统' 已存在，正在删除旧数据...")
            # 删除关联数据（大部分有 cascade 但手动遍历更安全）
            RdRequirementAssignee.query.filter(
                RdRequirementAssignee.requirement_id.in_(
                    db.session.query(RdRequirement.id).filter(RdRequirement.project_id == project_id)
                )
            ).delete(synchronize_session='fetch')
            RdRequirement.query.filter_by(project_id=project_id).delete()
            RdBugAssignee.query.filter(
                RdBugAssignee.bug_id.in_(
                    db.session.query(RdBug.id).filter(RdBug.project_id == project_id)
                )
            ).delete(synchronize_session='fetch')
            RdBug.query.filter_by(project_id=project_id).delete()
            RdComment.query.filter_by(project_id=project_id).delete()
            RdIteration.query.filter_by(project_id=project_id).delete()
            RdBranch.query.filter_by(project_id=project_id).delete()
            RdActivityLog.query.filter_by(project_id=project_id).delete()
            RdProjectMember.query.filter_by(project_id=project_id).delete()
            db.session.delete(existing)
            db.session.flush()
            print("  旧数据已删除")

        # ════════════════════════════════════════════════════════
        #  1. 项目
        # ════════════════════════════════════════════════════════
        print("\n创建项目：教学管理系统 (owner=Ecoll)")
        project = RdProject(
            id=project_id,
            workspace_id='ws-default',
            user_id=ecoll_id,
            name='教学管理系统',
            description=(
                '面向高校的综合性教学管理平台，涵盖课程管理、学生档案、排课选课、'
                '成绩录入、考勤追踪、数据看板等核心教务功能。支持管理员、教师、学生'
                '三级角色权限，旨在提升教务管理效率与教学数据透明度。'
            ),
            tech_stack={
                'frontend': 'Vue 3 + Element Plus + ECharts',
                'backend': 'Flask + SQLAlchemy + Celery',
                'database': 'MySQL 8.0 + Redis',
                'deployment': 'Docker Compose + Nginx',
            },
            coding_standards=(
                '1. ESLint (airbnb-base) + Prettier 统一代码风格\n'
                '2. Git Commit 遵循 Conventional Commits (feat/fix/docs/refactor)\n'
                '3. 后端 API 遵循 RESTful 规范，统一返回 `{code, message, data}` 格式\n'
                '4. 所有数据库操作使用 ORM，禁止拼接 SQL 字符串\n'
                '5. 敏感数据（密码、成绩）加密存储或脱敏展示\n'
                '6. 前端组件必须编写 Props 类型和默认值\n'
                '7. 关键业务流程（选课、成绩录入）必须有单元测试覆盖'
            ),
            status='active',
            visibility='private',
        )
        db.session.add(project)
        db.session.flush()
        print(f"  项目 ID: {project_id}")

        # ════════════════════════════════════════════════════════
        #  2. 成员
        # ════════════════════════════════════════════════════════
        print("创建项目成员...")
        members_data = [
            {'user_id': dev_ids['ecoll'], 'role': 'owner'},
            {'user_id': dev_ids['backend_lead'], 'role': 'admin'},
            {'user_id': dev_ids['frontend_lead'], 'role': 'developer'},
            {'user_id': dev_ids['frontend_dev'], 'role': 'developer'},
            {'user_id': dev_ids['reviewer'], 'role': 'developer'},
            {'user_id': dev_ids['tester'], 'role': 'viewer'},
        ]
        for m in members_data:
            db.session.add(RdProjectMember(
                project_id=project_id,
                user_id=m['user_id'],
                role=m['role'],
            ))

        # ════════════════════════════════════════════════════════
        #  3. 迭代
        # ════════════════════════════════════════════════════════
        print("创建迭代...")
        iter1_id = _make_uuid('edu-iter-1')
        iter2_id = _make_uuid('edu-iter-2')
        iter3_id = _make_uuid('edu-iter-3')

        iterations_data = [
            {
                'id': iter1_id,
                'name': 'Sprint 1 — 基础数据管理',
                'goal': (
                    '## 迭代目标\n\n'
                    '搭建教学管理系统的**基础数据层**，完成课程、学生、教师、班级四大核心实体的 CRUD 功能。\n\n'
                    '### 核心交付\n\n'
                    '| 模块 | 关键功能 | 负责人 | 工时 |\n'
                    '|------|---------|--------|------|\n'
                    '| 课程管理 | 课程创建/编辑/删除，含编号、名称、学分、学时、院系、课程描述 | 张三 | 20h |\n'
                    '| 学生档案 | 学生信息录入/批量导入/查询筛选，支持学号、班级、专业、入学年份 | 王五 | 18h |\n'
                    '| 教师档案 | 教师工号、姓名、职称、院系、研究方向管理 | 李四 | 12h |\n'
                    '| 班级管理 | 班级创建、学生分配、班主任指派、班级课表查看 | 赵六 | 16h |\n\n'
                    '### 验收标准\n'
                    '- 所有列表页支持分页、搜索、排序、筛选\n'
                    '- 表单支持前端校验 + 后端校验双层保障\n'
                    '- 批量导入支持 Excel 模板下载和数据校验\n'
                    '- API 文档通过 Swagger 自动生成\n\n'
                    '`预计工时: 66h` | `优先级: P0` | `开始: 2026-08-01` | `结束: 2026-08-14`'
                ),
                'start_date': '2026-08-01', 'end_date': '2026-08-14',
                'status': 'active', 'sort_order': 1,
            },
            {
                'id': iter2_id,
                'name': 'Sprint 2 — 教务核心功能',
                'goal': (
                    '## 迭代目标\n\n'
                    '实现教学管理的**核心业务闭环**：排课 → 选课 → 上课 → 考核 → 成绩。\n\n'
                    '### 核心交付\n\n'
                    '| 模块 | 关键功能 | 负责人 | 工时 |\n'
                    '|------|---------|--------|------|\n'
                    '| 排课系统 | 为课程分配教师/教室/时间段，自动冲突检测（教师/教室/班级三重校验） | 赵六 | 24h |\n'
                    '| 学生选课 | 课程浏览/搜索，选课/退课，学分上限校验，选课结果实时展示 | 王五 | 20h |\n'
                    '| 成绩管理 | 教师录入成绩（平时30%+期中30%+期末40%），自动计算总评，成绩统计分析 | 张三 | 22h |\n'
                    '| 考勤管理 | 课堂点名/签到，请假在线审批，缺勤自动预警（累计3次触发通知） | 李四 | 16h |\n\n'
                    '### 验收标准\n'
                    '- 排课冲突检测准确率 100%，冲突时给出明确提示和建议时间段\n'
                    '- 选课系统支持 500 并发学生同时选课不崩溃\n'
                    '- 成绩录入支持批量导入和单条编辑，自动计算加权总分\n'
                    '- 考勤数据实时同步到学生端和家长端（短信/微信通知）\n\n'
                    '`预计工时: 82h` | `优先级: P0` | `依赖 Sprint 1` | `开始: 2026-08-15` | `结束: 2026-08-28`'
                ),
                'start_date': '2026-08-15', 'end_date': '2026-08-28',
                'status': 'planning', 'sort_order': 2,
            },
            {
                'id': iter3_id,
                'name': 'Sprint 3 — 数据看板与系统管理',
                'goal': (
                    '## 迭代目标\n\n'
                    '为管理员和教师提供**数据驱动的决策支持**，完善系统权限和通知体系。\n\n'
                    '### 核心交付\n\n'
                    '| 模块 | 关键功能 | 负责人 | 工时 |\n'
                    '|------|---------|--------|------|\n'
                    '| 教学数据看板 | 课程开设统计、学生成绩分布、出勤率趋势、教师工作量分析 | 李四 | 18h |\n'
                    '| 报表导出 | 成绩单PDF生成、班级成绩汇总Excel、选课名单导出 | 王五 | 14h |\n'
                    '| 消息通知中心 | 选课结果推送、成绩发布提醒、补考通知、站内信+邮件双通道 | 张三 | 16h |\n'
                    '| 角色权限管理 | 管理员/教师/学生三级权限，功能级+数据级权限控制 | 赵六 | 20h |\n\n'
                    '### 验收标准\n'
                    '- 数据看板图表实时刷新，支持时间范围筛选和维度切换\n'
                    '- 成绩单PDF格式规范、排版美观，包含学校Logo和公章位置\n'
                    '- 消息通知送达率 > 95%，失败自动重试3次\n'
                    '- 权限控制覆盖所有API端点，未授权访问返回403\n\n'
                    '`预计工时: 68h` | `优先级: P1` | `依赖 Sprint 2` | `开始: 2026-08-29` | `结束: 2026-09-11`'
                ),
                'start_date': '2026-08-29', 'end_date': '2026-09-11',
                'status': 'planning', 'sort_order': 3,
            },
        ]
        for it in iterations_data:
            db.session.add(RdIteration(
                id=it['id'], project_id=project_id,
                name=it['name'], goal=it['goal'],
                start_date=it['start_date'], end_date=it['end_date'],
                status=it['status'], sort_order=it['sort_order'],
            ))

        # ════════════════════════════════════════════════════════
        #  4. 需求
        # ════════════════════════════════════════════════════════
        print("创建需求...")
        r = {}  # requirement IDs

        requirements_data = [
            # ── Sprint 1 ──
            {
                'id': _make_uuid('edu-req-1'), 'iteration_id': iter1_id,
                'title': '课程信息管理模块',
                'description': (
                    '## 功能概述\n\n'
                    '实现课程信息的完整 CRUD 管理，支持课程的多维度属性配置和批量操作。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 课程列表\n'
                    '- 表格展示所有课程，列包含：课程编号、课程名称、学分、学时、所属院系、课程类型（必修/选修/公选）、开设学期\n'
                    '- 工具栏：搜索（课程名称/编号模糊搜索）、院系筛选下拉框、课程类型筛选、每页条数选择\n'
                    '- 支持列排序（按学分、学时）\n\n'
                    '### 2. 课程创建/编辑\n'
                    '- 课程编号自动生成规则：`院系代码-4位年份-3位序号`（如 CS-2026-001）\n'
                    '- 必填项：课程名称、学分（0.5-10）、总学时（8-128）、所属院系、课程类型\n'
                    '- 选填项：课程描述（富文本）、先修课程、适用专业、教材信息、考核方式（考试/考查）\n'
                    '- 学分与学时联动校验：1学分 ≥ 16学时\n\n'
                    '### 3. 批量操作\n'
                    '- 支持 Excel 模板下载 → 批量导入课程\n'
                    '- 批量删除（二次确认）\n'
                    '- 批量修改院系/课程类型\n\n'
                    '### 4. 课程详情页\n'
                    '- 展示课程完整信息 + 选课学生列表 + 授课教师列表\n'
                    '- 关联查看：该课程的历史开课记录和教学评价'
                ),
                'acceptance_criteria': (
                    '1. 课程编号自动生成符合规则，且唯一性校验通过\n'
                    '2. 学分/学时联动校验：1学分 < 16学时时给出红色警告提示\n'
                    '3. Excel批量导入时，表头校验 + 数据格式校验，错误行标红提示\n'
                    '4. 课程列表搜索响应时间 < 500ms（1000条数据内）\n'
                    '5. 批量删除操作有二次确认弹窗，显示即将删除的课程数量\n'
                    '6. 课程详情页正确展示关联的学生和教师数据'
                ),
                'type': 'feature', 'priority': 'p0', 'status': 'in_progress',
                'story_points': 8, 'labels': ['后端', '前端', '课程', '核心功能'],
                'start_date': '2026-08-01', 'due_date': '2026-08-08',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['frontend_lead'],
                'tester_id': dev_ids['reviewer'],
                'assignees': [
                    {'user_id': dev_ids['frontend_lead'], 'role': 'primary'},
                    {'user_id': dev_ids['ecoll'], 'role': 'reviewer'},
                    {'user_id': dev_ids['reviewer'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-req-2'), 'iteration_id': iter1_id,
                'title': '学生信息管理模块',
                'description': (
                    '## 功能概述\n\n'
                    '建立学生电子档案库，支持学生信息的录入、查询、维护和批量管理。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 学生列表\n'
                    '- 展示字段：学号、姓名、性别、班级、专业、入学年份、联系电话、状态（在读/休学/退学/毕业）\n'
                    '- 高级筛选：专业、班级、入学年份、状态组合筛选\n'
                    '- 列表支持按学号、姓名、入学年份排序\n\n'
                    '### 2. 学生信息录入\n'
                    '- 单个新增：完整表单，含学号（自动生成/手动输入）、姓名、性别、身份证号、班级、专业、入学年份、生源地、联系电话、紧急联系人\n'
                    '- 批量导入：下载 Excel 模板 → 填写数据 → 上传 → 系统校验 → 导入预览 → 确认导入\n'
                    '- 照片上传：支持 jpg/png，自动裁剪为 1寸照片尺寸，最大 2MB\n\n'
                    '### 3. 学生详情\n'
                    '- 基本信息 Tab + 选课记录 Tab + 成绩单 Tab + 考勤记录 Tab\n'
                    '- 支持编辑基本信息、学籍异动记录（休学/复学/转专业）\n\n'
                    '### 4. 学籍异动\n'
                    '- 支持：休学、复学、转专业、退学、毕业 五种异动类型\n'
                    '- 异动记录带时间线展示，不可删除只能追加'
                ),
                'acceptance_criteria': (
                    '1. 学号自动生成规则：`4位年份-2位院系-4位序号`，唯一性校验\n'
                    '2. Excel批量导入时，身份证号格式校验、手机号格式校验通过\n'
                    '3. 照片上传后自动裁剪为 150×200 像素，文件大小 < 200KB\n'
                    '4. 学生详情切换 Tab 时数据延迟 < 300ms\n'
                    '5. 学籍异动操作为不可逆操作，有二次确认\n'
                    '6. 敏感信息（身份证号、手机号）仅管理员和本人可见'
                ),
                'type': 'feature', 'priority': 'p0', 'status': 'in_progress',
                'story_points': 8, 'labels': ['后端', '前端', '学生', '核心功能'],
                'start_date': '2026-08-03', 'due_date': '2026-08-12',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['reviewer'],
                'tester_id': dev_ids['frontend_lead'],
                'assignees': [
                    {'user_id': dev_ids['reviewer'], 'role': 'primary'},
                    {'user_id': dev_ids['backend_lead'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-req-3'), 'iteration_id': iter1_id,
                'title': '教师信息管理模块',
                'description': (
                    '## 功能概述\n\n'
                    '管理教师档案信息，支持教师资历、研究方向、授课记录的统一维护。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 教师列表\n'
                    '- 展示：工号、姓名、性别、职称（助教/讲师/副教授/教授）、所属院系、研究方向、联系电话、邮箱\n'
                    '- 搜索：姓名/工号模糊搜索，院系筛选，职称筛选\n\n'
                    '### 2. 教师信息维护\n'
                    '- 基本信息：工号、姓名、性别、出生日期、职称、院系、学历、毕业院校\n'
                    '- 学术信息：研究方向、论文成果、项目经历（Markdown 编辑器）\n'
                    '- 联系方式：办公电话、邮箱、办公地点\n\n'
                    '### 3. 授课记录\n'
                    '- 在教师详情中展示历史授课记录：学期、课程名称、班级、学生数、教学评教分数\n'
                    '- 支持按学期筛选\n\n'
                    '### 4. 工作量统计\n'
                    '- 当前学期：授课门数、总课时、指导论文数\n'
                    '- 图表展示近3年工作量变化趋势'
                ),
                'acceptance_criteria': (
                    '1. 工号唯一性校验，重复时给出明确提示\n'
                    '2. 职称枚举值校验，非法值不可提交\n'
                    '3. 研究方向字段支持 Markdown 语法高亮预览\n'
                    '4. 授课记录自动关联排课和选课数据\n'
                    '5. 工作量统计图表使用 ECharts 渲染，数据准确'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'todo',
                'story_points': 5, 'labels': ['后端', '前端', '教师'],
                'start_date': '2026-08-08', 'due_date': '2026-08-14',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['backend_lead'],
                'assignees': [
                    {'user_id': dev_ids['backend_lead'], 'role': 'primary'},
                    {'user_id': dev_ids['frontend_dev'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-req-4'), 'iteration_id': iter1_id,
                'title': '班级管理模块',
                'description': (
                    '## 功能概述\n\n'
                    '管理教学班级的创建、学生分配、班主任指派和班级课表查询。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 班级列表\n'
                    '- 展示：班级编号、班级名称、所属专业、年级、学生人数、班主任、状态（在读/已毕业）\n'
                    '- 搜索：班级名称模糊搜索、专业筛选、年级筛选\n\n'
                    '### 2. 班级创建\n'
                    '- 必填：班级名称、所属专业、年级、学制（3年/4年/5年）\n'
                    '- 选填：班主任（从教师列表中选择）、班级描述\n'
                    '- 班级编号自动生成：`专业代码-年级-序号`\n\n'
                    '### 3. 学生分配\n'
                    '- 支持将未分配班级的学生批量添加到班级\n'
                    '- 从班级移出学生（需确认）\n'
                    '- 班级间学生调换\n\n'
                    '### 4. 班级课表\n'
                    '- 以周视图展示班级一周课表\n'
                    '- 点击课程卡片跳转到课程详情'
                ),
                'acceptance_criteria': (
                    '1. 班级编号自动生成且唯一\n'
                    '2. 学生分配到班级时，检测学生是否已在其他班级（一个学生只能属于一个班级）\n'
                    '3. 班级课表数据与排课系统实时同步\n'
                    '4. 移除学生时弹出确认框显示学生姓名和学号\n'
                    '5. 班级人数统计实时更新'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'todo',
                'story_points': 5, 'labels': ['后端', '前端', '班级'],
                'start_date': '2026-08-10', 'due_date': '2026-08-14',
                'created_by': dev_ids['frontend_dev'],
                'developer_id': dev_ids['frontend_dev'],
                'assignees': [
                    {'user_id': dev_ids['frontend_dev'], 'role': 'primary'},
                    {'user_id': dev_ids['frontend_lead'], 'role': 'reviewer'},
                ],
            },

            # ── Sprint 2 ──
            {
                'id': _make_uuid('edu-req-5'), 'iteration_id': iter2_id,
                'title': '智能排课系统',
                'description': (
                    '## 功能概述\n\n'
                    '为课程分配教师、教室和时间段，系统自动检测冲突并提供智能建议。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 排课表单\n'
                    '- 选择课程 → 选择授课教师（可多选，支持合班授课）→ 选择教室 → 选择时间段\n'
                    '- 时间段：支持周一至周五，每天 1-2节/3-4节/5-6节/7-8节/9-10节 五个时段\n'
                    '- 起止周：1-16周、1-8周、9-16周 等灵活设置\n\n'
                    '### 2. 冲突检测（三重校验）\n'
                    '- **教师冲突**：同一教师同一时段不能有两门课\n'
                    '- **教室冲突**：同一教室同一时段不能有两门课\n'
                    '- **班级冲突**：同一班级同一时段不能有两门课\n'
                    '- 冲突时红色高亮提示，并推荐可用时间段\n\n'
                    '### 3. 排课看板\n'
                    '- 以周视图/日视图切换展示\n'
                    '- 教室维度：查看每间教室一周的使用情况\n'
                    '- 教师维度：查看每位教师一周的授课安排\n'
                    '- 班级维度：查看每个班级一周的课程表\n\n'
                    '### 4. 调课/停课\n'
                    '- 调课：更换时间/教室，需记录调课原因\n'
                    '- 停课：标记某节课停课，自动通知选课学生\n'
                    '- 调课记录可追溯'
                ),
                'acceptance_criteria': (
                    '1. 排课提交时自动执行三重冲突检测，100% 准确\n'
                    '2. 冲突时给出最多 3 个推荐可用时段（含教室建议）\n'
                    '3. 排课看板三种维度（教室/教师/班级）切换流畅\n'
                    '4. 调课操作自动校验新时间/教室是否冲突\n'
                    '5. 停课后自动向选课学生推送通知\n'
                    '6. 排课数据支持导出为 Excel 课表'
                ),
                'type': 'feature', 'priority': 'p0', 'status': 'in_progress',
                'story_points': 13, 'labels': ['后端', '前端', '排课', '核心功能', '复杂逻辑'],
                'start_date': '2026-08-15', 'due_date': '2026-08-24',
                'created_by': dev_ids['frontend_dev'],
                'developer_id': dev_ids['frontend_dev'],
                'tester_id': dev_ids['frontend_lead'],
                'assignees': [
                    {'user_id': dev_ids['frontend_dev'], 'role': 'primary'},
                    {'user_id': dev_ids['frontend_lead'], 'role': 'reviewer'},
                    {'user_id': dev_ids['backend_lead'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-req-6'), 'iteration_id': iter2_id,
                'title': '学生选课系统',
                'description': (
                    '## 功能概述\n\n'
                    '学生端选课/退课功能，支持课程浏览、搜索、学分校验和选课结果查看。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 课程广场\n'
                    '- 卡片式展示可选课程：课程名称、教师、学分、上课时间地点、已选人数/容量\n'
                    '- 搜索：课程名称/教师姓名模糊搜索\n'
                    '- 筛选：课程类型（必修/选修/公选）、院系、上课时间\n'
                    '- 课程详情弹窗：完整课程信息 + 教学大纲 + 选课同学列表\n\n'
                    '### 2. 选课流程\n'
                    '- 点击"选课" → 校验学分上限（默认 25 学分/学期）→ 校验时间冲突 → 校验课程容量\n'
                    '- 容量已满时提示"该课程已满，是否加入候补名单"\n'
                    '- 选课成功后实时更新已选学分和课程列表\n\n'
                    '### 3. 退课流程\n'
                    '- 在"我的课程"列表中点击退课 → 二次确认 → 校验是否超过退课截止日期\n'
                    '- 退课后自动释放课程名额，候补列表第一名自动补入\n\n'
                    '### 4. 我的课表\n'
                    '- 周视图展示已选课程的时间安排\n'
                    '- 课程卡片颜色区分必修/选修/公选\n'
                    '- 点击课程卡片查看详情\n\n'
                    '### 5. 选课统计\n'
                    '- 实时展示各课程选课人数/容量\n'
                    '- 热门课程排行\n'
                    '- 选课高峰期并发控制（Redis 分布式锁）'
                ),
                'acceptance_criteria': (
                    '1. 学分上限校验：超过25学分时提示"已超出学分上限，请先退选其他课程"\n'
                    '2. 时间冲突检测：新选课程与已选课程时间重叠时提示冲突\n'
                    '3. 课程容量已满时自动进入候补队列，有人退课自动补入\n'
                    '4. 退课截止日期后（开学第3周起）不可退课\n'
                    '5. 500名学生同时选课时系统响应正常，无超时报错\n'
                    '6. 选课结果实时反映在"我的课表"中'
                ),
                'type': 'feature', 'priority': 'p0', 'status': 'todo',
                'story_points': 8, 'labels': ['后端', '前端', '选课', '核心功能', '高并发'],
                'start_date': '2026-08-18', 'due_date': '2026-08-28',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['reviewer'],
                'tester_id': dev_ids['frontend_lead'],
                'assignees': [
                    {'user_id': dev_ids['reviewer'], 'role': 'primary'},
                    {'user_id': dev_ids['frontend_dev'], 'role': 'reviewer'},
                    {'user_id': dev_ids['fullstack'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-req-7'), 'iteration_id': iter2_id,
                'title': '成绩录入与统计分析',
                'description': (
                    '## 功能概述\n\n'
                    '教师在线录入学生成绩，系统自动计算加权总评，并提供多维度成绩分析。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 成绩录入\n'
                    '- 教师选择课程 → 展示该课程选课学生名单 → 逐行录入成绩\n'
                    '- 成绩构成可配置：平时成绩（默认30%）、期中成绩（默认30%）、期末成绩（默认40%）\n'
                    '- 支持百分制（0-100）和五级制（优秀/良好/中等/及格/不及格）\n'
                    '- 自动计算总评成绩 = 平时×权重 + 期中×权重 + 期末×权重\n\n'
                    '### 2. 批量导入\n'
                    '- 下载成绩模板 Excel → 填写成绩 → 上传 → 校验 → 预览 → 确认导入\n'
                    '- 校验：学号存在性、成绩范围、必填项检查\n\n'
                    '### 3. 成绩分析\n'
                    '- 成绩分布直方图（0-59/60-69/70-79/80-89/90-100 五段）\n'
                    '- 班级平均分、最高分、最低分、标准差\n'
                    '- 及格率、优秀率（≥90分）统计\n'
                    '- 与往届同课程成绩对比\n\n'
                    '### 4. 成绩发布与复议\n'
                    '- 教师确认发布后学生端可见\n'
                    '- 学生可申请成绩复议（填写理由）→ 教师审核 → 确认修改或驳回\n'
                    '- 成绩修改记录完整留痕'
                ),
                'acceptance_criteria': (
                    '1. 总评成绩自动计算，保留一位小数，四舍五入\n'
                    '2. 成绩权重可由教师在课程设置中自定义（三项权重之和必须为100%）\n'
                    '3. 批量导入时错误数据标红，显示具体错误原因\n'
                    '4. 成绩分布图使用 ECharts 渲染，支持导出图片\n'
                    '5. 成绩复议流程：学生申请 → 教师审核 → 修改/驳回 → 通知学生\n'
                    '6. 所有成绩修改操作记录日志，可追溯'
                ),
                'type': 'feature', 'priority': 'p0', 'status': 'todo',
                'story_points': 8, 'labels': ['后端', '前端', '成绩', '核心功能'],
                'start_date': '2026-08-20', 'due_date': '2026-08-28',
                'created_by': dev_ids['frontend_lead'],
                'developer_id': dev_ids['frontend_lead'],
                'tester_id': dev_ids['backend_lead'],
                'assignees': [
                    {'user_id': dev_ids['frontend_lead'], 'role': 'primary'},
                    {'user_id': dev_ids['ecoll'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-req-8'), 'iteration_id': iter2_id,
                'title': '考勤管理系统',
                'description': (
                    '## 功能概述\n\n'
                    '支持课堂考勤记录、请假审批和缺勤预警，确保教学秩序和学生出勤率监控。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 课堂考勤\n'
                    '- 教师端：按课程+日期创建考勤记录，学生名单一键勾选（出勤/迟到/早退/缺勤/请假）\n'
                    '- 学生端：查看个人出勤统计和考勤明细\n'
                    '- 支持二维码扫码签到：教师生成动态二维码 → 学生扫码签到 → 自动记录签到时间\n\n'
                    '### 2. 请假管理\n'
                    '- 学生提交请假申请：请假类型（事假/病假/公假）、起止时间、请假理由、附件（如病假证明照片）\n'
                    '- 审批流程：学生提交 → 辅导员审批 → （≥3天）院系领导审批\n'
                    '- 审批通过后自动在对应日期的考勤记录中标记为"请假"\n\n'
                    '### 3. 缺勤预警\n'
                    '- 同一门课程累计缺勤 ≥ 3次 → 系统自动推送预警通知给学生和辅导员\n'
                    '- 累计缺勤 ≥ 课程总学时 1/3 → 标记为"取消考试资格"\n'
                    '- 预警阈值可由管理员配置\n\n'
                    '### 4. 考勤统计\n'
                    '- 按学生/班级/课程/时间段多维度统计\n'
                    '- 出勤率趋势图\n'
                    '- 导出考勤汇总表'
                ),
                'acceptance_criteria': (
                    '1. 二维码签到码每 30 秒自动刷新，防止截图代签\n'
                    '2. 请假审批流支持多级审批，审批节点可配置\n'
                    '3. 缺勤达到预警阈值时，通知在 5 分钟内推送到学生端\n'
                    '4. 考勤统计的数据与明细记录一致，误差为 0\n'
                    '5. 取消考试资格判定：缺勤课时 ≥ 课程总学时的 1/3'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'todo',
                'story_points': 8, 'labels': ['后端', '前端', '考勤', '审批流'],
                'start_date': '2026-08-22', 'due_date': '2026-08-28',
                'created_by': dev_ids['backend_lead'],
                'developer_id': dev_ids['backend_lead'],
                'tester_id': dev_ids['reviewer'],
                'assignees': [
                    {'user_id': dev_ids['backend_lead'], 'role': 'primary'},
                    {'user_id': dev_ids['reviewer'], 'role': 'reviewer'},
                ],
            },

            # ── Sprint 3 ──
            {
                'id': _make_uuid('edu-req-9'), 'iteration_id': iter3_id,
                'title': '教学数据看板',
                'description': (
                    '## 功能概述\n\n'
                    '为管理员和院系领导提供教学数据的可视化大屏，一屏掌握教学全局。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 总览面板\n'
                    '- 顶部指标卡片：在读学生总数、在职教师总数、本学期开设课程数、当前选课总人次\n'
                    '- 数据每 5 分钟自动刷新\n\n'
                    '### 2. 课程维度\n'
                    '- 各院系开设课程数量对比柱状图\n'
                    '- 课程类型分布（必修/选修/公选）饼图\n'
                    '- 课程容量利用率排行榜\n\n'
                    '### 3. 学生维度\n'
                    '- 各专业学生人数分布\n'
                    '- 成绩分段分布（0-59/60-69/70-79/80-89/90-100）\n'
                    '- 出勤率趋势折线图（可按周/月/学期切换）\n\n'
                    '### 4. 教师维度\n'
                    '- 教师职称分布环形图\n'
                    '- 教师工作量排行（授课课时）\n'
                    '- 教学评教平均分趋势\n\n'
                    '### 5. 时间筛选\n'
                    '- 支持按学期、学年切换数据范围\n'
                    '- 支持自定义日期范围'
                ),
                'acceptance_criteria': (
                    '1. 所有图表使用 ECharts 渲染，支持自适应缩放\n'
                    '2. 指标卡片数据与数据库实时一致（缓存 TTL ≤ 5分钟）\n'
                    '3. 图表支持点击下钻（如点击院系 → 查看该院系各专业数据）\n'
                    '4. 页面首次加载时间 < 3 秒\n'
                    '5. 支持将看板数据导出为 PDF 报告'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'backlog',
                'story_points': 5, 'labels': ['前端', '数据可视化', '看板'],
                'start_date': '2026-08-29', 'due_date': '2026-09-05',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['backend_lead'],
                'tester_id': dev_ids['tester'],
                'assignees': [
                    {'user_id': dev_ids['backend_lead'], 'role': 'primary'},
                    {'user_id': dev_ids['reviewer'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-req-10'), 'iteration_id': iter3_id,
                'title': '成绩单与报表导出',
                'description': (
                    '## 功能概述\n\n'
                    '支持生成正式成绩单 PDF 和多种教学统计报表的 Excel 导出。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 个人成绩单（PDF）\n'
                    '- 模板包含：学校Logo + 标题"学生成绩单" + 学生基本信息 + 成绩表格 + 公章位置\n'
                    '- 成绩表格：学期、课程名称、学分、成绩、绩点\n'
                    '- 自动计算 GPA 和总学分\n'
                    '- 支持批量生成（按班级/专业一键生成所有学生成绩单）\n\n'
                    '### 2. 班级成绩汇总（Excel）\n'
                    '- 列为：学号、姓名、各科成绩、平均分、排名\n'
                    '- 自动标注不及格科目（红色字体）\n'
                    '- 自动生成汇总行：平均分、最高分、最低分、及格率\n\n'
                    '### 3. 选课名单导出\n'
                    '- 按课程导出选课学生名单 Excel\n'
                    '- 包含：学号、姓名、班级、专业、选课时间\n\n'
                    '### 4. 考勤汇总导出\n'
                    '- 按班级导出考勤汇总表\n'
                    '- 包含：出勤/迟到/早退/请假/缺勤 次数统计'
                ),
                'acceptance_criteria': (
                    '1. PDF成绩单格式规范，A4纸张适配，支持直接打印\n'
                    '2. GPA计算标准：4分制，90-100=4.0, 85-89=3.7, 82-84=3.3, 78-81=3.0, ...\n'
                    '3. Excel导出中文不乱码（UTF-8 BOM 编码）\n'
                    '4. 不及格科目自动红色字体标注\n'
                    '5. 批量生成100份成绩单 PDF 耗时 < 30 秒'
                ),
                'type': 'feature', 'priority': 'p2', 'status': 'backlog',
                'story_points': 5, 'labels': ['后端', '报表', 'PDF', 'Excel'],
                'start_date': '2026-09-02', 'due_date': '2026-09-08',
                'created_by': dev_ids['reviewer'],
                'developer_id': dev_ids['reviewer'],
                'assignees': [
                    {'user_id': dev_ids['reviewer'], 'role': 'primary'},
                    {'user_id': dev_ids['frontend_lead'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-req-11'), 'iteration_id': iter3_id,
                'title': '消息通知中心',
                'description': (
                    '## 功能概述\n\n'
                    '构建统一的消息通知系统，支持站内信和邮件双通道，覆盖选课、成绩、考勤、公告等场景。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 通知类型\n'
                    '- **系统通知**：选课结果、成绩发布、补考安排、学籍异动\n'
                    '- **提醒通知**：选课截止提醒、缴费提醒、缺勤预警\n'
                    '- **公告通知**：院系公告、教务通知、活动通知\n\n'
                    '### 2. 通知通道\n'
                    '- **站内信**：系统内消息中心查看，支持已读/未读状态\n'
                    '- **邮件通知**：自动发送到用户绑定邮箱\n'
                    '- 用户可在设置中配置通知偏好（开启/关闭各类通知）\n\n'
                    '### 3. 消息模板\n'
                    '- 管理员可在线编辑各类消息模板\n'
                    '- 模板变量：`{学生姓名}`、`{课程名称}`、`{成绩}`、`{日期}` 等\n'
                    '- 支持 HTML 富文本模板\n\n'
                    '### 4. 消息中心 UI\n'
                    '- 顶部导航栏铃铛图标 + 未读消息数角标\n'
                    '- 点击展开消息列表（最近20条）\n'
                    '- 点击"查看全部"进入消息中心页面\n'
                    '- 支持消息分类筛选、标记已读/全部已读\n\n'
                    '### 5. 发送策略\n'
                    '- 即时发送：选课成功、成绩发布\n'
                    '- 定时发送：选课截止前24小时提醒\n'
                    '- 失败重试：邮件发送失败自动重试3次，间隔5分钟'
                ),
                'acceptance_criteria': (
                    '1. 通知触发后 1 分钟内到达站内信\n'
                    '2. 邮件送达率 > 95%\n'
                    '3. 消息模板变量正确替换，无残留 `{xxx}` 占位符\n'
                    '4. 未读消息角标数字实时更新\n'
                    '5. 用户可分别控制各类通知的开启/关闭\n'
                    '6. 消息发送失败有日志记录和告警'
                ),
                'type': 'feature', 'priority': 'p2', 'status': 'backlog',
                'story_points': 5, 'labels': ['后端', '前端', '通知', '邮件'],
                'start_date': '2026-09-05', 'due_date': '2026-09-11',
                'created_by': dev_ids['frontend_lead'],
                'developer_id': dev_ids['frontend_lead'],
                'tester_id': dev_ids['reviewer'],
                'assignees': [
                    {'user_id': dev_ids['frontend_lead'], 'role': 'primary'},
                    {'user_id': dev_ids['backend_lead'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-req-12'), 'iteration_id': iter3_id,
                'title': '角色权限管理系统',
                'description': (
                    '## 功能概述\n\n'
                    '实现管理员、教师、学生三级角色的精细化权限控制，确保数据安全和操作合规。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 角色定义\n'
                    '- **超级管理员**：全部功能权限 + 用户管理 + 系统配置\n'
                    '- **院系管理员**：本院系数据范围内的管理权限\n'
                    '- **教师**：课程管理、成绩录入、考勤管理（仅限自己授课的班级）\n'
                    '- **辅导员**：学生管理、请假审批（仅限自己负责的班级）\n'
                    '- **学生**：选课、查看成绩、查看课表、请假申请（仅限个人数据）\n\n'
                    '### 2. 权限模型\n'
                    '- RBAC（基于角色的访问控制）：用户 → 角色 → 权限\n'
                    '- 权限粒度：页面级（菜单可见性）+ 操作级（按钮/API控制）+ 数据级（本院系/本班级/本人）\n'
                    '- 权限树管理界面：管理员可在线配置权限分配\n\n'
                    '### 3. 权限校验\n'
                    '- 前端：路由守卫 + 指令（v-permission）控制按钮显示\n'
                    '- 后端：装饰器/中间件校验每个 API 请求的权限\n'
                    '- 数据级权限：API 自动过滤数据范围（如教师只能看到自己授课班级的成绩）\n\n'
                    '### 4. 操作日志\n'
                    '- 记录所有敏感操作：成绩修改、权限变更、数据删除\n'
                    '- 日志包含：操作人、操作时间、IP地址、操作内容、操作结果'
                ),
                'acceptance_criteria': (
                    '1. 未授权用户访问受限页面时显示 403 页面\n'
                    '2. API 层权限校验覆盖率达到 100%\n'
                    '3. 教师A无法查看/修改教师B授课班级的成绩\n'
                    '4. 学生只能查看自己的成绩和考勤，无法查看其他同学数据\n'
                    '5. 权限变更后实时生效（无需重新登录）\n'
                    '6. 敏感操作日志保留期 ≥ 6 个月'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'backlog',
                'story_points': 8, 'labels': ['后端', '前端', '权限', '安全'],
                'start_date': '2026-08-29', 'due_date': '2026-09-11',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['frontend_dev'],
                'tester_id': dev_ids['backend_lead'],
                'assignees': [
                    {'user_id': dev_ids['frontend_dev'], 'role': 'primary'},
                    {'user_id': dev_ids['ecoll'], 'role': 'reviewer'},
                ],
            },

            # ── 子需求 ──
            {
                'id': _make_uuid('edu-sub-1-1'), 'iteration_id': iter1_id,
                'parent_id': _make_uuid('edu-req-1'),
                'title': '课程搜索与筛选功能',
                'description': (
                    '## 功能概述\n\n'
                    '为课程列表提供高性能的多条件模糊搜索和组合筛选功能。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 搜索栏\n'
                    '- 顶部搜索框支持课程名称、课程编号的模糊搜索\n'
                    '- 防抖输入（300ms），实时展示搜索结果\n'
                    '- 搜索关键词高亮显示在结果列表中\n\n'
                    '### 2. 高级筛选\n'
                    '- 院系下拉筛选（单选/多选）\n'
                    '- 课程类型筛选：必修/选修/公选\n'
                    '- 学分范围滑块：0.5 - 10\n'
                    '- 开设学期筛选\n'
                    '- 筛选条件支持组合使用\n\n'
                    '### 3. 结果展示\n'
                    '- 搜索结果数量实时显示\n'
                    '- 支持重置所有筛选条件\n'
                    '- 筛选条件保存到 URL query 参数，支持分享链接'
                ),
                'acceptance_criteria': (
                    '1. 搜索响应时间 < 300ms（1000条数据内）\n'
                    '2. 多条件组合筛选结果准确率 100%\n'
                    '3. 搜索关键词在结果中正确高亮\n'
                    '4. 筛选条件通过 URL 参数持久化'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'done',
                'story_points': 3, 'labels': ['前端', '搜索', '课程'],
                'start_date': '2026-08-04', 'due_date': '2026-08-08',
                'created_by': dev_ids['frontend_lead'],
                'developer_id': dev_ids['frontend_lead'],
                'assignees': [
                    {'user_id': dev_ids['frontend_lead'], 'role': 'primary'},
                ],
            },
            {
                'id': _make_uuid('edu-sub-1-2'), 'iteration_id': iter1_id,
                'parent_id': _make_uuid('edu-req-1'),
                'title': '课程批量导入导出',
                'description': (
                    '## 功能概述\n\n'
                    '支持通过 Excel 模板批量导入课程数据，以及将课程列表导出为 Excel。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 模板下载\n'
                    '- 提供标准 Excel 模板下载（含表头说明和示例数据）\n'
                    '- 模板包含字段校验规则（数据验证下拉、格式限制）\n\n'
                    '### 2. 批量导入\n'
                    '- 上传 Excel → 前端预览 → 数据校验 → 确认导入\n'
                    '- 校验规则：课程编号唯一性、学分范围、学时范围、院系存在性\n'
                    '- 错误行标红，鼠标悬停显示具体错误原因\n'
                    '- 支持部分导入（跳过错误行，导入正确行）\n\n'
                    '### 3. 导出\n'
                    '- 支持导出当前筛选结果为 Excel\n'
                    '- 支持选择导出列\n'
                    '- 文件名格式：`课程列表_2026-08-01.xlsx`'
                ),
                'acceptance_criteria': (
                    '1. 模板下载即用，无需手动调整格式\n'
                    '2. 导入 500 条课程数据 < 10 秒\n'
                    '3. 数据校验准确率 100%，无漏检/误报\n'
                    '4. 部分导入后显示"成功X条，失败Y条"汇总\n'
                    '5. 导出文件可在 Excel/WPS 中正常打开，中文不乱码'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'done',
                'story_points': 3, 'labels': ['后端', '前端', 'Excel', '课程'],
                'start_date': '2026-08-06', 'due_date': '2026-08-10',
                'created_by': dev_ids['backend_lead'],
                'developer_id': dev_ids['backend_lead'],
                'assignees': [
                    {'user_id': dev_ids['backend_lead'], 'role': 'primary'},
                ],
            },
            {
                'id': _make_uuid('edu-sub-2-1'), 'iteration_id': iter1_id,
                'parent_id': _make_uuid('edu-req-2'),
                'title': '学生照片管理功能',
                'description': (
                    '## 功能概述\n\n'
                    '实现学生证件照的上传、裁剪、存储和展示功能。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 照片上传\n'
                    '- 支持拖拽上传和点击上传\n'
                    '- 支持 jpg、png 格式，单文件最大 2MB\n'
                    '- 上传前前端预检：文件类型、文件大小\n\n'
                    '### 2. 照片裁剪\n'
                    '- 集成 cropper.js，支持拖拽裁剪区域\n'
                    '- 预设 1寸（150×200px）和 2寸（200×280px）裁剪比例\n'
                    '- 实时预览裁剪效果\n\n'
                    '### 3. 照片存储\n'
                    '- 裁剪后自动压缩至 < 200KB\n'
                    '- 存储到阿里云 OSS / 本地文件系统（可配置）\n'
                    '- 生成缩略图用于列表展示（60×80px）\n\n'
                    '### 4. 照片展示\n'
                    '- 学生列表显示缩略图\n'
                    '- 鼠标悬停放大预览\n'
                    '- 学生详情页显示完整照片'
                ),
                'acceptance_criteria': (
                    '1. 照片裁剪后尺寸精确为 150×200px（1寸）\n'
                    '2. 裁剪后文件大小 < 200KB\n'
                    '3. 上传非图片文件时前端正确拦截并提示\n'
                    '4. 照片加载失败时显示默认头像占位图\n'
                    '5. 批量上传 50 张照片无超时'
                ),
                'type': 'feature', 'priority': 'p2', 'status': 'done',
                'story_points': 2, 'labels': ['前端', '图片处理', '学生'],
                'start_date': '2026-08-07', 'due_date': '2026-08-11',
                'created_by': dev_ids['frontend_dev'],
                'developer_id': dev_ids['frontend_dev'],
                'assignees': [
                    {'user_id': dev_ids['frontend_dev'], 'role': 'primary'},
                ],
            },
            {
                'id': _make_uuid('edu-sub-2-2'), 'iteration_id': iter1_id,
                'parent_id': _make_uuid('edu-req-2'),
                'title': '学籍异动管理',
                'description': (
                    '## 功能概述\n\n'
                    '管理学生在校期间的学籍状态变更，支持异动申请、审批和时间线追溯。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 异动类型\n'
                    '- 休学：学生申请 → 辅导员审批 → 院系审批 → 教务处备案\n'
                    '- 复学：学生申请 → 教务处审批 → 分配新班级\n'
                    '- 转专业：学生申请 → 转出院系审批 → 转入院系审批 → 教务处审批\n'
                    '- 退学：学生/家长申请 → 辅导员确认 → 院系审批 → 教务处审批 → 校长审批\n'
                    '- 毕业：系统自动判定（修满学分 + 无欠费 + 无违纪）\n\n'
                    '### 2. 异动记录\n'
                    '- 每条异动记录包含：异动类型、申请日期、生效日期、申请原因、审批状态、审批链\n'
                    '- 时间线展示：按时间倒序展示所有异动记录\n'
                    '- 异动记录不可删除，只能追加新的异动来覆盖（如复学覆盖休学）\n\n'
                    '### 3. 审批流程\n'
                    '- 可视化的审批进度条\n'
                    '- 每个审批节点显示：审批人、审批时间、审批意见\n'
                    '- 审批超时自动提醒（3个工作日未审批）'
                ),
                'acceptance_criteria': (
                    '1. 异动记录不可物理删除，删除操作实际为软删除\n'
                    '2. 审批流程每个节点有明确的操作人和时间戳\n'
                    '3. 转专业审批涉及两个院系，流程正确\n'
                    '4. 毕业判定条件：学分修满 AND 无欠费 AND 无未处理违纪\n'
                    '5. 审批超时提醒在超时后 1 小时内发送'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'todo',
                'story_points': 5, 'labels': ['后端', '前端', '审批流', '学生'],
                'start_date': '2026-08-09', 'due_date': '2026-08-14',
                'created_by': dev_ids['ecoll'],
                'developer_id': dev_ids['reviewer'],
                'tester_id': dev_ids['frontend_dev'],
                'assignees': [
                    {'user_id': dev_ids['reviewer'], 'role': 'primary'},
                    {'user_id': dev_ids['ecoll'], 'role': 'reviewer'},
                ],
            },
            {
                'id': _make_uuid('edu-sub-6-1'), 'iteration_id': iter2_id,
                'parent_id': _make_uuid('edu-req-6'),
                'title': '选课冲突检测',
                'description': (
                    '## 功能概述\n\n'
                    '在选课过程中实时检测时间冲突、课程容量、先修课程等约束条件。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 时间冲突检测\n'
                    '- 选课时实时比对学生已有课表，检测上课时间重叠\n'
                    '- 冲突课程标红，显示冲突详情（课程名 + 时间 + 地点）\n'
                    '- 提供"仍要选择"选项（允许冲突选课但需教师确认）\n\n'
                    '### 2. 容量检测\n'
                    '- 实时显示课程已选人数/容量上限\n'
                    '- 容量已满时阻止选课，提示加入候补\n'
                    '- 容量利用率进度条（绿色<50%、黄色50-80%、红色>80%、灰色=100%）\n\n'
                    '### 3. 先修课程检测\n'
                    '- 检测学生是否已完成课程要求的先修课程\n'
                    '- 未完成先修课程时警告提示\n\n'
                    '### 4. 学分上限检测\n'
                    '- 每学期选课学分上限（默认25学分）\n'
                    '- 超过上限时阻止选课并提示"已达到本学期学分上限"'
                ),
                'acceptance_criteria': (
                    '1. 时间冲突检测准确率 100%，无漏检\n'
                    '2. 同一时间段不同课程冲突时正确标红显示\n'
                    '3. 容量检测实时刷新（延迟 < 2 秒）\n'
                    '4. 先修课程检测覆盖所有配置了先修关系的课程\n'
                    '5. 学分上限可由管理员在系统设置中配置'
                ),
                'type': 'feature', 'priority': 'p1', 'status': 'todo',
                'story_points': 3, 'labels': ['后端', '选课', '校验'],
                'start_date': '2026-08-18', 'due_date': '2026-08-22',
                'created_by': dev_ids['backend_lead'],
                'developer_id': dev_ids['backend_lead'],
                'assignees': [
                    {'user_id': dev_ids['backend_lead'], 'role': 'primary'},
                ],
            },
            {
                'id': _make_uuid('edu-sub-6-2'), 'iteration_id': iter2_id,
                'parent_id': _make_uuid('edu-req-6'),
                'title': '候补队列管理',
                'description': (
                    '## 功能概述\n\n'
                    '当课程容量已满时，学生可加入候补队列，有人退课后按队列顺序自动补入。\n\n'
                    '## 详细功能\n\n'
                    '### 1. 候补加入\n'
                    '- 课程满员后选课按钮变为"加入候补"\n'
                    '- 显示当前候补人数和排队位置\n'
                    '- 每人同时最多候补 3 门课程\n\n'
                    '### 2. 候补队列\n'
                    '- 按申请时间排序（先到先得）\n'
                    '- 有学生退课时，自动通知队首学生并预留名额 24 小时\n'
                    '- 24小时内未确认 → 名额顺延给下一位\n\n'
                    '### 3. 通知机制\n'
                    '- 候补成功通知："你已进入《XXX》候补队列，当前排名第 N 位"\n'
                    '- 补入通知："《XXX》有空余名额，请在 24 小时内确认选课"\n'
                    '- 超时提醒："距离确认截止还有 X 小时"\n\n'
                    '### 4. 候补管理\n'
                    '- 学生可随时取消候补\n'
                    '- 查看候补历史和当前排队状态'
                ),
                'acceptance_criteria': (
                    '1. 候补队列按申请时间严格排序，无插队情况\n'
                    '2. 补入通知在名额空出后 5 分钟内发送\n'
                    '3. 24 小时超时后名额自动顺延\n'
                    '4. 候补上限 3 门课程，超过时提示\n'
                    '5. 取消候补后排名即时更新'
                ),
                'type': 'feature', 'priority': 'p2', 'status': 'backlog',
                'story_points': 3, 'labels': ['后端', '前端', '选课', '队列'],
                'start_date': '2026-08-20', 'due_date': '2026-08-24',
                'created_by': dev_ids['frontend_lead'],
                'developer_id': dev_ids['frontend_dev'],
                'assignees': [
                    {'user_id': dev_ids['frontend_dev'], 'role': 'primary'},
                ],
            },
        ]
        for req in requirements_data:
            req_id = req['id']
            r[req_id] = req
            assignees = req.pop('assignees', [])
            developer_id = req.pop('developer_id', None)
            tester_id = req.pop('tester_id', None)
            req_record = RdRequirement(
                project_id=project_id,
                developer_id=developer_id,
                tester_id=tester_id,
                **req,
            )
            db.session.add(req_record)
            for a in assignees:
                db.session.add(RdRequirementAssignee(
                    requirement_id=req_id,
                    user_id=a['user_id'],
                    role=a['role'],
                ))

        db.session.flush()
        print(f"  已创建 {len(requirements_data)} 条需求")

        # ════════════════════════════════════════════════════════
        #  5. Bug
        # ════════════════════════════════════════════════════════
        print("创建 Bug...")
        bugs_data = [
            {
                'id': _make_uuid('edu-bug-1'),
                'iteration_id': iter1_id,
                'requirement_id': r[_make_uuid('edu-req-6')]['id'],
                'title': '选课时学分计算错误，已超上限仍能提交成功',
                'description': (
                    '## 复现步骤\n'
                    '1. 以学生身份登录，当前已选 22 学分\n'
                    '2. 进入课程广场，选择一门 4 学分的课程\n'
                    '3. 点击"选课"按钮\n\n'
                    '## 预期\n'
                    '系统应提示"已超出学分上限（25学分），当前已选22学分 + 该课程4学分 = 26学分 > 25学分上限"\n\n'
                    '## 实际\n'
                    '系统提示"选课成功"，刷新后已选学分变为 26，超过了 25 学分的上限\n\n'
                    '## 影响范围\n'
                    '所有学生，可能导致选课混乱和教务管理困难'
                ),
                'expected_behavior': (
                    '选课时校验：已选学分 + 待选课程学分 ≤ 学分上限（默认25）。'
                    '超过时阻止选课并给出明确提示。'
                ),
                'actual_behavior': (
                    '学分上限校验未生效或计算逻辑有误，学生可超出学分上限选课。'
                ),
                'severity': 'critical', 'priority': 'p0', 'status': 'in_progress',
                'environment': 'Chrome 120, Windows 11',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['后端', '选课', '核心逻辑', '数据错误'],
                'created_by': dev_ids['fullstack'],
                'developer_id': dev_ids['reviewer'],
                'assignees': [
                    {'user_id': dev_ids['reviewer'], 'role': 'fixer'},
                    {'user_id': dev_ids['frontend_lead'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-bug-2'),
                'iteration_id': iter1_id,
                'requirement_id': r[_make_uuid('edu-req-7')]['id'],
                'title': '成绩录入时小数精度丢失',
                'description': (
                    '## 复现步骤\n'
                    '1. 教师登录，进入成绩录入页面\n'
                    '2. 为某学生输入平时成绩 85.5 分\n'
                    '3. 点击保存，刷新页面\n\n'
                    '## 预期\n'
                    '成绩应保存为 85.5，显示为 85.5\n\n'
                    '## 实际\n'
                    '保存后成绩变为 85（小数部分丢失）。数据库字段类型为 INT，无法存储小数。\n\n'
                    '## 影响\n'
                    '总评成绩计算出现偏差，学生排名和绩点计算不准确。'
                ),
                'expected_behavior': '成绩字段支持一位小数，保存后精度不丢失。',
                'actual_behavior': '小数部分被截断，85.5 → 85，数据库字段类型为 INT。',
                'severity': 'major', 'priority': 'p1', 'status': 'fixed',
                'environment': '全平台',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['后端', '数据库', '成绩', '数据精度'],
                'created_by': dev_ids['frontend_lead'],
                'developer_id': dev_ids['frontend_lead'],
                'assignees': [
                    {'user_id': dev_ids['frontend_lead'], 'role': 'fixer'},
                    {'user_id': dev_ids['backend_lead'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-bug-3'),
                'iteration_id': iter2_id,
                'requirement_id': r[_make_uuid('edu-req-5')]['id'],
                'title': '排课冲突检测失效 — 同一教室相同时段被两门课占用',
                'description': (
                    '## 复现步骤\n'
                    '1. 为"高等数学"安排在 教学楼A-301，周一 1-2节（1-16周）\n'
                    '2. 为"线性代数"安排在 教学楼A-301，周一 1-2节（1-16周）\n'
                    '3. 系统未提示冲突，两门课均排课成功\n\n'
                    '## 预期\n'
                    '第二步提交时应提示："教室冲突：教学楼A-301 在周一1-2节已被《高等数学》占用"\n\n'
                    '## 实际\n'
                    '两门课排课成功，教室课表显示同一时段有两门课\n\n'
                    '## 根因分析\n'
                    '冲突检测逻辑可能只比较了"开始时间"而忽略了"起止周"的重叠判断。'
                ),
                'expected_behavior': '教室维度的冲突检测应同时验证时段和周次，完全重叠时报错。',
                'actual_behavior': '周次重叠判断逻辑缺失，仅比较了星期和时段。',
                'severity': 'critical', 'priority': 'p0', 'status': 'confirmed',
                'environment': 'Chrome 120, Windows 11',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['后端', '排课', '核心逻辑', '数据冲突'],
                'created_by': dev_ids['frontend_dev'],
                'developer_id': dev_ids['frontend_dev'],
                'assignees': [
                    {'user_id': dev_ids['frontend_dev'], 'role': 'fixer'},
                    {'user_id': dev_ids['frontend_lead'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-bug-4'),
                'iteration_id': iter2_id,
                'requirement_id': r[_make_uuid('edu-req-8')]['id'],
                'title': '考勤统计中请假天数计算不准确',
                'description': (
                    '## 复现步骤\n'
                    '1. 学生提交请假申请：2026-08-20 ~ 2026-08-22（共3天）\n'
                    '2. 辅导员审批通过\n'
                    '3. 查看该学生的考勤统计\n\n'
                    '## 预期\n'
                    '请假天数应显示为 3 天\n\n'
                    '## 实际\n'
                    '请假天数显示为 2 天（结束日期未计入），且跨周末的请假计算也有问题。\n\n'
                    '## 补充\n'
                    '如果请假包含周六日（如请假周五到周一，共4天含2个工作日），'
                    '系统只计算了工作日天数，但学生端期望看到的是自然日天数。'
                    '产品和开发需确认是按工作日还是自然日计算。'
                ),
                'expected_behavior': '请假天数计算规则明确且正确，前端展示与实际一致。',
                'actual_behavior': '结束日期未计入总天数，跨周末计算逻辑不清晰。',
                'severity': 'major', 'priority': 'p1', 'status': 'open',
                'environment': 'Chrome 120, Windows 11',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['后端', '考勤', '数据计算', '逻辑错误'],
                'created_by': dev_ids['backend_lead'],
                'developer_id': dev_ids['backend_lead'],
                'assignees': [
                    {'user_id': dev_ids['backend_lead'], 'role': 'fixer'},
                    {'user_id': dev_ids['reviewer'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-bug-5'),
                'iteration_id': iter3_id,
                'requirement_id': r[_make_uuid('edu-req-10')]['id'],
                'title': '导出 Excel 报表中文乱码',
                'description': (
                    '## 复现步骤\n'
                    '1. 管理员进入报表导出页面\n'
                    '2. 点击"导出班级成绩汇总"\n'
                    '3. 下载 Excel 文件并用 Excel 打开\n\n'
                    '## 预期\n'
                    'Excel 中所有中文字符正常显示\n\n'
                    '## 实际\n'
                    '学生姓名、课程名称等中文字段显示为乱码（????）\n\n'
                    '## 根因\n'
                    '生成 CSV/Excel 时未添加 UTF-8 BOM 头，Excel 默认以 GBK 编码打开导致乱码。'
                ),
                'expected_behavior': 'Excel 文件中文正常显示，编码兼容 Windows Excel。',
                'actual_behavior': '中文乱码，缺少 UTF-8 BOM 头。',
                'severity': 'major', 'priority': 'p1', 'status': 'open',
                'environment': 'Windows 11, Microsoft Excel 2019',
                'browser_info': 'Chrome 120', 'os_info': 'Windows 11',
                'labels': ['后端', '报表', '编码', '兼容性'],
                'created_by': dev_ids['tester'],
                'developer_id': dev_ids['reviewer'],
                'assignees': [
                    {'user_id': dev_ids['reviewer'], 'role': 'fixer'},
                    {'user_id': dev_ids['frontend_lead'], 'role': 'tester'},
                ],
            },
            {
                'id': _make_uuid('edu-bug-6'),
                'iteration_id': iter3_id,
                'requirement_id': r[_make_uuid('edu-req-11')]['id'],
                'title': '消息通知重复发送 — 成绩发布通知推送了两次',
                'description': (
                    '## 复现步骤\n'
                    '1. 教师发布某课程成绩\n'
                    '2. 查看学生端通知列表\n\n'
                    '## 预期\n'
                    '每位选课学生收到 1 条成绩发布通知\n\n'
                    '## 实际\n'
                    '部分学生收到了 2 条完全相同的成绩发布通知（相同内容、相同时间戳）\n\n'
                    '## 根因分析\n'
                    '消息发送任务可能被 Celery 重试机制触发重复执行，'
                    '且发送前未检查幂等性（同一消息ID是否已发送）。'
                ),
                'expected_behavior': '每条消息只发送一次，消息ID唯一，发送前检查幂等。',
                'actual_behavior': 'Celery 任务重试导致重复发送，缺少幂等性校验。',
                'severity': 'minor', 'priority': 'p2', 'status': 'confirmed',
                'environment': '全平台',
                'browser_info': '', 'os_info': '',
                'labels': ['后端', '通知', '消息队列', '幂等性'],
                'created_by': dev_ids['fullstack'],
                'developer_id': dev_ids['frontend_lead'],
                'assignees': [
                    {'user_id': dev_ids['frontend_lead'], 'role': 'fixer'},
                    {'user_id': dev_ids['backend_lead'], 'role': 'tester'},
                ],
            },
        ]
        bug_ids = {}
        for bug in bugs_data:
            assignees = bug.pop('assignees', [])
            developer_id = bug.pop('developer_id', None)
            b = RdBug(
                project_id=project_id,
                developer_id=developer_id,
                **bug,
            )
            db.session.add(b)
            bug_ids[bug['id']] = bug
            for a in assignees:
                db.session.add(RdBugAssignee(
                    bug_id=b.id,
                    user_id=a['user_id'],
                    role=a['role'],
                ))
        print(f"  已创建 {len(bugs_data)} 条缺陷")

        # ════════════════════════════════════════════════════════
        #  6. 评论
        # ════════════════════════════════════════════════════════
        print("创建评论...")
        req1_id = r[_make_uuid('edu-req-1')]['id']
        req2_id = r[_make_uuid('edu-req-2')]['id']
        req5_id = r[_make_uuid('edu-req-5')]['id']
        req6_id = r[_make_uuid('edu-req-6')]['id']
        bug1_id = _make_uuid('edu-bug-1')
        bug3_id = _make_uuid('edu-bug-3')

        comments_data = [
            {
                'id': _make_uuid('edu-comment-1'), 'target_type': 'requirement',
                'target_id': req1_id,
                'content': (
                    '课程管理模块的数据库表设计已完成，请各位查看 `docs/db-schema.md`。\n\n'
                    '核心表 `courses` 包含以下字段：\n'
                    '- `code` VARCHAR(20) UNIQUE — 课程编号\n'
                    '- `name` VARCHAR(200) — 课程名称\n'
                    '- `credits` DECIMAL(3,1) — 学分（0.5-10）\n'
                    '- `hours` INT — 总学时（8-128）\n'
                    '- `type` ENUM — 必修/选修/公选\n'
                    '- `department` VARCHAR(100) — 所属院系\n'
                    '- `description` TEXT — 课程描述（Markdown）\n\n'
                    '大家有什么修改意见？'
                ),
                'author_id': dev_ids['frontend_lead'], 'is_pinned': True,
                'days_ago': 12,
            },
            {
                'id': _make_uuid('edu-comment-2'), 'target_type': 'requirement',
                'target_id': req1_id, 'parent_id': _make_uuid('edu-comment-1'),
                'content': (
                    '建议在 `courses` 表中增加 `prerequisite` 字段（JSON类型），'
                    '存储先修课程列表，方便排课系统判断学生是否满足选课条件。'
                ),
                'author_id': dev_ids['frontend_dev'], 'is_pinned': False,
                'days_ago': 11,
            },
            {
                'id': _make_uuid('edu-comment-3'), 'target_type': 'requirement',
                'target_id': req1_id, 'parent_id': _make_uuid('edu-comment-1'),
                'content': (
                    '赞同，另外建议加一个 `syllabus` 字段（TEXT类型）存储教学大纲，'
                    '学生选课时可以预览课程内容和考核方式。'
                ),
                'author_id': dev_ids['ecoll'], 'is_pinned': False,
                'days_ago': 10,
            },
            {
                'id': _make_uuid('edu-comment-4'), 'target_type': 'requirement',
                'target_id': req2_id,
                'content': (
                    '学生批量导入功能需要注意几点：\n\n'
                    '1. Excel 模板表头必须固定，第一行为字段名，第二行为说明\n'
                    '2. 身份证号需要校验校验位（18位身份证最后一位可能是X）\n'
                    '3. 手机号正则：`^1[3-9]\\d{9}$`\n'
                    '4. 学号如果重复，应提示用户选择"覆盖"还是"跳过"\n'
                    '5. 导入失败时需要生成错误报告 Excel，标注哪些行哪些字段有问题'
                ),
                'author_id': dev_ids['backend_lead'], 'is_pinned': False,
                'days_ago': 9,
            },
            {
                'id': _make_uuid('edu-comment-5'), 'target_type': 'requirement',
                'target_id': req5_id,
                'content': (
                    '排课系统的冲突检测算法我写了一个初版，核心思路是：\n\n'
                    '```python\n'
                    'def check_conflict(new_schedule, existing_schedules):\n'
                    '    conflicts = []\n'
                    '    for s in existing_schedules:\n'
                    '        # 1. 星期和时段是否重叠\n'
                    '        if new_schedule.day != s.day:\n'
                    '            continue\n'
                    '        if new_schedule.start_period > s.end_period:\n'
                    '            continue\n'
                    '        if new_schedule.end_period < s.start_period:\n'
                    '            continue\n'
                    "        # 2. 周次是否重叠\n"
                    '        if new_schedule.end_week < s.start_week:\n'
                    '            continue\n'
                    '        if new_schedule.start_week > s.end_week:\n'
                    '            continue\n'
                    "        # 3. 检查教师、教室、班级冲突\n"
                    '        ...\n'
                    '    return conflicts\n'
                    '```\n\n'
                    '欢迎大家 review，尤其是周次重叠判断的边界条件！'
                ),
                'author_id': dev_ids['frontend_dev'], 'is_pinned': True,
                'days_ago': 5,
            },
            {
                'id': _make_uuid('edu-comment-6'), 'target_type': 'requirement',
                'target_id': req6_id,
                'content': (
                    '选课系统并发方案讨论：\n\n'
                    '考虑到选课高峰期可能有 500+ 并发请求，建议：\n'
                    '- 使用 Redis 分布式锁控制课程容量的扣减，避免超卖\n'
                    '- 选课请求先入消息队列（Redis List），异步处理\n'
                    '- 前端显示"选课处理中"，异步轮询结果\n\n'
                    '大家对这种方案有什么看法？如果同步处理，数据库行锁会成为瓶颈。'
                ),
                'author_id': dev_ids['reviewer'], 'is_pinned': False,
                'days_ago': 4,
            },
            {
                'id': _make_uuid('edu-comment-7'), 'target_type': 'bug',
                'target_id': bug1_id,
                'content': (
                    '已定位到 bug 原因：`enrollment_service.py` 第 87 行的学分校验逻辑中，'
                    '`current_credits + new_credits > max_credits` 的比较使用了错误的变量，'
                    '实际比较的是 `current_credits + current_credits`，导致校验永远通过。\n\n'
                    '修复中，预计今天提交 PR。'
                ),
                'author_id': dev_ids['reviewer'], 'is_pinned': False,
                'days_ago': 2,
            },
            {
                'id': _make_uuid('edu-comment-8'), 'target_type': 'bug',
                'target_id': bug3_id,
                'content': (
                    '排课冲突的 bug 确认是周次重叠判断的问题，`check_conflict()` 函数中'
                    '周次比较逻辑写反了——用了 `>` 而不是 `<`。\n\n'
                    '已经加了单元测试覆盖这种边界情况，不会再出现同样的问题了。'
                ),
                'author_id': dev_ids['frontend_dev'], 'is_pinned': False,
                'days_ago': 1,
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

        # ════════════════════════════════════════════════════════
        #  7. 分支
        # ════════════════════════════════════════════════════════
        print("创建分支...")
        branches_data = [
            {
                'id': _make_uuid('edu-br-1'), 'repo_id': 'repo-1',
                'branch_name': 'feature/EDU-001-course-management',
                'base_branch': 'develop',
                'source_type': 'requirement', 'source_id': req1_id,
                'status': 'active', 'created_by': dev_ids['frontend_lead'],
                'days_ago': 11,
            },
            {
                'id': _make_uuid('edu-br-2'), 'repo_id': 'repo-1',
                'branch_name': 'feature/EDU-002-student-management',
                'base_branch': 'develop',
                'source_type': 'requirement', 'source_id': req2_id,
                'status': 'active', 'created_by': dev_ids['reviewer'],
                'days_ago': 9,
            },
            {
                'id': _make_uuid('edu-br-3'), 'repo_id': 'repo-1',
                'branch_name': 'feature/EDU-005-schedule-system',
                'base_branch': 'develop',
                'source_type': 'requirement', 'source_id': req5_id,
                'status': 'active', 'created_by': dev_ids['frontend_dev'],
                'days_ago': 5,
            },
            {
                'id': _make_uuid('edu-br-4'), 'repo_id': 'repo-1',
                'branch_name': 'fix/EDU-BUG-001-credit-check',
                'base_branch': 'develop',
                'source_type': 'bug', 'source_id': bug1_id,
                'status': 'active', 'created_by': dev_ids['reviewer'],
                'days_ago': 2,
            },
            {
                'id': _make_uuid('edu-br-5'), 'repo_id': 'repo-1',
                'branch_name': 'fix/EDU-BUG-003-schedule-conflict',
                'base_branch': 'develop',
                'source_type': 'bug', 'source_id': bug3_id,
                'status': 'active', 'created_by': dev_ids['frontend_dev'],
                'days_ago': 1,
            },
        ]
        for br in branches_data:
            db.session.add(RdBranch(
                id=br['id'], project_id=project_id,
                repo_id=br['repo_id'],
                branch_name=br['branch_name'],
                base_branch=br['base_branch'],
                source_type=br['source_type'],
                source_id=br['source_id'],
                status=br['status'],
                created_by=br['created_by'],
                created_at=NOW - timedelta(days=br['days_ago']),
            ))

        # ════════════════════════════════════════════════════════
        #  8. 活动日志
        # ════════════════════════════════════════════════════════
        print("创建活动日志...")
        activities_data = [
            # 项目
            {'target_type': 'project', 'target_id': project_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了教学管理系统项目', 'days_ago': 14},

            # 迭代
            {'target_type': 'iteration', 'target_id': iter1_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了 Sprint 1 — 基础数据管理', 'days_ago': 14},
            {'target_type': 'iteration', 'target_id': iter1_id, 'action': 'status_changed',
             'actor_id': dev_ids['ecoll'], 'detail': 'Sprint 1 已启动', 'days_ago': 12},
            {'target_type': 'iteration', 'target_id': iter2_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了 Sprint 2 — 教务核心功能', 'days_ago': 7},
            {'target_type': 'iteration', 'target_id': iter3_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了 Sprint 3 — 数据看板与系统管理', 'days_ago': 3},

            # 需求创建
            {'target_type': 'requirement', 'target_id': req1_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了需求：课程信息管理模块', 'days_ago': 13},
            {'target_type': 'requirement', 'target_id': req2_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了需求：学生信息管理模块', 'days_ago': 12},
            {'target_type': 'requirement', 'target_id': r[_make_uuid('edu-req-3')]['id'], 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了需求：教师信息管理模块', 'days_ago': 10},
            {'target_type': 'requirement', 'target_id': r[_make_uuid('edu-req-4')]['id'], 'action': 'created',
             'actor_id': dev_ids['frontend_dev'], 'detail': '创建了需求：班级管理模块', 'days_ago': 9},
            {'target_type': 'requirement', 'target_id': req5_id, 'action': 'created',
             'actor_id': dev_ids['frontend_dev'], 'detail': '创建了需求：智能排课系统', 'days_ago': 7},
            {'target_type': 'requirement', 'target_id': req6_id, 'action': 'created',
             'actor_id': dev_ids['ecoll'], 'detail': '创建了需求：学生选课系统', 'days_ago': 6},
            {'target_type': 'requirement', 'target_id': r[_make_uuid('edu-req-7')]['id'], 'action': 'created',
             'actor_id': dev_ids['frontend_lead'], 'detail': '创建了需求：成绩录入与统计分析', 'days_ago': 5},

            # 需求状态变更
            {'target_type': 'requirement', 'target_id': req1_id, 'action': 'status_changed',
             'actor_id': dev_ids['frontend_lead'], 'detail': '课程信息管理模块 → 进行中', 'days_ago': 10},
            {'target_type': 'requirement', 'target_id': req2_id, 'action': 'status_changed',
             'actor_id': dev_ids['reviewer'], 'detail': '学生信息管理模块 → 进行中', 'days_ago': 8},
            {'target_type': 'requirement', 'target_id': req5_id, 'action': 'status_changed',
             'actor_id': dev_ids['frontend_dev'], 'detail': '智能排课系统 → 进行中', 'days_ago': 4},

            # Bug
            {'target_type': 'bug', 'target_id': bug1_id, 'action': 'created',
             'actor_id': dev_ids['fullstack'], 'detail': '提交了Bug：选课学分计算错误', 'days_ago': 3},
            {'target_type': 'bug', 'target_id': bug1_id, 'action': 'status_changed',
             'actor_id': dev_ids['reviewer'], 'detail': 'Bug 学分计算 → 修复中', 'days_ago': 2},
            {'target_type': 'bug', 'target_id': bug3_id, 'action': 'created',
             'actor_id': dev_ids['frontend_dev'], 'detail': '提交了Bug：排课冲突检测失效', 'days_ago': 2},
            {'target_type': 'bug', 'target_id': _make_uuid('edu-bug-2'), 'action': 'status_changed',
             'actor_id': dev_ids['frontend_lead'], 'detail': 'Bug 成绩精度丢失 → 已修复', 'days_ago': 1},
            {'target_type': 'bug', 'target_id': bug3_id, 'action': 'status_changed',
             'actor_id': dev_ids['frontend_dev'], 'detail': 'Bug 排课冲突 → 已确认', 'days_ago': 1},
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

        print("\n" + "=" * 60)
        print("[SUCCESS] 教学管理系统种子数据已写入!")
        print("=" * 60)
        print(f"  项目: 1 (教学管理系统) — 属于 Ecoll ({ecoll_id})")
        print(f"  成员: {len(members_data)}")
        print(f"  迭代: {len(iterations_data)} (Sprint 1/2/3)")
        print(f"  需求: {len(requirements_data)}")
        print(f"  Bug: {len(bugs_data)}")
        print(f"  评论: {len(comments_data)}")
        print(f"  分支: {len(branches_data)}")
        print(f"  活动日志: {len(activities_data)}")
        print(f"\n  角色分配:")
        for k, v in dev_ids.items():
            print(f"    {k}: {v}")
        print(f"\n  所有用户密码: weagent123")


if __name__ == '__main__':
    seed()
