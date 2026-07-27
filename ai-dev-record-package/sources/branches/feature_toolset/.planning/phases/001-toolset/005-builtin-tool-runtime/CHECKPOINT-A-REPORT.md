# CHECKPOINT-A: Contract and Regression Tests

## Scope

锁住 005 内置 Tool runtime 的核心失败用例，防止 Tool 再退回“只有卡片、没有契约”的状态。

## Completed

- 新增 `backend/tests/test_capability_tool_contract.py`。
- 覆盖内置 Tool version 必须有：
  - `weagent.tool/v1` manifest。
  - `TOOL.md` 内容。
  - `handler`、`tool_names`、`input_schema`、`output_schema`、`permissions`、`audit`、`ui.status`。
- 覆盖每个功能分类至少一个 `implemented` Tool：
  - 代码工具。
  - 文件与文档。
  - 网络与检索。
  - 数据处理。
  - 图像/多媒体。
  - 系统与终端。
- 覆盖 Tool projection 必须暴露 `tool-index.json`、`doc_path`、`manifest_path`。
- 扩展 `test_capability_container_projection.py`，覆盖 `.weagent/tools/<runtime_id>/TOOL.md` 和 `manifest.json` 写入。
- 扩展 `frontend/tests/toolset-ui-contract.test.js`，覆盖 Tool 状态、`TOOL.md` 文件视图和 handler 摘要。

## Verification

```powershell
python -m pytest tests\test_capability_tool_contract.py -q
python -m pytest tests\test_capability_container_projection.py::test_write_projection_creates_only_canonical_weagent_runtime_files -q
node tests\toolset-ui-contract.test.js
```

Result:

- `test_capability_tool_contract.py`: 2 passed.
- Container projection focused test: 1 passed.
- Toolset UI contract: passed.

## Notes

这些测试先在旧实现上失败，失败点正是旧内置 Tool 没有 `TOOL.md`、没有 `weagent.tool/v1` manifest、没有 `tool-index.json` 和代表 handler。
