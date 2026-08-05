# Education 导航、Agent 工作流、课件实渲染与作业闭环 Bugfix Phase 2 规格

## 0. 文档状态

- 日期：2026-07-31
- 状态：问题确认、根因诊断与交互设计均已确认，可进入实施阶段
- 文档类型：Bugfix / Product Completion Phase Spec
- 基线分支：`feature/education`
- 基线提交：`349dd9f fix(education): harden uploads and artifact previews`
- 前置文档：`2026-07-31-education-bugfix-phase-spec.md`
- 规格形成阶段约束：先完成问题确认、根因定位和方案定稿；业务代码在本规格确认后进入独立 Goal 实施

## 1. 本阶段结论

用户提出的 8 项内容并不都属于同一种问题，应拆成三类处理：

1. **确定性缺陷**：首次进入 Education 只显示一个左侧模块、带审核节点的固定工作流必然失败、聊天中虚构 HTML 路径触发鉴权错误、逐页视觉检查不是实际导出结果。
2. **已有能力入口错误**：课程知识中心层级不符合产品信息架构；帮助中心已有页面和路由，但主导航没有入口。
3. **中等规模产品补全**：文档/照片/PDF 发布作业、OCR 结构化导入、教师查看与批改学生提交，需要作为独立小阶段建设，不能伪装成按钮级 Bugfix。

本阶段建议按 `2A → 2B → 2C` 实施：

- **Phase 2A：稳定性与信息架构修复**

  修复 1—5、7，并为实际导出渲染建立统一预览契约。
- **Phase 2B：作业文件导入与 OCR 草稿**

  完成 6 的最小闭环。
- **Phase 2C：教师提交复核工作台**

  完成 8 的成品级教师批改体验。

这样可以保持 Education 服务、核心聊天和 Sandbox 的隔离边界，也避免把 OCR、Office 渲染器和批改领域模型挤进现有单页组件。

## 2. 验证基线

### 2.1 已启动并验证的服务

| 服务 | 地址 | 结果 |
|---|---|---|
| 核心后端 | `http://127.0.0.1:5002/api/health` | HTTP 200 |
| Education 服务 | `http://127.0.0.1:5102/health` | HTTP 200 |
| 前端 | `http://127.0.0.1:8080` | HTTP 200 |
| MySQL | 本机 3306 | 可连接并完成真实数据查询 |
| Sandbox | Docker | 可创建并运行 Education Agent 会话 |

### 2.2 真实 Agent 验证

本轮创建了隔离 UAT 教师、课程和 Student Insight 产品运行，运行结果如下：

- 产品类型：`student_insight`
- 运行状态：`completed`
- 两个工作节点均为 `done`
- 最终写入正式 `student_insight_report`
- 返回了可追溯的 `object_id` 和 `version_id`
- 正式业务路由为 `/education/teacher/insights`

这说明当前冷启动后的“学生画像与评估”固定 Agent 组合可以运行。用户截图中的“服务端固定工作流无效”来自另一条“阅读课教案协作”链路，二者不能混为一个故障。

### 2.3 历史错误记录

核心数据库中只找到一条与截图一致的错误消息：

- 时间：2026-07-31 12:39:07
- 会话：`高中英语读写成品验收 … · Agent 教案协作`
- 会话内 Agent：课程设计师、习题生成器、教学审校员、任务主持人

所需 Agent 均真实存在，因此历史错误不是 Agent 被删除或 Agent ID 丢失。

## 3. 问题与最小解决方案

## BUG-201：首次进入 Education 后，左侧只显示“教学空间”

### 用户看到的现象

首次登录、选择 Education 领域或尚未选中课程时，左侧“领域”区域只有“教学空间”。教师看不到“PPT 与课件”“学生画像与评估”；学生也看不到“模拟考试”“课程思维导图”。

### 已确认根因

`Sidebar/index.vue` 中的 Education 导航以 `activeCourse + membershipRole` 为显示条件：

```js
if (!course || !this.membershipRole) return [teachingSpace]
```

也就是说，导航可见性错误地依赖“是否已选中具体课程”，而不是依赖用户已选择的 Education 身份。首次进入时课程上下文还未恢复，所以必然只显示一个模块。

这不是顶层“智慧教育领域丢失”，而是 Education 领域下的独立模块被课程上下文提前隐藏。

### 最小解决方案

