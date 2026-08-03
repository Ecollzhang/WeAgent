# Education 聊天、业务卡片、工具与微服务接入 Spec

## 0. 文档状态

- 日期：2026-08-04
- 状态：待用户确认后进入实施计划
- 适用分支：`feature/education`
- 目标版本：Education Chat Integration Phase
- 本文只规定智慧教育与核心聊天、Toolset、RAG 和领域微服务的接入，不重做已经存在的课程、
  课时、课件、题库、作业和学情业务模块。
- 本文优先于旧文档中将“服务已注册/可勾选”等同于“Education 已完成产品接入”的描述。
- 本文不表示功能已经完成；必须通过本文的浏览器 UAT 和服务端审计后，才能标记
  “智慧教育聊天能力已上线”。

## 1. 问题陈述

目标不是让教师进入“智能研发”使用 RAG，也不是把 Education 业务包装成 RD 项目。
目标是：

> 教师和学生仍然在智慧教育产品中工作；需要 Agent 时可以进入一组与课程、课时和角色
> 绑定的核心聊天。聊天只获得本次授权的 EDU/RAG 服务和工具，能够生成或修改持久的
> Education 业务对象，并用 Education 卡片展示结果和返回业务页面。

当前实现存在四类不完整：

1. 新建聊天弹窗已经允许勾选 EDU，但没有课程、课时和成员角色绑定，也不会自动获得可信的
   Education 工具授权。
2. Education 产品任务可以创建聊天并生成正式课件，但创建的核心会话目前只设置
   `kb_domain="edu"`，没有显式写入 `services=["edu", "rag"]`。
3. 聊天中已有 RD 的项目、需求、缺陷、迭代卡片，尚无课程、课时、课件、作业、试卷、
   知识资源和学情等 Education 业务卡片。
4. `list_services`、`call_service_api` 已进入通用运行时，但当前会看到完整服务注册表，
   没有以会话选择的服务作为强制白名单；通用工具的 Capability 归属也被默认记为 RD。

因此，“弹窗里 EDU 不再显示待上线”只是 UI 状态，不构成上线。完整上线至少要求：

```text
可选择 EDU
→ 绑定真实课程/角色/可选课时
→ 注入可信上下文和受控工具
→ Agent 完成真实 Education 读写
→ 生成持久业务卡片
→ 卡片可预览、返回业务页
→ 灰度关闭后不影响 RD/Office
```

## 2. 设计原则

### 2.1 Education 是主领域，聊天是协作入口

- 教师主流程仍在“教学空间 / PPT 与课件 / 学生画像与评估”。
- 学生主流程仍在“教学空间 / 模拟考试 / 课程思维导图”。
- 聊天用于生成、修改、解释和追溯，不取代 Education 业务页面。
- 用户只输入自然语言，例如“根据当前教案生成 PPT”或“把本课时标题改得更准确”。
- 课程、课时、角色、工具协议、安全限制和输出 schema 由隐藏的系统上下文、Capability
  文档和服务端 grant 提供，不拼进用户可见 Prompt。

### 2.2 业务真源不进入 Docker

- Conversation、Message、Workflow 和可见 Agent 输出由核心数据库持久化。
- 课程、课时、课件、题目、试卷、作业和学情由 Education 数据库持久化。
- RAG 文档由 RAG 服务存储，并受 Education 课程范围约束。
- sandbox 只保存临时协作文件；`/workspace/...` 路径不能成为业务卡片的正式引用。

### 2.3 选择服务必须成为强授权边界

- `conversation.services` 是服务白名单，不只是 UI 标签。
- Agent 不能发现、调用未选择的服务。
- Toolset 绑定决定 Agent 是否具备某种能力；会话白名单决定本次运行能否使用该能力；
  Education RunGrant 再决定本次能操作哪门课程、什么角色和哪些动作。
- Prompt 约束不是权限控制，所有边界必须在服务端再次校验。

### 2.4 Education 写操作不走通用 API 工具

