# Education MVP 进度

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
