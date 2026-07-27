# Education 开源生态调研

> 调研时间：2026-07-27
> 范围：为 WeAgent `feature/education` 设计中等开发量的教师端/学生端能力。
> 证据规则：只引用项目官方 GitHub、官方文档、官方许可证/API 文档；活跃度是调研时快照，不是长期保证。

## 1. 先给结论

中等开发量下，不建议 fork 或内嵌一个完整 LMS。WeAgent 已经有 Agent、工作区、知识库/RAG、产物预览与 HTML 编辑器，应继续把自己定位成“AI 教学工作台”，只实现轻量课程域模型和教师/学生工作流，再通过小型库或旁路服务补齐编辑、协作、搜索和导出能力。

推荐组合：

1. **课程与课堂骨架自行实现**：课程、班级、成员、课时、学习材料、作业、提交、批注、评分、学习进度。Moodle / Open edX 主要作为领域模型和以后互操作的参考，不把其源码并入 WeAgent。
2. **内容编辑首选 Tiptap OSS**：`@tiptap/vue-2` 与当前 Vue 2.7 直接匹配；课程讲义、作业说明、反馈、题干统一保存为 Tiptap JSON，同时生成安全 HTML 预览。
3. **实时协作第二阶段再上 Yjs + Hocuspocus**：先做单人编辑、版本快照和教师发布；确有多人同时备课需求后，再增加 CRDT 文档服务，避免第一阶段被协作一致性拖慢。
4. **演示文稿走两条明确管线**：
   - reveal.js：轻量 HTML/Markdown 在线课件；Slidev：代码、公式、组件驱动的高级交互课件；
   - PptxGenJS：从结构化课件数据生成真正可继续编辑的 `.pptx`。
5. **联网检索首选自托管 SearXNG sidecar**：Flask 后端调用 JSON Search API，统一做安全搜索、域名白名单、缓存、去重和引用记录；不要依赖随机公共实例。
6. **RAG 不做框架级替换**：现有 WeAgent 已有 Chroma/RAG，LlamaIndex 只按需采用 reader、parser、retriever 等窄模块；避免同时维护两套索引抽象。
7. **互动题型分层**：MVP 自己做少量结构化题型与评分；H5P 作为后续“丰富互动内容包”能力。H5P 并非一个直接 `npm install` 就完成的编辑器，平台集成和内容类型生命周期都需要额外工程。
8. **白板为可选项**：Excalidraw 很成熟，但官方嵌入包是 React，而 WeAgent 当前是 Vue 2；中等范围内应先 iframe/独立微前端试点，不应为白板把主前端迁移到 React。

## 2. 与当前 WeAgent 的技术匹配

本地 `frontend/package.json` 显示主前端为 Vue 2.7、Element UI 2、Vuex 3、Vue Router 3，并已有 CodeMirror；`backend/requirements.txt` 显示后端为 Flask、SQLAlchemy、JWT、Socket.IO、Redis。仓库已经包含 `HtmlPageEditor` 与 `ArtifactWorkbench`，因此教育模块应复用现有产物模型和预览/编辑通道，而不是新建一套独立文件系统。

这带来几个具体约束：

- 优先采用 Vue 2 或框架无关的 JS 库；
- React-only UI 应通过 iframe/微前端隔离；
- 可执行 HTML、Slidev 页面、H5P 内容必须沙箱化，区分“作者预览”和“学生发布”；
- 教育实体只保存业务关系和版本引用，实际产物继续由现有 workspace/artifact 能力管理；
- 联网检索必须经后端代理，不能让浏览器直接接触搜索服务或密钥。

## 3. 项目与库对比

### 3.1 Moodle — 完整 LMS / 课堂领域参考

