# CHECKPOINT-B: Canonical Built-in Tool Definitions

## Scope

建立内置 Tool 的唯一事实来源，避免旧 `AgentTool` 模板和新 `Capability(type="tool")` 继续分叉。

## Completed

- 新增 `backend/app/services/builtin_tool_definitions.py`。
- 所有内置 Tool definition 都包含：
  - `value/source_ref`
  - `name`
  - `category`
  - `description`
  - `runtime`
  - `handler`
  - `tool_names`
  - `input_schema`
  - `output_schema`
  - `permissions`
  - `audit`
  - `ui.status`
  - `TOOL.md` markdown
- 更新 `tool_service.BUILTIN_TOOLS`，使旧 `/api/tools` 兼容视图来自 canonical definitions。
- 更新 `capability_service.seed_builtin_tool_capabilities()`：
  - 从 canonical definitions seed。
  - 新定义变化时生成新 version。
  - 不修改已有 Agent pinned binding。
- 保留旧 source_ref：
  - `code_generator`
  - `code_review`
  - `file_operations`
  - `document_parse`
  - `web_search`
  - `web_fetch`
  - `api_client`
  - `data_analysis`
  - `database_query`
  - `image_analysis`
  - `terminal`
  - `git_operations`
- 新增真实可用 source_ref：
  - `code_search`
  - `image_info`

## Verification

```powershell
python -m pytest tests\test_toolset_categories.py tests\test_capability_projection.py tests\test_capability_api.py -q
```

Result:

- 22 passed.

## Notes

旧展示项没有被粗暴删除，而是被重新标记为 `implemented`、`requires_config` 或 `deferred`，避免破坏既有页面和测试，同时消除“空壳可调用”的误导。