1. 用 Education Workspace 中的稳定身份字段决定导航集合：
   - 教师：教学空间、PPT 与课件、学生画像与评估、帮助中心；
   - 学生：教学空间、模拟考试、课程思维导图、帮助中心。
2. 课程只决定目标页面的上下文，不决定模块是否可见。
3. 没有课程时：
   - 教学空间进入课程创建/选择页；
   - 其他模块仍可进入，但显示“先选择或创建课程”的空状态；
   - 不直接报错，也不静默隐藏。
4. 刷新时先恢复 Education 身份，再异步恢复最近课程，避免导航闪烁。

### 验收标准

- 新用户选择教师身份后，无课程也能看到教师 4 个模块。
- 新用户选择学生身份后，无课程也能看到学生 4 个模块。
- 选择课程后模块不增不减，只更新课程上下文。
- 教师和学生不能看到对方专属模块。

## BUG-202：阅读课 Agent 协作返回“固定工作流无效”

### 用户看到的现象

从课时发起“阅读课设计（4 节点、3 连线）”后，任务立即返回：

> 服务端固定工作流无效或引用了不可用的 Agent。

### 已确认根因

Education 的 `reading_lesson` 模板包含：

1. 课程设计师；
2. 习题生成器；
3. 教学审校员；
4. `teacher-approval` 审核节点。

Education 把四个节点原样作为 `server_defined` 工作流发送给核心后端。核心后端 `_server_defined_workflow_plan` 的编译规则却是：

```python
if not isinstance(raw, dict) or raw.get('type') != 'agent_task':
    return None
```

因此只要模板包含 `approval` 节点，整张固定工作流就必然被判无效。数据库已确认三个业务 Agent 均存在，排除了“不可用 Agent”这一分支。

### 与“AI 分析师 Server Error”的关系

- 学生画像独立产品链路当前已完成真实运行，后端和 Agent 目录在冷启动后正常。
- 截图对应的是课时教案协作链路，不是学生画像链路。
- 两条链路共用部分核心 Runtime，但模板结构不同；不能通过增加重试或重建 Docker 一并解决。

### 最小解决方案

遵循此前“不是每个 Agent 阶段都人工审核”的产品决定：

1. Education 运行编译器只把 `agent_task` 发给核心 Runtime。
2. `approval` 不作为 Agent 节点执行，不创建 Sandbox Agent，也不参与核心依赖图。
3. Education 服务保留发布门禁：
   - Agent 运行完成后保存教师草稿；
   - 只有教师点击“发布”时才进行一次明确确认；
   - 教案、习题、课件不在每个步骤等待人工审核。
4. 编译时把跨审核节点的边重新连接到下一个可执行 Agent；若审核是尾节点，则直接从 Agent 图中移除。
5. 核心错误必须细分：
   - `unsupported_workflow_node_type`
   - `missing_worker`
   - `cyclic_workflow`
   - `invalid_finalizer`

### 需要补充的测试

- 含尾部 `approval` 的阅读课模板可执行三个 Agent 并形成草稿。
- 不含 `approval` 的学情分析模板行为不变。
- 发布动作仍要求教师确认。
- 缺少真实 Agent 时返回 `missing_worker`，不能继续使用当前模糊文案。
- 页面在 Sandbox 初始化期间显示“准备运行环境 / 创建 Agent / 预检工具”，不能把两分钟冷启动误报为 Server Error。

## BUG-203：逐页视觉检查与 PPTX/HTML 导出完全不一致

### 用户看到的现象

“逐页视觉检查”能看出是 PPT 内容，但它的布局、字体、换行和页面效果与下载的 PPTX 或 HTML 不一致。因此“检查通过”不能证明实际导出文件可用。

### 已确认根因

当前系统实际有三个渲染器：

| 场景 | 当前渲染方式 |
|---|---|
| 逐页视觉检查 | 前端根据 `SlideDocument` 再构造一份 HTML |
| HTML 导出 | 使用当前内容版本保存的 `rendered_html` |
| PPTX 导出 | `python-pptx` 根据 `SlideDocument` 重新排版 |

后端的 `visual-qa` 接口虽然生成了 PPTX 字节，但 `inspect_pptx_bytes` 只检查包结构、Shape 数量和边界等信息，没有把真实 PPTX 渲染为图片。接口返回的逐页数据仍来自源 JSON，前端再进行第四次近似表达。

因此当前“逐页视觉查看”是**源文档模拟预览**，不是 PPTX 实渲染，也不是 HTML 导出预览。

