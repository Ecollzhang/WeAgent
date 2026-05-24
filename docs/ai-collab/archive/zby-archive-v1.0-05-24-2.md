# Archive

版本 ：v1.0
更新时间：2026.5.24

## 1. 归档信息

- 归档名称：Web 网页预览卡片与全屏可视化编辑器实现
- 归档日期：2026-05-24
- 归档人：zby
- 对应 session：zby-session-v1.11-05-24-2.md
- 对应 session 记录范围：从 Web 预览卡片到完整可视化编辑器

## 2. 归档原因

本次对话触发归档的原因：

- 实现了 P0 功能的 Web 网页预览卡片，是第二个跑通全链路的 P0 功能
- ArtifactFullscreenPreview 从简单全屏预览演化为完整的可视化编辑器，包含属性面板、层级树、拖拽布局等子模块
- 形成了 postMessage 双向通信规范（weagent-select/weagent-style/weagent-text/weagent-sync 等消息类型）
- `visualHtml`/`savedHtml` 分离的架构设计对后续模块有参考价值

## 3. 对话主题

本轮对话主要主题为：

- Web 网页预览卡片实现（WebPreviewCard + ArtifactFullscreenPreview）
- 属性面板实现（宽度/高度/间距/颜色/字号/对齐/粗细/边框 + 文本内容编辑）
- 层级树实现（解析 HTML、可拖拽宽度、展开收起、虚线连接线、双向同步高亮）
- 工具栏精简与功能增强（撤销/重做/布局修改/插入图片）
- 存储架构：visualHtml 与 savedHtml 分离解决 iframe 刷新
- 路径匹配修复：stripInjected + getPath/buildLayerTree 两端过滤一致

## 4. 归档提炼

从原始对话中提炼出的有效内容：

### postMessage 通信规范（可复用）

| 消息类型 | 方向 | 用途 |
|----------|------|------|
| `weagent-select` | iframe → Vue | 选中元素，传递路径/标签/样式 |
| `weagent-style` | Vue → iframe | 修改 CSS 属性 |
| `weagent-text` | Vue → iframe | 修改文本内容 |
| `weagent-sync` | iframe → Vue | 同步完整 HTML |
| `weagent-select-path` | Vue → iframe | 层级树点击跳转 |
| `weagent-toggle-layers` | iframe → Vue | 切换层级树显示 |
| `weagent-duplicate` / `weagent-delete` | Vue → iframe | 复制/删除组件 |

### 架构设计要点

- `visualHtml` — iframe 稳定显示，不随 autoSync 更新
- `savedHtml` — 后台保存，autoSync 更新但自动 `stripInjected()` 剥离工具栏
- 路径匹配：`getPath()` 和 `buildLayerTree` 两端使用相同过滤逻辑（排除 `.we-toolbar`）
- 拖拽方向：用 `previousSibling` 遍历判断 DOM 位置，不依赖鼠标坐标

### 常用 CSS 属性面板字段

宽/高、padding（四边）、背景色、文字色、字号、对齐、粗细、边框宽/色/圆角

## 5. 已形成成果

本次归档已经形成的成果包括：

- `frontend/src/components/WebPreviewCard/index.vue` — 内联 iframe 预览卡片
- `frontend/src/components/ArtifactFullscreenPreview/index.vue` — 全功能可视化编辑器（~600 行）
- `frontend/src/components/MessageBubble/index.vue` — 新增 webpage 渲染分支

## 6. 后续去向

本次归档内容后续应落入：

- `rules/`
  - postMessage 通信消息类型命名规范
  - visualHtml/savedHtml 分离存储规则
- 仅保留在归档记录中
  - 属性面板具体字段设计
  - 层级树路径匹配实现细节

## 7. 备注

本次归档的可视化编辑器是 P0 需求中最大的模块，大量功能（属性面板/层级树/拖拽/复制删除）在单次对话中迭代完成。通信规范和架构设计对后续模块（如部署状态卡片）有直接复用价值。