- `call_service_api` 只用于服务发现和明确允许的只读接口。
- 创建/修改课程、课时、课件、题库、试卷、成员、作业或分析快照，必须走
  `education_action`。
- `education_action` 必须验证 Capability、短期 RunGrant、课程成员关系、动作白名单、
  schema 和 idempotency key。
- 发布、删除、最终成绩和反馈发布继续由业务页面的教师确认门负责。

## 3. 交付范围

### 3.1 本阶段必须完成

1. 普通聊天新建弹窗中的 EDU 正式上线，不再显示“待上线”或仅做静态勾选。
2. 从 Education 业务页和全局聊天页都能创建课程绑定的 EDU 会话。
3. Education 产品任务创建的会话显式保存 `services`，并出现在对应 Education Workspace
   的聊天列表中，刷新后不消失。
4. 聊天获得课程、可选课时、成员角色、允许动作和课程知识范围。
5. Toolset 中完成公共微服务工具和 Education 工具的归属迁移与默认绑定。
6. `list_services`、服务规范读取、`call_service_api`、`rag_search` 和
   `education_action` 按会话范围正确工作。
7. 增加统一的 Education 业务卡片，至少覆盖课程、课时、课件、作业、题库/试卷、
   知识资源和学情报告。
8. 支持业务页 → 聊天 → 业务页双向跳转，以及聊天内正式产物预览。
9. 增加领域专属灰度和跨领域回归，关闭 Education 聊天功能时 RD/Office 行为不变。

### 3.2 本阶段不做

- 不允许一个会话同时把 RD 项目上下文和 Education 课程上下文作为双主领域。
- 不开放 Agent 自动发布课件、作业、答案、反馈或最终成绩。
- 不开放 Agent 删除课程、课时、成员或正式业务版本。
- 不把任意内部 API、任意 URL 或宿主机文件路径暴露给 Agent。
- 不重做 PPT 多风格和视觉生成体系；本阶段只保证已有课件生成、预览、版本和导出能从
  EDU 聊天闭环触发。
- 不要求 Office 领域同时完成接入。

## 4. 用户入口与交互

### 4.1 从 Education 业务页进入聊天

适用入口：

- 教学空间的课时和教案。
- PPT 与课件。
- 课程知识中心。
- 作业与批改。
- 学生画像与评估。
- 学生模拟考试、弱点和思维导图。
- Education 课程首页的“用 Agent 创建课程”；这是唯一允许暂时没有 `course_id` 的
  `course_bootstrap` 会话，且只获得课程列出/创建权限。创建成功后立即绑定新课程。

页面动作使用业务语言：

- “用 Agent 生成”
- “用 Agent 修改”
- “继续本次协作”
- “查看协作历史”

系统自动携带：

- 当前 `course_id`
- 当前真实 `membership_role`
- 可选 `lesson_id`
- 当前业务对象 canonical reference
- 当前页面返回路由
- 推荐 Agent/工作流
- 必需服务和工具

一次独立业务任务创建一组聊天；同一任务内的重试、写入修复和继续编辑复用原聊天。

### 4.2 从全局聊天新建 EDU 会话

选择“智慧教育”后，弹窗展开 Education 上下文区：

1. 当前身份：由课程成员关系显示，不允许前端手工伪造。
2. 课程：选择一门有权限的课程。
3. 课时：可选；生成/编辑课件和课时相关任务时建议选择。
4. 知识库：默认使用当前课程允许的知识范围，可选择是否启用 RAG。
5. Agent：优先展示系统 Education Agent；自建 Agent 只有绑定所需 Capability 后才可选。

创建后的固定字段：

```json
{
  "kb_domain": "edu",
  "services": ["edu", "rag"],
  "project_id": null,
  "workspace_context": {
    "domain": "edu",
    "role": "teacher"
  }
}
```

当用户关闭课程 RAG 时，`services` 为 `["edu"]`。第一阶段不允许在同一个 EDU 会话中同时
选择 `rd`；如果用户先选择 RD 再选择 EDU，界面要求确定一个主领域。