### 目标契约

所有视觉检查必须明确检查对象：

- **HTML 实际导出预览**：展示当前版本导出的同一份 HTML。
- **PPTX 实际导出预览**：展示当前版本 PPTX 经 Office 兼容渲染器生成的逐页图片。
- **结构检查**：单独显示 SlideDocument Schema、溢出风险和可编辑 Shape 检查结果。

三者不能再共用“逐页视觉检查”这个含混名称。

### 最小可落地方案

1. `SlideDocument` 继续作为唯一规范源。
2. Education 服务生成当前版本 PPTX。
3. 独立 Render Adapter 使用 LibreOffice headless 把 PPTX 转成 PDF。
4. 使用 PyMuPDF 把 PDF 每页转换成 PNG/WebP 缩略图和高清图。
5. 生成并持久化 Render Manifest：
   - `content_id`
   - `version_id`
   - 源文档 checksum
   - exporter 版本
   - LibreOffice 版本
   - 页面数
   - 每页图片 asset ID、尺寸和 checksum
   - 渲染状态与错误
6. 前端视觉检查弹窗显示真实页面缩略图，点击后放大。
7. HTML 页签直接加载正式 `rendered_html` 的鉴权 Blob，不重新拼页面。
8. Render Adapter 不可用时明确显示“PPTX 实渲染服务不可用”，不得回退成模拟页并宣称通过。

LibreOffice 的命令行 PDF 转换能力与 PyMuPDF 的页面渲染能力均有官方文档，可作为独立服务适配器实现：

