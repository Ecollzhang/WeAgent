# 003 External Toolset Import and Audit SPEC

## 背景

当前工具集已经完成基础能力库：`Skill`、`MCP`、`Plugin`、`Tool` 作为并行能力类型保存到 DB，并能按分类展示、绑定到 Agent、在 session sandbox 中投影到 `.weagent/*`。

新的目标是让工具集从“只能手写 Markdown / 粘贴 manifest”升级为真实可用的外部导入和本地 bundle 管理：

- 用户可以先创建或导入工具能力，再创建 Agent 时勾选绑定。
- 外部导入支持 GitHub repo、`npx skills add ...`、`npx @scope/package` 这类 installer 包。
- Skill 不再只有 `SKILL.md`，还可以携带 `scripts/`、`references/`、`templates/` 等文件。
- 导入、上传、Agent 修改脚本时都必须经过安全审计；高风险允许专家模式强制发布，但必须二次确认并记录日志。

## 已确认决策

- v1 主模式是能力库模式：先创建单个 Skill/MCP/Plugin/Tool，再在 Agent 创建/编辑页勾选绑定。
- 批量工具集组合不是本阶段必做项，只预留批量选择入口。
- Agent 创建和编辑都支持默认能力绑定。
- API 支持 `pinned` 和 `follow_latest`，UI v1 默认只暴露固定版本和手动升级；实现困难时回退到纯固定版本。
- Markdown、上传 bundle、repo 静态扫描不强依赖 Docker。
- 执行式 npx 导入必须在 Docker import sandbox 中完成，并在容器内做基础安全检验。
- 上传 bundle v1 支持 `.md`、包含单个 `SKILL.md` 的 `.zip`、包含多个 `*/SKILL.md` 的 `.zip`；不支持 `tar.gz`、`node_modules`、二进制可执行文件。
- Agent 可以修改 runtime 副本里的 `SKILL.md` 和附属文件；同步回 DB 前必须形成草稿、重新审计、用户确认。
- 高风险审计项采用专家模式：允许强制发布，但需要二次确认并记录审计日志。

## 目标

1. 支持从 repo、npx installer、Markdown、zip bundle 导入 Skill bundle。
2. 支持 Skill 版本保存 `SKILL.md` 以外的附属文件，并在 UI 中以文件树查看。
3. 支持导入预览：扫描能力、文件树、权限推断、安全审计报告。
4. 支持导入确认：用户选择要导入的能力，高风险时二次确认后入库。
5. 支持 Agent 创建/编辑时按分类勾选能力，并保存为 Agent 默认绑定。
6. 支持 `.weagent/skills/<runtime_id>/...` 写出完整 bundle 文件。
7. 支持 Agent 修改 Skill bundle 文件后生成待审核草稿，并在发布前重新审计。
8. 内置 Tool 在详情中也提供统一的只读文件视图。

## 非目标

- 本阶段不实现保存命名的“工具集组合/Profile”。
- 本阶段不开放任意 shell/npx 命令执行。
- 本阶段不把外部导入结果自动绑定到 Agent。
- 本阶段不执行导入 Skill 自带脚本，只保存、扫描、审计和投影。
- 本阶段不保存 `node_modules`、二进制可执行文件或完整包缓存。
- 本阶段不生成 `.claude/*`、`.codex/*` 兼容映射；仍然只写 `.weagent/*`。
- 本阶段不实现完整 Plugin runtime；Plugin 仍以 manifest 和安装记录为主。

## 需求

### R-016: 外部导入采用两阶段流程

**当前状态：** 只有 Markdown 导入和 npx manifest 粘贴导入，没有外部 package 预览和确认流程。

**目标状态：** 所有 repo/npx/upload bundle 导入先创建 preview，返回可导入能力、文件树、权限推断、审计报告；用户确认后才写入 DB。

**验收标准：**
- `POST /api/capabilities/import/preview` 对合法输入返回 `import_job_id`、`capabilities`、`files`、`audit`。
- `POST /api/capabilities/import/confirm` 只接受有效 preview job，并写入选中的能力。
- 未确认的 preview 不创建正式 `Capability`。

### R-017: 执行式 npx 导入必须使用 Docker import sandbox

**当前状态：** MCP npx runtime 在 session sandbox 内执行；工具集导入本身还不支持执行式 npx installer。

**目标状态：** `npx skills add <source>`、`npx @scope/package`、`npx package` 只在一次性 Docker import sandbox 内执行。容器内设置临时 `HOME`、`CODEX_HOME`、`CLAUDE_HOME`、`AGENTS_HOME`，执行后扫描产物并销毁。