### 4.3 用户 Prompt 与系统上下文分离

用户在聊天中只看到并发送自己的表达：

```text
根据当前教案帮我生成一套 8 页左右的 PPT。
```

隐藏系统上下文负责提供：

- 当前课程/课时名称和授权范围。
- 学科、学段、课型和当前内容版本。
- 允许使用的 Education/RAG 工具。
- 输出 schema、幂等写入和失败修复规则。
- 不自动发布、不泄露答案和不扩大权限等约束。

系统 Prompt、RunGrant、内部 ID、Conversation ID、Sandbox ID 和工具协议不能伪装成
用户消息显示在聊天气泡中。

## 5. 会话与 Education 上下文模型

### 5.1 核心会话字段保持兼容

继续使用现有可空字段：

- `workspace_id`
- `services`
- `kb_domain`
- `kb_document_ids`
- `project_id`

Education 会话必须满足：

- Workspace 的 `domain="edu"`。
- Workspace `sub_role` 只用于界面分组，不能替代实时课程成员校验。
- `kb_domain="edu"`。
- `services` 至少包含 `edu`。
- `project_id` 永远为空，不能复用 RD 字段保存课程 ID。

本阶段不向核心 `conversations` 表新增 `course_id` 或 `lesson_id`，避免把 RD/EDU/Office
业务字段继续堆入通用表。

### 5.2 新增 EducationConversationBinding

课程上下文由 Education 数据库持久化：

```text
EducationConversationBinding
├─ conversation_id        唯一，引用核心会话 ID
├─ actor_user_id          创建者/当前所有者
├─ course_id?             普通 EDU 会话必填；course_bootstrap 暂时为空
├─ lesson_id?             可选
├─ membership_role_snapshot
├─ binding_mode           product | manual
├─ source_route?
├─ status                 active | revoked
├─ created_at
└─ updated_at
```

约束：

- `membership_role_snapshot` 只用于审计和展示；每次解析上下文仍重新检查当前成员关系。
- 没有课程的 `course_bootstrap` 不能默认推断用户为教师，必须校验独立的课程创建权限；
  创建成功后写入新 `course_id` 并按真实教师成员关系重新签发 grant。
- 绑定不是授权 token，不保存明文 RunGrant。
- 产品运行和普通 EDU 聊天都建立该绑定；`EducationAgentRun` 继续保存具体任务与
  `conversation_id` 的关系。
- 删除核心聊天时绑定软撤销；已经采用的 Education 业务对象不级联删除。

### 5.3 创建与恢复

新增 Education 会话引导接口：

```text
POST /api/edu/conversations/bootstrap
```

请求只包含用户可选择内容：

- course_id（普通 EDU 会话必填，`course_bootstrap` 除外）
- lesson_id?
- agent_ids
- enable_rag
- title?
- source_route?

Education 服务先验证成员和课时归属，再通过现有 CoreRuntimeClient 创建核心会话并保存
Binding。任何一步失败都回滚未完成的绑定；核心会话已创建但绑定失败时必须删除或标记为
不可用，不能留下无上下文 EDU 会话。

恢复旧聊天时：

```text
conversation_id + 当前用户
→ Education 重新校验 Binding 和 CourseMembership
→ 返回安全上下文摘要
→ 为本轮运行签发短期 RunGrant
→ 核心刷新 sandbox 运行环境
```

旧 Docker 是否存在不影响恢复。

## 6. 服务上下文注入

### 6.1 三层上下文

1. **用户可见上下文卡**
   课程、课时、身份、任务、进度、最新产物和返回业务页按钮。
2. **Agent 可见业务摘要**
   学科/学段、课程/课时标题、可用内容版本、授权知识范围和允许动作，不含 token。
3. **工具运行环境**
   短期 RunGrant、过滤后的服务注册表、RAG scope 和用户认证，由服务端注入，不进入 Prompt。

### 6.2 会话服务白名单

核心创建或恢复 sandbox 时，按 `conversation.services` 生成：

