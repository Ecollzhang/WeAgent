# CHECKPOINT-G: Docker UAT Guide and Real Sandbox Smoke

## Scope

完成 005 的真实 Docker sandbox smoke：验证新的内置 Tool runtime 不只在 host 单元测试中可用，也能在 `weagent-sandbox:latest` 镜像中通过 `.weagent` projection、Agent 级权限视图和 call record 链路执行。

## Completed

- 写入中文验收指南：
  - `REAL-TOOL-UAT-GUIDE.zh-CN.md`
- 写入可复用 Docker smoke 脚本：
  - `docker-smoke/smoke_tool_runtime.py`
- 重建 `weagent-sandbox:latest` 镜像。
- 修复真实 Docker smoke 暴露的问题：
  - sandbox 镜像原本没有安装 `git`，导致 `git_status/git_diff/git_log` 在真实容器内不可用。
  - 已更新 `backend/app/sandbox/Dockerfile`，在基础工具层安装 `git`。
- 在真实 Docker 容器中验证：
  - `.weagent/tools/<runtime_id>/TOOL.md` 写入。
  - `.weagent/agents/<agent_id>/tool-index.json` 写入。
  - 代码、文件/文档、网络/API、数据、图像、终端、Git 分类代表 Tool 可执行。
  - 权限不足调用被拒绝。
  - `deferred` Tool 被拒绝。
  - 成功和失败调用都写入 JSONL call record。

## Commands

```powershell
docker info --format '{{json .ServerVersion}}'
```

Result:

- Docker daemon ready: `29.5.2`

```powershell
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

Result:

- First rebuild after adding `git` hit Debian apt `502 Bad Gateway`.
- Retried build succeeded.
- New image was exported as `weagent-sandbox:latest`.

```powershell
$script=(Resolve-Path '.planning\phases\001-toolset\005-builtin-tool-runtime\docker-smoke\smoke_tool_runtime.py').Path
docker run --rm -v "${script}:/tmp/smoke_tool_runtime.py:ro" weagent-sandbox:latest python /tmp/smoke_tool_runtime.py
```

Result:

```json
{
  "status": "ok",
  "record_count": 17,
  "completed_records": 15,
  "failed_records": 2,
  "tool_index": "/workspace/.weagent/agents/uat-agent/tool-index.json"
}
```

## Tool Coverage

Successful calls:

- `code_search`
- `code_review_scan`
- `write_file`
- `read_file`
- `list_files`
- `document_text_extract`
- `http_fetch`
- `api_request`
- `csv_profile`
- `json_query`
- `sqlite_query_readonly`
- `image_info`
- `run_command_safe`
- `git_status`
- `git_log`

Expected failures:

- `limited-agent` calling `write_file` without `write_workspace` grant.
- `uat-agent` calling deferred `code_generator`.

## Notes

- This smoke intentionally avoids invoking Claude/model APIs. It tests the sandbox image, Tool runtime, projection, permission gate and audit records without making model availability part of the Tool runtime acceptance.
- The full front-end manual UAT path is still documented in `REAL-TOOL-UAT-GUIDE.zh-CN.md` for human inspection of cards, binding UI and file tree. The Docker runtime portion is now verified by command evidence above.
