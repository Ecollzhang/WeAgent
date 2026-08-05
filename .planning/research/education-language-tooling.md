# Education 语言学习工具接入调研

> 范围：高中英语、小学语文的阅读与写作能力。
> 证据边界：仅采用项目官方仓库、官方文档与正式标准；不修改业务代码。
> 决策目标：在中等开发量内，尽量复用 WeAgent 已有 Agent、RAG、联网检索、HTML Artifact 与编辑器能力。

## 结论摘要

第一阶段建议采用“轻量本地工具 + Agent 编排 + 教师复核”：

- 高中英语：前端接入 **Harper** 做离线语法、拼写与风格提示；Flask 直接接入 **textstat** 输出可解释的可读性指标。
- 小学语文：Flask 直接接入 **pypinyin** 做生字注音；将 **pycorrector** 作为异步 sidecar，只生成错别字候选，不自动改写学生原文。
- 联网阅读：复用已有或规划中的 **SearXNG** 检索，用 **Mozilla Readability** 抽取正文；抽取后的 HTML 必须再做消毒并保留来源信息。
- 题库与内容：MVP 使用自有轻量题目 JSON 和现有 HTML/编辑能力；**QTI 3、W3C Web Annotation** 只作为数据模型兼容目标，**H5P** 留到需要复杂互动题型的第二阶段。
- 不把语法规则命中数、传统可读性公式或大模型反馈直接当作成绩。所有建议均保留接受、拒绝、教师复核和审计记录。

目前没有发现一个许可证清晰、维护活跃且能直接给出“小学语文可读性或作文质量分数”的成熟官方开源库。中文侧应先组合分词、句长、字词难度、拼音与纠错候选等透明特征，再用本校教师标注样本校准，而不是引入一个未经验证的总分。

## 接入决策矩阵

