# 003 Toolset UAT Issues

## UAT-001: 新建 Skill 默认内容过空
- 发现：工具集页面点击“新建 Skill”时，Markdown 默认内容只有 `# New Skill`。
- 用户期望：参考 `skill-creator` 的结构，默认填入一个简短但真实的 Skill 模板。
- 建议修改：默认包含 YAML frontmatter、标题、适用场景、工作流、边界；模板需要能被当前 title parser 正常识别。
- 状态：记录，待统一修改。

## UAT-002: Repo 导入当前只支持本地路径，不符合用户预期
- 发现：当前后端 `preview_repo_static` 需要后端可访问的本地 `repo_path`。
- 用户期望：Repo 导入应能输入外部 repo 地址，例如 GitHub URL 或 `owner/repo`。
- 风险：如果只让用户填写本地路径，产品体验不合理，也不符合“外部工具集导入”的直觉。
- 建议修改：UI 暂时标注为“本地路径调试模式”；后续实现远程 repo clone/download 到 import sandbox，再静态扫描，不执行 repo 脚本。
- 状态：记录，待统一修改。

## UAT-003: 需要准备真实验收样例文件
- 发现：用户希望在 `WeAgent/toolset` 下放入可直接用于测试的 Markdown、zip bundle、npx 命令和典型命令。
- 处理：已准备 Markdown Skill、zip bundle source、`02-skill-bundle.zip`、npx import source 和说明。
- 注意：Repo 因当前仅支持本地路径，先放说明，不伪造远程 repo 样例。
- 状态：已处理样例，产品能力仍待后续改进。

## UAT-004: TOOL / Skill / Plugin / MCP 的安装方式需要明确边界
- 发现：用户希望看到 TOOL / Skill / Plugin / MCP 的典型下载或导入命令。
- 当前边界：TOOL 是平台内置能力，无下载命令；Skill 支持 Markdown / zip / npx skills installer 导入；MCP v1 目标是 npx MCP server 最小真实调用；Plugin 当前偏 manifest/install record，不是完整 runtime plugin 安装。
- 建议修改：UI 中给不同类型分别展示“当前支持的安装方式”和“不支持原因”；对 MCP/Plugin 增加 manifest 导入入口或专用安装向导。
- 状态：记录，待统一修改。

## UAT-005: 工具详情侧栏缺少关闭/收起入口
- 发现：在代码工具中点击默认 TOOL 后，右侧详情栏弹出，但没有明显关闭或收起按钮。
- 用户期望：右侧栏应能一键收起，避免页面被详情状态锁住。
- 建议修改：详情栏顶部增加关闭按钮；点击列表空白区域或切换分类时清空当前选中项。
- 状态：记录，待统一修改。

## UAT-006: 前端不应直接展示底层 manifest JSON
- 发现：TOOL 详情中展示了底层 manifest，例如 `runtime: builtin`、`tool.value`、`tool.category` 等字段。
- 用户疑问：manifest 是否应该展示给普通用户，以及 TOOL 标准是否应该长这样。
- 判断：manifest 是内部定义和调试信息，普通详情页应展示产品化字段：名称、类型、来源、权限、运行时说明、可调用动作；原始 JSON 可放到“开发者详情/高级模式”。
- 状态：记录，待统一修改。

## UAT-007: Skill 审查对 Markdown 中的 `requests` 报 medium 风险偏保守
- 发现：导入 Skill 时，`SKILL.md` 中出现 `requests` 会被识别为 `Dangerous library or API detected: requests`，并推断 `network` 权限和 `medium` 风险。
- 根因：当前检测引擎对 Markdown 也套用了 Python/JS/Shell 危险库扫描，容易把说明文字误判为实际代码调用。
- 判断：推断 `network` 权限可以接受；把 Markdown 说明里的 `requests` 标为 dangerous API 偏保守，容易误报。
- 建议修改：危险库/API 扫描只对脚本扩展名生效；Markdown 先做 secret/path/shell/network 轻量扫描，后续再按 fenced code block 的语言做精细扫描。
- 状态：记录，待统一修改。

