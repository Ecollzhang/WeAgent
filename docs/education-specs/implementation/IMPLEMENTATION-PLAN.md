# Education MVP 实施计划

## 1. 目标与完成条件

在不破坏 WeAgent 现有领域服务、Agent Runtime、RAG、工作空间与灰度体系的前提下，交付一个真实多用户教育闭环：

- 一名教师创建课程并邀请至少两名学生加入。
- 支持“高中英语”和“小学语文”，覆盖阅读与写作。
- 教师可备课、生成或编辑教案与学习材料、发布作业。
- 学生可接收、完成并提交作业，获得练习反馈。
- 学习事件回流为教师可查看的班级与个人学情。
- 教师侧与学生侧由相同平台、不同权限空间承载。
- 多 Agent 通过模板化工作流协作；MVP 固定主干流程，同时保留自建和扩展接口。
- 联网资料链路明确拆分为 SearchProvider、ContentFetcher/WebPageReader、Retriever/Reranker，并具备降级。
- Education 可独立灰度关闭，关闭时不泄露业务数据或留下可绕过入口。

只有自动化测试、构建、真实浏览器 UAT 和真实模型/检索 UAT 全部通过，且 P0/P1 问题清零，才视为 MVP 完成。

## 2. 固定边界

### 2.1 MVP 包含

- 课程、成员、邀请码及教师/学生权限。
- 单元、课时、活动与版本化内容。
- 教案模板：
  - 小学语文按课文类型区分叙事、写景、说明、诗歌/古诗、寓言/童话等侧重点。
  - 高中英语按阅读体裁与写作任务区分记叙、说明、议论、应用文等侧重点。
- 作业、提交、教师审核/反馈、学习事件与基础学情。
- 课件/学习材料的 HTML 和可编辑结构化内容；PPT 导出作为能力适配器接入。
- 教育资源库、课程范围 RAG、联网搜索与正文抓取。
- 课程设计、课件制作、习题生成、学情分析、学习规划、笔记整理、练习教练等 Agent 的 MVP 能力。
- 教师发布前审核、学生提交后教师可复核等业务审核点。
- 自动化质量门禁；不设置每阶段人工开发验收。

### 2.2 MVP 不包含

- 编程作业和编程项目导师。
- 完整 LMS 的教务、收费、排课、直播、家长端和校级组织管理。
- 自研 Office 编辑器、搜索引擎、向量数据库或完整工作流引擎。
- 强行一次性实现所有 Bonus 能力，如复杂动画、完整知识图谱编辑、SCORM/LTI 全量兼容。

### 2.3 兼容与隔离

- Education API 统一位于 `/api/edu/*`，前端路由统一位于 `/education/*`。
- 权限以服务端课程成员关系为准，不信任客户端 workspace `sub_role`。
- 课程、资源、Artifact、Agent Run、Submission 和 Analytics 均强制带租户/课程作用域。
- 核心模块仅做必要、向后兼容的扩展；Education 专属模型与控制器留在 `backend/services/edu`。
- 根目录 `.env` 仅由运行配置加载，保持忽略，禁止复制、打印、提交。

## 3. 对外契约

### 3.1 HTTP

- `/api/edu/health`
- `/api/edu/courses`
- `/api/edu/courses/{course_id}/members`
- `/api/edu/courses/{course_id}/invitations`
- `/api/edu/courses/{course_id}/units`
- `/api/edu/lessons/{lesson_id}`
- `/api/edu/lessons/{lesson_id}/versions`
- `/api/edu/lessons/{lesson_id}/publish`
- `/api/edu/courses/{course_id}/assignments`
- `/api/edu/assignments/{assignment_id}/submissions`
- `/api/edu/submissions/{submission_id}/feedback`
- `/api/edu/courses/{course_id}/analytics`
- `/api/edu/resources/search`
- `/api/edu/workflows` 与 `/api/edu/workflow-runs`

### 3.2 搜索与检索

```text
SearchProvider
  -> SearchHit(url, title, snippet, provider, fetched_at)
ContentFetcher/WebPageReader
  -> CleanDocument(url, title, text, metadata, fetch_status)
Retriever/Reranker
  -> RankedChunk(text, source, score, scope)
Education Agent
  -> 带来源的教案/材料/练习
```

搜索摘要只作为候选信息，不等同网页正文。抓取失败、搜索不可用或正文不可访问时必须返回可解释降级结果，允许基于课程资料继续工作。

### 3.3 Agent 与工作流

