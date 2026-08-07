# WeAgent Education 总体设计

> 状态：Review-ready（对话设计已确认，等待文件审阅）
> 日期：2026-07-27
> 目标分支：`feature/education`
> 适用范围：高中英语、小学语文；阅读与写作；真实教师—学生多用户闭环

## 1. 文档目的

本文档定义 WeAgent Education 的产品边界、架构约束、模块职责和分阶段目标。它不是实现计划，也不授权立即修改业务代码。

本设计遵循四条核心原则：

1. **多 Agent 协作必须服务真实教学功能**：Agent 的结果要进入教案、课件、习题、提交、反馈和学情，而不是停留在聊天消息里。
2. **借优而不重复造轮子**：课程与权限闭环由 WeAgent 自研；编辑、语法检查、拼音、搜索、正文抽取、HTML/PPT 导出等优先复用成熟开源能力。
3. **教育业务与 Agent runtime 解耦**：Education 服务拥有课程业务数据；核心服务继续拥有 Agent、会话、sandbox、capability 和 Artifact。
4. **真实权限优先于 Prompt 约束**：教师草稿、答案、学生提交和 RAG 内容必须由服务端授权隔离，不能依靠提示词保证安全。

## 2. 产品定位

WeAgent Education 是一个“AI 教学工作台 + AI 学习空间”：

- 教师使用多 Agent 团队完成课程设计、教案、课件、习题、发布、批改和学情分析。
- 学生在独立学习空间中阅读、写作、练习、整理笔记并接受个性化反馈。
- 教师和学生通过“教学—学习数据桥”连接：
  - 教师向学生发布课时、资料、课件和作业。
  - 学生的学习、提交、修改和反馈采纳数据回流为学情报告。

产品差异化不是“拥有多个 Agent 名字”，而是：

```text
多 Agent 有边界地协作
→ 生成可编辑且可追溯的教学产物
→ 教师审核发布
→ 学生真实使用和提交
→ 数据回流驱动反馈与下一轮教学
```

## 3. 已确认决策

- 采用真实多用户最小闭环。
- 使用统一教育底座和学科能力包，不分别开发英语、语文两套系统。
- 高中英语是功能旗舰；小学语文拥有完整但稍轻量的闭环。
- 两个学科均覆盖阅读与写作。
- 教师侧主要 Agent：
  - 课程设计 Agent
  - 课件制作 Agent
  - 习题生成 Agent
  - 学情分析 Agent
- 学生侧主要 Agent：
  - 学习规划 Agent
  - 笔记整理 Agent
  - 练习教练 Agent
- 项目导师 Agent 放入 Bonus；当前不做编程项目作业。
- 学生可上传受控文件和 URL，进入学生私有 RAG。
- 课程层级为 `Course → Unit（可选）→ Lesson → Activity`。
- 教师端采用统一课时工作台。
- 教案、讲义、课件和题目都有结构化真源；HTML、DOCX、PDF、PPTX 是发布或导出产物。
- 工作流支持系统模板、教师自建和主持 Agent 动态规划。
- MVP 工作流采用“模板骨架 + 受限动态子任务”的 guided 模式。
- 所有发布、反馈和最终成绩必须经过教师确认。
- 客观题可自动判分；简答和作文只给建议分，教师决定最终结果。
- 搜索、网页抓取、检索和重排必须拆成独立组件。
- SearchProvider 的结果正文只能称为 `snippet`，不能当作网页全文。
- 所有外部能力必须支持 fallback，失败不能阻断核心教学闭环。

完整决策清单见 [00-decisions-and-scope.md](education/00-decisions-and-scope.md)。

## 4. 模块化设计索引