- `CONVERSATION_SERVICES`
- 过滤后的 `SERVICE_REGISTRY`
- Education/RAG 作用域

不能再把 RD、EDU、RAG、Office 的完整注册表无条件注入所有会话。

工具必须二次验证：

```text
service_name ∈ CONVERSATION_SERVICES
```

即使环境变量被错误配置，服务端工具适配器也必须拒绝未授权服务。

## 7. 微服务规范与 Toolset 迁移

### 7.1 Education 服务自描述

Education 服务补齐：

```text
GET /api/edu/spec
GET /api/edu/health
```

`/api/edu/spec` 至少返回：

- 服务版本和健康状态。
- 能力分组。
- 可通过通用 API 工具读取的端点。
- 必须通过 `education_action` 调用的受保护动作。
- 角色、作用域和返回卡片类型。

规范不能宣称所有 endpoint 都能由 `call_service_api` 任意调用。

### 7.2 Capability 归属

Toolset 调整为：

| Capability | 归属 | 默认绑定 |
|---|---|---|
| `list_services` | `common` | 可使用微服务的系统 Agent |
| `call_service_api` | `common` | 可使用微服务的系统 Agent |
| `rag_search` | `common` | 需要知识检索的系统 Agent |
| `education_actions` | `edu` | 系统 Education Agent |

现有将除 `education_actions` 外所有内置工具标记为 RD 的种子逻辑必须迁移。迁移只更新
内置 Capability，不修改用户自建 Capability 的领域。

系统 Education Agent 默认绑定：

- 服务发现。
- 受控只读服务调用。
- 课程范围 RAG。
- Education 业务操作。

自建 Agent 不自动获得 Education 写权限；用户绑定 Capability 后，运行时仍需 RunGrant。

### 7.3 工具行为

#### `list_services`

- 只返回当前会话选择的服务。
- 返回显示名、状态、能力摘要和 spec 可用性。
- 不向模型暴露内部网络地址、token 或内部 key。

#### `call_service_api`

- 只能调用会话白名单中的服务。
- 只能调用服务规范声明为 `agent_read` 的方法和路径。
- 不允许任意 URL、路径穿越或重定向到未注册主机。
- Education 写接口返回 `protected_action_required`，提示改用 `education_action`。
- 调用记录进入 CapabilityCallRecord。

#### `rag_search`

- EDU 会话固定使用 `domain=edu`。
- 课程、用户、角色、可见范围和文档筛选由服务端 scope 注入，模型参数不能扩大。
- 教师可以检索当前课程的 `teacher_private` 与 `course_published`。
- 学生只能检索当前课程的 `course_published` 和本人 private 范围。
- 搜索结果保留来源、文档、片段和定位；没有正文的搜索 snippet 不能冒充 RAG 证据。

#### `education_action`

- 继续作为所有 Education 业务写操作和敏感读取的唯一入口。
- 服务端注入 course、actor、role 和默认 lesson；Agent 不传这些授权字段。
- 没有 course_id 时禁止以“默认教师”方式扩大权限；只有受控 `course_bootstrap` grant
  可以调用 `edu.course.create`。
- 每个写操作使用稳定且本次任务唯一的 idempotency key。
- 成功结果必须包含 canonical reference，供聊天卡片生成。

### 7.4 首批聊天动作

必须支持以下自然语言闭环：

| 用户意图 | 需要的动作 |
|---|---|
| 查看当前课程/课时 | `edu.course.context.get` |
| 新建课时 | `edu.lesson.create` |
| 修改课时标题、分类、时长或顺序 | 新增 `edu.lesson.update` |
| 根据当前教案生成 PPT | `edu.course.context.get` + `edu.knowledge.search`/RAG + `edu.courseware.create` |
| 查看当前课件结构 | 新增 `edu.courseware.get` |
| 修改某页并保存新版本 | 新增 `edu.courseware.version.create` |
| 上传/采用材料 | `edu.asset.attach` |
| 生成题目和试卷 | `edu.question_bank.upsert` + `edu.paper.compose` |
| 查看或刷新学情 | `edu.student_insight.refresh` |
| 按名单邀请/导入学生 | `edu.course.members.import`，执行前显示一次明确确认 |

