# 智慧教育 (Education) 领域服务

智慧教育领域为 WeAgent 平台提供完整的教与学全流程支持，覆盖教师课程管理、AI 辅助教学、学生个性化学习、作业批改与学情诊断。

## 功能预览

<!-- TODO: 替换为实际截图 -->

| 课程空间 | 作业批改 |
|---|---|
| ![课程空间](../../../static/image/edu_course_space.png) | ![作业批改](../../../static/image/edu_homeworkd.png) |

| 课件工作台 | 学生洞察 |
|---|---|
| ![课件工作台](placeholder) | ![学生洞察](placeholder) |

| 知识中心 | 模拟考试 |
|---|---|
| ![知识中心](placeholder) | ![模拟考试](placeholder) |

## 架构

```
frontend/src/views/education/          backend/services/edu/
├─ EducationHome.vue                   ├─ app.py                  # Flask 应用入口
├─ CourseSpace.vue                     ├─ config.py              # 配置
├─ LessonWorkbench.vue                 ├─ extensions.py          # 数据库/Socket.IO
├─ AssignmentWorkspace.vue             ├─ models.py              # 数据库模型
├─ SubmissionReviewWorkspace.vue       ├─ routes.py              # 学生/教师路由
├─ KnowledgeCenter.vue                 ├─ asset_models.py         # 资产模型
├─ CoursewareLibrary.vue               ├─ asset_routes.py         # 资产路由
├─ StudentInsights.vue                 ├─ asset_service.py        # 资产业务逻辑
├─ WeaknessCenter.vue                  ├─ content_models.py       # 内容模型
├─ MockExamCenter.vue                  ├─ content_routes.py       # 内容路由
├─ HelpCenter.vue                      ├─ content_exporters.py    # 内容导出
└─ MindMapCenter.vue                   ├─ knowledge_models.py     # 知识库模型
                                       ├─ knowledge_routes.py     # 知识库路由
                                       ├─ knowledge_service.py    # 知识库业务逻辑
                                       ├─ learning_models.py      # 学习数据模型
                                       ├─ learning_routes.py      # 学习路由
                                       ├─ learning_service.py     # 学习业务逻辑
                                       ├─ workflow_models.py      # 工作流模型
                                       ├─ workflow_routes.py      # 工作流路由
                                       ├─ conversation_routes.py  # 会话路由
                                       ├─ course_context_service.py # 课程上下文
                                       ├─ document_extraction.py  # 文档解析提取
                                       ├─ presentation_quality.py # 课件质量检测
                                       ├─ presentation_rendering.py # 课件渲染
                                       ├─ presentation_themes.py  # 课件主题
                                       ├─ resource_pipeline.py    # 资源管线
                                       ├─ rag_ingestion.py        # RAG 知识摄入
                                       ├─ subject_packs.py        # 学科包
                                       ├─ runtime_client.py       # 沙箱运行时客户端
                                       ├─ tool_gateway.py         # 工具网关
                                       ├─ tool_models.py          # 工具模型
                                       ├─ tool_routes.py          # 工具路由
                                       ├─ web_resource_service.py # 网络资源服务
                                       ├─ product_agent_runs.py   # Agent 产物运行
                                       ├─ access.py               # 访问控制
                                       ├─ agent_policy.py         # Agent 策略
                                       └─ schema_maintenance.py   # Schema 维护
```

## 功能模块

### 课程空间 (`CourseSpace`)

- 教师创建与管理课程体系，支持学科分类、课程描述与封面设置。
- 课程内容编排：按章节/课时组织教学材料，支持拖拽排序。
- 版本化教学循环：课件与作业按版本独立发布，支持版本回溯。
- 课程成员邀请制，学生通过邀请码加入课程。

### 课件工作台 (`LessonWorkbench`)

- 可视化课件编辑器，支持富文本、图片、代码块等多种内容格式。
- Agent 辅助生成可编辑课件、演示文稿（PPTX 导出）。
- 课件主题与模板系统，一键切换风格。
- 课件质量自动检测与优化建议。

### 作业批改 (`AssignmentWorkspace` / `SubmissionReviewWorkspace`)

- 教师发布作业任务，支持截止日期、评分标准、附件要求。
- 学生在线提交作业，支持文档导入与 OCR 识别。
- AI 辅助批改工作流：自动评分、评语建议、语法纠错。
- 批改结果可按班级/学生/作业维度筛选查看。

### 学生洞察 (`StudentInsights`)

- 学生学情数据聚合分析：作业完成率、平均得分、进步趋势。
- 知识点薄弱项自动诊断与可视化（薄弱项雷达图）。
- 个性化学习建议与针对性练习推荐。
- 班级整体学情报告生成。

### 薄弱项诊断 (`WeaknessCenter`)

- 基于作业与考试数据的多维度薄弱项识别。
- 知识点 → 薄弱项的映射与权重计算。
- 针对性强化练习自动生成。

### 模拟考试 (`MockExamCenter`)

- 教师创建试卷模板，支持题型配置与分值设定。
- 学生在线答题，自动计时与提交。
- 自动阅卷与成绩分析，薄弱项联动诊断。

### 知识中心 (`KnowledgeCenter`)

- 学科知识库内容管理，支持文档上传与结构化存储。
- RAG 知识摄入管线：文档解析 → 向量化 → 语义检索。
- 学习资源管线：网络资源抓取、清洗与入库。

## Agent 集成

- **课程上下文注入**：`course_context_service` 向 Agent 提供当前课程、章节、学生信息作为系统提示词。
- **Agent 辅助教学**：Agent 可自动批改作业、生成课件、回答学生提问。
- **运行时沙箱**：`runtime_client` 管理教育场景的 Docker 沙箱，Agent 在隔离环境中处理课件与作业文件。
- **工具网关**：`tool_gateway` 管理教育专用 Agent 工具（批改工具、课件生成工具、题库检索工具等）。

## API 路由一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/api/edu/courses` | 课程列表/创建 |
| GET/PUT/DELETE | `/api/edu/courses/<id>` | 课程详情/更新/删除 |
| POST | `/api/edu/courses/<id>/invite` | 生成课程邀请码 |
| POST | `/api/edu/courses/<id>/join` | 学生加入课程 |
| GET/POST | `/api/edu/courses/<id>/lessons` | 课时列表/创建 |
| PUT/DELETE | `/api/edu/lessons/<id>` | 更新/删除课时 |
| GET/POST | `/api/edu/courses/<id>/assignments` | 作业列表/发布 |
| GET/POST | `/api/edu/assignments/<id>/submissions` | 提交列表/提交 |
| PUT | `/api/edu/submissions/<id>/review` | AI 批改 |
| GET | `/api/edu/students/<id>/insights` | 学生学情洞察 |
| GET | `/api/edu/students/<id>/weaknesses` | 薄弱项诊断 |
| GET/POST | `/api/edu/knowledge` | 知识库内容管理 |
| GET/POST | `/api/edu/exams` | 考试列表/创建试卷 |
| GET/POST | `/api/edu/exams/<id>/results` | 考试成绩 |
| GET | `/api/edu/spec` | 服务能力描述 |
| GET | `/api/edu/health` | 健康检查 |

## 启动

```powershell
cd backend/services/edu
pip install -r requirements.txt
python app.py
```

开发阶段通过主后端代理路由访问。首次启动自动建表。教育领域依赖 RAG 服务提供知识检索能力，请确保 RAG 服务已启动。
