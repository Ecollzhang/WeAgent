# Education 单一导航、Agent 双向关联与课件质量设计

## 0. 状态与适用范围

- 状态：已确认。
- 日期：2026-07-29。
- 本文修正此前“全局侧栏 + Education 内侧领域栏”的双栏设计，并补充 Agent 聊天追溯、
  sandbox 生命周期、课件工具可靠性和后续视觉质量要求。
- 本文优先于旧文档中与导航层级、学生领域、AI 生成记录和 sandbox 持久性冲突的描述。
- 本轮只更新设计，不代表对应代码已经完成。

## 1. 已确认决策

1. WeAgent 最左侧主侧栏是唯一一级导航；移除 Education 内侧领域栏，不能出现两个
   “教学空间”。
2. 当前课程选择器放在 Education 页面顶部的共享上下文栏，不占用窄主侧栏。
3. 教师一级领域为“教学空间 / PPT 与课件 / 学生画像与评估”。
4. 学生一级领域为“教学空间 / 模拟考试 / 课程思维导图”；作业弱点属于学生教学空间，
   不再作为一级领域。
5. Education Agent 运行与核心聊天采用双向关联；保留现有 Workflow 展示形式。
6. 业务页只渲染最新一次 Agent 运行和最新产物；历史运行通过小型“协作历史”入口回到
   对应聊天查看。
7. 历史聊天、Workflow 和正式产物的查看不能依赖原 Docker 容器仍然存在。
8. 课件 Agent 启动前必须通过工具可用性预检；没有成功调用 `edu.courseware.create`
   的运行不能标记完成。
9. 多风格课件、视觉生成 Skill 和自动视觉验收进入课件质量增强阶段；基础工具可靠性先完成。

## 2. 单一主侧栏

### 2.1 信息架构

全局侧栏在当前 domain 为 `edu` 时，在“领域”分组内按当前课程的真实
`membership_role` 显示：

教师：

- 教学空间
- PPT 与课件
- 学生画像与评估

学生：

- 教学空间
- 模拟考试
- 课程思维导图

角色只来自服务端课程成员关系。workspace `sub_role`、本地偏好或路由参数不能扩大权限。
没有有效当前课程时只显示可进入的“教学空间”，由课程列表完成创建、加入或选择。

### 2.2 当前课程上下文

Education 页面顶部提供共享当前课程栏：

- 课程名。
- 当前成员身份。
- 学科和学段。
- 课程切换器。
- 返回全部课程。

切换同角色课程时保留当前领域并替换 `courseId`；切换到另一角色课程或当前页面不适用于
新角色时，回到该课程教学空间。页面刷新和深链必须按
“路由 courseId → 有效 active course → 第一门可用课程”恢复上下文。

### 2.3 页面布局

- `EducationShell` 只保留全局 `AppSidebar` 和主内容区。
- Education 品牌、帮助和持久化说明进入页面标题、帮助入口或空状态，不再形成第二根侧栏。
- Education 路由通过 `meta.domain`、`meta.educationModule` 和 `meta.educationRole`
  驱动主侧栏高亮与访问校验，不能用共同的 `/education` 前缀同时高亮多个入口。
- 窄屏时主侧栏折叠为 drawer；当前课程上下文仍在页面顶部可访问。

## 3. 教师和学生领域

### 3.1 教师教学空间

负责课程、课时、成员、教案、教学活动、材料、题库、试卷库、知识库、作业发布和批改。
它不是通用 Agent 协作台。

### 3.2 PPT 与课件

作为独立教师领域，从当前课程选择课时，读取教案、目标、活动、材料和授权知识来源，
生成或编辑 `SlideDocument`，保存不可变版本并导出 HTML、PPTX 和 PDF。

### 3.3 学生画像与评估

作为独立教师领域，先显示班级最高分、最低分、平均分、中位数、完成率、分布和趋势，
再下钻到单个学生与提交、作答、教师评分证据。

### 3.4 学生教学空间

学生教学空间是学生课程主线，至少包含：

- 下载和预览教师已发布的课件与材料。
- 查看待完成、进行中和已完成作业。
- 保存作答、提交和查看教师反馈。
- 按作业查看弱点、错因、证据和补练建议。

“作业弱点”是教学空间内的页签或聚合区，不是一级领域。模拟考试与课程思维导图继续作为
与教学空间同级的独立入口。

## 4. Agent 与聊天双向关联

### 4.1 一个业务任务，一组聊天

从 Education 领域发起一次独立 AI 任务时，系统自动创建一组核心聊天并关联
`EducationAgentRun.conversation_id`。重试、写入修复和同一任务内的继续修改留在原聊天；
新的独立生成任务创建新聊天。

标题格式：

