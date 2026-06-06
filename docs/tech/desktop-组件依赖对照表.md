# desktop-组件依赖对照表

更新日期：2026-06-05

## 范围

本表用于记录 Web 端统一工作台核心组件迁移到 `clients/desktop` 前的依赖扫描结果，作为阶段 2 的输入物。

路径基准：

- `3-WeAgent/combineartifact_editing_system(base_v1.08)/WeAgent/`

## 组件对照

| 组件 | 源文件 | 直接组件依赖 | API 依赖 | 第三方依赖 | Store 依赖 | webpack 专属能力 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ArtifactWorkbench` | `frontend/src/components/ArtifactWorkbench/index.vue` | `CodeEditor`、`DiffViewCard`、`HtmlPageEditor`、`ImageCropper` | `getFileTree`、`getSessionRawFileUrl`、`getSessionZipExportUrl`、`getWorkspaceFileUrl`、`getSessionDownloadUrl`、`writeFile` | 无新增三方直引 | 未发现 | 未发现 | 本轮迁移时去掉 `ImageCropper` 分支，保留 P0 主闭环 |
| `CodeEditor` | `frontend/src/components/CodeEditor/index.vue` | 无 | `writeFile` | `codemirror`、`vue-codemirror` | 未发现 | 未发现 | 已确认为 desktop 阶段 0 的硬依赖 |
| `HtmlPageEditor` | `frontend/src/components/HtmlPageEditor/index.vue` | 无 | `writeFile` | 无新增 npm 包 | 未发现 | 未发现 | 依赖 iframe 真实预览与 DOM 注入逻辑，迁移时需重点验证 Electron 兼容性 |
| `DiffViewCard` | `frontend/src/components/DiffViewCard/index.vue` | 无 | `writeFile` | 无 | 未发现 | 未发现 | 可优先用于打通 diff 应用闭环 |

## 结论

- 当前四个核心组件中，未发现对 Vuex 的直接依赖，不将引入 Vuex 作为本轮默认前置条件。
- 当前四个核心组件中，未发现 `require()`、`require.context` 等 webpack 专属能力。
- `CodeEditor` 明确依赖 `codemirror` 与 `vue-codemirror`，这两项已纳入 desktop 阶段 0。
- `ArtifactWorkbench` 的主风险点不在状态管理，而在 desktop 服务层对齐、文件 URL 构造和子组件迁移顺序。
