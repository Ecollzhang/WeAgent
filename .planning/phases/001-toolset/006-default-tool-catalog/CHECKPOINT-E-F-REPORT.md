# Checkpoint E/F Report: Runtime Projection and Configured Tool Adapters

日期：2026-06-02

## 目标

让配置通过并启用的 Tool 能被 Agent 绑定、投影到 `.weagent/*`、在 sandbox 中调用，并写入调用记录。

## 已完成

### Runtime Projection

- `capability_projection_service` 会为绑定 Agent 查询当前用户的 `valid` provider profile。
- 对 `requires_config` Tool：
  - 没有 `valid` profile 时不可绑定，不进入运行视图。
  - 有 `valid` profile 并绑定后，runtime status 投影为 `implemented`。
- Agent 视图中的 `capabilities.json` 和 `tool-index.json` 包含：
  - `status`
  - `tool_names`
  - `handler`
  - 非敏感 `provider_config`
- `.weagent/tools/<runtime_id>/manifest.json` 也包含运行态 status 和 provider profile 摘要。
- `secret_refs` 不写入 projection，避免进入 `.weagent/*`。

### Sandbox Gate

- `resolve_bound_tool_capability()` 优先读取 Agent 视图中的 runtime status。
- `ToolRegistry.call_from_agent()` 会把 `provider_config` 注入到配置型 Tool adapter。
- 未绑定或权限不足仍然返回结构化错误，并写入 failed call record。

### Configured Tool Adapters

新增四个 deterministic runtime adapter：

- `web_search`
  - 需要 `http` provider。
  - 运行时调用配置的 HTTP endpoint，并按 `q` 和 `limit` 拼接查询参数。
  - 支持 JSON `results` 返回。
- `image_analysis`
  - 需要 `model` 或可投影 provider。
  - 读取 workspace 图片 metadata，返回确定性分析摘要。
- `image_generate`
  - 需要启用 profile。
  - 写入确定性 1x1 PNG 到 workspace，验证写入路径和 call record。
- `database_query`
  - 需要 `database` provider。
  - v1 sandbox fixture 支持 SQLite 只读查询。
  - 继续复用只读 SQL gate，只允许 SELECT 和 PRAGMA table_info。

### 权限映射

新增 Tool runtime name 和 permission usage：

- `web_search`: `network`
- `image_analysis`: `read_workspace`
- `image_generate`: `write_workspace`
- `database_query`: `read_workspace`、`use_secret`

## 验证结果

通过：

```powershell
python -m pytest tests\test_configured_tool_runtime_gate.py -q
```

结果：1 passed。

该测试覆盖：

- 本地 HTTP 搜索 fixture。
- workspace SQLite fixture。
- workspace PNG fixture。
- 四个 configured Tool 绑定。
- `.weagent/*` projection。
- sandbox `ToolRegistry.call_from_agent()`。
- `calls.jsonl` 中 4 条 completed call record。
- projection 不泄露测试 secret alias。

通过：

```powershell
python -m pytest tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_builtin_tool_handlers.py -q
```

结果：8 passed。

通过 006 后端组合：

```powershell
python -m pytest tests\test_capability_models.py tests\test_capability_service.py tests\test_capability_api.py tests\test_capability_projection.py tests\test_capability_tool_audit.py tests\test_default_tool_catalog.py tests\test_tool_provider_config_api.py tests\test_configured_tool_runtime_gate.py -q
```

结果：35 passed。

## 当前边界

- `image_analysis` 和 `image_generate` 是 deterministic sandbox adapter，不直接调用真实外部模型。
- `database_query` 的真实 Docker smoke 先覆盖 SQLite fixture；MySQL/Postgres 外部连接需要后续 provider driver 和 secret vault。
- `web_search` 支持 HTTP provider endpoint，真实搜索服务需要用户提供兼容 endpoint。