**验收标准：**
- Docker 不可用时，npx 执行式导入返回明确错误，Markdown/upload 静态导入不受影响。
- npx 导入不能写入宿主机真实 Codex/Claude/Agents 目录。
- 导入日志记录命令、退出码、超时、扫描目录和错误摘要。

### R-018: npx 命令必须通过允许列表解析

**当前状态：** 没有 npx installer 导入入口。

**目标状态：** 后端只接受结构化 source，而不是任意 shell 字符串；允许 `npx skills add <source>` 和 `npx <package>`。禁止管道、重定向、命令连接符、shell 包裹和任意参数注入。

**验收标准：**
- `npx @orchestra-research/ai-research-skills` 被解析为合法 package installer。
- `npx skills add eze-is/web-access` 被解析为合法 skills CLI installer。
- 包含 `&&`、`;`、`|`、`>`、`<`、PowerShell/cmd 包裹的输入被拒绝。

### R-019: Skill 版本支持附属文件资产

**当前状态：** `CapabilityVersion.content` 只能保存主要 Markdown，无法保存 `scripts/`、`references/`、`templates/`。

**目标状态：** 新增版本资产模型，保存相对路径、内容、大小、checksum、文件类型和审计状态。`SKILL.md` 仍作为主内容，附属文件作为 assets 归属于版本。

**验收标准：**
- 导入含 `scripts/check.mjs` 的 Skill 后，DB 中能查到该 asset。
- 版本 checksum 覆盖 `SKILL.md` 与 assets。
- 删除旧版本不会影响其他版本的 assets。

### R-020: 上传 bundle 支持 Markdown 与 zip

**当前状态：** 前端只支持读取单个 Markdown 文件。

**目标状态：** 用户可上传 `.md` 或 `.zip`；zip 内可包含一个或多个 `SKILL.md`，以及 `scripts/`、`references/`、`templates/`。上传后进入 preview 审计。

**验收标准：**
- 单个 `.md` 作为一个 Skill preview。
- 单个 `SKILL.md` zip 作为一个 Skill preview。
- 多个 `*/SKILL.md` zip 返回多个 Skill preview。
- `node_modules`、二进制可执行文件、路径穿越文件被拒绝或标记阻断。

### R-021: 安全审计必须输出风险等级和权限推断

**当前状态：** 权限由用户或 manifest 声明，没有统一审计报告。

**目标状态：** 导入、上传、草稿发布前都运行审计，输出 `risk_level`、`risk_items`、`blocking_items`、`inferred_permissions`、`scanned_files`。

**验收标准：**
- 脚本中出现网络请求时推断 `network`。
- 脚本中出现 shell/subprocess/child_process 时推断 `run_command`。
- 脚本中访问 env/secret/private key 时推断 `use_secret` 并产生高风险项。
- 审计结果随导入版本或草稿发布记录保存。

### R-030: 检测引擎必须包含语法、词法、非法库和非法操作检查

**当前状态：** 计划中已有“脚本文本规则”和“安全审计”，但没有明确拆分语法检查、词法扫描、非法库/API 扫描和非法操作扫描。

**目标状态：** 导入、上传、草稿发布前的 audit engine 必须按层输出检测结果：

- 语法检查：对 `.js`、`.mjs`、`.ts`、`.py`、`.sh`、`.ps1` 做 best-effort parse 或 compile 检查。
- 词法扫描：按 token/keyword 识别危险关键字、shell 操作符、路径模式、secret 模式。
- 非法库/API 扫描：识别危险 import、require、module、function call。
- 非法操作扫描：识别删除文件、读密钥、远程下载执行、写出 workspace 外路径、启动服务等行为。
- 结果汇总：每一条检测命中都输出 `category`、`severity`、`path`、`line`、`message`、`evidence`、`suggested_permission`。

**验收标准：**
- 语法错误脚本会产生 `syntax` 类 audit item，但不导致整个 preview 崩溃。
- `child_process`、`subprocess`、`os.system`、`eval`、`Function`、`socket`、`requests`、`fs.rm` 等危险库/API 会产生 `illegal_library` 或 `dangerous_api` 项。
- `rm -rf`、`curl ... | sh`、读取 `.env`、访问 `.ssh`、写绝对路径、下载后执行会产生 `illegal_operation` 或 high risk 项。
- 检测项能映射到 `network`、`run_command`、`write_workspace`、`use_secret`、`start_service` 等推断权限。
- 检测失败时返回降级提示，而不是跳过安全审计。

