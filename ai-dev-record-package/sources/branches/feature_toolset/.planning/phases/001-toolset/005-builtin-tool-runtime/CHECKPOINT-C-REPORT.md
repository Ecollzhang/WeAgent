# CHECKPOINT-C: Tool Runtime Projection and Progressive Disclosure

## Scope

让 Tool 像 Skill 一样进入 `.weagent/*` runtime projection，但采用轻量 `tool-index.json` + 按需读取 `TOOL.md` 的渐进式披露。

## Completed

- 更新 `backend/app/services/capability_projection_service.py`：
  - `_tool_record()` 输出 `content`、`doc_path`、`manifest_path`、`tool_names`、`handler`、`status`。
  - Agent view 新增 `tool_index`。
  - Agent bootstrap 中加入 Tool index 路径。
- 更新 `backend/app/sandbox/container/capabilities.py`：
  - 写入 `.weagent/tools/<runtime_id>/TOOL.md`。
  - 写入 `.weagent/tools/<runtime_id>/manifest.json`。
  - 写入 `.weagent/agents/<agent_id>/tool-index.json`。
  - `agent_bootstrap_instruction()` 提示读取 Tool index。
- 更新 `backend/app/sandbox/container/orchestrator.py`：
  - Prompt 优先展示当前 Agent 绑定的 Tool index。
  - 不再把 registry 中所有工具无条件当成当前 Agent 可用工具展示。
  - 指示 Agent 需要更多说明时读取 `TOOL.md`。

## Verification

```powershell
python -m pytest tests\test_capability_tool_contract.py tests\test_capability_container_projection.py tests\test_capability_projection.py -q
```

Result:

- Contract/projection 相关测试通过。

## Notes

`TOOL.md` 是 Agent-facing 使用说明；系统执行仍只信 manifest、handler、权限和 binding。