| 项目 / 标准 | 主要能力 | 决策 | 许可证与维护状态 | Vue2 / Flask 适配 | 与 WeAgent 现有能力关系 | 关键约束 |
|---|---|---|---|---|---|---|
| [Harper](https://github.com/automattic/harper) / [harper.js 文档](https://writewithharper.com/docs/harperjs/introduction) | 英语语法、拼写、风格检查，离线运行 | **直接接入** | Apache-2.0；官方仓库持续发布，2026 年仍有版本 | `harper.js` 可在 Vue2 中以框架无关的 JS/WASM 模块调用 | 补充 Agent 反馈的确定性规则层，不替代作文评价 Agent | 仅英语；输出是语言建议，不是课程标准评分 |
| [textstat](https://github.com/textstat/textstat) / [官方文档](https://docs.textstat.org/) | Flesch、年级难度、句词统计等英语可读性指标 | **直接接入** | MIT；2026 年仍有发布 | Python 包可直接用于 Flask 服务 | 提供可解释指标，避免让 Agent 自行估算 | 主要面向英语；只反映表层复杂度，不能评价论证和内容质量 |
| [pypinyin](https://github.com/mozillazg/python-pinyin) / [官方文档](https://pypinyin.readthedocs.io/) | 汉字转拼音、声调、轻声、多音字候选 | **直接接入** | MIT；成熟 Python 项目 | 可直接用于 Flask | 补充小学语文生字、朗读和注音能力，现有 RAG 不覆盖 | 多音字需短语词典和教师纠正机制 |
| [Mozilla Readability](https://github.com/mozilla/readability) | 从网页提取标题、作者、正文、纯文本等 | **直接接入（受控 Node/沙箱工具）** | Apache-2.0；Mozilla 官方维护 | 与现有 Node/HTML Artifact 链路匹配；Flask 通过内部工具调用 | 与联网检索形成“搜索—抽取—教学加工”链路，不重复搜索 | 官方明确说明它不负责 HTML 消毒；还需 sanitizer、CSP、SSRF 防护 |
| [LanguageTool](https://github.com/languagetool-org/languagetool) / [HTTP Server 文档](https://dev.languagetool.org/http-server.html) | 多语言语法、拼写与风格规则 | **sidecar（Harper 覆盖不足时启用）** | LGPL-2.1-or-later；官方说明约每三个月发布，Java 17 | 官方建议通过本地 HTTP `/v2/check`，适合独立 Java 服务 | 与 Harper 英语检查部分重复，但覆盖语言和规则更广 | 不使用免费公共 API 承载自动化课堂流量；自托管开源版不含云端 AI 规则 |
| [pycorrector](https://github.com/shibing624/pycorrector) | 中文错别字、音近形近和语法纠错候选 | **sidecar** | 代码 Apache-2.0；2025 年仍有版本；模型与数据许可证须单独审核 | Flask 调异步 Python 服务；避免模型与主进程争抢内存 | 给中文写作 Agent 增加可复核候选，不替代教师或 Agent 解释 | 默认 KenLM 模型约 2.8 GB，较强模型可能需要 GPU；领域误纠风险明显 |
| [HanLP](https://github.com/hankcs/HanLP) / [官方文档](https://hanlp.hankcs.com/docs/index.html) | 分词、词性、实体、句法、语义角色等中文分析 | **sidecar（许可证审核后）** | 代码 Apache-2.0；官方默认模型通常为 CC BY-NC-SA 4.0，具体模型须逐项核查 | 可部署 Python 服务或调用其 REST API | 能生成作文结构特征，但与 RAG/Agent 的通用 NLP 有一定重叠 | 默认模型的非商业与相同方式共享条款可能不适合产品化；能力明显超出 MVP |
| [SearXNG](https://github.com/searxng/searxng) / [Search API](https://docs.searxng.org/dev/search_api.html) | 聚合联网搜索 | **sidecar（复用既有规划）** | AGPL-3.0；官方项目活跃 | Flask 调 JSON Search API，Vue2 不直接访问 | 复用 WeAgent 联网检索，不再引入第二套搜索框架 | 注意 AGPL 部署边界、搜索源条款、速率限制和来源可追溯 |
| [H5P](https://h5p.org/) / [开发者文档](https://h5p.org/developers) / [许可证说明](https://h5p.org/licensing) | 互动题型、互动视频、内容包、xAPI 数据 | **sidecar（第二阶段）** | 官方说明尽可能使用 MIT，但核心/内容类型可能含 GPL 或其他许可证，需逐包审核 | 对 Vue2/Flask 不是轻量组件，通常需独立宿主和内容包管理 | 与 HTML Artifact、原生题目编辑器存在重叠 | MVP 接入成本偏高；只有复杂互动题型收益明显时再引入 |
| [1EdTech QTI 3](https://www.1edtech.org/standards/qti/index) / [官方示例](https://github.com/1EdTech/qti-examples) | 题目、试卷、结果和 LMS 之间的交换标准 | **仅参考** | 正式标准；官方示例使用 1EdTech 规范文档许可证，不应视为普通 OSS 代码复制 | 内部 JSON 预留映射字段，后续做导入/导出适配器 | 为未来题库互操作提供边界，不重复当前业务 | 完整解析器、播放器、互操作验证超出中等开发量 |
| [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) | 批注主体、目标、选择器和来源的标准模型 | **仅参考** | W3C Recommendation | 现有 Vue2 编辑器可实现简化数据模型；Flask 持久化 JSON | 复用现有 HTML 编辑/Artifact，不再引入整套批注平台 | 文档版本变化后，纯 offset 容易漂移，应同时保存 quote selector 与内容版本 |
| [jieba](https://github.com/fxsjy/jieba) | 中文分词、关键词、词性 | **不建议新增** | MIT，但官方仓库维护活跃度和现代工程适配有限 | Python 接入简单 | HanLP 或现有 Agent/NLP 已能覆盖，新增收益低 | 仅为分词再维护一个依赖不划算；若未来只需最小离线分词再重新评估 |
| LanguageTool 免费公共 API | 远程语法检查 | **不建议** | [官方限制](https://dev.languagetool.org/public-http-api.html)明确不允许自动化批量使用 | 虽可 HTTP 调用，但不适合作为产品后端 | 与自托管 LanguageTool 能力相同 | 速率、隐私、稳定性和使用政策均不满足课堂生产流量 |

## 建议的产品能力

### 高中英语

1. 学生写作时，Harper 在本地标记拼写、语法和风格问题，展示规则解释，不自动替换原文。
2. 提交后，textstat 输出句长、词长、Flesch Reading Ease、Flesch-Kincaid Grade 等指标及其局限说明。
3. WeAgent 按教师配置的 rubric 评价主题完成度、结构、论证和证据；规则工具只作为证据输入。
4. 教师端可查看原文、工具建议、学生采纳记录、Agent 评价，并能覆盖最终反馈。
5. 若 Harper 的覆盖不足，再部署 LanguageTool sidecar；避免首期同时维护两套英语规则引擎。

### 小学语文

1. pypinyin 为阅读材料生成可切换的拼音、声调和生字卡，教师可修正多音字。
2. pycorrector 异步生成错别字和语病候选，并附原位置、候选、置信或规则来源；默认不改学生原文。
3. 先计算透明特征：字数、句数、平均句长、段落结构、生字比例、重复词、标点使用等；如确需更深句法特征，再评估 HanLP。
4. “可读性等级”和“作文能力”必须用本地年级材料与教师标注样本做校准，并展示形成依据。
5. 教师端维护年级词表、生字表、范文、评分 rubric 和误纠白名单；学生端看到适龄解释和修改历史。

## 题库、编辑与批注

MVP 不直接实现完整 QTI 或 H5P。内部题目模型保持轻量，同时为后续映射预留：

- `item_id`、题型、题干、素材与来源；
- 作答结构、正确答案或评分规则；
- 能力点、年级、难度、语言、版本；
- 自动反馈、教师反馈、尝试记录；
- 来源 URL、作者、发布时间、抓取时间和引用片段。

内容编辑继续复用现有 HTML Artifact、CodeMirror/页面编辑能力。教育场景新增的批注数据可参考 W3C Web Annotation，至少保存：

- 批注内容、作者、角色与时间；
- 文档版本；
- 目标段落/节点；
- 精确原文 quote、前后文和 offset；
- 已解决、接受、拒绝等状态。

这样教师可以在阅读材料和作文上逐段批注，学生修改后仍可追踪反馈，而不需要首期引入新的大型编辑器或协作平台。

## 联网检索与引用链

推荐链路：

`SearXNG 检索 → 后端白名单抓取 → Readability 抽取 → HTML 消毒 → 年级/语言分析 → 教师选用 → 生成阅读任务`

每份外部材料必须保留标题、原始 URL、作者、发布时间、抓取时间、选用片段和加工记录。Readability 只负责正文抽取，不提供可信度判断、版权许可或安全消毒；教师端应能查看原网页和排除不合适内容。首期没有必要再加一套参考文献管理库，已有搜索结果元数据加上述来源字段即可满足课堂引用与审计。

## 分阶段落地

### 第一阶段：中等开发量

- Harper、textstat、pypinyin；
- SearXNG + Readability 安全抽取；
- 轻量题目 JSON、教师 rubric、反馈接受/拒绝与审计记录；
- 现有编辑器上的教师批注；
- pycorrector 先做小样本准确率和资源评测，再决定是否上线 sidecar。

### 第二阶段：按证据扩展

- Harper 覆盖不足时增加自托管 LanguageTool；
- 中文结构分析确有教学收益且模型许可证通过后增加 HanLP；
- 有互动视频、拖放、复杂互动题型需求时接入 H5P；
- 有 LMS/题库交换需求时实现 QTI 3 导入导出适配器。

## 上线门槛

- 用教师标注的小规模高中英语作文与小学语文作文建立回归集，分别统计误报、漏报和教师采纳率。
- 所有自动反馈均可解释、可撤销、可由教师覆盖，不直接写回学生原文。
- 代码、模型、数据集、内容包分别建立许可证清单；尤其不能用 HanLP 代码许可证代替模型许可证判断。
- 学生文本默认在本地或受控服务处理；启用任何外部 API 前重新评估未成年人隐私和数据保留。
- 网页内容必须经过 SSRF 防护、超时/大小限制、HTML 消毒和 CSP，并保留来源。
