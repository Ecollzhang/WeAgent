# Checkpoint I Report: 端到端验证和回归

## 目标

确认 003 阶段的导入、审计、入库、资产、projection、草稿、Agent 默认绑定和前端入口没有破坏既有能力。

## 自动化验证

### 后端

```powershell
python -m pytest tests\test_capability_import_security.py tests\test_capability_detection_engine.py tests\test_capability_import_preview.py tests\test_capability_import_confirm.py tests\test_capability_assets.py tests\test_capability_asset_drafts.py tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_capability_security_audit.py tests\test_capability_npx_import_sandbox.py tests\test_capability_skill_draft_sync.py tests\test_capability_api.py
```

结果：

- `50 passed`

覆盖内容：

- npx allowlist parser
- bundle path/security scanner
- 语法、词法、非法库/API、非法操作检测
- Markdown / zip / repo / npx preview
- high risk 专家 override
- confirm 入库和 asset 查询
- runtime projection
- asset draft diff 和 publish
- Agent capability binding API
- Tool/MCP/Skill/Plugin peer model 回归

### 前端

```powershell
node tests\toolset-ui-contract.test.js
node tests\capability-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
node tests\toolset-regression-contract.test.js
npm run build
```

结果：

- `toolset UI contract ok`
- `capability UI contract ok`
- `agent capability selector contract ok`
- `toolset regression contract ok`
- `npm run build` 成功

### Diff 检查

```powershell
git diff --check
```

结果：

- 无 whitespace error。
- 仅输出 Windows 工作区既有 LF/CRLF 转换 warning。

## 已知限制

- 未进行浏览器人工 UAT；本轮完成了 Vue build 和契约测试。后续建议在 Docker 环境中手动走一遍：zip preview -> confirm -> Agent 绑定 -> session projection -> 修改脚本生成 draft。
- 前端 build 仍有既有 asset size warning：`img/bg...png` 和 `chunk-vendors...js` 过大。
- SQLAlchemy legacy/deprecation warnings 和 Flask-SQLAlchemy drop cycle warning 是既有噪声，本阶段未处理。
- `.planning/STATE.md.lock` 仍是 untracked 文件，创建时间早于本轮；没有在本阶段删除。

## 结论

003 阶段的核心闭环已经落地：外部导入先 preview/audit，再 confirm 入库；Skill bundle assets 可以保存、投影、被 Agent 修改为草稿并在发布前重新审计；工具集页面和 Agent 创建/编辑页都已经接入新的能力库工作流。