### R-022: 专家模式允许高风险强制发布

**当前状态：** 没有高风险导入确认流程。

**目标状态：** 高风险 preview 或草稿默认要求二次确认；用户输入确认文案并提交 override reason 后可以发布。系统记录审计日志。

**验收标准：**
- 高风险 confirm 缺少二次确认时失败。
- 二次确认成功后能力可以入库，但 audit record 标记 `overridden=true`。
- 审计日志记录 user、source、risk items、override reason、confirmed_at。

### R-023: Agent 修改 Skill bundle 后生成草稿

**当前状态：** 只检测 `SKILL.md` 的 runtime 改动并同步为 `SkillRevisionDraft`。

**目标状态：** 检测 `SKILL.md` 和允许的 asset 文件改动，生成包含文件 diff、审计报告和完整新版本内容的草稿。发布草稿时创建新 `CapabilityVersion` 和 assets。

**验收标准：**
- Agent 修改 `scripts/foo.py` 后，平台能看到 pending draft。
- 发布前重新审计；高风险变更需要专家确认。
- 未发布草稿不修改用户库 latest version。

### R-024: Runtime projection 写出完整 Skill bundle

**当前状态：** session sandbox 只写 `SKILL.md`、manifest 和 baseline。

**目标状态：** 绑定 Agent 后，`SKILL.md` 和 assets 都写到 `.weagent/skills/<runtime_id>/...`；Agent 视图仍通过 `.weagent/agents/<agent_id>/skill-index.json` 和 `capabilities.json` 隔离权限。

**验收标准：**
- 含 `scripts/` 的 Skill 绑定 Agent 后，session workspace 中能看到对应文件。
- Agent 只能通过自己的 skill index 看到被授权能力。
- baseline 记录覆盖所有受控文件，用于后续 draft diff。

### R-025: 工具集 UI 提供文件树和审计视图

**当前状态：** 详情页主要展示 Markdown 或 manifest 摘要。

**目标状态：** 能力详情增加文件树、审计报告、版本信息；内置 Tool 也显示只读虚拟文件，例如 `manifest.json` 和 `tool-definition.json`。

**验收标准：**
- Skill bundle 能在 UI 查看 `SKILL.md`、`scripts/`、`references/`。
- 审计 Tab 显示风险等级、风险项、权限推断和 override 记录。
- 内置 Tool 详情不展示原始大段 manifest，而是以文件视图和摘要展示。

### R-026: Agent 创建和编辑页支持能力勾选

**当前状态：** 能力数据和 Agent binding API 已存在，但工具集选择器还未统一进入 Agent 创建/编辑体验。

**目标状态：** 创建 Agent 和编辑 Agent 都提供“默认工具能力”选择器，按分类展开，再按 Skill/MCP/Plugin/Tool 展示可勾选项。保存时默认使用 pinned 版本和显式权限授权。

**验收标准：**
- 新 Agent 创建时可勾选 Skill/Tool/MCP/Plugin 并保存 bindings。
- 已有 Agent 编辑时可新增、禁用、移除、手动升级能力版本。
- 创建/编辑保存后的 session projection 使用 Agent 的默认绑定。

### R-027: 版本策略 API 保留双模式，UI 默认固定版本

**当前状态：** API 已支持 `pinned` 与 `follow_latest`，但 UI 仍需收敛产品行为。

**目标状态：** API 保留两种策略；UI v1 默认固定当前版本，只提供手动升级提示。如果实现成本过高，UI 和 API 调用都回退到 pinned。

**验收标准：**
- Agent binding 默认 `version_policy=pinned`。
- 有新版本时编辑页能看到可升级提示。
- 手动升级会更新 binding 的 `capability_version_id`。

### R-028: Repo 静态导入不执行脚本

**当前状态：** 没有 repo 导入。

**目标状态：** GitHub repo 导入优先走静态下载/clone 和扫描，不执行 repo 中脚本。repo 可识别根目录 `SKILL.md`、多目录 `*/SKILL.md`、`.codex/skills/*/SKILL.md`、`.claude/skills/*/SKILL.md`、`.agents/skills/*/SKILL.md`。

**验收标准：**
- `eze-is/web-access` 可作为 repo source 进入 preview。
- repo 中的脚本不会在 preview 阶段执行。
- 未发现 `SKILL.md` 时返回可理解的错误。

