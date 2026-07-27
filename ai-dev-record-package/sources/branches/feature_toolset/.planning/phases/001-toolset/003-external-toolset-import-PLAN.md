# 003 External Toolset Import and Audit PLAN

## 执行原则

- 继续在 `feature/toolset` 上开发，远端目标为 `origin/feature/toolset`。
- 不回滚当前工作区已有模型配置、沙盒和工具集 UI 改动。
- 所有执行式 npx 导入必须进入 Docker import sandbox。
- 所有外部导入先 preview，后 confirm。
- 高风险允许专家 override，但必须记录审计日志。
- 实现困难时，Agent 版本策略 UI 回退为纯 pinned。

## Checkpoint A: 合同测试和模型骨架

目标：先锁住新功能的数据边界，避免后面 UI 和 sandbox 改动漂移。

任务：

- 新增后端测试覆盖：
  - import source parser 接受 `npx @scope/package`、`npx skills add owner/repo`。
  - parser 拒绝 `&&`、`;`、`|`、重定向、shell wrapper。
  - zip bundle scanner 拒绝路径穿越、敏感文件、二进制可执行。
  - audit engine 能推断 `network`、`run_command`、`use_secret`。
  - syntax checker 能报告 JS/Python/Shell/PowerShell 语法错误。
  - lexical scanner 能识别危险 token、secret pattern、路径逃逸。
  - illegal library/API scanner 能识别 `child_process`、`subprocess`、`os.system`、`eval`、`Function`、`requests`、`socket`、`fs.rm`。
  - illegal operation scanner 能识别 `rm -rf`、`curl | sh`、读取 `.env`、访问 `.ssh`、绝对路径写入、下载后执行。
- 新增模型：
  - `CapabilityVersionAsset`。
  - `CapabilityImportJob`。
  - `CapabilitySecurityAudit`。
- 更新 `backend/sql/init.sql` 和 app startup 轻量建表路径。
- 确保 `CapabilityVersion` checksum 纳入 assets 摘要。

验证：

```powershell
python -m pytest tests\test_capability_import_security.py tests\test_capability_assets.py
```

## Checkpoint B: 静态导入 Preview

目标：先不跑 npx，把 Markdown、zip、repo 静态扫描打通。

任务：

- 新增 import service：
  - `preview_markdown`
  - `preview_zip_bundle`
  - `preview_repo_static`
  - `confirm_import_job`
- repo source 支持：
  - `owner/repo`
  - `https://github.com/owner/repo`
- 扫描 Skill 路径：
  - `SKILL.md`
  - `*/SKILL.md`
  - `.codex/skills/*/SKILL.md`
  - `.claude/skills/*/SKILL.md`
  - `.agents/skills/*/SKILL.md`
  - `skills/*/SKILL.md`
- 识别 asset 路径：
  - `scripts/`
  - `references/`
  - `templates/`
  - `manifest.json`
- 生成 preview payload：
  - 候选 capabilities。
  - 文件树。
  - 审计报告。
  - 推断权限。

验证：

```powershell
python -m pytest tests\test_capability_import_preview.py
```

## Checkpoint C: 安全审计与专家模式

目标：实现可解释的风险报告和高风险二次确认。

任务：

- 实现 audit engine：
  - 文件路径规则。
  - 文件大小和数量限制。
  - 敏感文件规则。
  - 语法检查规则：
    - JS/MJS/TS 解析 import、require、call expression。
    - Python 使用 AST/compile 级检查。
    - Shell/PowerShell 做 best-effort parse，失败时降级到 token scan。
  - 词法扫描规则：
    - shell 控制符、命令替换、重定向。
    - secret/env/private key 关键词。
    - 路径穿越、绝对路径、Windows drive path。
  - 非法库/API 规则：
    - JS: `child_process`、`fs.rm`、`fs.unlink`、`eval`、`Function`、动态 import、网络 client。
    - Python: `subprocess`、`os.system`、`eval`、`exec`、`socket`、`requests`、`urllib`、`shutil.rmtree`。
    - Shell: `rm -rf`、`curl | sh`、`wget | sh`、`chmod +x` 后执行、后台服务启动。
  - 非法操作规则：
    - 删除或批量覆盖文件。
    - 读取 secret、token、ssh/private key。
    - 下载远程代码并执行。
    - 写入 workspace 外目录。
    - 启动长期运行服务或监听端口。
  - 权限推断。
  - 风险等级聚合。
  - 统一 audit item 输出：`category`、`severity`、`path`、`line`、`message`、`evidence`、`suggested_permission`。