- Agent 工具必须通过能力绑定和运行授权，不能因工具名称存在而默认放行。
- 课件团队启动前必须预检实际注册的工具目录和 `edu.courseware.create` 写入能力。
- 缺少 canonical 写入时只重试写入节点一次并保留可恢复草稿，不能用聊天完成代替业务完成。
- 工具结果必须回灌模型，直到得到最终答案、需要业务审核或达到安全迭代上限。
- 工作流持久化到服务端；前端只负责编辑与呈现。
- MVP 提供教师备课主流程和学生练习主流程模板，并保留自建工作流接口。

## 4. 实施波次

### Wave 0：基线、文档与风险台账

- [x] 迁移并修复 Education 设计文档链接。
- [x] 建立 Decisions、Issues、Progress、UAT Report。
- [x] 修复灰度初始化覆盖人工关闭状态的问题。
- [x] 清理既有核心测试中的 P0/P1 基线失败。

验证：正确工作目录下运行后端全量测试；前端构建与既有契约测试。

### Wave 1：服务可运行与服务端灰度

- 修复 Education 服务导入与应用工厂。
- 建立测试配置、数据库扩展和迁移入口。
- 提供健康检查。
- 核心代理与 Education 服务双层执行 `feature.education.enabled`。
- 关闭灰度时业务入口不可访问，健康检查仍可用于运维。

测试：健康、JWT、灰度关闭/开启、代理转发和现有领域服务回归。

### Wave 2：真实多用户与课程权限

- Course、CourseMembership、Invitation。
- 教师创建课程与邀请码；两名独立学生加入。
- 教师、学生、非成员的授权矩阵。
- 所有对象查询采用 scoped query，避免先查对象再补判断。

测试：至少三个独立用户身份，覆盖 IDOR、重复加入、邀请码过期/撤销、角色越权。

### Wave 3：课程内容、教案与发布

- Unit、Lesson、Activity、ContentVersion。
- 草稿、版本、发布快照和学生可见清单。
- 高中英语和小学语文学科模板与课型约束。
- HTML/结构化内容 Artifact；可编辑内容保留源结构。
- PPT 能力通过适配器接入，失败时保留 HTML/结构化产物。

测试：版本不可变、发布前后可见性、学科模板校验、Artifact ACL 与导出降级。

### Wave 4：教—学数据闭环

- Assignment、Submission、Feedback、LearningEvent。
- 教师发布，学生接收/保存/提交，自动反馈，教师复核。
- 班级与学生基础学情：完成率、正确率、最高分、最低分、平均分、成绩分布、
  阅读/写作维度和常见错因。
- 正式统计只纳入客观题规则判分和教师确认后的主观题最终成绩；AI 建议分保持
  “待确认”，不得进入最高分、最低分、平均分或排名。
- 支持按作业/模拟考试、时间范围、阅读/写作和知识点筛选，并能从结论下钻到证据。
- 事件幂等与派生统计可重建。

测试：完整教师+两学生流程、迟交/重复提交、反馈权限、部分评分班级、AI 建议分排除、
混合作业/模拟考试统计和证据回溯。

### Wave 5：资源、RAG、联网搜索与运行时

- 教育资源上传、课程绑定与检索作用域。
- 修复 RAG 的用户、工作空间、课程权限下沉。
- 实现 SearchProvider、ContentFetcher/WebPageReader、Retriever/Reranker 契约。
- 搜索、正文抓取、课程资料检索的逐级 fallback。
- 补齐 SSRF 防护、URL 策略、超时、大小与内容类型限制。
- Runtime 支持工具结果回灌和安全迭代上限。

测试：检索隔离、恶意 URL、抓取失败、搜索不可用、工具循环、引用来源与无结果降级。

### Wave 6：多 Agent 与能力包

- 教师侧：课程设计、教案/课件制作、习题生成、学情分析。
- 学生侧：学习规划、笔记整理、练习教练。
- 备课审核 Agent 作为可选工作流节点，不替代教师发布决定。
- 教师备课与学生练习模板工作流。
- 课程级 Agent Run Grant 和 Artifact 归属。

测试：模板编排、自建保存、能力拒绝、业务审核暂停/恢复、运行记录与产物追溯。

### Wave 7：前端教师端与学生端

- Education 灰度路由守卫与课程成员驱动的空间。
- WeAgent 最左侧全局 Sidebar 是唯一一级导航；移除 Education 内侧领域栏，当前课程选择器
  放入页面顶部共享上下文。
- 教师左侧固定为三个独立业务领域：教学空间、PPT 与课件、学生画像与评估；
  不以协作台或 Agent 卡片组织一级页面。
