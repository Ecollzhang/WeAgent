# CHECKPOINT-D: Runtime Gate and Audit Hardening

## Scope

确保 Tool 调用必须经过绑定、授权和状态检查，并继续写入统一 call record。

## Completed

- 更新 `ToolRegistry.call_from_agent()`：
  - capability-aware session 中，未绑定 Tool 会拒绝执行。
  - 权限不足会拒绝执行。
  - `deferred` / `requires_config` Tool 会拒绝执行。
  - 只有没有 `.weagent` projection 的 legacy session 才保留旧 fallback。
- 更新 `permissions_for_tool()`：
  - 覆盖新增 runtime tool name。
  - 包含代码搜索、文档读取、HTTP/API、CSV/JSON/SQLite、图像信息、Git 只读、受限命令。
- 更新 input/output summary：
  - 路径摘要。
  - 搜索 query 摘要。
  - 命令摘要。
  - URL 去 query 摘要。
  - 输出 keys、matches、findings、row_count、status_code、exit_code。
- 扩展 `test_capability_tool_audit.py`：
  - 未绑定 Tool 拒绝执行。
  - deferred Tool 拒绝执行并写入 failed call record。

## Verification

```powershell
python -m pytest tests\test_capability_tool_audit.py -q
```

Result:

- Tool audit suite passed as part of the 005 focused regression subset.

## Notes

这一步解决了旧逻辑里最危险的迁移期漏洞：有 projection 时不能再绕过 Agent capability binding 去调用 registry 中的任意基础工具。
