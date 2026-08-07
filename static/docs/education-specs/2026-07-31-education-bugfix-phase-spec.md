# Education 产品 Agent、会话、上传与产物预览 Bugfix Phase 规格

## 0. 文档状态

- 日期：2026-07-31
- 状态：根因诊断完成，等待确认后实施
- 文档类型：Bugfix Phase Spec
- 适用范围：WeAgent Education 教师端、学生端、核心聊天、Education 独立服务、Sandbox 文件预览
- 本轮约束：只完成真实前后端诊断和方案定稿，不修改业务代码

## 1. 本阶段目标

本阶段解决的不是若干孤立按钮问题，而是修复以下四条产品契约：

1. 用户只表达自然业务意图，系统策略、工具约束、Schema 和 Agent 分工不能伪装成用户消息。
2. Education 发起的聊天必须永久归属于正确的 Education 工作空间，刷新和 Sandbox 回收后仍可检索。
3. “预览最新产物”必须打开本次运行成功写入的正式 Education 对象及版本，不能只跳转到一个业务页面。
4. 所有 Education 上传入口声明的文件大小上限必须与数据库真实承载能力一致，并返回可诊断的业务错误。

本阶段完成后，教师应能用一句“根据我的教案帮我生成 PPT”发起任务，在聊天中追踪协作，在业务页预览正式产物；课件、材料和知识库文件可稳定上传、刷新、下载；学情分析可显示可读摘要和正式报告，而不是 JSON 编译错误或鉴权错误。

## 2. 用户问题的精确表述

### BUG-01：产品内自然请求被内部运行协议冒充为用户消息

**用户预期**

用户输入或确认的是自然业务意图，例如：

> 根据当前教案生成 6—8 页高中英语读写课件，使用纸张批注风格。

**当前表现**

聊天中显示为用户发送了一段很长的运行协议，其中包含：

- 工具白名单与调用约束；
- `idempotency_key`、`course_id` 注入规则；
- Sandbox 文件名和目录约束；
- `SlideDocument` Schema；
- Agent 角色分工；
- 校验、修复和最终写入协议。

**问题性质**

这不是文案过长，而是消息角色建模错误。内部执行上下文被作为 `/api/messages.content` 写入，并以 `sender_type=user` 持久化，导致：

- 用户看起来像主动输入了系统 Prompt；
- 产品策略、内部路径和实现细节被暴露；
- 后续审计无法区分“用户真正要求”与“系统追加约束”；
- 同一套系统规则被重复拼接、重复存储，难以版本化。

### BUG-02：Education 自动创建的聊天在左侧会话栏消失

**用户预期**

从课件、学情分析等业务页发起的聊天，应自动出现在当前用户的 Education 聊天列表中，刷新后仍存在。

**当前表现**

- 从业务页“返回本次聊天”可以进入；
- 左侧会话栏不一定出现该会话；
- 直接进入时可能临时可见，刷新聊天列表后再次消失。

**问题性质**

Education Runtime 创建 Conversation 时没有提交 `workspace_id`。聊天侧列表按当前工作空间过滤；直接路由只会临时补入当前会话，而刷新时会用过滤后的服务端结果覆盖。

真实数据进一步确认：本次课件运行的 Conversation 已存在于核心数据库，但 `workspace_id = NULL`。现有启动迁移还会把未归属会话默认放入研发空间，不能正确修复 Education 会话。

### BUG-03：聊天中的 Markdown、HTML、JSON 产物不能按类型正确预览和编辑

**用户预期**

- Markdown：按文档渲染，可切换编辑；
- HTML：在受限预览容器中显示真实页面，可编辑源文件；
- JSON：显示结构化摘要、树形信息或原始数据，不执行、不“编译”；
- 正式 Education 产物：提供业务渲染器，而不是暴露文件路径。

**当前表现**

- HTML 预览显示 `{"msg":"Missing Authorization Header"}`；
- JSON 被当作需要编译的内容，失败时出现错误或乱码；
- Markdown 主要落入代码查看逻辑；
- 部分失败文案本身已经是乱码；
- 预览依赖仍在运行的 Sandbox 文件。

