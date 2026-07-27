# CHECKPOINT-H: Integration Regression and Cleanup

## Scope

确认 005 的内置 Tool runtime 改造没有破坏 001/002/003 已经完成的能力库、工具集分类、Agent 绑定、sandbox projection、MCP runtime 以及前端构建路径。

## Completed

- 回归后端能力库与工具集分类：
  - Capability API 的 list/create/import/delete/bind/unbind 相关测试仍通过。
  - Toolset category counts、archived 能力不计数、分类展示契约仍通过。
  - Agent 能力绑定中的 Skill/MCP/Plugin/Tool peer model 仍通过。
- 回归 sandbox projection 与 runtime gate：
  - Skill projection 保持兼容。
  - MCP runtime 相关测试仍通过。
  - Tool projection 新增 `.weagent/tools/<runtime_id>/TOOL.md`、`manifest.json`、Agent 级 `tool-index.json`。
  - capability-aware session 中未绑定 Tool 与 deferred/requires_config Tool 会被拒绝执行。
- 回归前端契约：
  - 工具集页面能够显示 Tool status、handler、`TOOL.md` 文档视图。
  - Agent 创建/编辑能力选择器 contract 仍通过。
- 清理状态表达：
  - `web_search`、`database_query` 标记为 `requires_config`。
  - `code_generator`、`image_analysis` 标记为 `deferred`。
  - 已实现 Tool 在 manifest 与 UI 中带 `implemented` 状态。

## Verification

```powershell
python -m pytest tests\test_capability_tool_contract.py tests\test_builtin_tool_handlers.py tests\test_capability_container_projection.py tests\test_capability_tool_audit.py tests\test_toolset_categories.py tests\test_capability_projection.py tests\test_capability_api.py tests\test_capability_mcp_runtime.py -q
```

Result:

- 38 passed.

```powershell
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
```

Result:

- Toolset UI contract: passed.
- Agent capability selector contract: passed.

```powershell
npm run build
```

Result:

- Build completed successfully.
- Existing asset-size warnings remain for `bg.d0047cc4.png` and `chunk-vendors.aad3cdea.js`.

```powershell
git diff --check
```

Result:

- No whitespace errors reported.
- Git reported expected LF-to-CRLF working-copy warnings on Windows.

## Remaining

- Checkpoint G 的真实 Docker runtime smoke 已执行并记录在 `CHECKPOINT-G-REPORT.md`。前端人工 UAT 路径仍可按 `REAL-TOOL-UAT-GUIDE.zh-CN.md` 继续做页面级检查。
- `database_query` 与 `web_search` 仍需要后续接入 provider/MCP/配置后才能从 `requires_config` 进入 `implemented`。
- `code_generator` 与 `image_analysis` 暂不冒充真实能力，后续应接模型能力或 MCP 后再开放调用。
