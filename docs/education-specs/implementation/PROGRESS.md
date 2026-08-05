# Education MVP 进度

## 2026-07-29 设计校准（待实施）

- 已确认只使用 WeAgent 最左侧全局 Sidebar：教师为教学空间、PPT 与课件、学生画像与评估；
  学生为教学空间、模拟考试、课程思维导图。Education 内侧领域栏移除，作业弱点归入学生
  教学空间。
- 当前课程选择器移到 Education 页面顶部共享上下文，角色始终来自服务端 membership。
- 已确认 Agent/聊天双向关联：业务页只显示最新运行和最新产物，“协作历史”进入旧聊天，
  聊天中的持久产物卡可返回业务页。
- 已确认 Docker sandbox 是可丢弃计算层：可见产物先快照，终态后 TTL 回收，继续旧聊天
  创建新 runtime generation。
- 课件完成门只解决了“不能假成功”，尚未解决工具注册缺失。下一实施切片需要实际工具目录
  preflight、`edu.courseware.create` writer 定向重试和可恢复草稿。
- 当前 PPTX 导出代码基线是 `python-pptx`；多风格、插图、逐页渲染和视觉 QA 属于后续质量
  增强，不得引用下方历史结构验收声称已经完成。

以下“2026-07-29”记录是本次设计校准前的实现/测试历史，保留作证据，不代表上述新合同已经
完成验收。

## 2026-07-29

- 校准教师端信息架构：教学空间、PPT 与课件、学生画像与评估被确认为三个独立业务领域，
  不再按 Agent 协作台组织一级页面。
- 固定课件领域主线：课程 → 课时 → 教案/目标/活动/资料上下文 → SlideDocument
  → HTML 预览 → 多版本 → PPTX/PDF/HTML 导出。
- 固定画像正式统计口径：只使用客观题规则判分和教师确认后的主观题最终成绩；
  AI 建议分保持待确认，不进入最高分、最低分或平均分。
- 明确不同满分的跨作业/考试统计先换算百分制；单项详情保留原始分和满分。
- 将后续实施更新为 R1–R5：领域导航、课件上下文投影、正式成绩投影、画像体验、
  内嵌 Agent 与最终 UAT。
- 完成教师端三个独立领域与学生端三个独立领域的角色化导航；当前课程的服务端 membership
  决定页面能力，删除任何伪角色切换入口。
- 新增稳定的课程/课时上下文投影，包含教案、目标、活动、材料、知识来源和校验码，作为
  课件 Agent 与结构化课件编辑器的共同输入。
- 完成正式成绩投影：作业增加满分字段，跨任务按百分制汇总，班级最高/最低/平均/中位数、
  完成率、分布和趋势只使用已确认成绩。
- 引入 Apache ECharts 的按需模块化渲染，用于画像页分布和趋势；统计计算仍全部位于
  Education 后端。
- 完成结构化 SlideDocument 编辑器：同一课件内编辑标题、简单块和讲者备注，保存生成不可变
  新版本，并从当前版本导出 PPTX、DOCX、PDF、HTML、JSON。
- 修复 Product Agent 乐观完成与 moderator/worker 可见性竞态；只有要求的持久写工具调用成功
  后才可完成，历史错误完成记录自动校正为 `partial`。
- 完成真实 Agent 工具 UAT：读取课程上下文、写入 6 页课件 v1，教师继续编辑保存为 v2；
  删除临时 sandbox 后课件仍在数据库中可用。
- 完成教师/学生图文帮助中心，采用与 Education 领域风格一致的轻量示意图、短说明和直达按钮。
- 最终自动化：后端全量 `373 passed`，Agent/Tool Gateway 定向 `18 passed`，前端 `12 passed`，
  生产构建成功。
- 最终浏览器双角色 UAT：教师课件、画像、帮助以及学生模拟考试、弱点、思维导图和教师页面
  隔离全部通过。

## 2026-07-27

