# Education 内容、搜索、RAG 与 Artifact

## 1. 内容真源

| 内容 | 可编辑真源 | 发布/导出 |
|---|---|---|
| 教案 | `lesson_plan_json` | HTML、DOCX、PDF |
| 讲义/题干/反馈 | Tiptap JSON | sanitized HTML、PDF |
| 课件 | `slide_document_json` | reveal.js HTML、PPTX、PDF |
| 题目与试卷 | `assessment_json` / item versions | HTML、打印文件 |
| Rubric | `rubric_json` | 评分界面、PDF |

导出文件不反向成为主数据。MVP 不承诺将教师在 PowerPoint 中修改后的 PPTX 无损导回系统。

## 2. 内容编辑

### 2.1 Tiptap

适用于：

- 讲义。
- 教案叙述块。
- 阅读材料加工。
- 题干和解析。
- 作文和反馈。

自定义节点：

- 来源引用。
- 课程资源。
- 词汇/生字卡。
- 阅读问题。
- 提示块。
- 教师私有答案块。
- 简单互动块。

保存时必须校验节点 schema 和可见范围。

### 2.2 SlideDocument

每页由语义块组成：

- title
- text
- image
- quote
- vocabulary
- question
- answer_reveal
- chart
- diagram
- teacher_note

同一 SlideDocument：

- reveal.js 渲染在线 HTML。
- PptxGenJS 导出可编辑 PPTX。

### 2.3 安全渲染

- 作者预览和学生发布使用不同安全策略。
- 不可信 HTML 经过 sanitizer。
- 发布 iframe 使用 sandbox 和 CSP。
- 禁止学生内容获得主应用同源权限。
- 外部资源通过允许列表或资源代理。

## 3. 搜索与正文读取合同

搜索发现和正文获取必须分离：

```text
SearchProvider
→ SearchHit
→ ContentFetcher / WebPageReader
→ FetchedDocument
→ Chunker
→ Retriever / Reranker
→ EvidenceChunk
→ Agent
```

## 4. SearchProvider

职责：

- 接收查询、语言、安全级别和时间范围。
- 调用 SearXNG 或其他 provider。
- 归一化候选结果。
- 去重。

SearchHit：

```text
url
title
snippet
provider
rank
published_at
search_query
```

规则：

- 禁止命名为 `content`。
- snippet 只是搜索服务返回的摘录或描述。
- snippet 不能进入“已获取全文”状态。
- Agent 可以用 snippet 推荐候选，但不能把它当作可验证全文证据。

## 5. ContentFetcher / WebPageReader

职责：

- URL scheme、DNS/IP 和重定向检查。
- SSRF 防护。
- 超时、最大响应大小、MIME 白名单。
- 下载 HTML、PDF 或受支持文档。
- Readability 主正文抽取。
- 通用 DOM 文本 fallback。
- sanitizer 和资源清理。
- 提取 metadata。
- checksum 和抓取快照。

FetchedDocument：

```text
canonical_url
title
author
clean_text
clean_html
published_at
fetched_at
checksum
content_status
```

content_status：

- `full_extracted`
- `partial_extracted`
- `snippet_only`
- `blocked`
- `failed`

`snippet_only` 只保留为候选线索，默认不进入课程 RAG，也不得直接支撑事实性结论。
教师需要成功抓取正文、上传可用材料，或将其显式标记为“未核验线索”后再使用。

## 6. Retriever / Reranker

职责：

- 切片。
- 关键词、向量或混合检索。
- 可选 rerank。
- 返回可引用 EvidenceChunk。

EvidenceChunk：

```text
document_id
document_checksum
chunk_id
text
locator
retrieval_score
rerank_score
source_url
```

Agent 输出引用必须指向 EvidenceChunk 或教师上传文档位置。

## 7. Fallback

### 7.1 搜索

```text
primary SearchProvider
→ backup provider
→ teacher-entered URL
→ course RAG / uploaded materials only
```

### 7.2 正文获取

```text
Readability
→ generic DOM extraction
→ snippet_only（明确标记）
→ teacher upload / skip
```

### 7.3 检索

```text
hybrid + rerank
→ vector search
→ keyword/BM25
→ teacher-selected excerpts
```

原则：

- SearchProvider 失败不阻断基于课程资料的备课。
- fetch 失败不能拿 snippet 冒充全文。
- reranker 不可用不阻断基础检索。
- 所有 fallback 在 UI 和审计记录中可见。

## 8. 与现有工具整合

- 现有 `web_search` 适配为 SearchProvider。
- 现有 `http_fetch` 和 RAG URL 抓取适配为 ContentFetcher。
- 现有 RAG search 适配为 Retriever。
- 不创建重复的 `education_web_search`、`education_http_fetch` 和第二套向量库。
- 教育业务传递课程、用户和可见范围，底层工具保持通用。

## 9. RAG 可见范围

### 9.1 教师

可检索：

- `teacher_private`。
- `course_published`。

教师不得直接查询学生的 private 分区。批改与反馈只能读取学生主动提交后冻结在
`SubmissionVersion` 中的正文和附件快照；未提交的笔记、草稿和私有上传始终不可见。

### 9.2 学生

可检索：

- `course_published`。
- 本人 `student_private`。

不可检索：

- 答案和 rubric。
- 教师草稿。
- 其他学生内容。

## 10. 学生上传

MVP 支持：

- PDF。
- DOCX。
- TXT。
- Markdown。
- 受控 URL。

限制：

- 文件类型和大小。
- 病毒/恶意内容检查接口。
- 处理超时。
- 私有 RAG。
- 删除和归档。
- 外部 provider 使用前最小化个人信息。

## 11. 引用和版权

每个外部来源保存：

- 标题。
- URL。
- 作者。
- 发布时间。
- 抓取时间。
- checksum。
- 使用片段。
- 加工记录。
- copyright_status。

默认发布：

- 必要摘录。
- 教师/Agent 改编内容。
- 原链接和来源。

完整发布只允许：

- 教师上传并确认拥有使用权。
- 开放许可证内容。
- 项目自有内容。

仓库示例不得包含未经授权教材全文。

## 12. Artifact

Artifact 类型沿用核心模型；Education 添加业务关联：

- source content/version。
- lesson/assignment。
- generating Agent run。
- provider。
- subject pack version。
- publish status。

生成产物：

- HTML。
- PPTX。
- DOCX。
- PDF。
- 图片。
- 可下载资料。

发布前检查 Artifact 是否存在、可打开且可安全预览。

## 13. 产物失败

- HTML 失败：保留 SlideDocument，允许重新渲染或编辑。
- PPTX 失败：HTML 课件仍可发布，PPTX 标记未生成。
- DOCX 失败：教案仍可在系统内使用。
- RAG 入库失败：资源标记 failed，不进入 Agent 检索范围。
- 导出失败不能删除结构化真源。