`edu.courseware.create` 保持兼容；修改已有课件必须追加不可变版本，不能覆盖历史版本。

## 8. Education 聊天卡片

### 8.1 采用统一卡片封装

本阶段推荐增加一个上报类型：

```text
education_card
```

通过 `object_type` 渲染不同业务外观，避免为每种对象复制一套消息协议。

首批 `object_type`：

- `course`
- `lesson`
- `lesson_plan`
- `courseware`
- `assignment`
- `question_bank`
- `assessment_paper`
- `knowledge_resource`
- `student_insight`
- `mind_map`

### 8.2 卡片合同

```json
{
  "type": "education_card",
  "data": {
    "schema_version": "1.0",
    "object_type": "courseware",
    "canonical_ref": {
      "object_id": "opaque-id",
      "version_id": "opaque-version-id"
    },
    "title": "The Gift of the Magi：证据与反讽",
    "summary": "8 页 · 纸张批注 · 草稿",
    "status": "draft",
    "meta": {
      "lesson_title": "The Gift of the Magi",
      "slide_count": 8,
      "theme": "paper_annotation"
    },
    "preview_kind": "slide_document"
  }
}
```

安全规则：

- Agent 不得自行提供任意 URL 或前端 route。
- `canonical_ref` 必须来自成功的 Education 工具结果。
- 后端根据当前用户权限把 canonical reference 投影为可用的预览和业务路由。
- 正式业务卡片由工具结果适配器生成，不依赖模型手写 JSON 声称“已保存”。
- 卡片读取时重新校验课程成员关系和对象可见范围。

### 8.3 卡片交互

所有卡片显示：

- 类型、标题、状态、版本时间。
- 来源 Agent/Workflow 的简短说明。
- 与对象类型相关的 2–4 个摘要字段。
- “预览”
- “打开业务页面”
- “继续编辑”或“继续协作”

课件卡额外显示：

- 页数、主题、版本。
- HTML 预览。
- PPTX/HTML/PDF 已生成状态。
- 返回“PPT 与课件”的按钮。

聊天预览必须通过带认证的前端 API 或短期签名资源完成，不能把受保护 API URL直接塞进
无认证 iframe，因此不得再出现 `Missing Authorization Header`。

### 8.4 上下文条与卡片的关系

- `EducationChatContext` 是会话级上下文，只显示当前课程、课时、角色、任务进度和返回入口。
- `education_card` 是消息级业务结果，一次运行可以产生多个。
- 上下文条不能替代业务卡片；业务卡片也不能靠解析聊天标题恢复课程上下文。

## 9. 灰度隔离

### 9.1 新增或调整灰度键

| config_key | domain/domains | 作用 |
|---|---|---|
| `feature.education.chat.enabled` | `edu` | Education 聊天接入总开关 |
| `feature.education.chat.manual_create` | `edu` | 全局聊天新建 EDU 会话 |
| `feature.education.chat.tools` | `edu` | EDU 会话工具授权 |
| `ui.chat.card.education` | `common` + `["edu"]` | Education 业务卡片 |
| `feature.education.rag.enabled` | `edu` | 课程范围 RAG |

已有 RD 卡片必须收窄为：

```text
ui.chat.card.requirement → domains=["rd"]
ui.chat.card.bug         → domains=["rd"]
ui.chat.card.iteration   → domains=["rd"]
ui.chat.card.project     → domains=["rd"]
```

共享 Chat UI 不等于共享领域可见性。EDU 会话不能渲染 RD 卡片，RD 会话不能渲染
Education 卡片。

### 9.2 回滚

关闭 `feature.education.chat.enabled` 后：

- 已有 Education 业务对象和历史聊天仍可只读打开。
- 不再创建新的 EDU 会话或签发新的 Education 聊天工具 grant。
- Education 主业务页面仍由 `feature.education.enabled` 独立控制。
- RD、RAG 和 Office 的会话创建、卡片和工具行为不变。

