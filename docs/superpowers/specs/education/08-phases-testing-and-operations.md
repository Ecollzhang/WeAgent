# Education 阶段、测试与运行保障

## 1. 分阶段原则

- 每阶段都有可运行用户闭环。
- 先建设数据和权限，再增加智能。
- 没有真实数据时不宣称难度校准、掌握度或自适应。
- 外部工具先 adapter、再试验、最后进入默认能力包。
- 每阶段保持其他领域和原有 Agent 路径兼容。

## 2. MVP：真实可执行闭环

### 2.1 教育底座

- Course、Membership、Unit、Lesson、Activity。
- 邀请码/邀请链接。
- 教师/学生权限矩阵。
- 草稿/发布不可变版本。
- 四种 visibility scope。
- EducationRunGrant。
- 站内通知。

### 2.2 课程资料

- 教师资料上传。
- 学生私有资料上传。
- RAG 范围隔离。
- SearchProvider adapter。
- ContentFetcher/WebPageReader。
- Retriever/Reranker 合同和 fallback。
- 来源、checksum 和版权状态。

### 2.3 教案和内容

- SubjectPackVersion。
- 高中英语和小学语文主题/文本类型/课型。
- 分类建议 + 教师确认。
- 结构化教案和版本。
- HTML、DOCX、PDF。
- Tiptap 讲义。
- SlideDocument。
- reveal.js HTML 和 PptxGenJS PPTX。

### 2.4 Agent 与工作流

- 教师四 Agent、学生三 Agent。
- 资料研究和教学审校 Worker。
- 系统、个人和课程工作流。
- strict/guided 合同，MVP 默认 guided。
- 服务端 workflow persistence/version。
- 编译到当前 workflow schema。
- 快速处理/团队协作。
- EducationAgentRun。
- 协作时间线。
- 节点级重试。

### 2.5 作业与学习

- 七类 MVP 题型。
- rubric。
- 客观题规则判分。
- 简答/作文建议分。
- 截止时间、多提交版本和修订。
- Tutor。
- 学习规划。
- 笔记/知识卡片。
- 练习教练和一道变式题。

### 2.6 数据桥和学情

- LearningEvent。
- 完成率、正确率、知识点和 rubric 维度。
- 常见错因。
- 反馈查看/采纳。
- 修订前后变化。

## 3. V1：完整多模块系统

- 多 Unit、多课时管理体验。
- 题库和组卷蓝图。
- 自动组卷和题目去重。
- 思维导图。
- 简单课程知识树可视化。
- 完整模板库。
- 分层作业。
- 更完善的班级学情看板。
- 动态学习计划。
- 间隔复习的规则版。
- 作文逐句批注和版本对比增强。
- H5P/知识图谱等能力的试点 adapter。
- 助教角色评估。

## 4. V2：自适应智能增强

- 使用真实作答数据校准题目难度。
- 掌握度模型。
- 自适应选题。
- 长期学习路径动态调整。
- 教学干预效果追踪。
- 课程知识图谱。
- 教师审核数据集和模型评测面板。
- adaptive 工作流模式。

## 5. Bonus

- 项目导师。
- 编程、实验、论文。
- 实时共同备课。
- H5P 完整内容生命周期。
- Excalidraw 白板。
- 复杂教学动画。
- TTS、朗读和口语评测。
- LTI/QTI。
- Moodle/Canvas/Open edX connector。
- 离线同步。
- 家长/教务。
- 邮件、移动端推送。

## 6. MVP 标杆验收

准备：

- 一个教师账号。
- 至少两个学生账号。
- 一个高中英语课程。
- 一个小学语文课程。
- 每个课程一节阅读—写作标杆课。
- 教师自有或开放许可证示例材料。
- 可重复运行的固定 Agent 输入和验收样本。

每个课程必须完成：

```text
建课
→ 加课
→ 资料上传/搜索/fetch
→ 分类与教案
→ 多 Agent 课件和习题
→ 审校
→ 编辑和发布
→ 两名学生学习/作答/写作
→ 规则判分和 AI 建议
→ 教师反馈
→ 学生修订
→ 学情回流
```

## 7. 测试分层

### 7.1 单元测试

- 状态机。
- 权限 predicates。
- workflow DAG validation。
- 模板解析和 fallback。
- SearchHit/FetchedDocument/EvidenceChunk schema。
- publish snapshot。
- 客观题判分。
- 学习事件聚合。

### 7.2 服务测试

- Controller → Service → Model。
- core/edu/RAG adapter contracts。
- CourseMembership 授权。
- EducationRunGrant。
- Artifact 引用。
- idempotency。

### 7.3 权限矩阵测试

必须尝试：

