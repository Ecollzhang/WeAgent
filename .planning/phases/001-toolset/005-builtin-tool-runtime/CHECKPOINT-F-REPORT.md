# CHECKPOINT-F: Toolset UI Status and Documentation View

## Scope

让工具集页面明确展示 Tool 是否真实可用，并把 `TOOL.md` 作为 Agent-facing 文档显示出来。

## Completed

- 更新 `frontend/src/views/Tools.vue`：
  - Tool 卡片展示状态标签：`已实现`、`部分实现`、`需要配置`、`未实现`。
  - Tool 详情概览展示状态和 runtime handler。
  - Tool 文件视图新增 `TOOL.md`。
  - Tool 文件视图的 `manifest.json` 使用最新 manifest。
  - `tool-definition.json` 摘要包含 `handler`、`tool_names`、`status`。
- 更新 `frontend/tests/toolset-ui-contract.test.js`：
  - 断言存在 `toolStatusLabel`。
  - 断言 Tool 文件视图包含 `TOOL.md`。
  - 断言详情中有 `toolHandler` 摘要。

## Verification

```powershell
node tests\toolset-ui-contract.test.js
```

Result:

- Toolset UI contract: passed.

## Notes

前端仍保留开发者可读 manifest，但用户主视图会优先看到状态、权限、handler 摘要和 `TOOL.md`，不再只面对原始 JSON。