### R-029: 导入和审计记录可追溯

**当前状态：** Plugin 有 install record，Skill/外部导入没有统一导入审计记录。

**目标状态：** 导入来源、命令、repo、package、版本、checksum、审计结果、用户确认行为都可追溯。

**验收标准：**
- 能力详情能看到 source、source_ref、import job 或 audit record。
- 高风险 override 可被查询。
- 测试可断言导入记录与 capability version 关联。

## 安全策略

### 允许的导入输入

- Markdown 文本或 `.md` 文件。
- `.zip` bundle，内部包含 `SKILL.md` 或多个 `*/SKILL.md`。
- GitHub repo 简写或 URL，例如 `eze-is/web-access`、`https://github.com/eze-is/web-access`。
- `npx skills add <source>`。
- `npx <package>`，例如 `npx @orchestra-research/ai-research-skills`。

### 阻断规则

- 路径穿越：`..`、绝对路径、Windows drive path。
- 敏感文件：`.env`、`.ssh`、`id_rsa`、`*.pem`、`*.key`、token 文件。
- 二进制可执行：`.exe`、`.dll`、`.so`、`.dylib`、`.bat`、`.cmd`。
- 包缓存：`node_modules`、`.git`、大型 lock/cache 目录。
- 命令注入：`;`、`&&`、`||`、`|`、`>`、`<`、shell wrapper。
- 文件数量、单文件大小、总大小超过配置限制。

### 风险提示规则

- 低风险：只有 Markdown/reference/template，无脚本或敏感模式。
- 中风险：包含脚本、写文件、访问网络、启动服务等能力迹象。
- 高风险：读取 secret/env、远程下载并执行、删除大量文件、访问 ssh/private key、动态执行 eval、任意 shell 拼接。

### 检测引擎分层

审计引擎按以下层级执行，并把每一层结果合并成统一 audit report：

1. 语法检查
   - JavaScript / MJS / TypeScript：解析 import、require、call expression；解析失败记为 `syntax` warning。
   - Python：使用 AST/compile 级检查；解析失败记为 `syntax` warning。
   - Shell / PowerShell：做 best-effort parse；无法完整解析时至少执行 token scan。
2. 词法扫描
   - 识别 shell 控制符：`;`、`&&`、`||`、`|`、重定向、命令替换。
   - 识别 secret/env 关键词：`API_KEY`、`TOKEN`、`SECRET`、`.env`、`.ssh`、`id_rsa`。
   - 识别路径逃逸：`..`、绝对路径、Windows drive path。
3. 非法库/API 扫描
   - JavaScript：`child_process`、`fs.rm`、`fs.unlink`、`eval`、`Function`、动态 import、网络 client。
   - Python：`subprocess`、`os.system`、`eval`、`exec`、`socket`、`requests`、`urllib`、`shutil.rmtree`。
   - Shell：`rm -rf`、`curl | sh`、`wget | sh`、`chmod +x` 后执行、后台服务启动。
4. 非法操作扫描
   - 删除或批量覆盖文件。
   - 读取 secret、token、ssh/private key。
   - 下载远程代码并执行。
   - 写入 workspace 外目录。
   - 启动长期运行服务或监听端口。
5. 风险聚合
   - 低风险：没有脚本或只含文档资源。
   - 中风险：需要 `network`、`write_workspace`、`run_command` 但未触发高风险模式。
   - 高风险：触发 secret 读取、远程下载执行、批量删除、workspace 外写入、任意 eval/shell 拼接。

所有检测规则都必须是可测试的 fixture，而不是只在 UI 文案中描述。

### 专家模式

高风险导入或发布不会直接阻断最终保存，但必须满足：

- 前端展示具体高风险项。
- 用户二次确认并填写 override reason。
- 后端记录 audit override。
- 后续绑定 Agent 时仍然必须显式授权权限。

## 数据模型

新增或扩展模型：

- `CapabilityVersionAsset`
  - `capability_version_id`
  - `path`
  - `kind`: `skill_md` / `script` / `reference` / `template` / `manifest` / `virtual`
  - `content`
  - `size`
  - `sha256`
  - `mime_type`
  - `meta`
- `CapabilityImportJob`
  - `user_id`
  - `source_type`: `markdown` / `upload` / `repo` / `npx`
  - `source_ref`
  - `status`: `previewed` / `confirmed` / `failed` / `expired`
  - `preview_payload`
  - `audit_summary`
  - `expires_at`