### BUG-04：“预览最新产物”没有预览具体产物，且会报错

**用户预期**

点击按钮后打开当前 Agent 运行最终采纳的课件版本、学情报告或其他正式业务产物。

**当前表现**

- 按钮存在时不代表运行已经产生正式产物；
- 点击后主要执行 `router.push(run.business_route)`；
- 已在对应业务页时仍可能再次导航并抛出错误；
- 课件页和学情页没有消费组件发出的 `preview` 事件；
- 运行记录没有给前端稳定的 `object_id/version_id` 预览引用。

因此，该按钮现在是“跳转到业务模块”的脆弱别名，不是产物预览。

### BUG-05：课件、课时材料、知识库等上传入口对正常文件普遍失败

**用户预期**

产品声明支持的 PPTX、PDF、DOCX、HTML 等文件，在 25MB 限制内均可上传并持久化。

**当前表现**

- 很小的测试文件可以成功；
- 常见大小的文件返回 HTTP 500 / Server Error；
- 前端统一显示“上传失败，请检查文件类型和大小”，无法知道真实原因；
- 多个入口表现相似。

**问题性质**

这些入口最终共用 `edu_assets.blob_bytes`，因此不是多个独立前端 Bug，而是共享存储契约失配。

### BUG-06：逐页视觉检查只有结论，没有可核验页面

**用户预期**

课件的“视觉检查通过”必须有逐页缩略图或渲染页作为证据；教师可点击放大检查具体页面。

**当前表现**

界面能显示检查通过，但没有逐页编译后的预览入口；用户无法确认页面是否真的无溢出、遮挡、乱码或破图。

## 3. 已完成的真实诊断

### 3.1 验证方法

本次诊断同时使用：

- 内置浏览器操作真实教师端界面；
- 核心网关 HTTP 请求；
- Education 独立服务；
- MySQL 表结构和事务写入；
- Sandbox 文件树与原始文件接口；
- 前端和后端源代码路径核对。

未使用 Mock 页面替代真实产品链路。

### 3.2 上传诊断结果

| 验证点 | 结果 | 结论 |
|---|---|---|
| 浏览器上传 305B HTML | 成功，文件立即出现在课程文件柜 | 选择文件、FormData、网关转发和权限链路基本可用 |
| 经核心网关上传 70,085B HTML | HTTP 500 | 可稳定复现用户所见 Server Error |
| Education 应用配置 | 允许最大 25MB | 业务层认为 70KB 合法 |
| MySQL `edu_assets.blob_bytes` | 实际类型为普通 `BLOB` | 最大容量约 65,535B |
| 事务 `flush()` | MySQL `DataError 1406: Data too long for column 'blob_bytes'` | 已确认直接根因 |
| MySQL `max_allowed_packet` | 64MB | 不是本次失败原因 |

**根因结论**

应用层允许 25MB，但数据库字段仍是普通 `BLOB`。超过约 64KB 的文件在数据库写入阶段失败。PPTX、PDF、DOCX 和一般 HTML 通常都会超过该阈值，所以用户会感觉“所有上传能力都不行”。

课件文件柜、课时材料和课程知识中心最终都写入同一张 `edu_assets` 表，因此共享同一根因。

此外，当前上传路由只捕获业务校验异常，没有捕获 SQLAlchemy/MySQL `DataError`；核心网关最终只能返回泛化的 500。前端又丢弃服务端错误详情，进一步把根因隐藏为通用提示。

### 3.3 HTML 预览诊断结果

本次课件 Agent 的 Sandbox 中确实存在完整文件：

- `slide_document.json`
- `preview.html`

同一份 `preview.html`：

- 携带合法 Bearer JWT 请求时返回 HTTP 200 和 `text/html`；
- 不携带 JWT 时返回 HTTP 401：

```json
{
  "msg": "Missing Authorization Header"
}
```

前端 Axios 实例会自动增加 JWT，但 `<iframe src="...">` 不会增加自定义 Authorization Header；原生 `fetch(...)` 也没有复用 Axios 拦截器。当前 HTML 预览正好走了无鉴权直链，因此用户看到的不是 HTML，而是 401 JSON。