```text
{课程名}｜Education·{主题或课时}（{任务类型}）｜{YYYY-MM-DD HH:mm}
```

业务页不显示 Conversation ID、Sandbox ID、内部路径、系统 Prompt 或原始思维链。

### 4.2 业务页展示

业务页只展示最新一次相关运行：

- Workflow 节点、状态和简化进度。
- 最新正式产物摘要。
- `预览最新产物`。
- `返回本次聊天`。
- 小型 `协作历史 {N}` 按钮。

“协作历史”打开轻量抽屉，只列任务名、时间、状态、Agent 数量和“进入聊天”。旧产物不在
业务页重复渲染；用户进入对应聊天查看当时的 Agent 对话和产物。

### 4.3 聊天展示

Education 聊天保留核心 Workflow 视觉，并增加通用的业务上下文卡：

- Education、课程、课时或主题、任务类型。
- `x/y Agent 已完成` 的简化进度。
- 每个 Agent 的用户可见说明与交接关系。
- 持久化产物卡和对应渲染器。
- `打开 Education 产物` 或 `返回业务页面`。

聊天不能通过解析标题或 Prompt 猜测业务对象。核心消息保存可选
`education_run_id` / `canonical_refs`，Education 提供按 `conversation_id` 查询的授权投影。

## 5. 聊天、Artifact 与 sandbox 生命周期

### 5.1 不变量

- Conversation、Message、Workflow elements 和可见 Agent 输出由核心数据库持久化。
- 课程、课件、题目、成绩、导图、EducationAsset 和版本由 Education 数据库持久化。
- Docker sandbox 只负责可丢弃计算，不是聊天历史或业务产物的真源。
- 打开旧聊天和预览正式 Education 产物不得启动或寻找旧 Docker 容器。

### 5.2 可见产物快照

只保存 `/workspace/...` 路径的文件不能成为可预览产物。Agent 报告的重要文件必须在运行
结束或容器进入 idle 前：

1. 通过白名单和权限校验。
2. 生成 checksum、MIME、大小和来源 manifest。
3. 小型结构化内容写入 Artifact/Education 版本；二进制或大文件写入可替换的
   Blob/ObjectStorage provider。
4. 在消息中保存持久 Artifact ID 或 Education canonical reference。

快照排除 provider home、API key、授权 token、隐藏推理和未授权文件。

### 5.3 TTL 与恢复

- 活跃运行期间保留 sandbox。
- 终态后使用可配置 idle TTL；建议开发默认 120 分钟，生产默认 30–120 分钟。
- 容器销毁后继续聊天时创建新的 runtime generation，从数据库消息摘要、持久附件、
  Education 当前上下文和必要快照恢复，不依赖 provider 隐式 resume marker。
- 后续增加 `SandboxSession` 持久状态与 snapshot provider；完整 workspace 热快照属于增强项，
  正式 Education 产物不受其 TTL 影响。
- 删除聊天优先软删除并立即销毁 sandbox；正式 Education 对象和审计记录不随聊天级联删除。

## 6. 课件工具可靠性

### 6.1 运行前预检

课件运行启动前检查：

- `weagent_tools` MCP server 或等价 provider adapter 已注册。
- `education_action` 可发现并可执行。
- grant 包含 `edu.course.context.get`、`edu.knowledge.search` 和
  `edu.courseware.create`。
- 课件制作 Agent 被绑定为必需写入节点。

预检失败时不创建完整 Agent 团队、不消耗生成配额，并显示可行动的基础设施错误。

### 6.2 写入状态机

```text
pending
→ preflight
→ collaborating
→ validating_draft
→ writing_canonical
→ completed
```

异常分支：

- 工具不可用：`preflight_failed`。
- 内容有效但缺少成功写入：`recoverable_draft`，自动定向重试课件制作节点一次。
- schema/参数错误：把字段路径和错误原因返回原 Agent 修复一次。
- 第二次仍未写入：`partial`，保留聊天、结构化草稿和“重试写入”入口。

只有审计中出现成功的 `edu.courseware.create`，且返回可读取的
`object_id/version_id`，运行才可进入 `completed`。聊天完成、文件路径或自然语言声明都不能
代替正式写入。

## 7. 课件 Skill 与视觉质量增强

### 7.1 Skill 分层

开发和 UAT 所使用的 Codex/桌面 Skills 与产品运行时能力必须分开：

- 开发期可使用 presentation、image generation、frontend design 和 browser automation
  能力制作样例、生成插图并进行真实浏览器视觉检查。
- WeAgent 产品必须把可复用能力注册为版本化 Capability/Skill，并通过 Tool Gateway 或
  sandbox adapter 调用；不能假设开发环境中的私有 Skill 自动存在于生产 Agent。

建议的产品能力包：

