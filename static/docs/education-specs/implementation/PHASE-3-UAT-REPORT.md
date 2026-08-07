# Education Bugfix Phase 3 实施与 UAT 报告

## 1. 结论

Phase 3A、3B、3C 已按 `2026-08-01-education-content-management-bugfix-phase-3-spec.md` 实现。课程内容资产、作业版本、题库与试卷、联网知识资料、可视化思维导图和产品内 Agent 记录都回到 Education 正式业务对象中；Docker 沙箱和聊天附件不再承担权威数据职责。

验收日期：2026-08-01。分支：`feature/education`。

## 2. 实现范围

### 2.1 统一课程资产

- `EducationAsset` 继续作为唯一二进制资产来源，按 `courseware`、`lesson_material`、`assignment_source`、`knowledge_resource` 等 purpose 隔离。
- PPT 文件柜与教学空间课时材料读取同一 canonical query；支持按当前课时或全课程筛选。
- 教师可在两个入口统一切换“教师可见 / 学生可见”，并执行软删除。
- 已被作业、知识资源或正式内容引用的资产返回 `409 asset_in_use`，不会破坏依赖对象。
- 学生端只读取 `course_published`，不能修改权限或删除教师资产。

### 2.2 作业内容与批改闭环

- 作业正文、附件、评分标准和发布设置进入可编辑工作区。
- 每次保存生成不可变内容版本；发布固定指向快照，教师继续编辑不会原地覆盖学生正在使用的版本。
- 支持 Ctrl/Cmd+S、未保存发布提醒、历史版本和重新发布。
- 教师详情先显示全班提交总览，再进入单份批改；未提交、待批、已批、订正和平均分分区清晰。
- 教师与学生的超长任务正文均限制为 420px 独立滚动区域，不再把整页撑长。

### 2.3 课程知识中心

- 题库：稳定题目身份、不可变版本、教师答案隔离、规范 A/B/C/D 选项渲染。
- 试卷库：只冻结当前课程已发布题目版本，保留顺序、分值、时长与用途。
- 知识库：教师上传与联网采纳均持久化为课程资产和知识资源，RAG 索引状态与文件下载解耦。
- 联网管线固定为 `SearchProvider -> ContentFetcher -> Retriever -> Reranker -> 教师采纳`；搜索摘要不会冒充网页正文。
- Wikipedia 与 DuckDuckGo provider fallback、正文重抓、安全 URL 校验、来源与许可说明均有自动化覆盖。

### 2.4 思维导图 v2

- 支持 course、lesson、custom 三种范围及多课时关系。
- 支持节点拖动、父子重挂、关系线、缩放/平移/居中、撤销/重做、版本保存与历史恢复。
- v1 数据可包装升级为 v2；课程来源权限仍由服务端校验。

### 2.5 Agent 与业务终结器

- 用户在产品中只提交业务请求，例如“根据当前教案生成 PPT”，系统协议不会显示成用户输入。
- 课件继续使用受控 `slide_document.json + preview.html` 终结器，校验后调用 `edu.courseware.create`。
- 习题、试卷、知识资料使用严格 JSON 回复终结器：
  - 习题校验后调用 `edu.question_bank.upsert`；
  - 试卷先调用 `edu.question_bank.search`，过滤已发布题目，再调用 `edu.paper.compose`；
  - 知识资料先调用 `edu.web.research`，再对重抓候选调用 `edu.knowledge.resource.adopt`。
- 最终工具结果会以有界 `trusted_finalizer_result` 传给后续审校 Agent；沙箱路径、聊天文本和伪 JavaScript 均不算业务产物。
- DeepSeek 运行时不再注册不可用的 MCP 工具；余额不足和限流不会触发错误的“刷新 API Key”提示。

## 3. 自动化验证

### 3.1 后端

- 命令：Education 测试集 + 服务端固定工作流 + Codex 沙箱回归。
- 结果：`182 passed`。
- 覆盖：资产权限/删除/依赖、作业版本、RAG 管线、题库/试卷、导图 v2、Agent 终结器、DeepSeek 工具预检和错误分类。
- Python `compileall`：通过。

### 3.2 前端

- Node contract tests：`22 passed`。
- Vue 生产构建：通过；仅保留仓库原有 bundle size warning，无编译错误。
- 覆盖：统一导航、课程上下文、课件文件柜、作业版本编辑器、知识 Agent、导图 v2、结构化课件渲染与 Vue 编译。

## 4. 真实 HTTP 双用户 UAT