- [LibreOffice PDF 命令行参数](https://help.libreoffice.org/latest/om/text/shared/guide/pdf_params.html)
- [PyMuPDF 基础能力](https://pymupdf.readthedocs.io/en/latest/the-basics.html)

### 验收标准

- 同一内容版本的 PPTX 下载文件与视觉检查页来自同一份 PPTX 字节。
- 页数一致，抽查页面标题、文本换行、图片和主题样式一致。
- HTML 预览与下载的 HTML 内容 checksum 一致。
- 切换内容版本后不会复用旧缩略图。
- 每页均可点击放大，不再只有“通过”结论。

## BUG-204：部分 HTML 正常，部分显示 Missing Authorization Header

### 用户看到的现象

同一聊天中：

- `/workspace/preview.html` 显示 `Missing Authorization Header`；
- `/workspace/agents/课件制作师/preview.html` 可以正常显示课件。

### 已确认根因

这是“虚构产物路径”和“鉴权回退”两个问题叠加：

1. 后端会扫描 Agent 文本中出现的所有 `/workspace/...` 字符串，并直接生成文件产物元素；它没有验证路径是否真实存在。
2. Agent 文本或协议中提到了 `/workspace/preview.html`，因此前端收到一个实际上不存在的“幽灵产物”。
3. 真实文件位于 Agent 私有目录：`/workspace/agents/课件制作师/preview.html`。
4. 前端会先通过带 JWT 的文件读取接口获取 HTML 并创建 Blob URL；真实文件因此可以预览。
5. 幽灵路径读取失败后，前端又回退到受保护的原始 URL。
6. `<iframe>` 无法自动附加 Axios 的 Authorization Header，最终显示 401 JSON。

所以问题不是“有些 HTML 语法能解析、有些不能”，而是：

- 正常项对应真实文件；
- 异常项对应未验证路径；
- 失败回退错误地访问了需要 Bearer JWT 的直链。

### 最小解决方案

后端：

1. 只有经过 Sandbox 文件事件、文件树或显式存在性检查确认的路径才能生成 Artifact Element。
2. 规范化 `/workspace` 路径并按 `session_generation + canonical_path` 去重。
3. Agent 文本中的路径仅作为候选，不能作为存在证据。
4. 对历史幽灵元素返回 `artifact_missing`，不要伪装成网页。

前端：

1. HTML 只能通过带鉴权的文件读取 API 获取，再转换成 Blob URL。
2. 禁止 iframe 回退到受保护的 raw URL。
3. 加载中显示 Skeleton。
4. 404 显示“文件不存在或路径未经验证”。
5. 401 显示“会话鉴权已失效，请重新登录”，不能把 JSON 放进网页预览框。
6. Sandbox 已回收时，引导打开正式 Education 产物；不要求找回旧容器。

### 数据边界

聊天消息、Agent 运行记录、正式 Education 对象和版本保存在数据库中；Sandbox 只是临时协作环境。聊天中的临时 HTML 可以随 Sandbox 回收失效，但被采纳的课件、报告和附件必须能从 Education 数据库或持久对象存储重新预览。

## UX-205：课程知识中心不在课时、成员、学情同一级

### 当前表现

课程页已有“课程知识中心”入口，但它位于页面头部操作按钮；课程主标签只有课时、作业、成员、学情。

### 目标结构

教师课程页主标签统一为：

1. 课时与教案
2. 作业
3. 课程成员
4. 学情
5. 知识中心

“知识中心”不再作为头部按钮。学生不显示教师私有知识中心；学生只接收已发布的课件、材料和作业。

### 最小解决方案

- 增加 `knowledge` 课程标签。
- 标签点击进入现有 Knowledge Center 页面或在当前课程壳中嵌入该页面。
- 保留当前课程、教师权限和返回路径。
- 删除重复的头部入口。
- 不重写现有题库、试卷库、知识库服务。

## FEATURE-206：上传文档、照片或 PDF 创建/发布作业

### 用户目标

教师除了手动填写作业，还应能：

1. 直接上传 PDF/DOCX/图片作为作业附件并发布；
2. 把扫描 PDF 或照片识别成可编辑作业；
3. 让 Agent 在识别结果基础上整理题目、要求和评分标准；
4. 教师确认后再发布给学生。

### 必须区分的两种模式

#### 模式 A：作为附件发布

- 支持 PDF、DOCX、JPG、PNG。
- 上传后保存为持久 `EducationAsset`。
- 教师填写标题、说明、截止时间即可发布。
- 学生可在作业页在线查看支持的格式或下载原文件。
- 不强制 OCR，不改变文件内容。

#### 模式 B：识别为可编辑作业

处理链路：

```text
持久上传
  → 文件安全检查
  → 文本直取或 OCR
  → AssignmentImportDraft
  → 作业 Agent 结构化
  → Schema 校验
  → 教师对照原件复核
  → 创建现有 Assignment
  → 教师明确发布
```

### OCR 与文档解析选型

推荐组合：

- **PyMuPDF**：优先提取数字 PDF 中已有文本，并负责 PDF 页面栅格化；
- **PaddleOCR**：中文、英文、版面和文档结构识别的主 OCR；
- **Tesseract**：PaddleOCR 服务不可用时的纯文字 fallback。

参考：

- [PaddleOCR 官方仓库](https://github.com/PaddlePaddle/PaddleOCR)
- [PyMuPDF OCR 与页面处理文档](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html)
- [Tesseract OCR 官方仓库](https://github.com/tesseract-ocr/tesseract)

### 独立模块边界

新增独立的 `DocumentExtractionJob`，不能在上传 HTTP 请求中同步跑 OCR：

- `uploaded`
- `extracting`
- `review_required`
- `ready`
- `failed`

新增 `AssignmentImportDraft`，至少保存：

- 原始 asset ID 和 checksum；
- 页码；
- 文本块；
- 位置框；
- OCR confidence；
- 题目候选；
- 未识别警告；
- Agent 结构化结果；
- 教师修订结果。

Agent 只接收经过安全处理的文本、版面引用和业务工具，不获得数据库、宿主机文件系统或用户 Token。发布继续复用现有 Assignment 接口。

### 安全要求

- 检查扩展名、MIME 和 magic bytes；
- 限制文件大小、页数、像素和压缩比；
- 隔离或拒绝含宏/主动内容的 Office 文件；
- OCR 低置信度区域必须标记；
- Agent/OCR 结果不能自动发布；
- 学生只访问已发布附件，不访问教师原始解析草稿。

### MVP 范围

本阶段支持：

- PDF、JPG、PNG；
- 数字 PDF 文本直取；
- 中英文印刷体 OCR；
- 基础题干/说明识别；
- 原件与可编辑草稿并排复核；
- 作为附件直接发布。

暂不纳入：

- 手写作文全文高精度识别；
- 复杂数学公式；
- 跨页表格重建；
- 自动批量拆分多份学生试卷；
- 无教师确认的自动发布。

## UX-207：帮助中心已有页面，但用户找不到

### 已确认现状

系统已经存在：

- `/education/help` 路由；
- `HelpCenter.vue`；
- 教师快速开始；
- 学生快速开始。

当前 Education 左侧导航没有帮助中心入口，所以它属于“已有功能不可达”，不是从零开发。

### 最小解决方案

1. 在教师和学生 Education 导航末尾固定显示“帮助中心”。
2. 不依赖课程是否存在。
3. 帮助内容补齐：
   - 教师：创建课程、邀请学生、课时/教案、PPT、发布作业、OCR 导入、查看提交、学生画像；
   - 学生：加入课程、下载课件、完成作业、查看反馈、模拟考试、思维导图；
   - Agent：运行进度、正式产物与聊天临时文件的区别、返回历史聊天；
   - 故障：文件类型与大小、Sandbox 已回收、HTML 预览失败。
4. 业务页可通过问号按钮跳转到对应锚点。

## FEATURE-208：教师查看学生提交页面不足以完成批改闭环

### 已确认现状

当前教师端作业页仅有：

- 左侧学生提交列表；
- 中间纯文本答案；
- 教师反馈文本框；
- 下一步建议；
- 直接发布反馈。

现有后端已经保存：

- 提交版本；
- `answer_json`；
- `artifact_ids`；
- 最终分数；
- Feedback。

但前端没有使用附件、版本比较和分数字段，也没有筛选、量规、批改草稿或发布前复核。

### 已确认的信息架构

采用“**作业总览 → 独立批改工作台**”两层结构。教师从课程作业列表点击一份作业时，不自动选中第一位学生，也不直接进入空白反馈表单。

建议路由：

- 作业总览：`/education/courses/:courseId/assignments/:assignmentId`
- 单份批改：`/education/courses/:courseId/assignments/:assignmentId/review/:submissionId`

#### 第一层：作业总览

默认标签为“提交与批改”，同级标签包括：

1. 提交与批改；
2. 作业内容；
3. 发布设置；
4. 作业分析。

页面顶部显示：

- 作业标题、状态、类型、满分、截止时间和订正规则；
- 预览学生视角；
- 编辑作业；
- 提醒未交；
- 批改下一份。

班级指标显示：

- 应交人数；
- 已交、未交、迟交；
- 待批改、已批改、要求订正；
- 最高分、最低分、平均分；
- 分数分布。

提交列表必须支持：

- 搜索学生姓名；
- 按提交状态、班级/小组筛选；
- 按待批优先、提交时间、姓名和分数排序；
- 显示真实课程姓名、提交时间、提交版本、状态和分数；
- 未提交学生显示“提醒”，不能进入不存在的 Submission；
- 已批改学生进入只读查看或新建反馈版本；
- 点击学生或“批改下一份”进入独立批改工作台。

作业内容和评分标准不再永久占据总览页左侧，也不能显示原始 JSON。它们在“作业内容”标签中使用业务渲染器展示。

#### 第二层：单份批改工作台

工作台顶部显示：

- 返回作业总览；
- 学生真实课程姓名；
- 提交状态、时间、字数和附件数；
- 当前提交版本；
- 上一位、下一位；
- 保存并进入下一份。

工作区使用三栏结构。

**左侧：作业与评分依据**

- 作业要求；
- 学科、学段和任务类型；
- 可读的量规维度及分值；
- 默认折叠的教师参考答案或典型范文；
- 本次提交包含的正文和附件摘要。

**中间：学生学习证据**

- 写作任务显示长文本正文和锚定批注；
- 阅读任务显示逐题作答卡；
- PDF、图片和文档使用对应的安全预览器；
- 支持提交版本切换与差异；
- 支持查看附件和批注列表；
- 真正为空时显示“无正文”“仅附件”或“文件加载失败”，禁止渲染 `{}`、原始 JSON 或 UUID。

**右侧：评分与反馈**

- 量规维度评分；
- 自动汇总总分；
- AI 建议；
- 做得好的地方；
- 关键问题；
- 下一步建议；
- 教师反馈编辑器；
- 要求订正；
- 保存批改草稿；
- 发布成绩与反馈。

### AI 建议触发与缓存决策

采用“**打开时懒触发、后台运行、按版本缓存**”：

1. 教师首次打开某份提交时，如果没有有效分析，自动在后台触发 AI 批改建议；
2. 教师可以立即阅读和评分，不能被 AI 运行阻塞；
3. 缓存键至少包含：
   - `submission_version_id`
   - `assignment_evaluation_version/checksum`
   - `agent_prompt_version`
4. 提交版本或评分量规变化后，旧建议标记为过期并提供“重新分析”；
5. 第一版不自动批量分析全班，避免无效成本和过期结果；
6. AI 建议必须带证据引用和采纳按钮；
7. AI 不能直接修改量规得分、教师反馈、正式成绩或发布状态；
8. 每次 AI 分析形成可追溯的 Product Agent Run，并可从页面打开对应聊天记录。

### 状态模型

建议使用：

```text
submitted
  → reviewing
  → graded
  → revision_requested
  → revised
  → reviewing
```

反馈需要“草稿”和“已发布”两种状态。已发布反馈生成不可变版本；再次修改形成新版本，保留审计记录。

### 数据模型最小补充

- `ReviewDraft`，或为 Feedback 增加 `status=draft/released`；
- `rubric_scores`；
- `annotations`；
- `reviewed_by`、`reviewed_at`；
- Feedback 版本号；
- `revision_request`。
- `SubmissionReviewAnalysis`，保存提交版本、量规 checksum、Prompt 版本、Agent Run、结构化建议和失效状态。

### MVP 范围

本阶段完成：

- 概览计数；
- 搜索、筛选、排序；
- 文本和附件查看；
- 总分与量规评分；
- 保存批改草稿；
- 发布反馈；
- AI 建议采纳；
- 下一份未批改。
- AI 打开时懒触发、运行状态和版本缓存；
- 从 AI 建议返回对应聊天记录。

暂不纳入：

- 多教师实时协同批改；
- 手写图片自由画笔批注；
- 全班一键自动评分；
- 面向家长的报告；
- 复杂成绩册规则。

## 4. 实施拆分

### Phase 2A：稳定性与导航

范围：

- BUG-201 首次导航；
- BUG-202 固定工作流审核节点；
- BUG-203 实际导出渲染契约与基础 Render Adapter；
- BUG-204 幽灵路径与 iframe 鉴权回退；
- UX-205 知识中心同级标签；
- UX-207 帮助中心入口。

最小修改模块：

- `frontend/src/components/Sidebar/index.vue`
- `frontend/src/components/MessageBubble/index.vue`
- `frontend/src/views/education/CourseSpace.vue`
- `frontend/src/views/education/CoursewareLibrary.vue`
- `frontend/src/views/education/HelpCenter.vue`
- `backend/services/edu/workflow_routes.py`
- `backend/services/edu/content_routes.py`
- `backend/app/services/message_element_builder.py`
- 新增隔离的 Education Render Adapter

### Phase 2B：作业文件导入

范围：

- 附件型作业；
- OCR 异步任务；
- 可编辑导入草稿；
- 教师复核后发布。

原则：

- 复用现有 `EducationAsset`、Assignment 和权限；
- OCR 服务独立；
- Agent 通过 Education 工具调用，不直接操作数据库；
- 不改变学生提交协议。

### Phase 2C：提交复核工作台

范围：

- 班级概览；
- 提交队列；
- 证据查看器；
- 批改草稿；
- 量规评分；
- 反馈发布与订正状态。

原则：

- 复用现有 SubmissionVersion 和 artifact IDs；
- 所有 AI 评分仅为建议；
- 正式成绩必须由教师确认。

## 5. 数据持久化与 Docker 边界

### 5.1 必须持久化的数据

以下内容不能依赖 Docker Sandbox：

- 课程、课时、成员；
- 教案、课件、作业及版本；
- 上传附件；
- 学生提交及版本；
- 反馈和成绩；
- AI 产品运行记录；
- 被采纳产物的 object ID、version ID；
- 渲染清单和正式缩略图；
- OCR 原始附件、解析草稿和教师修订结果；
- Conversation 元数据和消息。

### 5.2 Sandbox 只负责

- Agent 私有工作目录；
- Agent 间临时协作文件；
- 临时预览；
- 工具调用过程；
- 可回收的执行环境。

Docker 容器停止或被回收后：

- 历史聊天文字仍应存在；
- 正式 Education 产物仍应可预览与下载；
- 临时文件可以显示“执行环境已回收”；
- 不要求恢复旧容器才能查看正式业务结果。

### 5.3 推荐的进一步改进

当前二进制资产仍可由数据库持久化，但为了后续 OCR 原件、PPTX、PDF、逐页图片和大量学生附件，建议抽象 `AssetStorage`：

- MVP：MySQL `LONGBLOB`；
- 可扩展：MinIO / S3；
- 数据库只保存 asset 元数据、权限、checksum 和 storage key。

这不是 Phase 2A 的强制迁移项，但 Phase 2B 开始前应先完成存储接口抽象，避免 OCR 功能继续扩大数据库耦合。

## 6. 统一验收场景

### UAT-01：首次教师进入

1. 新建用户；
2. 选择 Education 教师身份；
3. 不创建课程；
4. 左侧仍显示教学空间、PPT 与课件、学生画像与评估、帮助中心；
5. 进入后显示选择/创建课程空状态。

### UAT-02：阅读课 Agent 协作

1. 创建高中英语阅读写作课时；
2. 用户只输入自然要求；
3. 课程设计师、习题生成器、教学审校员依次运行；
4. 不创建审核 Agent；
5. 教案和题目保存为草稿；
6. 教师点击发布时只确认一次。

### UAT-03：真实课件视觉检查

1. 生成或上传一份 6—8 页课件；
2. 下载 PPTX；
3. 点击“PPTX 实际渲染”；
4. 逐页检查标题、换行、图片和主题；
5. 页数和下载文件一致；
6. 点击 HTML 页签时显示同版本实际导出 HTML。

### UAT-04：聊天 HTML

1. Agent 文本同时提到真实路径和不存在路径；
2. 真实 HTML 通过 Blob 正常渲染；
3. 不存在路径显示明确错误；
4. 页面中不出现 `Missing Authorization Header` JSON；
5. Sandbox 回收后仍能从“正式产物”打开持久课件。

### UAT-05：课程信息架构

1. 教师进入课程；
2. “知识中心”与课时、作业、成员、学情同级；
3. 头部不再有重复按钮；
4. 学生不显示教师知识中心。

### UAT-06：附件与 OCR 作业

1. 教师上传 PDF 直接作为附件作业；
2. 学生可下载并提交；
3. 教师上传扫描图片并选择“识别为可编辑作业”；
4. 页面显示 OCR 进度；
5. 低置信度区域被标出；
6. 教师修改草稿后发布；
7. 未确认前学生不可见。

### UAT-07：帮助中心

1. 无课程时也可从左侧进入；
2. 教师和学生看到各自流程；
3. 业务页面帮助按钮能跳到对应章节。

### UAT-08：查看学生提交

1. 至少三名学生形成未交、已交未批、已批状态；
2. 点击作业先进入全班总览，不自动选择第一份提交；
3. 总览显示真实课程姓名、提交状态、版本、时间和得分，不出现用户 UUID 或原始 JSON；
4. 教师可搜索、筛选、排序，并通过“批改下一份”进入独立工作台；
5. 工作台可查看写作长文、阅读逐题作答、附件和提交版本；
6. 量规分项得分可自动汇总并保存为批改草稿；
7. 首次打开提交会后台触发 AI 建议，教师编辑不被阻塞；
8. 相同提交版本和量规版本复用缓存，版本变化后提示重新分析；
9. AI 建议包含证据定位，且不会未经教师采纳写入正式反馈或成绩；
10. 发布后学生看到分数和反馈，要求订正后可形成新提交版本。

## 7. 非目标

本轮不做：

- 重写核心聊天系统；
- 把所有 Education 数据迁入 Sandbox；
- 每个 Agent 节点都增加人工审核；
- 让 Agent 自动发布作业、课件或成绩；
- 自研 OCR 引擎；
- 自研 Office 渲染引擎；
- 为了兼容错误 Agent 输出继续无限扩展前端解析器；
- 恢复已经回收的 Docker 容器作为正式数据访问前提。

## 8. 完成定义

Phase 2 只有同时满足以下条件才可声明完成：

1. BUG-201—204 有自动化回归测试和真实浏览器 UAT。
2. 阅读课固定工作流不再因审核节点失败。
3. 学生画像独立运行仍能成功，不能被工作流修复回归。
4. PPTX 视觉检查展示实际导出渲染，而非前端模拟。
5. HTML 预览不再出现未鉴权 raw URL。
6. 知识中心和帮助中心的信息架构符合本规格。
7. 附件作业、OCR 草稿、教师确认发布形成最小闭环。
8. 教师可完成“查看提交—评分—保存草稿—发布反馈”。
9. Docker Sandbox 回收后，正式业务产物仍可访问。
10. Education、核心后端和前端测试均通过，工作区无意外改动。