- `education.presentation.plan`：从教案生成页级叙事和版式 brief。
- `education.presentation.compose`：生成合法 `SlideDocument`。
- `education.presentation.theme.apply`：选择主题 token、母版和字体 fallback。
- `education.presentation.visual_asset`：检索或生成有来源的插图、图标和图表。
- `education.presentation.render`：生成 HTML、PNG 页面和 PPTX。
- `education.presentation.visual_qa`：检查溢出、遮挡、对齐、对比度、密度和素材失败。
- `education.presentation.repair`：根据 QA finding 定向修改问题页。

### 7.2 借优与边界

- 参考 [Anthropic PPTX Skill](https://github.com/anthropics/skills/tree/main/skills/pptx)
  的“模板资产 + 渲染 + 逐页视觉检查 + 修复”工作流；该目录是 source-available 参考，
  未确认可兼容许可证前不复制实现。
- Skill 包结构参考 [OpenAI Skills](https://github.com/openai/skills) 的
  `SKILL.md + scripts + references + assets` 分层。
- 当前仓库以 `python-pptx` 作为基础 PPTX 导出 Provider；后续评估
  [PptxGenJS](https://github.com/gitbrent/PptxGenJS) 作为原生可编辑对象、母版和图表能力更强的
  可替换 Provider。无论采用哪一个，`SlideDocument` 都是业务真源。
- 使用 [reveal.js](https://github.com/hakimel/reveal.js) 作为 HTML 交互预览基线。
- [Slidev](https://sli.dev/) 和 [Marp](https://marp.app/) 作为主题、Markdown 和
  多格式导出参考或可替换 provider；其 PPTX 常以页面图像保证视觉一致，不能冒充完全可编辑
  的 PowerPoint。
- PPTist 只研究交互和数据模型，不复制 AGPL 源码进入主前端。

### 7.3 初始风格

质量增强阶段至少提供四种可选风格，主题只改变视觉 token 和版式策略，不改变教学内容：

1. **清朗课堂**：高留白、高对比、适合通用讲授。
2. **纸张批注**：阅读材料、重点句和写作批注，优先高中英语。
3. **童趣绘本**：柔和色彩、插图和识字卡，优先小学语文。
4. **深色聚焦**：大字号、少文本、适合展示和讨论。

每种风格声明颜色、字体栈、字号阶梯、间距、圆角、图像策略、允许版式和
`subject/grade_band` 适用范围。中文字体必须有可部署 fallback，不能依赖开发机字体。

### 7.4 自动视觉验收

生成后必须先把每页渲染为图片，再由规则检查和视觉模型/人工抽检共同验证：

- 无裁切、溢出、重叠、空白占位符或破图。
- 标题、正文、注释层级清晰。
- 字号、行数和文本密度适合投影。
- 对齐、间距、色彩和视觉 motif 在整套课件中一致。
- 图片与课程内容相关，并记录来源或生成 provenance。
- HTML 预览、页面截图和 PPTX 的主要内容一致。
- PPTX 可由 PowerPoint 或 LibreOffice 打开，文本和基础形状可继续编辑。

视觉 QA 失败时只重做问题页，最多自动修复一轮；仍失败则保留结构化版本并明确标记，不能
声称“美观验收通过”。

## 8. 分阶段顺序

1. **P0 工具可靠性**：MCP/Tool 预检、`edu.courseware.create` 必需写入、定向重试。
2. **P1 信息架构与追溯**：单一主侧栏、页面顶部课程上下文、学生教学空间、双向聊天、
   最新运行和协作历史入口。
3. **P2 持久预览与容器治理**：Artifact/canonical refs、sandbox TTL、按需重建。
4. **P3 课件质量增强**：多风格、插图能力、渲染截图、视觉 QA、问题页修复。

P3 可以后置，但 P0–P2 不能依赖它。任何阶段都不得用保存长期 Docker 容器代替数据持久化。

## 9. 验收标准

- 任一 Education 页面只有一根主侧栏和一个“教学空间”入口。
- 教师和学生的领域集合与当前课程真实成员角色一致。
- 学生能在教学空间下载课件、完成作业并查看作业弱点。
- 业务页仅显示最新运行/最新产物，并能进入本次聊天和历史聊天。
- 聊天能显示 Education 上下文、Workflow、多 Agent 输出和持久产物预览，并能返回业务页。
- 删除或回收 sandbox 后，旧聊天、Workflow、正式产物和已快照预览仍可打开。
- 工具未注册时课件任务在预检阶段失败；不能运行完整团队后再伪装成功。
- 成功课件运行必须留下 `edu.courseware.create` 成功审计和可读取版本。
- P3 完成后，用户至少可选择四种风格，生成结果通过真实页面截图视觉检查和 PPTX 打开验证。