## UAT-008: Workspace Organizer 在 Agent 创建页可选，但工具集页不可见
- 发现：数据库中 `Workspace Organizer` 是用户导入的 Skill，`category_id = null`；Agent 创建页请求全部能力所以可见，工具集页按分类请求所以不可见。
- 根因：旧导入或未分类能力没有归入 `tool_custom`，导致分类页和 Agent 选择器的数据口径不一致。
- 建议修改：未分类能力默认归入“自定义/用户工具”；或者迁移历史 `category_id is null` 的能力到 `tool_custom`。
- 状态：记录，待统一修改。

## UAT-009: NPX 导入展示 npm warn / notice，且真实运行可能超时或解码失败
- 发现：用户在 NPX 导入时看到 `npm warn exec The following package was not found and will be installed: skills@1.5.9` 和 npm 新版本提示。
- 判断：这条 npm warn/notice 本身不是失败，表示 Docker import sandbox 是干净环境，`npx` 会临时下载 `skills` CLI；npm 升级提示也不需要用户处理。
- 真实问题：后端日志显示 Windows 上 `subprocess` 默认按 GBK 解码 npm 输出，可能触发 `UnicodeDecodeError`；`npx @orchestra-research/ai-research-skills` 还出现过 180 秒超时，且超时后的临时目录清理错误会掩盖真正原因。
- 已做修复：npx sandbox runner 改为 UTF-8 容错解码；超时返回明确错误；临时目录清理不再掩盖主错误；Docker 命令增加 npm 环境变量以抑制 update/fund/audit 等噪音；内部执行改为 `npx --yes ...`，避免干净容器首次安装 installer 时等待确认或显示安装确认提示。
- 状态：已修复后端基础问题，仍需真实 UI 复测。

## UAT-010: MCP 用户侧没有形成可验收的真实样例
- 发现：代码中已有 sandbox-side MCP runtime 和测试骨架，但工具集页面/真实 UAT 没有一个明确的 MCP 样例能力，因此用户视角会认为 MCP “没有实现”。
- 处理：新增内置 `Memory MCP` capability，来源为官方 `@modelcontextprotocol/server-memory`，manifest 使用 `npx --yes @modelcontextprotocol/server-memory`，权限要求为 `run_command`，分类归入 `tool_data`。
- 处理：新增 host sandbox API 转发入口，可对 session 内 MCP 执行 start、list tools、call、stop。
- 处理：repo 导入由于当前只是后端本地路径扫描，已从前端导入向导移除；后端 repo preview 返回明确错误，提示使用 zip bundle 上传。
- 验证：相关后端测试通过；前端工具集契约通过；前端 production build 通过。
- 验证：已用 `docker run node:22-alpine npx --yes @modelcontextprotocol/server-memory` 做真实 JSON-RPC smoke，`initialize` 和 `tools/list` 能返回，工具包括 `create_entities`、`read_graph`、`search_nodes`、`open_nodes` 等。
- 状态：已实现基础链路，仍需在 WeAgent 页面里完成“创建/编辑 Agent 绑定 Memory MCP -> 开启 sandbox session -> 调用 MCP”的端到端 UAT。

## UAT-011: MCP 需要前端新增入口，NPX 也要兼容 MCP/Skill
- 发现：前端导入向导原本只有 Markdown、zip bundle、npx；MCP 虽然能被系统展示，但用户不知道如何新增 MCP。
- 用户期望：zip + Markdown + NPX 之外，要有一个 MCP 专用接口；NPX 导入要兼容 Skill 和 MCP。
- 已做修复：新增后端 `POST /api/capabilities/import/mcp-manifest`，只接收 MCP capability manifest；前端导入向导新增 `MCP manifest` 入口，可编辑 JSON、生成预览、选择能力后入库。
- 已做修复：NPX/zip 产物预览不再只查 `SKILL.md`，也会识别 `schema_version = weagent.capability/v1` 的 JSON manifest；确认导入时可把 manifest 中的 MCP/Skill/Plugin candidate 写入能力库。
- 验证：`test_capability_import_preview.py`、`test_capability_import_confirm.py`、`test_capability_api.py`、`test_capability_npx_import_sandbox.py`、`test_capability_mcp_runtime.py`、`test_toolset_categories.py` 共 34 个后端测试通过；`toolset-ui-contract.test.js` 通过；前端 production build 通过。
- 状态：已实现，等待真实页面 UAT。