## 10. 兼容迁移

### 10.1 数据库

- 新增 `EducationConversationBinding` 到 `weagent_edu`，使用幂等迁移。
- 不修改 RD 业务表。
- 不把课程 ID 写入 `conversations.project_id`。
- 不覆盖用户自建 Agent、Capability 或 Workspace。

### 10.2 历史 Education 会话

根据已有 `EducationAgentRun.conversation_id` 回填 Binding：

- course_id、lesson_id、requested_by 和角色来自 Education 数据。
- `services` 根据 Workflow manifest 回填为 `["edu"]` 或 `["edu", "rag"]`。
- `kb_domain` 修正为 `edu`。
- `project_id` 保持空。

不能仅按标题、Prompt 或 Workspace 名称猜测课程。

### 10.3 Capability 与灰度

- 内置通用工具迁移到 `domain="common"`。
- Education 系统 Agent 幂等绑定所需 Capability 最新固定版本。
- RD 卡片的 `domains` 必须执行明确 UPDATE，不能只用 `INSERT IGNORE`，否则旧库会继续让
  RD 卡片在 EDU 中可见。
- 所有新增字段可空或位于 Education 独立表，旧会话和旧镜像仍能启动。

### 10.4 沙箱镜像

修改 `agent.py`、`orchestrator.py`、`weagent-report` 或 Tool registry 后必须重建镜像。
运行时和镜像版本必须通过健康检查返回，禁止前端已经展示新卡片而容器仍使用旧白名单。

## 11. 错误与恢复

- EDU 服务不可用：创建弹窗显示“智慧教育服务暂不可用”，不能创建无绑定会话。
- 课程成员失效：撤销 Binding 的执行权限，历史聊天只展示仍允许读取的内容。
- 必需 Capability 缺失：在预检阶段失败，不启动 Agent 团队。
- RAG 不可用：继续使用当前课程结构化资料，并明确显示 fallback。
- schema 错误：把精确字段路径返回原 Agent 修复一次。
- 工具成功但卡片失败：业务对象仍然成功；后端可从 canonical reference 重建卡片。
- 卡片存在但对象无权限：显示“对象不可访问或权限已变更”，不泄露标题和摘要。
- sandbox 被删除：从 Binding、消息、Artifact 和 Education canonical object 恢复，不依赖旧路径。
- 服务调用超时：记录工具失败和服务名；不能把自然语言回复当作业务成功。

## 12. 验收方案

### 12.1 自动化测试

必须覆盖：

1. EDU 会话 bootstrap 的课程成员、课时归属和回滚。
2. 普通 EDU 会话与产品任务会话都写入正确的 Workspace、`kb_domain` 和 `services`。
3. `list_services` 只返回 EDU 会话选择的 `edu/rag`。
4. EDU 会话尝试调用 RD 被服务端拒绝。
5. `call_service_api` 尝试调用 EDU 写接口被拒绝并引导使用 `education_action`。
6. RunGrant 不能跨用户、跨课程、跨角色或超时复用。
7. RAG 不能读取其他课程、其他学生 private 或教师答案范围。
8. 成功工具结果生成合法 `education_card`，伪造 canonical reference 被拒绝。
9. 关闭 Education 灰度后 RD 会话、RD 卡片和现有单/多 Agent 行为不变。
10. 历史产品会话迁移后能恢复上下文和返回业务页面。

### 12.2 真实教师 UAT

使用同一真实教师账号完成：

1. 从全局聊天新建 EDU 会话，选择高中英语课程和一个课时。
2. 只输入“根据当前教案帮我生成一套 8 页左右的 PPT”。
3. 聊天显示课程上下文、受控工具进度和课件卡片。
4. 课件卡可以打开 HTML 预览、下载 PPTX，并返回“PPT 与课件”。
5. 在原聊天说“把第三页改成证据—推理—结论结构，并保存新版本”。
6. 新版本进入同一课件对象，旧版本仍可回看。
7. 在聊天中修改一个课时标题或时长，业务页刷新后显示变更。
8. 上传一份正常 PDF 到课程知识库，Agent 检索时显示真实引用。
9. 尝试询问另一门课程的私有材料，系统拒绝或返回无权访问。