- 教学空间：课程、成员、课时、教案、作业发布和提交复核。
- PPT 与课件：课程 → 课时 → 教案/目标/活动/资料上下文 → SlideDocument 编辑
  → HTML 预览 → 多版本 → PPTX/PDF/HTML 导出。
- 学生画像与评估：先显示班级正式成绩总览，再按学生、作业/考试、时间和知识点下钻。
- 学生一级领域为教学空间、模拟考试、课程思维导图；教学空间内完成课件/材料下载、
  作业作答、反馈和作业弱点。
- Agent 仅作为领域内“AI 生成/分析/校验”动作；过程和产物默认折叠显示，不显示
  Conversation ID、Sandbox ID 或底层 provider 细节。
- 业务页仅内嵌最新运行和最新产物，提供“返回本次聊天”和“协作历史”；历史产物在聊天
  查看，聊天可返回业务页。
- 编辑器、工作流、资源库和 Artifact 复用现有组件，但数据改为服务端持久化。
- iframe/HTML 预览收紧 sandbox 与内容安全策略。
- 关键交互增加稳定 `data-testid`。

测试：前端契约测试、生产构建、单一侧栏、顶部课程切换、浏览器多会话角色流程、课件
独立领域流程、业务页/聊天双向跳转、正式成绩统计口径、刷新恢复、越权与灰度关闭。

### Wave 8：真实 UAT 与收尾

- 使用根 `.env` 配置启动真实依赖，不输出任何 secret。
- 通过产品 API 和浏览器触发真实模型、RAG、搜索及降级路径。
- 教师创建课程并邀请两个学生。
- 分别完成高中英语阅读/写作、小学语文阅读/写作样例。
- 发布教案/材料/作业，学生提交，教师查看回流学情。
- 记录命令、结果、可公开的模型/Provider 标识、时间和证据路径。
- 全量测试、构建、静态检查、迁移检查和安全回归。
- 回收运行 sandbox 后确认旧聊天、Workflow、正式产物和已快照预览仍能打开；继续聊天会
  创建新的 runtime generation。

验证：`UAT-REPORT.md` 有可复现证据；P0/P1 为零；未提交 secret；工作树只含预期变更。

### Wave 9：课件多风格与视觉质量（可后置）

- 在可靠写入和持久预览完成后提供清朗课堂、纸张批注、童趣绘本、深色聚焦四种主题。
- 将课件计划、组合、主题、视觉素材、渲染、视觉 QA 和定向修复做成版本化产品 Capability。
- 当前 `python-pptx` 保留为基础 Provider；评估 PptxGenJS 等可替换 Provider。
- 每页渲染成图片检查裁切、溢出、重叠、破图、层级、密度、对齐和对比度；只重做问题页
  一轮，并用 PowerPoint/LibreOffice 验证可打开和基础可编辑。

## 5. 测试策略

- 每个行为先写失败测试，再写最小实现，再重构。
- 单元测试覆盖领域规则；HTTP 集成测试覆盖授权与事务；浏览器测试覆盖真实用户旅程。
- 只模拟网络、外部模型、搜索、Redis 等系统边界，不模拟被测业务核心。
- 所有权限至少验证“允许、拒绝、跨课程对象、伪造客户端角色”四类路径。
- 每个外部能力都验证正常、超时、不可用和部分结果。
- 完成前运行后端全量、前端构建/契约、Education 集成和真实 UAT。

## 6. 威胁模型

| 威胁 | 必须实施的控制 |
|---|---|
| 越权读取课程对象 | 服务端成员关系、scoped query、对象与课程一致性 |
| Artifact 跨用户泄露 | 所有者/课程 ACL、下载与预览同样校验 |
| 提示词或搜索结果注入 | 外部内容标记为不可信、工具许可固定、引用与内容分离 |
| SSRF 与大文件抓取 | 协议/地址白名单策略、DNS/IP 校验、重定向复核、大小/超时限制 |
| 伪造教师角色 | 不信任 workspace `sub_role`，仅信任服务端 membership |
| 工具无限循环或越权 | 最大迭代、时间预算、能力绑定、运行审计 |
| 灰度绕过 | 核心代理和 Education 服务双层检查 |
| Secret 泄露 | `.env` 保持忽略，不记录值，不复制到测试夹具或报告 |

## 7. 提交与推进规则

- 每个可验证切片一个原子提交。
- 发现非阻断问题写入 `ISSUES.md` 并继续；优先修复 P0/P1。
- 不自动 merge、不部署、不删除用户数据；最终发布门通过后 push
  `feature/education`，中间切片保留原子本地提交。
- 不进行阶段性人工验收；仅在完整 MVP 通过 UAT 后交付一次最终报告。
