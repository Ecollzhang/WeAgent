# Education 开源借优与依赖边界

## 1. 借优原则

每个模块在实现前必须完成“借优卡片”：

1. 调研了哪些成熟 LMS、开源项目或标准。
2. 借用了什么领域模型、交互或数据结构。
3. 选择直接依赖、sidecar、仅参考或不采用的理由。
4. 代码、模型、数据和内容分别采用什么许可证。
5. 主动排除了哪些复杂能力。
6. WeAgent 自研的差异化是什么。
7. 依赖如何替换、升级和降级。

## 2. LMS 与教育平台借鉴

| 项目 | 许可证 | 借鉴内容 | 决策 |
|---|---|---|---|
| [Moodle](https://github.com/moodle/moodle) | GPL-3.0 | 课程、成员、活动、成绩和插件概念 | 参考；未来 connector |
| [Open edX](https://github.com/openedx/openedx-platform) | AGPL-3.0 | Studio/LMS 分离、发布和 LTI | 参考；不作为 MVP 基座 |
| [Canvas LMS](https://github.com/instructure/canvas-lms) | AGPL-3.0 | Enrollment、Assignment、Submission、Rubric | 参考领域模型/API |
| [Kolibri](https://github.com/learningequality/kolibri) | 项目许可证见官方仓库 | 资源→课时→测验、coach report | 参考教师/学生闭环 |
| [Oppia](https://github.com/oppia/oppia) | 项目许可证见官方仓库 | 问题—反馈—下一步的学习状态 | 后续自适应参考 |
| [Khan Perseus](https://github.com/Khan/perseus) | MIT | 题目编辑、渲染和评分分离 | 参考数据合同；React 不直接嵌入 |

GPL/AGPL 项目不得直接复制源代码进入主仓库。借鉴领域概念不等于复制实现。

## 3. MVP 直接接入

| 能力 | 项目 | 许可证 | 接入方式 |
|---|---|---|---|
| 结构化富文本 | [Tiptap](https://github.com/ueberdosis/tiptap) | Editor Core MIT | `@tiptap/vue-2` |
| 英语规则提示 | [Harper](https://github.com/automattic/harper) | Apache-2.0 | 浏览器 JS/WASM |
| 英语可读性 | [textstat](https://github.com/textstat/textstat) | MIT | Flask Python 包 |
| 汉字拼音 | [pypinyin](https://github.com/mozillazg/python-pinyin) | MIT | Flask Python 包 |
| 网页正文抽取 | [Mozilla Readability](https://github.com/mozilla/readability) | Apache-2.0 | Node/sandbox 工具 |
| HTML 课件 | [reveal.js](https://github.com/hakimel/reveal.js) | MIT | Artifact 渲染 |
| 可编辑 PPTX（当前基线） | [python-pptx](https://github.com/scanny/python-pptx) | MIT | Education 导出 Provider |
| 可编辑 PPTX（目标候选） | [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | MIT | 评估后作为可替换导出 Provider |
| DOCX | [python-docx](https://github.com/python-openxml/python-docx) | MIT | 导出 capability/worker 复用同一依赖 |

注意：

- Tiptap Pro/Cloud 不属于默认 MIT 核心能力。
- Harper 是语言建议，不是评分器。
- DOCX 导出只复用 python-docx 依赖，不跨服务导入 RAG 解析器的业务实现。
- textstat 只提供表层指标。
- Readability 不负责 HTML 消毒。
- `python-pptx` 是当前代码事实；基础导出可用不等于多风格视觉质量已经验收。
- PptxGenJS 是生成库，不是 PowerPoint 编辑器。

## 4. Sidecar 或试验接入

| 能力 | 项目 | 许可证 | 决策 |
|---|---|---|---|
| 搜索聚合 | [SearXNG](https://github.com/searxng/searxng) | AGPL-3.0 | 独立 SearchProvider sidecar |
| 中文纠错候选 | [PyCorrector](https://github.com/shibing624/pycorrector) | 代码 Apache-2.0；模型另审 | 先用教师样本评测 |
| 多语言语法 | [LanguageTool](https://github.com/languagetool-org/languagetool) | LGPL-2.1+ | Harper 不足时自托管 |
| 中文深层分析 | [HanLP](https://github.com/hankcs/HanLP) | 代码与模型需分别审核 | MVP 不作为强依赖 |

Sidecar 要求：

- 核心服务启动不依赖 sidecar。
- 健康状态可见。
- 超时和 fallback。
- API adapter 隔离。
- 许可证和模型清单。

## 5. 第二阶段或仅参考

| 能力 | 项目/标准 | 决策 |
|---|---|---|
| 多人实时编辑 | [Yjs](https://github.com/yjs/yjs) + Hocuspocus | V1/Bonus |
| 互动视频/拖放题 | [H5P](https://h5p.org/) | 第二阶段 sidecar |
| 题库互操作 | [QTI 3](https://www.1edtech.org/standards/qti) | 先预留映射 |
| LMS 互操作 | LTI 1.3 | Bonus |
| 白板 | [Excalidraw](https://github.com/excalidraw/excalidraw) | React iframe/微前端，后置 |
| 高级课件 | [Slidev](https://github.com/slidevjs/slidev) | 编程/复杂互动课后置 |
| Markdown 课件 | [Marp](https://github.com/marp-team/marp) | 主题与多格式导出参考；不替代结构化真源 |
| 通用批注标准 | [W3C Web Annotation](https://www.w3.org/TR/annotation-model/) | 数据模型参考 |

## 6. 不重复现有能力

- 不以 Haystack/LlamaIndex 全量替换现有 RAG。
- 不另建教育 Agent runtime。
- 不另建教育 Artifact 服务。
- 不另建教育 Socket/SSE。
- 不另建 Skill/MCP/Plugin/Tool 注册系统。
- 不另建通用工作流图编辑器。
- 不在 edu 服务重复实现 web_search/http_fetch。

## 7. 许可证清单

每个 SubjectPackVersion 维护：

- dependency name/version。
- code license。
- model license。
- dataset/content license。
- source URL。
- usage mode：linked、embedded、sidecar、reference。
- NOTICE/attribution。
- 商业/网络提供限制。

禁止：

- 用代码许可证代替模型许可证判断。
- 用项目总体开源声明代替 H5P content type 审核。
- 将 AGPL/GPL 源码复制进主仓库后忽略义务。
- 将未经授权教材或网页全文提交到仓库。

## 8. 支持研究

详细证据：

- [Education 开源生态调研](../../../.planning/research/education-open-source-landscape.md)
- [Education 语言学习工具接入调研](../../../.planning/research/education-language-tooling.md)

## 9. 独立领域实现的借优结论（2026-07-29）

本轮只引入可以替换、许可证清晰且不会反向接管 Education 业务数据的组件：

| 项目 | 许可证 | 本轮决策 | 边界 |
|---|---|---|---|
| [Presenton](https://github.com/presenton/presenton) | Apache-2.0 | 预留 `CoursewareProvider` / API / MCP adapter，不作为 MVP 强依赖 | 未来可承担自动排版；课程、课时、版本与发布状态仍以 Education 数据库为准 |
| [python-pptx](https://github.com/scanny/python-pptx) | MIT | 保留为当前 `SlideDocument → PPTX` 基础 Provider | 当前只证明基础结构和文件打开，不代表视觉质量或复杂对象保真 |
| [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | MIT | 作为目标可替换 Provider 评估母版、图表、媒体和可编辑对象 | 它是生成库，不是在线编辑器，也不保存业务状态 |
| [PPTist](https://github.com/pipipi-pikachu/PPTist) | AGPL-3.0 | 仅研究 SlideDocument、页面缩略图和编辑器交互 | 不复制源码、不嵌入主前端，避免把 AGPL 实现混入主仓库 |
| [Apache ECharts](https://github.com/apache/echarts) | Apache-2.0 | 学生画像与评估领域按需模块化加载 | 只负责图表表达，统计口径由 Education 后端计算并返回证据 |
| [GrapesJS](https://github.com/GrapesJS/grapesjs) | BSD-3-Clause | 第二阶段再评估 HTML 页面级编辑 | MVP 继续使用现有富文本与结构化 SlideDocument，避免两套编辑器并存 |
| [AutoAnimate](https://github.com/formkit/auto-animate) | MIT | 暂不新增依赖；只借鉴自动布局过渡原则 | 当前领域页使用克制的 CSS 动效，并尊重 `prefers-reduced-motion` |
| [Driver.js](https://github.com/kamranahmedse/driver.js) | MIT | 帮助中心稳定后可作为站内导览 Provider | MVP 采用静态图文步骤，避免导览锚点随页面迭代失效 |

落地原则：Agent 只通过受控 Education 工具写入 canonical 业务对象；导出器、图表库、
排版服务和未来的编辑器都是 Provider。替换任何 Provider 都不能改变课程成员权限、
课时上下文、正式成绩口径、内容版本或发布审核规则。

## 10. 课件 Skill 与视觉检查借优

开发期 Codex Skills 与 WeAgent 产品运行时 Capability 必须明确分层：

- 开发/UAT 可使用演示文稿、图像生成和浏览器自动化能力制作样例、逐页截图并做视觉检查。
- 产品运行时以版本化的
  `presentation.plan / compose / theme.apply / visual_asset / render / visual_qa / repair`
  能力包接入 Tool Gateway，不能假设开发机私有 Skill 会随产品部署。

借优来源：

- [Anthropic PPTX Skill](https://github.com/anthropics/skills/tree/main/skills/pptx) 只参考
  模板资产、渲染、逐页检查和定向修复流程；其仓库对文档 Skills 的授权需单独复核，
  未确认前不复制实现。
- [OpenAI Skills](https://github.com/openai/skills) 参考
  `SKILL.md + scripts + references + assets` 的可维护包结构。
- [reveal.js](https://github.com/hakimel/reveal.js) 继续作为 HTML 交互预览基线。
- [Slidev](https://sli.dev/guide/exporting.html) 与
  [Marp](https://github.com/marp-team/marp-cli) 用于研究主题和多格式导出；以页面图像生成的
  PPTX 只能标为“视觉一致导出”，不能标为“原生完全可编辑”。

PPT 质量增强阶段至少提供清朗课堂、纸张批注、童趣绘本、深色聚焦四种风格，并用真实
渲染图片检查溢出、重叠、破图、层级、密度、对齐、对比度和主题一致性。