### 12.3 双向跳转 UAT

```text
PPT 与课件
→ 用 Agent 修改
→ 对应聊天
→ 课件业务卡片预览
→ 返回 PPT 与课件
→ 协作历史
→ 找回原聊天
```

刷新浏览器、重启核心服务和删除旧 sandbox 后，上述路径仍成立。

### 12.4 灰度与跨领域 UAT

- 关闭 `feature.education.chat.manual_create`：新建弹窗不显示 EDU 创建入口，RD 正常。
- 仅关闭 `ui.chat.card.education`：Education 聊天保留文本和业务返回入口，RD 卡片正常。
- EDU 会话只看到 EDU/RAG 服务；RD 会话不出现 Education 卡片。
- 使用旧 RD 项目会话完成一次项目/需求查询，结果与迁移前一致。

## 13. 完成定义

只有同时满足以下条件才可标记完成：

- 新建聊天中的“智慧教育”不再是静态入口，能够创建真实课程绑定会话。
- Education 产品任务和普通 EDU 会话都在聊天列表中稳定存在。
- 用户使用自然语言即可完成课件生成、课件版本修改和课时修改。
- Toolset 的通用工具与 Education 工具归属、默认绑定和运行白名单正确。
- Agent 只能列出和调用本会话选择的微服务。
- 所有 Education 写操作都有 RunGrant、idempotency 和审计记录。
- 聊天中出现可验证的 Education 业务卡片，而不是文件路径或“已完成”文本。
- 卡片预览、业务页返回和协作历史均能工作。
- RAG 使用真实课程 PDF 做过范围内检索，并完成跨课程隔离测试。
- 灰度关闭后 RD/Office 和原聊天路径无回归。
- 内置浏览器完成教师端真实 UAT，服务端日志、数据库对象和导出文件三方一致。

## 14. 推荐实施顺序

1. **P0 合同与隔离**
   Education spec/health、Binding、服务白名单、Capability 归属、灰度键。
2. **P1 EDU 会话完整上线**
   全局 bootstrap、业务页入口、产品会话 services、上下文恢复和自然语言 Prompt 分离。
3. **P2 工具闭环**
   受控服务发现、RAG、Education 动作、课时更新和课件版本工具。
4. **P3 Education 卡片**
   后端可信卡片生成、前端变体渲染、认证预览和双向跳转。
5. **P4 迁移与 UAT**
   历史会话回填、镜像重建、真实 PDF、教师/学生权限和 RD 回归。

P0–P3 任何一项缺失都不能用“智慧教育聊天已上线”描述。

## 15. 需要用户确认的决策

### 决策 1：全局新建 EDU 会话是否必须选择课程

- **A（推荐）**：第一阶段课程必选，课时可选。权限、RAG 和工具范围最清晰。
- B：允许无课程 EDU 会话，但只能列出/创建课程，不能操作课时、课件或课程知识。

### 决策 2：首阶段是否允许 EDU 与 RD 同时成为一个会话的服务

- **A（推荐）**：不允许。EDU 会话只允许 `edu`，可附加 `rag`；跨领域协作后续单独设计。
- B：允许 `edu + rd + rag`，但需要额外设计双业务上下文、卡片冲突和两套对象权限。

### 决策 3：Education 卡片协议

- **A（推荐）**：一个 `education_card`，通过 `object_type` 渲染课程、课时、课件等变体。
- B：为每种对象建立独立卡片类型，例如 `courseware_card`、`lesson_card`、
  `assignment_card`。

### 决策 4：成员导入的聊天权限

- **A（推荐）**：本阶段允许 Agent 调用 `edu.course.members.import`，但执行前只对该高影响
  动作做一次明确确认。
- B：本阶段不允许聊天导入成员，只保留教师业务页面操作。
