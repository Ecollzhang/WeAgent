# Education Agent 团队与工作流

## 1. 设计目标

多 Agent 协作必须同时满足：

- 分工明确。
- 输入和输出结构化。
- 可并行但可控。
- 失败可以从节点恢复。
- 贡献可追溯。
- 权限由工具和服务端校验。
- 教师能够编辑和审批。
- 复用现有 moderator、AgentRun、workflow element 和 sandbox runtime。

## 2. 教师侧 Agent

### 2.1 课程设计 Agent

职责：

- 识别主题、文本类型和课型。
- 设计教学目标。
- 规划教师/学生活动。
- 编写结构化教案。
- 指定课件和习题需求。
- 保证阅读输入与写作输出衔接。

主要输入：

- 学科能力包。
- 年级、课时、班级情况。
- 教材、课程资料和教师要求。
- 课程标准或教师提供的目标。

主要输出：

- `lesson_plan_json`
- 课件任务 brief
- 习题任务 brief
- 引用和待教师确认项

### 2.2 课件制作 Agent

职责：

- 根据已确认或指定版本教案生成讲义。
- 生成 `slide_document_json`。
- 产出 reveal.js HTML。
- 通过 PptxGenJS 产出可编辑 PPTX。
- 生成简单图表、流程图和互动块。

不能：

- 修改教案教学目标而不产生变更建议。
- 自行发布课件。
- 把教师私有答案写入学生课件。

### 2.3 习题生成 Agent

职责：

- 按知识点、题型蓝图和课文证据生成题目。
- 生成答案规则、解析、知识点和预估难度。
- 生成阅读材料题组和写作任务。
- 检查题目能否从指定材料作答。

不能：

- 把 Agent 预估难度称为统计难度。
- 自动发布未经审校的答案。

### 2.4 学情分析 Agent

职责：

- 读取结构化学习事件和聚合指标。
- 分析完成率、正确率、错因和 rubric 维度。
- 输出班级共性问题和教学建议。
- 解释所使用的数据窗口。

MVP 不输出未经验证的长期掌握度概率。

## 3. 学生侧 Agent

### 3.1 学习规划 Agent

- 读取诊断结果、教师目标、截止时间和当前进度。
- 生成可执行的任务计划。
- 根据完成、错题和反馈事件做规则化调整。
- 计划调整必须显示原因。

### 3.2 笔记整理 Agent

- 将学生材料和零散笔记整理为大纲。
- 生成摘要和知识卡片。
- 保留原文引用。
- 不把教师答案或其他学生内容混入笔记。

### 3.3 练习教练 Agent

- 根据错误知识点选择练习。
- 提供即时反馈、错因解释和一道变式题。
- 优先提示和引导，不直接泄露进行中作业答案。
- 记录学生是否采纳建议。

## 4. 内部 Worker

### 4.1 资料研究 Worker

- 通过 SearchProvider 获得候选。
- 通过 ContentFetcher 获取正文。
- 通过 Retriever/Reranker 获取证据。
- 整理引用和冲突来源。

### 4.2 教学审校 Worker

校验：

- 目标—活动—评价一致性。
- 教学时长。
- 年级适配。
- 课件/习题与教案版本一致。
- 答案可验证性。
- 引用来源和正文获取状态。
- 学生可见内容中是否泄露答案。

## 5. 工作流来源

### 5.1 系统模板

MVP 提供：

- 教师备课全流程。
- 阅读课设计。
- 写作课设计。
- 阅读—写作整合课。
- 习题生成与发布。
- 作文批改与反馈。
- 课后学情分析。
- 学生诊断与学习规划。

### 5.2 教师自建

教师可以：

- 新建空白工作流。
- 复制系统模板。
- 选择注册 Agent/动作节点。
- 编辑节点说明。
- 设置依赖和并行。
- 插入人工审批节点。
- 保存为 personal 或 course scope。

教师不能：

- 直接修改 system template。
- 使用未授权 Agent/capability。
- 创建循环。
- 添加任意代码执行节点。
- 删除发布和最终评分的人工门。