### 3.4 “预览最新产物”诊断结果

当前组件执行顺序是：

1. 发出 `preview` 事件；
2. 如果存在 `run.business_route`，执行路由跳转。

但存在三个确定问题：

1. 课件页和学情页没有监听该 `preview` 事件；
2. `this.$route.fullPath` 是字符串，`run.business_route` 是 `{path, query}` 对象，两者比较永远不相等；
3. `business_route` 只有模块路由，没有正式产物的对象 ID、版本 ID 和渲染类型。

这解释了为什么点击后可能报导航错误，也解释了为什么即使成功跳转，仍无法知道应该预览哪一份产物。

### 3.5 会话持久性诊断结果

真实课件会话包含完整的 6 条消息、多 Agent Workflow 和文件元素，说明聊天数据本身已经进入核心数据库；但该 Conversation 的 `workspace_id` 为空。

核心创建会话请求当前只提交：

- 标题；
- 群聊类型；
- Agent 参与者；
- `kb_domain=edu`；
- Agent 配置。

没有提交或由服务端解析 Education Workspace。左侧栏刷新后按 Workspace 查询，自然无法返回该会话。

### 3.6 源文件编码诊断

相关组件中的部分中文字符串已经以乱码形式存在于源文件，而不是仅在浏览器渲染时发生编码转换。Bugfix 实施时必须将被修改文件统一保存为 UTF-8，并增加静态乱码扫描，不能只在 UI 上替换一两个可见字符串。

## 4. 目标设计

### 4.1 用户意图与执行上下文分层

一次产品 Agent 任务拆成两个对象：

#### A. `VisibleUserIntent`

作为用户可见消息持久化，只包含用户真实提供或在表单中确认的内容：

```json
{
  "summary": "根据当前教案生成 PPT",
  "requirements": "6—8 页，高中英语读写，纸张批注风格"
}
```

#### B. `AgentExecutionEnvelope`

只存在于服务端运行上下文或 Run 元数据，不以用户身份显示：

```json
{
  "course_context_ref": "...",
  "lesson_context_ref": "...",
  "workflow_definition_ref": "...",
  "tool_grant_ref": "...",
  "policy_version": "...",
  "artifact_contract_version": "...",
  "runtime_constraints": {}
}
```

系统 Prompt、Agent 分工、工具使用规则、Schema、最终写入协议分别由版本化的 Policy、Workflow、Skill/Capability 和 Artifact Contract 组装。

**强制约束**

- 用户消息不得包含系统 Prompt、Token、内部 ID、Sandbox 路径或工具注入细节；
- Runtime 可以同时接收 `display_content` 与 `execution_context`，但聊天记录只把前者标为用户消息；
- 旧会话保持只读兼容，不重写历史用户消息；
- 新运行必须记录所用 Policy/Workflow/Contract 版本，便于审计。

### 4.2 Education 会话的可信 Workspace 归属

创建产品会话时，由核心服务根据以下信息解析 Workspace：

```text
认证用户 + domain=edu + 当前课程成员角色
```

不允许浏览器任意指定其他用户的 Workspace。

建议契约：

```json
{
  "domain": "edu",
  "workspace_context": {
    "course_id": "...",
    "membership_role": "teacher"
  }
}
```

核心服务解析或创建该用户对应的 Education Workspace，并把 `workspace_id` 写入 Conversation。

迁移规则：

- 通过 `EducationAgentRun.conversation_id` 精确识别历史 Education 会话；
- 将其回填至同一用户、同一角色的 Education Workspace；
- 不再把所有 `workspace_id IS NULL` 的会话默认归入研发空间；
- 直接链接、侧栏列表和刷新必须读取同一个数据源，不能靠前端临时插入。

### 4.3 正式产物引用 `adopted_object`

每个成功完成的产品 Agent Run 必须保存：

```json
{
  "adopted_object": {
    "domain": "edu",
    "object_type": "courseware",
    "object_id": "...",
    "version_id": "...",
    "preview_kind": "slide_document",
    "business_route": {
      "path": "/education/teacher/courseware",
      "query": {
        "courseId": "...",
        "lessonId": "..."
      }
    }
  }
}
```