- 未入课用户。
- removed 学生。
- 过期、撤销、超次数和暴力枚举的邀请令牌。
- 学生读取草稿。
- 学生读取答案/rubric。
- 学生 DTO 或 Artifact 泄露 answer/rubric 引用。
- 学生读取其他学生提交。
- 教师检索未提交的学生 private RAG。
- Tutor 搜索 teacher collection。
- Artifact URL 越权。
- workflow 使用未授权 capability。
- prompt injection 请求敏感数据。

### 7.4 Agent 契约测试

- LessonPlan JSON schema。
- SlideDocument schema。
- Assessment schema。
- Rubric schema。
- Agent 输出缺字段。
- 无引用或 snippet-only 引用。
- 年级/文本类型错误。
- provider 输出非 JSON。

### 7.5 Artifact 测试

- HTML 可预览且 sandbox/CSP 生效。
- PPTX 可由 PowerPoint/LibreOffice 打开。
- DOCX 可打开和继续编辑。
- 导出失败不损坏源版本。

### 7.6 E2E

- 两个标杆课程完整闭环。
- 两个学生数据隔离。
- Agent 节点失败后恢复。
- SearchProvider 失败 fallback。
- ContentFetcher 失败显示 snippet-only。
- RAG 不可用时人工编辑。
- 撤回和重新发布。

## 8. 教学质量评测

建立小规模教师标注集：

### 8.1 高中英语

- 阅读材料年级适配。
- 语篇类型。
- 题目答案依据。
- Harper 误报/漏报。
- 作文建议采纳率。
- rubric 与教师判断一致性。

### 8.2 小学语文

- 主题和课文类型。
- 拼音/多音字。
- 年级适配。
- PyCorrector 误纠率。
- 阅读题和作文反馈采纳率。

所有自动反馈可拒绝、修改和回放。

## 9. 失败降级

| 失败 | 降级 |
|---|---|
| SearchProvider | 备用 provider → 手动 URL → 课程 RAG |
| ContentFetcher | 通用提取 → snippet-only → 上传/跳过 |
| Reranker | 向量 → BM25 → 教师选择 |
| RAG 入库 | 资源失败，不进入检索；允许人工内容 |
| Harper/textstat/pypinyin | Agent/人工继续，标记工具不可用 |
| PyCorrector | 功能隐藏，不影响语文提交 |
| PPTX/DOCX | 保留结构化源和 HTML |
| 单个 Agent | 保留节点结果，从失败节点重试 |
| provider | 按现有 provider 策略切换/失败 |
| Socket 重连 | 从持久化 AgentRun/Message 恢复状态 |

任何降级都禁止自动发布不完整内容。

## 10. 可观测性

记录：

- Education workflow/run/node latency。
- provider 和模型。
- token/调用数量（若现有 provider 可提供）。
- capability 调用状态。
- search/fetch/retrieval fallback。
- Artifact 生成状态。
- 教师审批耗时。
- 反馈采纳/拒绝。
- 权限拒绝。

不得把学生正文写入普通错误日志。

## 11. 性能与预算

MVP 运行边界：

- 最大 workflow 节点数。
- 最大并发 Agent。
- 单节点最大重试。
- fetch 超时和大小。
- 上传文件大小。
- 每课程/学生 RAG 配额。
- 运行可取消。

UI 启动前显示团队 Agent 和步骤。局部任务优先快速处理，完整备课使用团队协作。

## 12. 安全与隐私

- 学生数据最小化发送。
- 记录 provider 和用途。
- 管理员可禁止某 provider 接触学生内容。
- 搜索使用 SafeSearch 和域名策略。
- URL 抓取执行 SSRF 防护。
- HTML 使用 sanitizer、sandbox iframe 和 CSP。
- secret 不进入 Agent 输出和 Artifact。
- 学生内容不用于默认共享知识库。
- 学生内容默认不用于模型训练或跨课程优化。
- 邀请令牌只保存 hash，支持过期、撤销、次数限制和尝试限流。
- Education 不提供学生账号公共目录；未成年人账号创建和认证沿用核心平台治理。
- 数据保留期由部署策略配置；删除、匿名化和审计要求必须与已评分历史保留规则共同验证。
- 删除/归档遵循业务关系，不破坏已评分历史。

## 13. 发布门槛

MVP 进入演示/试用前必须：

- 所有 P0 权限测试通过。
- 两个 E2E 标杆流程稳定通过。
- Artifact 格式验证通过。
- 搜索/fetch fallback 验证通过。
- 教师标注样本有可报告指标。
- 许可证清单完整。
- 关闭 Education 灰度后原系统回归通过。
- 文档、API 和数据迁移说明同步。
