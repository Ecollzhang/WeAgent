# Session

版本 ：v1.11
更新时间：2026.5.24

## 1. 基本信息

- Session 名称：可视化编辑器路径匹配修复、图片缩放、撤销栈、HTML 生成规范
- 日期：2026-05-24
- 参与人类成员：zby
- 参与 AI 角色：opencode (AI Agent)
- 对应负责人：zby
- 对应任务方向：4-多模态数据流 — 多模态产物内联展示
- 本次记录范围：修复可视化编辑器多个 bug，补充规则文件

## 2. 本轮背景与初始判断

上一轮实现了 ArtifactFullscreenPreview 全功能可视化编辑器，但存在多个运行时问题：层级树路径跳转不准、图片缩放破坏布局、撤销不可用、点击组件指向错误目标。本轮逐一排查修复，并沉淀 HTML 生成规范到 rules。

## 3. 讨论过程

- 【问题】层级树路径匹配不准 → 根因：iframe 中 body 有 `.we-toolbar` 子元素，`savedHtml` 通过 `stripInjected` 剥离了它，两端 `:nth-of-type` 索引不一致
- 【修正】`savedHtml` 不再剥离 toolbar，`buildLayerTree` 遇到 `.we-toolbar` 直接 `return`（不计入树显示但计入兄弟计数），`stripInjected` 仅在 `$emit('save')` 时使用
- 【问题】图片缩放 (`width: N%`) 破坏父容器布局，图片跑出外部
- 【修正】尝试 `transform: scale` → 用户满意效果但仍溢出 → 最终改用 `width: N% + max-width: 100% + height: auto`，插入时自带 `width: 100%; object-fit: contain`
- 【进展】自定义 undo/redo 栈实现：`undoStack` 存储 HTML 快照（最多 50 步），覆盖属性面板/文本编辑/拖拽/图片插入等所有操作
- 【问题】用户反映开发时需要规范来生成可用的 HTML → 沉淀为 `rules/html-generation.md`

## 4. 当前收敛结果

- 路径匹配：`savedHtml` 保留完整注入 HTML → 两端 `:nth-of-type` 索引一致
- 图片缩放：`width: N% + max-width: 100% + height: auto`，父容器内自适应
- 撤销/重做：自定义快照栈，覆盖所有操作类型
- HTML 生成规范：已写入 `rules/html-generation.md`

## 5. 未解决问题 / 后续建议

- 拖拽排序在复杂嵌套结构下的稳定性仍需验证
- 当前 `savedHtml` 保留了注入的工具栏 HTML，增大了内存占用，后续可考虑只保留结构不保留内容

## 6. 可沉淀结果

- 是否值得升级为 `Archive`：否（主要是 bug 修复，新增规则已写入 rules）
- 可升级为 `Spec`：否
- 可升级为 `Skill`：否
- 可升级为 `Rules`：是（HTML 生成规范已写入 rules）
