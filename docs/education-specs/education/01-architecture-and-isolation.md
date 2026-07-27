# Education 架构、兼容性与隔离

## 1. 服务边界

### 1.1 核心服务

继续负责：

- 用户、认证和 JWT。
- Workspace、Conversation、Message。
- Agent、AgentRun 和多 Agent 调度。
- Sandbox 生命周期和 Provider runtime。
- Capability、版本、权限投影和调用记录。
- Artifact 和现有实时事件。
- `/domain/edu/*` 领域代理入口。

### 1.2 Education 服务

负责：

- 课程、成员、Unit 和课时。
- 教案、讲义、课件源数据和版本。
- 资料业务关系与可见范围。
- 作业、题目、rubric、提交和反馈。
- 学科能力包、教案模板和教育工作流模板。
- EducationAgentRun 业务状态。
- 学习事件和学情聚合。
- 所有课程级授权。

Education 服务不负责：

- 启动 provider 进程。
- 创建另一套 sandbox。
- 保存核心 Conversation 或 Artifact 副本。
- 绕过核心服务直接推送另一套实时事件。

### 1.3 RAG 服务

继续负责：

- 文件解析。
- URL 内容入库。
- 切片、向量化和搜索。
- 语义/关键词/混合检索。

Education 为每次检索提供允许访问的课程和可见范围；RAG 不通过 Prompt 猜测权限。

## 2. 正式运行路径

教育 Agent 仍经过：

```text
Education UI
→ 核心消息/调度入口
→ message_service
→ sandbox host manager/client
→ container server/orchestrator
→ AgentRuntime
→ ProviderRunnerFactory
→ provider
```

EducationAgentRun 只保存该运行与课程业务对象的关联，不取代核心 AgentRun。

跨服务身份规则：

- 外部请求先经过核心服务认证和领域代理。
- 核心服务向 Education 传递经过签名或内部可信通道保护的 actor、request/correlation ID。
- Education 必须重新执行 CourseMembership 和对象级授权，不能信任请求体中的 `user_id`、
  `role` 或 visibility scope。
- Education 调用 RAG、Artifact 等服务时传递服务身份和最小范围 grant，不透传可伪造的
  客户端权限字段。

## 3. 创作空间与学习空间

### 3.1 教师创作空间

可访问：

- 未发布教案和课件。
- 答案、解析和 rubric。
- 教师私有 RAG。
- 所有成员提交。
- 学情数据。
- Agent 中间产物。

### 3.2 学生学习空间

可访问：

- 已发布的不可变课时版本。
- 学生自己的笔记、上传资料和 RAG。
- 学生自己的提交和反馈。
- 当前允许的 Tutor 工具。

课程内容跨用户发布必须经过 Education 服务，不能通过 `/workspace/shared` 直接共享。

教师可以查看学生主动提交的 SubmissionVersion 和附件快照，但不能因此检索学生完整的私有 RAG。学生把私有资料用于作业时，系统只将明确选择的附件或引用快照绑定到该次提交。

## 4. 可见范围

统一使用：

- `teacher_private`
- `course_published`
- `student_private`
- `feedback_released`

这些范围适用于 EducationContent、Resource、RAG 文档、Artifact 引用和反馈。
可见范围只是第一层过滤，读取时还必须同时校验 active CourseMembership、对象归属和
对象级 ACL。`course_published` 只对当前课程成员开放；`feedback_released` 只对该反馈
对应的学生和课程教师开放，绝不表示全班可见。

建议 RAG 逻辑空间：

```text
course/{course_id}/teacher
course/{course_id}/published
course/{course_id}/student/{user_id}
```

## 5. Agent 双重授权

第一层是现有 Capability 权限：

- Agent 绑定固定 capability version。
- capability 声明 required/optional permissions。
- sandbox projection 写入 Agent 私有投影。
- capability call record 记录实际调用。

第二层是短期 EducationRunGrant：

```text
EducationRunGrant
├─ actor_user_id
├─ course_id
├─ membership_role
├─ allowed_resource_scopes
├─ allowed_actions
├─ source_version_ids
├─ agent_run_id
└─ expires_at
```

教育工具调用同时验证：

1. Agent 是否绑定该 capability。
2. 当前 RunGrant 是否允许对目标课程和资源执行该动作。

例如学生 Tutor 即使绑定 `rag_search`，也只能查询 grant 中的 published 和本人 private 空间。

## 6. 发布隔离

发布生成不可变快照，而不是简单切换草稿状态：

```text
draft content versions
→ teacher approval
→ PublishedLessonVersion
   ├─ lesson_plan_version_id
   ├─ content_version_ids
   ├─ assessment_version_ids
   ├─ activity_ids
   ├─ student_release_manifest
   ├─ teacher_evaluation_manifest
   ├─ artifact_ids
   ├─ subject_pack_version_id
   └─ published_at/by
```

教师继续修改草稿不会改变学生正在学习的发布版本。
学生 API 只从 `student_release_manifest` 构造响应；答案、解析和 rubric 只存在于
`teacher_evaluation_manifest` 的授权读取路径中。

撤回规则：