- 创建 Goal，范围限定为 Education MVP。
- 验证根目录 `.env` 被 `.gitignore` 忽略。
- 将设计文档迁移到 `docs/education-specs`，修复 9 个失效的本地链接。
- 将逐阶段人工审核改为自动验证连续推进，保留产品教师审批门。
- 提交：`e40a025 docs(education): relocate specs and streamline review gates`。
- 启动 backend、frontend、runtime/RAG 三条只读代码勘察。
- 建立后端和前端构建基线，记录现有阻塞。
- 完成三条架构勘察，确认 edu 服务、前端占位、RAG 授权和工具闭环的真实缺口。
- 以红绿测试修复核心灰度迁移的 SQLite 兼容问题，并保留管理员关闭的灰度配置。
- 灰度修复后后端全量回归从 `68 errors` 收敛为 `14 failed, 241 passed`。
- 固化 `IMPLEMENTATION-PLAN.md`，将 MVP 拆为八个可验证波次。
- 完成 Education 应用工厂、独立数据库扩展、健康检查与 JWT 业务入口。
- 增加核心网关与 Education 服务双层灰度门；`feature.education.enabled` 关闭时不转发业务流量。
- Education 基础切片及灰度回归：`5 passed`。
- 完成 Course、CourseMembership、CourseInvitation 领域模型和 HTTP API。
- 邀请令牌只保存 SHA-256 hash；支持期限、次数、撤销和幂等加入。
- 课程授权只依赖服务端 active membership，伪造 workspace 子角色不能越权。
- 教师与两名学生闭环测试连同服务基础回归：`8 passed`。
- 修复知识库检索能力的内建分类和 OpenCode 最终输出契约。
- 后端全量基线清零：`263 passed`。
- 增加小学语文与高中英语版本化能力包，按文本类型提供不同教学侧重点。
- 补齐教师侧、学生侧与内部 Worker 的 Agent 角色合同，以及八个 MVP 系统工作流模板。
- 教师可保存课程级 strict/guided DAG；循环、任意可执行代码、缺少发布审核门会被服务端拒绝。
- Education 课程、工作流和基础联合回归：`14 passed`。
- 核心 Artifact 创建、读取、更新和消息列表增加会话 owner/participant 对象 ACL。
- Artifact ACL 与既有 Artifact 合同回归：`4 passed`。
- 集成 Unit、Lesson、Activity、不可变内容版本和幂等发布快照。
- 发布严格拆分学生 manifest 与教师答案/rubric manifest。
- 完成作业发布、学生多版本提交、教师反馈、学习事件与班级基础学情。
- Education 全业务联合回归：`20 passed`。
- Sandbox 创建时从会话 owner 和受信 workspace 注入不可由模型扩大的 RAG user/domain/workspace scope。
- 教育系统 Agent 补齐笔记整理、资料研究和教学审校角色，并移除编程题范围。
- 完成安全工具结果回灌、带 scope 的 RAG、搜索—正文抓取—检索—重排 fallback 和 SSRF 防护。
- 完成 Education 教师/学生页面、Vuex/API、单一教学空间导航和服务端灰度路由守卫。
- 学生草稿改为服务端持久化并支持刷新恢复；本地存储仅作为网络失败 fallback。
- 前端 8 个合同测试全部通过，生产构建成功。
- 修正作业发布后的统一恢复参数、已评分作业只读状态和教案 `source_json` 恢复。
- sandbox 文件树、预览、下载、导出和写回增加会话 owner/participant 对象级 ACL。
- 最终真实业务 UAT：2 门课程、2 名学生、4 个阅读/写作课时、4 份作业、8 次草稿
  恢复与提交、8 次教师反馈、22 项隔离断言全部通过。
- 使用根目录 `.env` 的 OpenAI-compatible 配置完成真实模型调用：HTTP 200，
  最终验收返回 1410 字符的教案结果；只保留模型标识、长度与摘要 hash。
- 在生产前端构建上完成浏览器 UAT：加载两类课程、创建高中英语课程、进入课程空间、
  查看真实成员数据；本地 UAT 浏览器与服务进程均已关闭。
- 最终后端全量回归：`304 passed`；前端 8 个合同测试与生产构建再次通过。
- 增加教师端可编辑 JSON 与 HTML 下载接口；PPTX 保持能力适配器边界，适配器未安装时
  明确返回 HTML/JSON 无损 fallback，不伪造演示文稿。
- 补齐 `/api/edu/resources/search` 执行入口：课程 membership 生成服务端 scope，
  客户端伪造 user/domain/course 范围无效；未配置外部 SearchProvider 时回退课程 RAG。

## 2026-07-30 成品 Goal 收口

- 完成角色感知单一全局导航：教师三领域、学生三领域、顶部课程上下文，移除 Education
  内部重复领域栏。
- 完成学生教学空间闭环：课件与材料、作业提交/恢复/只读终态、教师反馈、基于正式证据的
  作业弱点；模拟考试与课程思维导图保持同级独立领域。
- 完成业务产品运行与聊天双向关联：业务页展示最新运行和协作历史，聊天展示固定工作流、
  每个 Agent 的输出与产物预览，并能返回业务页面。
- 固化服务端 Product DAG 与角色绑定工具写入；课件采用大产物文件协议、严格 schema、
  逐页视觉 QA、最多两次定向修复和 canonical `edu.courseware.create` 写入。
- 完成四套 PPT 主题、HTML/PPTX/DOCX/PDF/JSON 导出、版本时间、实际 PPTX 渲染和视觉检查。
- 完成 sandbox 外部快照、TTL、generation 恢复、路径归一化、工具预检和会话对象 ACL；
  真实运行验证 generation 1 → 2 与课件文件恢复。
- 修复产品页返回聊天未自动选中会话、历史 JSON 卡片显示为 JS、学生已评分状态未恢复、
  释放反馈未显示、作业弱点忽略正式反馈等验收缺口。
- 真实模型 UAT、教师/学生浏览器 UAT、sandbox 回收恢复、PPTX 打开渲染全部通过。
- 最终回归：后端 `410 passed`，前端 14 个测试文件通过，生产构建和 Python 编译通过。