学情分析使用对应的 `student_insight_report` 类型。该对象只能来自成功的 Education 写工具返回值，不能从聊天标题、自然语言、文件名或 Sandbox 路径猜测。

**按钮规则**

- 只有存在且可读取 `adopted_object` 时显示“预览最新产物”；
- `running`、`partial`、`failed` 或缺少正式写入时，显示“尚无可预览的正式产物”，不能跳转；
- 点击后按 `object_id + version_id` 打开业务预览抽屉或详情页；
- “返回业务页面”与“预览产物”是两个不同按钮；
- 路由比较使用 Router 解析后的规范化 `fullPath`，并处理重复导航。

### 4.4 预览渲染策略

| 产物类型 | 默认行为 | 编辑行为 |
|---|---|---|
| 正式课件 | 使用 `SlideDocument` 业务渲染器，显示整套和逐页缩略图 | 进入对应版本的课件编辑器 |
| 正式学情报告 | 显示结论摘要、统计指标、证据引用和生成时间 | 只允许教师调整可编辑说明，不改写原始成绩证据 |
| Markdown | 安全 Markdown 渲染 | 文档编辑器 |
| 自包含 HTML | 经鉴权 API 取回 Blob/文本，在 sandboxed iframe 中渲染 | HTML 编辑器 |
| JSON | 结构化摘要、树形查看、原始数据折叠 | 文本编辑；不执行、不编译 |
| 普通文本 | 文档阅读模式 | 文本编辑器 |
| 不支持的二进制 | 显示元数据和下载 | 在对应业务编辑器或外部应用打开 |

MVP 的聊天 HTML 预览使用 Axios 鉴权读取内容，再生成短生命周期 Blob URL 或 `srcdoc`。iframe 必须启用严格 `sandbox`，销毁组件时回收 Blob URL。

多文件 HTML 或依赖相对资源时，不把长期 JWT 放入 Query。后续使用短期、单会话、单路径、只读的预览票据，或由服务端生成经过白名单校验的预览 Bundle。

正式 Education 产物不应依赖 Sandbox 预览链路。Sandbox 被回收后，`adopted_object` 对应的正式版本仍必须可预览。

### 4.5 课件逐页可视化证据

课件版本保存后生成：

- 每页渲染缩略图；
- 每页视觉 QA 状态；
- 溢出、遮挡、字体缺失、破图等具体 Finding；
- 渲染器版本和生成时间。

业务页提供“逐页预览”：

- 缩略图网格；
- 点击后进入大图或真实页面渲染；
- 可从问题页直接进入编辑器；
- “视觉检查通过”必须能回溯到本次版本的渲染证据。

### 4.6 上传存储修复

本阶段保持“Education 数据库为主要持久化来源”的既定边界，不强制引入对象存储。

#### 数据库

将：

```sql
blob_bytes BLOB NOT NULL
```

迁移为：

```sql
blob_bytes LONGBLOB NOT NULL
```

不能使用 `MEDIUMBLOB`，因为它最大约 16MB，仍小于产品当前声明的 25MB。

SQLAlchemy 模型使用 MySQL `LONGBLOB` 方言变体，同时保持 SQLite 测试兼容。迁移必须可重复执行，并在执行前记录表大小和备份策略。

#### 应用

- 保持单文件 25MB 上限；
- 保持 MySQL `max_allowed_packet >= 32MB`，当前 64MB 足够；
- 在读取全部文件前后都校验大小；
- 捕获数据库 `DataError` 并回滚；
- 返回稳定错误码，例如 `asset_storage_capacity_exceeded`，不得退化为通用 500；
- 记录文件大小、MIME、扩展名、checksum、课程、操作者和失败阶段，不记录文件正文。

#### 前端

- 课件、课时材料、知识中心统一显示服务端 `error/error_code` 对应的中文提示；
- 文件过大、扩展名不支持、服务不可用、存储失败必须区分；
- 上传中显示文件名、大小和进度；
- 成功后重新查询服务端列表，不仅依赖本地追加；
- 下载后可通过 checksum 或字节数验证完整性。

#### 未来扩展