- 新访问不再展示被撤回版本。
- 历史提交仍保留其作答版本和引用。
- 不物理删除已经参与评分或反馈的版本。

## 7. 与当前系统兼容

### 7.1 数据库

- Education 主实体只进入 `weagent_edu`。
- 核心数据通过 ID 引用，不跨库外键。
- 优先使用现有 `AgentRun.meta`、Message meta 和 Artifact ID，避免为 Education 修改核心表。
- 若核心需要新增通用扩展点，必须保持字段可空并不改变其他领域行为。

### 7.2 前端

- 保持 Vue 2.7、Element UI、Vuex 和现有路由体系。
- 复用并抽取当前 ChatWindow 工作流编辑器，不重写一个教育专用图编辑器。
- React-only 项目只允许隔离 iframe/微前端；MVP 不引入。

### 7.3 调度

- 保留现有 moderator → worker 计划格式。
- 保留 `nodes`、`edges`、`depends_on`、`parallel_groups`。
- 保留现有 AgentRun 和 Socket 事件。
- Education Workflow Compiler 输出当前调度器可消费的数据，不引入第二套 scheduler。

### 7.4 Capability

- 教育能力仍使用现有 `Capability`、`CapabilityVersion` 和 `AgentCapabilityBinding`。
- SubjectPack 只引用 capability IDs 和不可变版本。
- 不在 edu 服务复制 Skill/MCP/Plugin/Tool 注册系统。

### 7.5 Artifact

- Artifact 继续由核心服务拥有。
- Education 保存 Artifact ID、业务语义、输入版本和发布引用。
- 对旧 Artifact 类型保持兼容；Education 可新增语义 metadata，但不改变旧渲染路径。

## 8. 灰度与回滚

- Education 菜单和路由受 domain/feature flag 控制。
- 关闭灰度后，核心聊天、rd 和 office 行为保持不变。
- SubjectPack、Workflow、Capability 和模板均固定版本。
- 新版本先用于新课程；已有课程显式升级。
- sidecar 不可用时核心服务仍能启动。
- 回滚通过重新绑定上一不可变版本完成，不覆盖历史版本。

## 9. 兼容性回归

必须验证：

- 原有单 Agent 会话不变。
- 原有多 Agent 主持调度不变。
- 未选择 Education workflow 时现有行为不变。
- 旧 capability projection 仍可构建。
- 旧 workspace、conversation 和 artifact 可打开。
- edu 路由错误不会导致核心服务启动失败。
- 不同 course、不同学生的 RAG、Artifact 和提交不能交叉读取。

## 10. 队友协作与 Agent 迁移

### 10.1 代码所有权

- Education 业务、表和迁移归 `backend/services/edu` 对应模块所有。
- 核心认证、消息、AgentRun、sandbox、capability、Artifact 和领域代理属于共享核心；
  Education 只能提交最小、通用、向后兼容的扩展，并由对应负责人 review。
- RAG 是公共基础设施；Education 通过合同和 adapter 扩展 scope，不直接把课程业务写入
  RAG 内部。
- 前端 Education 页面使用独立 api/store/view/component 边界；公共组件改动必须验证
  rd、office 和原聊天路径。
- 数据模型、依赖、跨模块接口和迁移在实施前单独确认，不能夹带在 UI 提交中。

### 10.2 Education Agent 的迁移单元

Education Agent 不是一份复制出来的运行时代码。每个角色以可版本化 manifest 接入现有
Agent 与 capability 体系，至少声明：

- 稳定 `role_code` 和显示名称。
- 使用的核心 Agent/配置模板引用。
- 输入、输出 schema。
- capability version refs。
- SubjectPack 和 WorkflowTemplate refs。
- context policy、可见范围和审批要求。
- manifest version、checksum 和变更说明。

迁移/种子脚本必须幂等，以稳定 role code + version 匹配，不按可变显示名匹配，也不得
覆盖用户自建 Agent。旧版本继续服务已发布课时，新课程或显式升级后才绑定新版本。

### 10.3 Agent 运行与交接

- provider adapter 仍由 sandbox runtime 调用，不能迁到 host 侧绕过容器。
- Agent 之间可以在同一运行的 workspace 中协作，但正式交接必须登记结构化
  EducationContentVersion、Artifact 或版本 ID。
- `/workspace/shared` 只用于同一运行的临时协作，不是跨用户发布或权限授权机制。
- context 恢复沿用现有 provider/session 策略；Education 不重复注入完整聊天历史。
- 事件继续映射到现有 `elements`、`meta.events` 和 `raw_output` 持久化展示模型。

### 10.4 协作交付

- 先更新设计/API/schema，再拆成 edu、core、RAG、frontend 和测试任务。
- 一个提交只承担一个清晰模块责任；数据库迁移、依赖接入和公共核心改动分别 review。
- 跨模块合同变化同步更新 AI 协作文档的 module boundary，并留下决策记录。
- 每一阶段都执行自动化测试、自审、回滚点和灰度验证，通过后自动进入下一阶段。
- 开发过程只在 MVP 整体验收时请求人工确认；产品运行时的课时/作业发布、反馈发布和
  最终成绩仍保留教师审批门。
