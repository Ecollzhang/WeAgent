# Checkpoint G Report: 工具集 UI 导入向导和文件视图

## 目标

让用户可以在工具集页面完成导入预览、审计查看、确认入库，并在能力详情里看到文件树和审计记录；内置 Tool 不再展示大段原始 manifest，而是展示只读虚拟文件和摘要。

## 已完成

- 扩展前端 API：
  - `previewCapabilityImport`
  - `confirmCapabilityImport`
  - `getCapabilityAssets`
  - `getCapabilityAudits`
- 补充后端 preview API 的 `upload` source：
  - 前端可把 `.zip` 读成 base64。
  - 后端解码后复用 `preview_zip_bundle`。
- 重写 `Tools.vue`：
  - 保留一级分类 + Skill/MCP/Plugin/Tool 四类展开。
  - 新增三步导入向导：选择来源、预览审计、确认入库。
  - 支持 Markdown、zip bundle、repo、本地 Docker npx preview。
  - preview 阶段展示候选能力、文件列表、风险等级、推断权限、风险项。
  - high risk confirm 阶段要求专家确认和原因。
  - confirm 成功后写入当前分类，并刷新选择新能力。
- 详情面板改为 Tab：
  - 概览
  - 文件
  - 安全审计
  - 版本
- 文件视图：
  - Skill 加载 `SKILL.md` 和 DB assets。
  - Tool 展示只读虚拟 `tool-definition.json` 和简化 `manifest.json`。
  - MCP/Plugin 展示 manifest 文件视图。
- 保留右侧详情关闭按钮。

## 验证

```powershell
node tests\toolset-ui-contract.test.js
node tests\capability-ui-contract.test.js
npm run build
```

结果：

- `toolset UI contract ok`
- `capability UI contract ok`
- `npm run build` 成功

补充后端 upload API 验证：

```powershell
python -m pytest tests\test_capability_import_confirm.py
```

结果：

- `5 passed`

## 注意事项

- repo preview 当前仍使用后端可访问的本地路径扫描，不在前端直接 clone GitHub。
- npx preview 依赖 Docker import sandbox；Docker 不可用时会返回后端错误，静态 Markdown/upload/repo 不受影响。
- 前端 build 仍有既有 asset size 警告，未在本 checkpoint 中处理。