对象存储作为 `storage_backend` 的可替换 Provider 保留，但不作为本 Bugfix 的前置条件。当课程资产量、备份成本或数据库膨胀达到阈值时，再迁移二进制正文；元数据和权限始终由 Education 数据库持有。

## 5. 实施范围

### 5.1 本阶段必须完成

1. 上传列迁移至 `LONGBLOB`，修复所有共享 `edu_assets` 的上传入口。
2. 增加数据库异常映射和可读前端错误。
3. 分离可见用户意图与内部执行上下文。
4. 新 Education 会话写入可信 Workspace，并回填历史 Education 会话。
5. Product Run 持久化 `adopted_object`。
6. “预览最新产物”按正式对象和版本打开，不再只跳路由。
7. 修复聊天 HTML 鉴权读取、Markdown 渲染、JSON 摘要和乱码文案。
8. 课件提供真实逐页预览和视觉 QA 证据入口。
9. 学情分析最新产物使用正式报告预览，不尝试编译 JSON。
10. 增加真实 MySQL、核心网关和浏览器 UAT。

### 5.2 本阶段不做

- 不引入完整对象存储集群；
- 不重写历史聊天内容；
- 不允许 Agent 直接访问数据库；
- 不把长期 JWT 放到文件 URL；
- 不把 Sandbox 文件路径升级为正式业务引用；
- 不在本阶段扩展新的 Education 业务模块；
- 不以“保留 Docker 容器”代替会话和产物持久化。

## 6. 推荐实施顺序

### P0：阻断性数据与鉴权问题

1. `edu_assets.blob_bytes` 迁移为 `LONGBLOB`；
2. 上传异常分类和前端错误透传；
3. HTML 经鉴权读取并安全渲染；
4. 修复被触达组件的 UTF-8 乱码。

### P1：会话与 Prompt 语义

1. 定义 `VisibleUserIntent / AgentExecutionEnvelope`；
2. Runtime 使用隐藏执行上下文；
3. Education Conversation 绑定正确 Workspace；
4. 历史 Education Conversation 精确回填。

### P2：正式产物双向关联

1. Tool 成功结果写入 `adopted_object`；
2. 业务页按正式版本预览；
3. 聊天页显示正式产物卡并可返回业务对象；
4. 对无正式产物的运行禁用错误预览入口。

### P3：可视化验收

1. 课件逐页缩略图和放大预览；
2. 视觉 QA Finding 绑定具体页；
3. 学情报告摘要与证据钻取；
4. Sandbox 回收后的持久化回归。

## 7. 数据迁移与回滚

### 7.1 上传列迁移

- 迁移前：记录 `edu_assets` 行数、总字节数、最大文件和表结构；
- 迁移：`ALTER TABLE edu_assets MODIFY blob_bytes LONGBLOB NOT NULL`；
- 迁移后：上传 64KB 以上文件并读取 checksum；
- 该列升级对旧代码向后兼容，不建议回退为 `BLOB`；
- 若出现应用问题，应回滚代码而保留 `LONGBLOB`。已有大文件时强行缩列会造成数据不可表示。

### 7.2 会话回填

- 只回填被 `EducationAgentRun.conversation_id` 引用的会话；
- 每条迁移记录原值、目标 Workspace 和原因；
- 冲突时不覆盖，进入异常报告；
- 不按标题文本猜测 Education 会话。

### 7.3 `adopted_object`

- 新字段或 JSON 结构允许为空，以兼容旧运行；
- 旧运行若存在可验证的成功工具调用，可离线回填；
- 无法验证的旧运行继续显示聊天和 Workflow，但不显示“预览最新产物”。

## 8. 测试与验收标准

### AC-01：自然语言请求

- 教师只输入或确认一句自然业务请求；
- 聊天中的用户消息不包含系统规则、内部路径、Token、Schema 或 Agent 操作协议；
- 后端运行日志能关联 Policy、Workflow 和 Artifact Contract 版本。

### AC-02：会话可恢复

- 从课件页和学情页分别创建一次 Agent 任务；
- 两个会话立即出现在 Education 聊天列表；
- 刷新页面、重新登录后仍存在；
- 直接链接与侧栏选择打开同一个 Conversation；
- 回收 Sandbox 后，历史消息和正式产物仍可查看。

