# Rule: HTML 生成规范 — 可视化编辑器兼容指南

版本 ：v1.0
更新时间：2026.5.24

## 1. 规则名称

- 名称：可编辑 HTML 的生成规范
- 创建日期：2026-05-24
- 维护人：zby

## 2. 规则来源

该规则来源于：

- 哪一轮 session：`sessions/zby-session-v1.11-05-24-3.md`
- 哪一份 archive：`archive/zby-archive-v1.0-05-24-2.md`
- 哪类重复出现的问题或有效做法：可视化编辑器（ArtifactFullscreenPreview）中，HTML 结构不规范会导致层级树路径匹配失败、元素选择异常、缩放溢出等问题。需要一套统一的生成规范来保证 Agent 产出的 HTML 可被编辑器正确渲染和编辑。

## 3. 规则内容

### 3.1 整体结构

- **必须**使用完整的 `<!DOCTYPE html>` 声明
- **必须**包含 `<html>`, `<head>`, `<body>` 三层结构
- **必须**在 `<head>` 中声明 `<meta charset="UTF-8">` 和 `<meta name="viewport">`
- **建议**所有样式写在 `<style>` 标签内嵌入 `<head>`，不使用外部 CSS 文件
- **建议**所有资源使用内联（base64）或 data URI，避免外部依赖

### 3.2 HTML 标签要求

- **必须**使用语义化的闭合标签（`<div>`, `<h1>`, `<p>`, `<span>` 等），避免自闭和标签的嵌套
- **必须**确保每个元素有明确的父容器，不要出现游离文本节点
- **建议**为可交互的区块元素添加有意义的 `class` 名称（如 `.card`, `.grid`, `.header`）
- **不建议**使用 `<table>` 布局，优先使用 `flex` 或 `grid`
- **必须**避免使用 `<iframe>` 和 `<object>`（编辑器无法处理嵌套文档）

### 3.3 CSS 样式要求

- **必须**使用内联 `<style>` 或 `style=""` 属性，不依赖外部样式表
- **必须**为图片设置 `max-width: 100%; height: auto;` 以防止溢出父容器
- **建议**使用 `display: flex` / `display: grid` 布局，方便编辑器中拖拽排序
- **必须**避免使用 `position: absolute` / `position: fixed`（破坏层级树顺序）
- **建议**为容器元素设置 `overflow: hidden` 以容纳内部缩放的元素

### 3.4 层级树兼容要求

- **必须**确保 body 的直接子元素之间有清晰的标签类型区分（不要在 body 下混放不同类型的块级元素）
- **必须**避免 body 下有非元素子节点（纯文本、注释节点），否则 `:nth-of-type` 索引会偏移
- **建议**将页面内容包裹在一个顶层容器 `<div class="page">` 中，避免 body 下有多个同级块级元素
- **警告**：body 下的 `.we-toolbar` 为编辑器注入元素，不计入层级树但影响 `:nth-of-type` 计数，生成 HTML 时无需关心

### 3.5 图片要求

- **必须**使用 `<img>` 标签，设置 `src` 为 base64 data URI 或完整 URL
- **必须**为每个 `<img>` 设置 `alt` 属性
- **建议**将图片包裹在 `<div>` 容器中并设置 `text-align: center` 或 `overflow: hidden`
- **格式**：`<div style="max-width:100%;overflow:hidden;"><img src="data:..." style="width:100%;height:auto;display:block;object-fit:contain;"></div>`

### 3.6 elements 数据格式（在 messages 表中存储）

当 Agent 回复一个网页产物时，message 的 `elements` 应包含 `webpage` 类型：

```json
{
  "type": "webpage",
  "data": {
    "content": "<!DOCTYPE html>...完整 HTML 字符串...",
    "title": "页面标题",
    "language": "html",
    "artifact_id": "uuid"
  }
}
```

### 3.7 示例：最小可用 HTML

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>页面标题</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, sans-serif; background: #f5f5f5; padding: 20px; }
    .card { background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>标题</h1>
      <p>内容段落</p>
    </div>
  </div>
</body>
</html>
```

## 4. 适用范围

该规则适用于：

- Agent 生成 HTML 网页产物时（`elements` 中 `type: "webpage"`）
- 需要在 ArtifactFullscreenPreview 可视化编辑器中进行编辑的 HTML
- 希望层级树、属性面板、拖拽排序正常工作的场景

该规则当前不适用于：

- 纯代码产物（`type: "code"`）
- 文档/PPT 产物（`type: "document"` / `type: "ppt"`）
- 非 HTML 的富文本内容

## 5. 使用说明

在实际归档或协作中，应如何使用该规则：

1. Agent 需要生成网页时，调用该规则生成符合规范的 HTML
2. 在 `_mock_agent_response()` 中模拟网页时，遵循相同的 HTML 结构规范
3. 评估一个 HTML 是否"可编辑"时，检查是否满足第 3 节的所有要求
4. 若 HTML 不满足规范，在可视化编辑器中可能出现以下问题：
   - 层级树显示异常 → 检查标签闭合和 body 子元素
   - 图片溢出 → 添加 `max-width: 100%`
   - 拖动排序无效 → 改用 flex/grid 布局
   - 属性面板不响应 → 检查元素是否有明确的 class

## 6. 备注

本规则的内容来源于可视化编辑器多次迭代修复中积累的经验。后续如果编辑器新增功能（如响应式断点、组件库等），本规则相应扩展。