| 模块 | 文档 | 负责回答 |
|---|---|---|
| 范围与决策 | [00-decisions-and-scope.md](education/00-decisions-and-scope.md) | 做什么、不做什么、MVP 的准确边界 |
| 架构与隔离 | [01-architecture-and-isolation.md](education/01-architecture-and-isolation.md) | 数据归属、权限、兼容性和隔离策略 |
| 领域模型 | [02-domain-model-and-permissions.md](education/02-domain-model-and-permissions.md) | 核心实体、状态机、可见范围和授权规则 |
| Agent 与工作流 | [03-agent-team-and-workflows.md](education/03-agent-team-and-workflows.md) | Agent 分工、模板/自建工作流、运行和审批 |
| 学科能力包与教案 | [04-subject-packs-and-lesson-plans.md](education/04-subject-packs-and-lesson-plans.md) | 课文分类、教案模板、英语/语文侧重点 |
| 内容、搜索与产物 | [05-content-search-rag-artifacts.md](education/05-content-search-rag-artifacts.md) | 编辑真源、搜索/抓取/RAG、引用和导出 |
| 教师与学生体验 | [06-teacher-student-experience.md](education/06-teacher-student-experience.md) | 页面、交互、教学—学习数据桥 |
| 开源借优 | [07-open-source-reuse.md](education/07-open-source-reuse.md) | 直接复用、sidecar、仅借鉴和许可证边界 |
| 阶段与验收 | [08-phases-testing-and-operations.md](education/08-phases-testing-and-operations.md) | MVP/V1/V2/Bonus、测试、失败降级和运营 |

## 5. 总体系统关系

```text
Vue 2 教师端 / 学生端
        ↓
核心服务 :5002
  ├─ 认证、JWT、Workspace、Conversation
  ├─ Agent 调度、AgentRun、Socket 事件
  ├─ Sandbox、Capability Projection
  └─ Artifact
        ↓ /domain/edu/*
Education 服务 :5102
  ├─ Course / Membership
  ├─ Lesson / Content Version
  ├─ Assignment / Submission / Feedback
  ├─ Subject Pack / Workflow Version
  ├─ EducationAgentRun
  └─ Learning Event / Analytics
        ↓
RAG 服务 :5104
  ├─ teacher_private
  ├─ course_published
  └─ student_private
```

正式 Agent 执行路径保持不变：

```text
message_service
→ sandbox host manager/client
→ container server/orchestrator
→ AgentRuntime
→ ProviderRunnerFactory
→ Claude / Codex / OpenCode
```

Education 不创建另一条执行路径。

## 6. 标杆端到端场景

MVP 准备两个可重复运行的标杆课程：

1. 高中英语阅读与写作。
2. 小学语文阅读与写作。

二者必须走完同一个业务闭环：

```text
教师创建课程
→ 学生通过邀请码加入
→ 教师上传或检索资料
→ Agent 识别主题、语篇类型与课型
→ 课程设计 Agent 生成结构化教案
→ 课件和习题 Agent 并行生成产物
→ 教学审校 Worker 检查一致性
→ 教师编辑并发布不可变版本
→ 学生阅读、练习并提交写作
→ 规则工具和 Agent 产生反馈建议
→ 教师确认反馈与成绩
→ 学习事件回流为学情报告
```

MVP 验收使用一个教师账号和至少两个学生账号，两个学生均应拥有独立提交、反馈和私有 RAG 空间。

## 7. 非目标

以下内容不进入 MVP：

- 完整 Moodle、Canvas 或 Open edX 部署。
- 浏览器版 PowerPoint。
- H5P 全平台集成。
- Yjs 多人实时共同编辑。
- 复杂动画编辑器和自由白板。
- 基于真实统计模型的题目难度校准。
- BKT/IRT 等长期掌握度模型。
- 全自动作文最终评分。
- 编程、实验或论文项目导师。
- 家长端、教务端、缴费、排课、证书。
- 邮件、短信和移动推送。
- 教材全文随代码仓库分发。

## 8. 设计权威与变更规则

- 本总设计和模块文档共同构成 Education 的设计合同。
- 模块文档可以补充细节，但不得与总设计的已确认决策冲突。
- 任何涉及跨服务数据归属、权限放宽、依赖许可证、数据库主实体或 Agent 正式执行路径的变更，都必须先更新设计并重新确认。
- 实现计划必须引用具体模块和验收条目，不能以“实现 Education”作为无边界任务。

## 9. 研究依据

外部生态与语言学习工具调研分别保存在：

- [Education 开源生态调研](../../.planning/research/education-open-source-landscape.md)
- [Education 语言学习工具接入调研](../../.planning/research/education-language-tooling.md)

项目内部架构依据：

- [队友开发指南](../competition/队友开发指南.md)
- [Sandbox Agent Adapter 合并方案](../report/sandbox-agent-adapter-merge-plan.md)
- [AI 协作入口](../../AI协作文档/1-AI协作友好/ai-entry-overview.md)
- [AI 协作规范](../../AI协作文档/1-AI协作友好/collaboration.md)
- [模块边界](../../AI协作文档/1-AI协作友好/module-boundary.md)