### 5.3 主持 Agent 动态规划

用于一次性任务。动态计划必须经过相同的 DAG、Agent、权限、最大节点数和审批校验。

## 6. 执行模式

### 6.1 strict

- 节点和依赖固定。
- 只允许填充模板参数。
- 适合发布、批改、正式报告。

### 6.2 guided

- 以模板为骨架。
- 主持 Agent 可以补充受限子任务。
- 可以跳过标记为 optional 的节点。
- 不可绕过 required gate。
- **MVP 默认。**

### 6.3 adaptive

- 主持 Agent 可在预算内自由构建计划。
- 进入 V2/Bonus。

## 7. 工作流数据合同

复用当前字段：

- `id`
- `name`
- `nodes`
- `edges`
- `parallel_groups`
- `depends_on`

Education 扩展：

- `schema_version`
- `workflow_version_id`
- `scope`
- `execution_mode`
- `subject_pack_version_id`
- `required_approval_gates`
- `max_nodes`
- `max_retries`
- `max_parallelism`
- `allowed_agent_roles`
- `input_contract`
- `output_contract`

节点类型：

- `agent_task`
- `capability_task`
- `transform`
- `validation`
- `approval`

MVP 不支持循环和通用条件脚本。简单条件由节点结果状态和 optional policy 表示。
`transform` 和 `validation` 只能引用服务端注册、版本固定且带输入输出 schema 的动作；
工作流 JSON 不得携带可执行源码、shell 命令或任意表达式。

## 8. 与当前调度的结合

当前系统已经：

- 接受 workflow payload。
- 将选中 workflow 写入消息 meta。
- 让主持 Agent生成 tasks、depends_on 和 parallel_groups。
- 后端按并行组和依赖执行 worker。
- 将主持计划转换为 workflow element。

MVP 需要补齐：

1. Workflow 服务端持久化和版本。
2. Education Workflow Compiler。
3. DAG、Agent、权限和审批门校验。
4. guided 模式下对主持计划的约束校验。
5. 前端 localStorage 工作流向服务端保存的迁移。
6. EducationAgentRun 与核心 AgentRun 的关联。

正式执行仍由现有 message service 和 sandbox runtime 完成。

## 9. 快速处理与团队协作

### 9.1 快速处理

适合：

- 修改一段教案。
- 重写一个课件页面。
- 生成一道变式题。
- 整理一份学生笔记。

默认使用一个目标 Agent，不启动完整团队。

### 9.2 团队协作

适合：

- 完整备课。
- 组卷。
- 作文批改。
- 学情分析。

启动前显示：

- 参与 Agent。
- 预计节点。
- 是否联网。
- 必须人工确认的阶段。

运行限制：

- 最大节点数。
- 最大并发。
- 单节点最大重试。
- 运行可取消。

## 10. 状态与恢复

EducationAgentRun 状态：

- `pending`
- `running`
- `partial`
- `awaiting_approval`
- `approved`
- `failed`
- `cancelled`

节点状态：

- `pending`
- `running`
- `done`
- `failed`
- `skipped`
- `awaiting_approval`

失败规则：

- 保存已完成节点结果。
- 依赖失败的节点标记 skipped。
- 允许从失败节点重试。
- 重试继续引用相同输入版本，除非教师显式选择新版本。
- 不完整运行禁止自动发布。

## 11. 用户可见协作

显示：

- Agent 名称和角色。
- 当前任务和状态。
- 使用的资料/教案版本。
- 生成的内容和 Artifact。
- 节点间交接关系。
- 错误、fallback 和教师审批。

不显示：

- provider 原始思维链。
- 系统提示词。
- secret、token 或内部权限 grant。
- 学生不可见答案。

## 12. 人工审批门

必须审批：

- 发布课时。
- 发布作业。
- 发布学生反馈。
- 确认最终成绩。

可配置审批：

- 教案确认后再生成课件。
- 资料引用确认。
- 自动组卷确认。

中间内容自动保存为草稿，不要求每个 Agent 节点都暂停。