使用隔离教师/学生账号和新数据执行 `backend/scripts/education_phase3_uat.py`，结果 `status=passed`。

- 课程：高中英语与小学语文各 1 门，每门 3 个课时。
- 资产：每门 2 个课件、课时材料、作业来源、知识资料；权限切换、撤回、软删除和依赖冲突均通过。
- 作业：英文超长正文 5040 字符，发布快照 v2；中文作业发布快照 v3。
- 知识中心：最终验收数据共 12 道题、4 份冻结试卷。
- 导图：lesson、course、custom 范围均创建成功；custom v2、2 条跨节点关系，多课时关联通过。

主要验收课程：

- 高中英语：`4bc29f89-cd3d-43b8-88dc-89ad86f95eb3`
- 小学语文：`3f9db181-4b59-4fd2-8692-49f788534d18`

## 5. 内置浏览器 UAT

教师与学生账号顺序登录真实前端 `http://127.0.0.1:8080`，验证结果如下：

| 场景 | 结果 |
|---|---|
| 教师左侧领域导航 | 教学空间、PPT 与课件、学生画像与评估、帮助中心层级正确，无图标重影 |
| 教学空间顶部 | AI 生成记录位于页头与课时模块之间；知识中心与课时/作业/成员/学情同级 |
| 课件文件柜 | 当前课时与全课程筛选正常；全课程显示 6 个既有资产，控制台无错误 |
| HTML 上传 | 通过浏览器选择并上传本地 HTML，立即持久化为教师可见资产 |
| 权限菜单 | 下载、教师可见、学生可见、删除四项均可见；学生端没有管理菜单 |
| 结构化课件 | 最新 `dark_focus` 课件逐页显示真实编译画面，而非只有“通过”文本 |
| 多格式导出 | HTML、PPTX、PDF、DOCX、JSON 入口均来自同一结构化版本 |
| 题库 | 8 道英文验收题正常显示，选项为 `A 文本`，不存在 `1. A. A.` 重复 |
| 试卷库 | 2 份诊断卷，每份 4 题、20 分、30 分钟，题目版本已冻结 |
| 知识库 | 2 份课程知识资料可下载，上传与联网补充入口正常 |
| 学生作业 | 长正文容器实测 `clientHeight=420`、`scrollHeight=2493`、`overflow-y=auto` |
| 教师作业 | 提交总览、未交名单、内容编辑、附件、评分标准和发布设置分区正常 |
| 学生思维导图 | 多课时导图可见，节点拖动、撤销/重做、保存版本与历史恢复已验证 |
| 聊天关联 | 业务记录可返回会话，会话侧栏刷新后仍存在；会话可返回业务页面 |
| 用户提示词 | 显示简短业务请求，不展示 system prompt、Sandbox ID 或内部协议 |
| 控制台 | 上述验收页面无新增 JavaScript error |

## 6. 真实 Agent 证据与外部环境记录

成功课件运行：

- run：`ccdeb701-5d05-47fc-aa28-2382e6cf38dc`
- conversation：`8c0effd1-e2bc-4035-9445-3038a2a266ea`
- 正式课件对象：`711a21f1-10f1-46c3-9796-99d38384976e`
- 正式版本：`84147e01-0b73-4539-9eba-df1febb832ca`
- 审计工具：指定课件 Agent 成功调用 `edu.courseware.create`
- 浏览器逐页视觉结果：`dark_focus`、9 页、74 个可编辑文字框、全部页面通过；HTML/PPTX/PDF 导出已验证。

最终复验 run `0980d96e-139d-4774-b820-4e49bb91d6ab` 在课程设计师第一次模型请求时收到 DeepSeek `Insufficient Balance`。沙箱健康、Agent 创建、能力投影和运行时预检均正常，因此判定为外部账户余额事件，不是 Education 业务回归。系统已改为原样呈现该原因，不再附加“缺少 API Key”的误导文本；普通课程功能和此前已落库产物不受影响。

## 7. 安全与数据边界

- `.env` 仅用于本地 UAT，保持 Git ignore；报告、测试和提交不记录 Token 或验收密码。
- Agent 不接收可伪造的 `course_id`、`user_id`、角色或授权 Token；服务端从运行授权注入作用域。
- 学生不能读取教师答案、教师草稿、其他学生提交或管理资产权限。
- 网络抓取限制为 HTTP(S) 公网目标，并执行地址、重定向、大小、MIME、正文与许可检查。
- 所有可验收结果落入 Education 数据库；Docker 对话容器关闭不会删除课程业务数据。