- **能力**：成熟的课程、成员、活动、作业、评分、文件、插件与移动端生态。官方称其为开源学习平台；外部系统可使用完整的 Web Service / External API 框架，文件还有专用上传下载端点。
- **技术栈与集成**：主体为 PHP，辅以 JavaScript、Mustache 等。对 WeAgent 最合理的集成是把 Moodle 当作外部 LMS，通过 Web Service、文件端点或后续 LTI 对接；不适合把 PHP 模块拷进 Flask 应用。
- **许可证**：GPL-3.0。
- **活跃度线索**：官方镜像有约 12 万次提交；Moodle 5.x External Services 文档在 2026 年 4–5 月仍在更新。
- **适合复用**：课程/活动/作业/评分的领域术语；外部 LMS 同步接口；未来将 WeAgent 教学 Agent 作为 Moodle 外部工具。
- **不适合**：直接 fork 成 WeAgent 的教育前后端，体量、技术栈和 GPL 边界都不符合中等开发量。
- **第一方资料**：[官方仓库与 GPL-3.0](https://github.com/moodle/moodle)、[External Services API](https://moodledev.io/docs/5.0/apis/subsystems/external)、[文件上传下载端点](https://moodledev.io/docs/5.0/apis/subsystems/external/files)。

### 3.2 Open edX — 大规模课程平台 / LTI 互操作参考

- **能力**：Open edX 的 CMS/Studio 负责课程创作，LMS 负责学习内容交付；LTI Consumer 支持 LTI 1.3，以及 Deep Linking、Assignment and Grade Services（成绩回传）、Names and Role Provisioning。
- **技术栈与集成**：Python/Django + JavaScript，架构是大型模块化单体、独立服务和 React 微前端。可把 WeAgent 设计成 LTI 1.3 Tool，未来被 Open edX 等 LMS 启动；也可参考其 Studio/LMS 的教师端与学生端分离。
- **许可证**：核心 `openedx-platform` 为 AGPL-3.0（仓库注明个别部分可能另有说明）。
- **活跃度线索**：官方核心仓库约 6.8 万次提交，最新官方文档持续更新；官方自己明确说明生产安装并不简单，推荐使用 Tutor 或服务商。
- **适合复用**：LTI 1.3 互操作设计、课程创作/学习交付分层、成绩回传协议。
- **不适合**：把整个 Open edX 部署作为 WeAgent 教育 MVP；基础设施和运维量远超中等范围。
- **第一方资料**：[官方仓库、架构与 AGPL-3.0](https://github.com/openedx/openedx-platform)、[LTI 1.3 配置与成绩回传](https://docs.openedx.org/en/latest/educators/how-tos/course_development/exercise_tools/set_up_lti_1_3_component.html)、[LTI 能力说明](https://docs.openedx.org/en/latest/educators/concepts/exercise_tools/about_lti_component.html)。

### 3.3 Tiptap — 讲义、题干、反馈的结构化富文本编辑器

- **能力**：基于 ProseMirror 的 headless 富文本框架，扩展机制可覆盖标题、列表、链接、表格、图片、代码块、自定义教育节点；可输出 JSON 或 HTML。
- **技术栈与集成**：TypeScript。官方仍提供 `@tiptap/vue-2`，与 WeAgent Vue 2.7 直接匹配，基础安装为 `@tiptap/vue-2`、`@tiptap/pm`、`@tiptap/starter-kit`。
- **许可证**：编辑器核心 MIT；官方明确标注部分高级 Pro Extensions（如某些评论、版本、AI 能力）需要订阅，不能把“核心 MIT”误解成所有功能都免费。
- **活跃度线索**：官方 GitHub 在 2026-05 发布 v3.23.6，累计近千个 release。
- **适合复用**：课程讲义、作业说明、答案解析、教师反馈、题目内容；用自定义节点嵌入公式、代码、附件、检索引用、H5P/白板占位。
- **不适合**：直接把不受约束的任意 HTML 当作 Tiptap 文档往返编辑；Tiptap 有严格 schema，未知节点可能丢失。也不要在未核许可证的情况下依赖 Pro 扩展。
- **第一方资料**：[官方仓库、功能与许可边界](https://github.com/ueberdosis/tiptap)、[Vue 2 官方接入](https://tiptap.dev/docs/editor/getting-started/install/vue2)、[编辑器设计说明](https://tiptap.dev/docs/editor/getting-started/overview)。

### 3.4 Yjs + Hocuspocus — 多人备课与共享笔记的实时协作底座

- **能力**：Yjs 提供共享 Map/Array/Text 等 CRDT 数据类型，可离线编辑、冲突合并、共享光标、快照和 undo/redo；Hocuspocus 是官方 Tiptap 生态中的开源 Yjs WebSocket 后端。
- **技术栈与集成**：Yjs/客户端为 JavaScript；Hocuspocus 为 TypeScript/Node WebSocket 服务。推荐独立 sidecar 部署，通过文档 ID 与 WeAgent JWT/权限映射，不要尝试用现有 Socket.IO 消息自行重写 CRDT 协议。
- **许可证**：Yjs 及相关项目 MIT；Hocuspocus 官方仓库亦为 MIT。
- **活跃度线索**：Yjs 在 2026-07 仍连续发布 v14 RC，稳定线 v13.6.31 同时存在；Tiptap 官方在 2026 年维护 Hocuspocus 4。
- **适合复用**：教师共同备课、学生小组文档、共享课堂笔记、在线 presence；可以与 Tiptap 绑定。
- **不适合**：第一阶段就对所有教育对象启用实时协作；需要额外处理权限、持久化、schema 版本、断线重连和历史快照。应固定稳定版，不直接上 Yjs RC。
- **第一方资料**：[Yjs 官方仓库、能力与 MIT](https://github.com/yjs/yjs)、[Yjs 官方 releases](https://github.com/yjs/yjs/releases)、[Hocuspocus 概览](https://tiptap.dev/hocuspocus/)、[开源 provider 接入](https://tiptap.dev/docs/hocuspocus/provider/install)。

### 3.5 Slidev — HTML/Markdown 交互课件与代码演示

- **能力**：Markdown 驱动的演示文稿，基于 Vue 3/Vite，可嵌入 Vue 组件，内置代码高亮/运行、Monaco、公式、Mermaid、演讲者模式、标注和录制；能构建成静态 Web 应用。
- **技术栈与集成**：Vue 3 + Vite + UnoCSS。最适合把它作为受控生成/构建器：Education Agent 产出 `slides.md` 与资源，经 sandbox/worker 构建为 HTML，ArtifactWorkbench iframe 预览。无需把 Slidev UI 嵌进 Vue 2 主应用。
- **许可证**：MIT。
- **活跃度线索**：官方 GitHub 显示 2026-05 发布 v52.15.2，release 数量超过 400。
- **适合复用**：交互课件、编程教学、公式和图表、HTML 分享页；其内置 MCP Server 也说明课件天然适合 Agent 检查、编辑、重排。
- **不适合**：作为“可编辑 PowerPoint”唯一方案。官方说明 Slidev 的 PPTX 导出是逐页图片，文字不可选择，交互也会在离线导出时丢失。
- **第一方资料**：[官方仓库、技术栈与 MIT](https://github.com/slidevjs/slidev)、[导出格式及 PPTX 限制](https://sli.dev/guide/exporting.html)、[功能列表](https://sli.dev/features/)。

### 3.6 reveal.js — 低摩擦 HTML/Markdown 演示框架

- **能力**：HTML/Markdown 演示、水平/垂直嵌套页、Auto-Animate、代码高亮、LaTeX、讲者备注、插件和 PDF 导出。
- **技术栈与集成**：JavaScript/TypeScript/HTML，可从 npm 引入，也可零构建使用已编译资源。最适合从 WeAgent 的 `slide document JSON` 生成 `section` 标记或 Markdown，再直接交给现有 HTML artifact/iframe 预览。
- **许可证**：MIT。
- **活跃度线索**：官方仓库显示 2026-04 发布 v6.0.1，累计 50+ releases。
- **适合复用**：通用课程讲授、低构建成本的 HTML 课件、讲者视图和 PDF；相比 Slidev 更接近“纯渲染框架”，更容易纳入现有 HTML 产物链。
- **不适合**：完整的 PowerPoint 式可视化编辑。官方同作者的图形编辑产品 Slides.com 是独立服务；开源 reveal.js 的可编辑源仍是 HTML/Markdown。
- **与 Slidev 的取舍**：通用课程首选 reveal.js；需要 Vue 组件、Monaco、代码运行、录制或 Agent/MCP 操作时选 Slidev。两者都不应成为 PPTX 的唯一源。
- **第一方资料**：[官方仓库、功能、MIT 与 v6.0.1](https://github.com/hakimel/reveal.js/)、[安装方式](https://revealjs.com/installation/)、[Markdown](https://revealjs.com/markdown/)、[讲者视图](https://revealjs.com/speaker-view/)、[PDF 导出](https://revealjs.com/pdf-export/)。

### 3.7 PptxGenJS — 真正可编辑的 PowerPoint 导出

- **能力**：用 JavaScript/TypeScript 生成 OOXML `.pptx`，支持文本、图片、表格、图表、形状、母版、讲者备注；兼容 PowerPoint、Keynote、LibreOffice 和 Google Slides 导入。
- **技术栈与集成**：JavaScript，支持 Node、浏览器、Vite、Electron；可在 Flask 旁增加一个小型 Node 导出 worker，或在前端/桌面端直接生成。最佳做法是从 WeAgent 自己的 `slide document JSON` 生成，而不是从任意 HTML 逆向还原。
- **许可证**：MIT。
- **活跃度线索**：官方 release 页面显示 v4.0.1 发布于 2025-06；属于成熟库，但更新节奏不如 Slidev，需锁版本并做 PowerPoint/LibreOffice 回归样例。
- **适合复用**：教师下载后仍可编辑的 PPTX；AI 生成课件后再人工微调；课程模板/母版。
- **不适合**：直接承担浏览器中的可视化自由排版编辑器；它是生成库而非完整 PowerPoint UI。`tableToSlides()` 也只处理 HTML 表格，不是通用 HTML-to-PPT 转换器。
- **第一方资料**：[官方仓库、能力、MIT 与 releases](https://github.com/gitbrent/PptxGenJS)、[官方介绍和安装](https://gitbrent.github.io/PptxGenJS/docs/introduction/)、[各运行环境接入](https://gitbrent.github.io/PptxGenJS/docs/integration/)。

### 3.8 Excalidraw — 教学白板、草图与可编辑图

- **能力**：手绘风格白板，可创建文本、形状、箭头、图片、frame，支持导入导出场景和图像；官方开发文档提供应用嵌入接口。
- **技术栈与集成**：React/TypeScript，npm 包为 `@excalidraw/excalidraw`。由于 WeAgent 是 Vue 2，推荐先用同源 iframe 或单独 React 微前端，并把 `.excalidraw` 场景 JSON、SVG/PNG 作为 artifact 保存。
- **许可证**：MIT。
- **活跃度线索**：官方 v0.18.1 于 2026-04 发布安全修复，专门处理上游 Mermaid XSS；这也说明教育发布内容必须锁版本并保留依赖扫描。
- **适合复用**：教师画板、学生解题草稿、流程图、概念图；保存源场景后仍可编辑。
- **不适合**：在中等范围内实现与主应用深度融合的实时协作。官方 React 组件并不等于开箱即用的自托管多人房间，协作、鉴权和存储需要额外系统。
- **第一方资料**：[官方开发文档](https://docs.excalidraw.com/)、[官方仓库](https://github.com/excalidraw/excalidraw)、[MIT 许可证](https://github.com/excalidraw/excalidraw/blob/master/LICENSE)、[官方 releases](https://github.com/excalidraw/excalidraw/releases)。

### 3.9 SearXNG — 联网搜索聚合服务

- **能力**：隐私导向的元搜索引擎，聚合多个搜索服务/数据库；提供 `/`、`/search` 的 GET/POST API，可返回 JSON、CSV、RSS，并支持语言、时间范围、安全搜索、类别和指定引擎。
- **技术栈与集成**：Python Web 服务，建议 Docker/sidecar 自托管。Flask 后端调用 `GET /search?q=...&format=json`，再统一做结果清洗、页面抓取、引用快照和 RAG 入库。
- **许可证**：AGPL-3.0。
- **活跃度线索**：官方文档版本为 2026.7.x，仓库与文档在 2026-07 仍持续更新；官方配置文档列出数百个引擎。
- **适合复用**：教师备课检索、学生研究助手、Agent 的 web-search tool；可配置教育/学术/新闻域、语言和 SafeSearch。
- **不适合**：依赖公共实例作为生产 SLA。官方文档提示公共实例可能关闭 JSON 格式；不同上游引擎也有速率、地区、API key 和使用条款差异。AGPL sidecar 的修改与网络提供义务应由项目负责人复核。
- **第一方资料**：[官方仓库与 AGPL-3.0](https://github.com/searxng/searxng)、[Search API](https://docs.searxng.org/dev/search_api.html)、[引擎配置](https://docs.searxng.org/admin/settings/settings_engines.html)、[已配置引擎概览](https://docs.searxng.org/user/configured_engines.html)。

### 3.10 LlamaIndex OSS — 文档接入、解析与检索编排

- **能力**：面向 LLM/Agent 应用的数据框架，含数据 connectors/readers、文档切分、索引、retriever、query engine、reranker 和工作流；官方仓库说明有 300+ 可按需安装的 integration packages。
- **技术栈与集成**：Python，适配 Flask 后端。应只安装 `llama-index-core` 与明确需要的 reader/vector-store 包，例如沿用现有 Chroma，而非安装大而全的 starter 并替换全部 RAG。
- **许可证**：OSS 仓库 MIT；官方同时提供 LlamaParse 等商业平台，必须把 OSS 包和付费云服务区分开。
- **活跃度线索**：官方 releases 在 2026-03 发布 core v0.14.16，官方组织仓库在 2026-05 仍更新。
- **适合复用**：PDF/Office/网页教材的 reader、结构化切分、引用节点、retriever/reranker；教师知识库到“课件/测验生成”的检索链。
- **不适合**：与 WeAgent 现有 RAG 并列再建一套数据模型、会话 Agent 和向量库管理。框架依赖变化快，应包装在 adapter 后并固定小版本。
- **第一方资料**：[官方仓库、架构、安装方式与 MIT](https://github.com/run-llama/llama_index)、[官方 releases](https://github.com/run-llama/llama_index/releases)。

### 3.11 H5P — 互动课件、题型和内容包

- **能力**：浏览器中创建/编辑/播放可移植的 HTML5 互动内容，内容类型包括互动视频、Course Presentation、题组、拖拽、填空、分支场景等；`.h5p` 是有固定目录、元数据、依赖和 semantics 的 ZIP 内容包。
- **技术栈与集成**：HTML5/CSS/JavaScript，内容结构和元数据为 JSON。典型完整集成依赖 Moodle/WordPress/Drupal 等宿主的 H5P 平台层；WeAgent 可先支持受控 iframe/embed 和 `.h5p` 导入导出，编辑器/Hub/成绩事件放在后续 adapter。
- **许可证**：H5P 官方称尽可能使用 MIT，但 PHP Library 因第三方净化代码包含 GPL 部分；每个内容类型及内容本身也可声明自己的许可证，不能以“H5P 总体开源”替代逐包审计。
- **活跃度线索**：H5P 官方组织有 150+ 仓库，互动视频、Course Presentation、题型和编辑组件在 2026-07 仍有更新。
- **适合复用**：丰富题型、互动视频、分支学习、可移植内容包；比 WeAgent 自研几十种交互组件更现实。
- **不适合**：当作一个纯前端组件直接塞入 Vue 2。完整 authoring、内容类型安装升级、依赖解析、安全净化、xAPI/成绩收集都需要平台层。
- **第一方资料**：[H5P 官方能力说明](https://h5p.org/)、[开发者集成指南](https://h5p.org/developers)、[`.h5p` 规范](https://h5p.org/documentation/developers/h5p-specification)、[许可证说明](https://h5p.org/licensing)、[官方 GitHub 组织与活跃内容类型](https://github.com/orgs/h5p/repositories)。

## 4. 能力—项目映射

| WeAgent 教育能力 | 首选复用 | 备选/参考 | 中等范围建议 |
|---|---|---|---|
| 课程、班级、作业、成绩 | 自研轻量域模型 | Moodle、Open edX | 只做本产品必需字段；预留 LTI/外部 LMS ID |
| 讲义、题干、解析、反馈 | Tiptap OSS | 现有 HTML 编辑器 | Tiptap JSON 为源，HTML 为发布快照 |
| 共同备课、小组文档 | Yjs + Hocuspocus | 现有 Socket.IO 仅做通知 | 第二阶段，独立协作 sidecar |
| HTML 交互课件 | reveal.js + 现有 ArtifactWorkbench | Slidev、H5P | 通用课件用 reveal.js；代码课用 Slidev；iframe 沙箱发布 |
| 可继续编辑的 PPTX | PptxGenJS | Slidev 仅用于图片式 PPTX | 从统一 slide JSON 生成 |
| 教学白板 | Excalidraw | 自研画布不推荐 | iframe/React 微前端试点 |
| 联网检索 | SearXNG | 具体搜索引擎官方 API | 后端代理、缓存、SafeSearch、引用 |
| 教材/论文 RAG | 现有 Chroma/RAG + 少量 LlamaIndex 模块 | 全量 LlamaIndex | 不替换现有 RAG 抽象 |
| 基础测验与作业 | 自研少量 JSON 题型 | H5P | MVP 做单选/多选/判断/简答/附件 |
| 互动视频、拖拽、分支题 | H5P | — | 后续内容包 adapter，不进首个闭环 |

## 5. 建议的中等开发范围

### 5.1 教师端

- 创建课程/班级、邀请或导入学生；
- 教学资源库：上传 PDF、文档、网页，沿用知识库/RAG；
- 备课 Copilot：联网检索并保留标题、URL、检索时间、引用片段；
- 生成并编辑讲义：Tiptap JSON/HTML；
- 生成并编辑课件：统一 slide JSON，可预览为 HTML，导出 Slidev Web 与 PptxGenJS `.pptx`；
- 发布课时：材料、课件、测验、截止时间；
- 作业/测验：基础题型、附件提交、规则评分 + 教师复核；
- Agent 辅助批改：输出建议分、rubric 命中、证据片段，最终成绩必须由教师确认；
- 班级概览：完成率、逾期、题目正确率、常见误区，不做复杂学习分析平台。

### 5.2 学生端

- 课程/课时列表和进度；
- 查看讲义、HTML 课件、可下载 PPT/PDF；
- 基于课程限定知识库的问答，答案展示引用；
- 完成测验、提交文件/文本作业；
- 查看教师反馈、rubric 与修订建议；
- 个人学习笔记；多人实时小组笔记放到第二阶段；
- 错题与薄弱知识点回顾，可由 Agent 生成变式题但标明“AI 生成”。

### 5.3 Agent 角色

- **Course Planner Agent**：从教学目标、时长和学生水平生成课时结构；
- **Research Agent**：SearXNG 检索、页面证据整理、引用去重；
- **Content Agent**：生成讲义、Slidev、PPT slide JSON；
- **Assessment Agent**：从指定材料生成题目、答案、rubric 和难度标签；
- **Tutor Agent**：只访问当前学生可见课程材料，采用提示式辅导而非直接泄露答案；
- **Feedback Agent**：按 rubric 生成建议，教师审核后发布；
- **Safety/Policy Agent**：检查未成年人内容、提示注入、外链和可执行 HTML。

不要为每个 Agent 建独立数据孤岛。它们应共享课程/课时/资源/作业的业务对象，仅使用不同 toolset、prompt policy 和权限。

## 6. 建议的数据与产物边界

建议内部保留三个稳定源格式：

1. `rich_document_json`：Tiptap JSON，适用于讲义、题干、反馈；
2. `slide_document_json`：WeAgent 自有的语义化 slides/blocks schema，适用于生成 Slidev 与 PPTX；
3. `assessment_json`：题目、选项、答案规则、rubric、知识点、版本。

HTML、PDF、PPTX、Slidev 静态站点、PNG 都是上述源格式的“发布产物”。这样教师可以继续编辑源数据，而不是反向编辑导出文件，也能让 Agent 做可靠的局部修改和 diff。

## 7. 主要风险与规避

- **许可证**：Moodle GPL、Open edX/SearXNG AGPL 不应直接拷源码进主仓库；使用独立服务/API 并保留 LICENSE/NOTICE，部署前由负责人复核网络分发义务。H5P 需逐内容类型和内容包检查许可证。
- **未成年人和隐私**：搜索查询、作业、批改记录、学习画像属于敏感数据；默认最小化采集，教师可见范围与学生自见范围分开。
- **联网内容可信度**：搜索结果不等于事实；保存来源、时间和引用片段，教师发布前审核。对安全搜索、域名白名单、下载类型和 SSRF 做后端控制。
- **可执行内容**：Slidev、H5P、HTML artifact 不能与主应用同权限运行。使用无同源能力的 sandbox iframe、CSP、资源代理、大小/时长限制和恶意脚本扫描。
- **AI 批改**：建议分与最终分分离；记录模型、rubric 版本、证据和教师修改，不自动给高风险主观题定最终成绩。
- **协作一致性**：Yjs 文档 schema、持久化和业务版本要分层。发布课件应从协作文档生成不可变版本，避免学生看到正在编辑的草稿。
- **框架漂移**：LlamaIndex、Tiptap/Yjs 等更新较快，必须经 adapter 接入、锁版本并准备契约测试。

## 8. 不建议进入首个版本的内容

- 部署或 fork 完整 Moodle/Open edX；
- 自研 Google Docs 级多人编辑协议；
- 自研 PowerPoint 文件解析与可视化设计器；
- 为 Excalidraw 将主前端从 Vue 2 迁到 React；
- 一开始支持 H5P 全部内容类型、Hub 和 authoring；
- 全自动主观题最终评分；
- 复杂教务排课、缴费、证书和校级多租户运营。

首个可演示闭环应是：

**教师导入资料 → Agent 联网/RAG 备课 → 生成可编辑讲义与课件 → 发布课时与测验 → 学生学习/提交 → Agent 依据 rubric 给出带证据的反馈建议 → 教师确认并发布反馈。**