- 检测引擎必须降级可用：
  - 语法解析器不可用时不跳过审计，至少执行 lexical scan。
  - 解析失败记录 `syntax` warning，并继续执行后续规则。
  - 扫描失败记录 audit error，不允许静默通过。
- 实现专家 override：
  - high risk confirm 必须带 `override_confirmed=true`。
  - 必须带 `override_reason`。
  - 可选要求前端确认文案，例如“我确认承担风险”。
- 保存 `CapabilitySecurityAudit`。
- 能力详情返回最新 audit 摘要。

验证：

```powershell
python -m pytest tests\test_capability_security_audit.py tests\test_capability_detection_engine.py
```

## Checkpoint D: Docker Import Sandbox 和 npx Preview

目标：把执行式安装器限制在一次性容器里。

任务：

- 新增 import sandbox manager，复用现有 Docker/sandbox 基础设施时保持隔离：
  - 临时 workspace。
  - 临时 `HOME`、`CODEX_HOME`、`CLAUDE_HOME`、`AGENTS_HOME`。
  - 超时。
  - 日志捕获。
  - 退出后扫描产物并清理。
- npx source 支持：
  - `npx skills add eze-is/web-access`
  - `npx @orchestra-research/ai-research-skills`
  - `npx <package>`
- 容器内基础安全检验：
  - 命令 allowlist。
  - 写入目录限制。
  - 产物扫描。
  - 审计报告。
- Docker 不可用时返回可展示错误：
  - npx 导入不可用。
  - Markdown/upload/repo static 仍可用。

验证：

```powershell
python -m pytest tests\test_capability_npx_import_sandbox.py
docker info
```

## Checkpoint E: Confirm 入库和 Assets 查询

目标：preview 通过用户确认后，创建正式能力和版本资产。

任务：

- 新增 API：
  - `POST /api/capabilities/import/preview`
  - `POST /api/capabilities/import/confirm`
  - `GET /api/capabilities/<id>/assets`
  - `GET /api/capabilities/<id>/audits`
- 扩展已有创建版本 API，使其支持 assets。
- confirm 时：
  - 按用户选择导入多个 capabilities。
  - 写入 `Capability`、`CapabilityVersion`、`CapabilityVersionAsset`。
  - 写入 `CapabilitySecurityAudit`。
  - 保留分类和权限声明。
- 高风险 confirm 缺少专家确认时拒绝。

验证：

```powershell
python -m pytest tests\test_capability_import_confirm.py tests\test_capability_api.py
```

## Checkpoint F: Runtime Projection 和 Asset Draft Sync

目标：让保存进 DB 的 bundle 在 Agent session 中真实可见，并允许 Agent 修改后走草稿。

任务：

- 扩展 `capability_projection_service`：
  - Skill record 包含 asset manifest。
  - Agent skill index 保持按授权过滤。
- 扩展 container `capabilities.py`：
  - 写出 `SKILL.md` 和 assets。
  - baseline 记录所有受控文件 checksum。
  - draft collect 检测 Markdown 和 asset diff。
- 扩展 draft sync：
  - 保存文件级 diff。
  - 发布前重新 audit。
  - 发布时创建新 version + assets。
- 高风险 draft 发布走专家 override。

验证：

```powershell
python -m pytest tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_capability_asset_drafts.py
```