## UAT-012: `npx skills add eze-is/web-access` 导入失败
- 发现：前端 NPX 导入返回失败，日志中出现 `Failed to clone ... Error: spawn git ENOENT`。
- 根因 1：NPX import sandbox 使用 `node:22-alpine`，该镜像没有 `git`；`skills add eze-is/web-access` 内部需要 `git clone` GitHub repo。
- 根因 2：切换到带 git 的镜像后，`skills` CLI 会进入“选择安装到哪些 agent”的交互式提示；原先只传了 `npx --yes`，没有给 `skills add` 自己传 `--yes --global`。
- 已做修复：NPX import sandbox 改用 `node:22` 镜像；`npx skills add <repo>` 内部规范化为 `npx --yes skills add --yes --global <repo>`。
- 验证：真实 Docker 命令可 clone 并安装 `web-access`；真实后端 `preview_npx("npx skills add eze-is/web-access")` 能返回 `web-access Skill`，入口为 `.agents/skills/web-access/SKILL.md`。
- 验证：`test_capability_npx_import_sandbox.py`、`test_capability_import_security.py` 通过；003 相关后端回归子集 34 个测试通过。
- 状态：已修复并重启本地后端，等待前端复测。

## UAT-013: NPX 预览展示 `.npm-cache/_cacache/...` 缓存文件
- 发现：`npx skills add eze-is/web-access` 生成预览后，审计结果里出现 `.npm-cache/_cacache/content-v2/sha512/...`、`.npm-cache/_logs/...` 等路径。
- 判断：不合理。这些文件是 npm/npx 下载依赖产生的包缓存和日志，不是用户要导入的 Skill/MCP 内容；扫描它们会导致大量假阳性，例如 `exec`、`curl`、shell operator、path escape。
- 已做修复：导入产物收集阶段忽略包管理器缓存目录：`.npm-cache`、`.npm`、`_cacache`、`.pnpm-store`、`node_modules`、`.git`。这些文件不会进入预览文件树、bundle_files 或安全审计输入。
- 验证：新增 `test_preview_directory_ignores_npm_cache_artifacts`；真实后端 `preview_npx("npx skills add eze-is/web-access")` 返回 `FILES: 15`，且 `HAS_NPM_CACHE_FILE=False`、`HAS_NPM_CACHE_RISK=False`。
- 验证：003 相关后端回归子集 44 个测试通过。
- 状态：已修复并重启本地后端，等待前端复测。

## UAT-014: MCP / Skill / Plugin / Tool 需要删除与解绑能力
- 发现：当前工具集已经支持创建、导入、展示和 Agent 绑定，但缺少用户侧删除能力的完整产品路径。
- 用户期望：用户导入或自建的 Skill、MCP、Plugin、Tool 应可删除；删除前需要提示影响范围，例如已经绑定到哪些 Agent、是否存在 workspace runtime 副本或调用记录。
- 边界建议：内置能力不允许物理删除，只允许从 Agent 解绑或在默认推荐中隐藏；用户能力采用软删除/归档优先，保留版本、审计和调用记录，避免历史 Agent 与调用日志断链。
- 下一阶段建议：补充后端 delete/archive API、绑定关系检查、前端详情栏删除入口、删除确认弹窗，以及 Agent 绑定页的解绑路径。
- 已做修复：新增删除影响预览 API、用户能力归档 API、Agent capability binding 解绑 API；用户能力删除时会从工具集隐藏并解除用户 Agent 绑定，版本、审计和调用记录继续保留；内置能力删除会被拒绝。
- 已做修复：工具集详情栏对非内置能力展示删除按钮，删除前读取后端影响范围并提示绑定 Agent 数和历史调用记录数；Agent 编辑页对已持久化的能力绑定使用真实解绑 API，而不是只置为 disabled。
- 验证：`test_capability_api.py` 新增删除/解绑覆盖；相关后端回归子集通过；工具集与 Agent 能力选择器前端契约通过；前端生产构建通过。
- 状态：已处理，等待真实页面 UAT。

