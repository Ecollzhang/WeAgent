# CHECKPOINT-E: First Implemented Tool Set by Category

## Scope

为每个功能分类落地至少一个真实可调用 Tool，并把不适合 v1 的项标为 `requires_config` 或 `deferred`。

## Implemented Tools

代码工具:

- `code_search`
- `code_review_scan`

文件与文档:

- `read_file`
- `write_file`
- `list_files`
- `document_text_extract`

网络与检索:

- `http_fetch`
- `api_request`
- `web_search` 标为 `requires_config`

数据处理:

- `csv_profile`
- `json_query`
- `sqlite_query_readonly`
- `database_query` 标为 `requires_config`

图像/多媒体:

- `image_info`
- `image_analysis` 标为 `deferred`

系统与终端:

- `run_command_safe`
- `git_status`
- `git_diff`
- `git_log`
- `report_progress`

自定义:

- 不强塞平台内置执行 Tool；继续作为用户自建/导入 Tool 容器。

## Verification

```powershell
python -m pytest tests\test_builtin_tool_handlers.py -q
python -m pytest tests\test_capability_tool_contract.py -q
```

Result:

- Built-in handler tests: 2 passed.
- Tool contract tests: 2 passed.

## Notes

`code_generator`、通用 `web_search`、外部 `database_query`、AI `image_analysis` 这类能力没有被假装成已实现 Tool。它们仍可作为目录项存在，但必须显示真实状态。