## Checkpoint G: 工具集 UI 导入向导和文件视图

目标：让用户能实际导入、看文件、看审计、确认风险。

任务：

- 扩展 `frontend/src/api/capabilities.js`：
  - import preview。
  - import confirm。
  - assets。
  - audits。
- 改造 `Tools.vue`：
  - 新增上传 bundle、repo 导入、npx 导入入口。
  - 导入向导三步：来源、preview、confirm。
  - preview 展示候选能力、文件树、权限推断、安全审计。
  - 高风险二次确认。
  - 详情页新增文件和审计视图。
  - 内置 Tool 显示只读虚拟文件。
- 保持分类 + Skill/MCP/Plugin/Tool 展开方式不变。

验证：

```powershell
node tests\toolset-ui-contract.test.js
npm run build
```

## Checkpoint H: Agent 创建和编辑能力选择器

目标：让“先创建能力，再创建 Agent 勾选能力”闭环可用。

任务：

- 找到现有 Agent 创建和编辑页面入口。
- 新增“默认工具能力”选择器：
  - 分类筛选。
  - Skill/MCP/Plugin/Tool 分组。
  - 勾选能力。
  - 显示权限、版本、风险摘要。
  - 默认 pinned。
- 保存时调用现有 Agent capability binding API。
- 编辑页支持：
  - 新增能力。
  - 禁用/移除能力。
  - 手动升级版本。
- `follow_latest` 保留 API，不作为 UI 主路径。
- 若复杂度过高，UI 只实现 pinned 绑定和手动升级。

验证：

```powershell
node tests\agent-capability-selector-contract.test.js
python -m pytest tests\test_capability_api.py tests\test_capability_projection.py
```

## Checkpoint I: 端到端验证和回归

目标：确认导入、绑定、投影、审计、草稿和 UI 都走通。

手动 UAT：

1. 上传一个包含 `SKILL.md` 和 `scripts/check.mjs` 的 zip。
2. 在 preview 中看到文件树、权限推断和风险提示。
3. confirm 后在工具集页面看到 Skill。
4. 创建 Agent，勾选该 Skill 并授权权限。
5. 启动 session，确认 `.weagent/skills/<runtime_id>/scripts/check.mjs` 存在。
6. 在 workspace 中修改脚本，触发 draft sync。
7. 在平台看到草稿和重新审计报告。
8. 高风险草稿需要二次确认才能发布。
9. 内置 Tool 详情能看到虚拟文件视图。

自动验证：

```powershell
python -m pytest tests\test_capability_import_security.py tests\test_capability_detection_engine.py tests\test_capability_import_preview.py tests\test_capability_import_confirm.py tests\test_capability_assets.py tests\test_capability_asset_drafts.py tests\test_capability_projection.py tests\test_capability_api.py
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
npm run build
git diff --check
```

## 风险和回退

- Docker import sandbox 在 Windows 上可能启动慢：npx preview 允许异步 job 化，v1 至少返回明确 loading/error 状态。
- 外部包安装结果目录不统一：先扫描 `.codex/skills`、`.claude/skills`、`.agents/skills`、`skills` 和根目录。
- Orchestra 类 package 可能导入大量 skills：preview 必须支持多选，confirm 可以先默认全选但允许取消。
- Asset 草稿 diff 复杂：第一版可保存全量 proposed assets，同时展示 changed paths。
- Agent 版本策略复杂：UI 回退为 pinned + 手动升级。
- 高风险专家模式容易误用：前端必须展示风险原因，后端必须保存 override record。

## 开发顺序建议

1. 先做模型、审计、静态上传 preview。
2. 再做 confirm 入库和文件视图。
3. 再做 projection 和 asset draft。
4. 再接 Docker npx import sandbox。
5. 最后做 Agent 创建/编辑选择器和完整 UAT。

这样即使 npx sandbox 遇到 Docker 问题，Markdown/zip/repo 静态导入和 Agent 绑定也能先形成真实闭环。