- `CapabilitySecurityAudit`
  - `user_id`
  - `capability_id nullable`
  - `capability_version_id nullable`
  - `import_job_id nullable`
  - `draft_id nullable`
  - `risk_level`
  - `risk_items`
  - `blocking_items`
  - `inferred_permissions`
  - `overridden`
  - `override_reason`
  - `confirmed_at`

扩展 `SkillRevisionDraft`：

- 支持文件级 diff。
- 保存 proposed assets 摘要。
- 关联审计报告。

## API

新增建议端点：

- `POST /api/capabilities/import/preview`
  - 输入 `source_type`、`source_ref`、`upload` 或结构化 npx source。
  - 返回 import job、候选能力、文件树、审计报告。
- `POST /api/capabilities/import/confirm`
  - 输入 `import_job_id`、选中的 capability ids、分类、权限确认、高风险 override。
  - 输出正式创建的 capabilities。
- `GET /api/capabilities/<id>/assets`
  - 返回 latest 或指定 version 的文件树。
- `GET /api/capabilities/<id>/audits`
  - 返回导入与发布审计记录。
- `GET /api/agents/<agent_id>/capabilities/upgrades`
  - 继续用于手动升级提示。

已有端点扩展：

- `POST /api/capabilities/skills` 支持带 assets 创建。
- `POST /api/capabilities/<id>/versions` 支持带 assets 创建，并触发审计。
- `POST /api/capabilities/drafts/<draft_id>/publish` 支持资产草稿和高风险 override。

## UI

### 工具集页面

保留一级分类，再按 `Skill / MCP / Plugin / Tool` 展开。

新增导入入口：

- 新建 Skill。
- 导入 Markdown。
- 上传 Skill Bundle。
- Repo 导入。
- npx 导入。

新增详情 Tab：

- 概览。
- 权限。
- 文件。
- 安全审计。
- 调用记录。
- 版本。

### 导入向导

导入向导分三步：

1. 选择来源：Markdown、zip、repo、npx。
2. Preview：展示发现的能力、文件树、权限推断、风险报告。
3. Confirm：选择导入项、分类、权限声明；高风险时二次确认。

### Agent 创建/编辑页

新增“默认工具能力”区块：

- 左侧按分类筛选。
- 中间按 Skill/MCP/Plugin/Tool 分组勾选。
- 右侧显示选中能力、版本、权限和风险摘要。
- 默认固定当前版本。
- 编辑页显示可升级提示并允许手动升级。

## Runtime Projection

Skill bundle 投影到：

```text
.weagent/skills/<runtime_id>/SKILL.md
.weagent/skills/<runtime_id>/scripts/...
.weagent/skills/<runtime_id>/references/...
.weagent/skills/<runtime_id>/templates/...
.weagent/skills/<runtime_id>/manifest.json
.weagent/drafts/skills/<runtime_id>/baseline.json
```

Agent 视图仍为：

```text
.weagent/agents/<agent_id>/capabilities.json
.weagent/agents/<agent_id>/skill-index.json
.weagent/agents/<agent_id>/permissions.json
```

内置 Tool 文件视图为虚拟只读文件：

```text
manifest.json
tool-definition.json
```

## 验收标准总表

- [ ] repo source 能 preview 出 Skill bundle，且不执行 repo 脚本。
- [ ] `npx @orchestra-research/ai-research-skills` 类型 source 只能在 Docker import sandbox 中 preview。
- [ ] `npx skills add eze-is/web-access` 类型 source 能被 allowlist parser 接受。
- [ ] 高风险导入必须二次确认，确认后有 audit override record。
- [ ] zip bundle 能导入 `SKILL.md` 和附属文件。
- [ ] Agent 创建和编辑页能勾选能力并保存默认绑定。
- [ ] session projection 能写出完整 `.weagent/skills/<runtime_id>/...`。
- [ ] Agent 修改脚本后能生成 draft，发布前重新审计。
- [ ] 内置 Tool 能在 UI 中看到只读文件视图。
- [ ] 原有 Capability API、Tool call audit、MCP runtime、Plugin manifest、Skill Markdown flow 不回归。

## Ambiguity Report

- Goal Clarity: 0.90
- Boundary Clarity: 0.84
- Constraint Clarity: 0.82
- Acceptance Criteria: 0.84
- Ambiguity: 0.15

所有维度达到 GSD spec gate。剩余不确定性主要是 Docker import sandbox 的具体复用方式和文件大小阈值，这些属于 PLAN 阶段可实现决策。