### AC-03：上传矩阵

通过核心网关和真实 MySQL 分别验证：

| 文件 | 大小 | 预期 |
|---|---:|---|
| HTML | 1KB | 成功 |
| HTML | 70KB | 成功 |
| PPTX | 1—5MB | 成功 |
| PDF | 1—5MB | 成功 |
| DOCX | 1—5MB | 成功 |
| 支持类型 | 24.9MB | 成功 |
| 任意类型 | 大于 25MB | 明确返回文件过大，不是 500 |
| 不支持类型 | 任意合法大小 | 明确返回类型不支持 |

每个成功文件必须：

- 刷新后仍在；
- 可下载；
- 下载字节数和 SHA-256 与上传文件一致；
- 教师私有与课程发布权限正确；
- 学生只能看到已发布内容。

### AC-04：聊天产物预览

- HTML 不再显示 `Missing Authorization Header`；
- Markdown 默认显示为排版文档；
- JSON 显示摘要/树形/原始折叠，不执行编译；
- 编辑并保存后重新打开内容一致；
- 所有中文提示均为 UTF-8，无乱码；
- 不向 URL、日志或页面泄露长期 JWT。

### AC-05：正式产物预览

- 只有成功写入 Education 的运行显示“预览最新产物”；
- 课件按钮打开准确的 `object_id/version_id`；
- 学情按钮打开准确的正式报告；
- 点击不产生重复导航错误；
- 老版本可从聊天历史进入，但业务页默认只显示最新版本；
- Sandbox 停止或删除后，正式产物预览仍成功。

### AC-06：逐页视觉检查

- 每一页都有真实渲染缩略图；
- 可点击查看大图或真实渲染；
- QA 失败精确指出页码和 Finding；
- “通过”状态能关联本版本的渲染证据；
- 至少用内置浏览器检查桌面宽屏和窄屏布局。

## 9. 自动化测试缺口

当前资产测试主要使用 SQLite 内存库和极小字节串，无法发现 MySQL `BLOB` 容量问题。本阶段必须增加：

- MySQL 集成测试，而非只跑 SQLite；
- 64KB 边界上下测试；
- 25MB 产品上限测试；
- 经核心 Domain Proxy 的 Multipart 测试；
- PPTX/PDF/DOCX/HTML 真实样本；
- 401/403/404/413/422/500 错误映射测试；
- iframe/Blob HTML 预览鉴权测试；
- Conversation Workspace 刷新回归；
- `adopted_object` 与成功工具调用一致性测试；
- Sandbox 回收后的正式产物预览测试。

## 10. 完成定义

本阶段只有在以下条件同时满足时才算完成：

1. 所有 P0—P3 必做项已实施；
2. 自动化测试通过；
3. 使用内置浏览器完成真实教师端前端 UAT；
4. 使用核心网关、Education 服务和 MySQL 完成后台验证；
5. 上传矩阵、会话刷新、HTML 预览、正式产物预览、逐页预览全部通过；
6. 没有用 Mock、临时直连、保留 Sandbox 或手工改数据库替代产品链路；
7. 仅允许存在不阻断主流程、已记录且可复现的小型 UI 缺陷。

## 11. 本次诊断结论

当前最先需要修复的阻断项顺序是：

1. **上传数据库列类型失配**：这是正常文件普遍 500 的直接根因；
2. **HTML 预览鉴权链路缺失**：这是 `Missing Authorization Header` 的直接根因；
3. **正式产物引用缺失**：这是“预览最新产物”只能跳页面或报错的结构性根因；
4. **Education Conversation 未绑定 Workspace**：这是会话刷新后消失的直接根因；
5. **内部执行协议以用户消息持久化**：这是 Prompt 角色错位的直接根因；
6. **类型渲染器和 UTF-8 基线不完整**：这是 JSON、Markdown 和乱码问题的共同根因。

这些问题可以在一个 Bugfix Phase 内完成，但必须按共享契约修复，不能分别在课件页、学情页和聊天页堆叠特例。
