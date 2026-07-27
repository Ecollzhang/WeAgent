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
| 可编辑 PPTX | [PptxGenJS](https://github.com/gitbrent/PptxGenJS) | MIT | Node/sandbox 导出 |
| DOCX | [python-docx](https://github.com/python-openxml/python-docx) | MIT | 导出 capability/worker 复用同一依赖 |

注意：

- Tiptap Pro/Cloud 不属于默认 MIT 核心能力。
- Harper 是语言建议，不是评分器。
- DOCX 导出只复用 python-docx 依赖，不跨服务导入 RAG 解析器的业务实现。
- textstat 只提供表层指标。
- Readability 不负责 HTML 消毒。
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

- [Education 开源生态调研](../../../../.planning/research/education-open-source-landscape.md)
- [Education 语言学习工具接入调研](../../../../.planning/research/education-language-tooling.md)