## UAT-015: 工具集卡片图标渲染异常
- 发现：工具集卡片左侧图标当前显示为色块内的残缺小图标，例如 `Git操作` 卡片中只露出一个不完整符号。
- 初步判断：当前能力卡片使用 `typeMeta(capability.type).icon`，同一类型下全部 Tool 共用类型图标，没有优先使用能力 manifest/tool 自身的 icon；同时部分 Element icon 类名在当前前端版本中可能不存在或渲染尺寸/颜色不匹配。
- 用户期望：卡片图标应稳定、清晰、可识别；Git、终端、搜索、数据库等常见 Tool 应有合理图标，不应出现破碎或空白图标。
- 下一阶段建议：统一 icon resolver，优先级为 capability manifest icon -> category icon -> type icon -> fallback icon；过滤不可用 icon；必要时把内置 Tool 图标迁移到当前 UI 库可用的图标名，并补充前端契约测试。
- 已做修复：工具集卡片和详情头部改为统一 icon resolver，优先使用 capability manifest/tool icon，其次 category icon，再回退到 type icon；新增 Element icon 白名单和别名映射，把当前不可用的 `el-icon-console` 映射到可用图标；补充图标字号与 line-height，避免小图标残缺。
- 追加修复：真实截图发现右侧详情栏仍异常，根因为 `.detail-header span` 这条泛化样式覆盖了 `.detail-icon`，把图标容器从 `flex` 改成 `block`；已改为只作用于 `.detail-heading > div > span`，并新增契约防止再次出现泛化覆盖。
- 验证：前端契约覆盖“不能强制所有 Tool 使用通用类型图标”和“详情头部 span 样式不能覆盖图标容器”；生产构建通过；Chrome headless 真实截图验证右侧详情栏 `.detail-icon` 为 `display:flex`，图标中心偏移为 `0,0`。
- 状态：已处理，等待真实页面 UAT。

## UAT-016: 内置 Tool 需要真实实现并补充公认好用的内置项
- 发现：当前内置 Tool 已作为 capability 展示和授权，但部分展示项仍偏“目录/定义”，与 sandbox 内真实可调用工具名不完全对应；例如平台展示有 `代码审查`、`Git操作`、`数据库查询`，而容器内已注册的基础工具主要是 `read_file`、`write_file`、`run_command`、`list_files`、`report_progress`。
- 用户期望：内置 Tool 不只是前端卡片，而是能被 Agent 真实调用、记录调用、受权限控制；同时希望内置一些公认好用的能力，而不是空壳占位。
- 边界建议：v1 先做“安全、确定、容易验收”的内置 Tool：文件读取/写入、目录列举、受限命令执行、Git 状态/差异读取、文本搜索、代码审查摘要；高风险能力如任意 Git 写操作、数据库写入、外网搜索/API 调用先走更严格权限或后续阶段。
- 下一阶段建议：建立 Tool manifest 与 runtime handler 的一一映射，展示“已实现/即将支持”状态；把 `Git操作` 拆成安全只读 Git 工具和高风险写入工具；为每个真实 Tool 增加调用记录和权限测试。
- 状态：记录，下一阶段设计并实现。

## UAT-017: 归档删除后 Skill/MCP/Plugin/Tool Tab 数字未刷新
- 发现：用户删除 2 个 Skill 后，卡片列表只剩 2 个，但 `Skill` tab 徽标仍显示 4。
- 根因：工具集卡片列表调用 `/api/capabilities`，已经过滤 `source = archived`；tab 徽标来自 `/api/toolsets/categories` 的分类 `counts`，该统计逻辑没有过滤已归档能力，导致数字仍包含被删除/归档的 Skill。
- 已做修复：`toolset_category_service._counts_by_category` 与能力列表使用一致可见性规则，统计时排除 `Capability.source == "archived"`。
- 验证：新增 `test_category_counts_exclude_archived_capabilities` 覆盖“归档后分类计数不再包含已删除能力”；真实页面 Chrome headless 验证 `Skill 2` 且卡片数量为 2。
- 注意：左侧一级分类 `代码工具` 的总数如果显示 4 是合理的，因为它统计该分类下所有可见类型，例如 2 个 Skill + 2 个 Tool。
- 状态：已处理，等待真实页面 UAT。
