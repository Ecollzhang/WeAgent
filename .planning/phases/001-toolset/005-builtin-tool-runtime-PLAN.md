# 005 Built-in Tool Runtime and Markdown Contract PLAN

## Purpose

实现 `005-builtin-tool-runtime-SPEC.md`：让内置 Tool 不再只是工具集卡片，而是具有 `TOOL.md` 说明、结构化 manifest、sandbox handler、权限 gate、渐进式披露、调用记录和分类状态的真实 runtime capability。

## Current Baseline

- `backend/app/services/tool_service.py` 定义旧内置 Tool 模板。
- `backend/app/services/capability_service.py` 将旧模板 seed 为 `Capability(type="tool")`。
- `backend/app/sandbox/container/tools/__init__.py` 真实注册 `read_file`、`write_file`、`run_command`、`report_progress`、`list_files`。
- `backend/app/sandbox/container/capabilities.py` 只映射 `file_operations` 和 `terminal` 到 runtime tool names。
- `capability_projection_service` 当前投影 Skill/MCP/Plugin/Tool metadata，但没有 `.weagent/tools/<runtime_id>/TOOL.md` 和 `tool-index.json`。
- `Tools.vue` 能展示 Tool 卡片、详情、虚拟文件，但还不能表达“已实现/部分实现/需要配置/未实现”的执行状态。

## Checkpoint A: Contract and Regression Tests

**Goal:** 先锁住 Tool 契约和空壳修复的失败用例。

Tasks:

1. 新增或扩展后端测试：
   - 内置 Tool manifest 必须符合 `weagent.tool/v1`。
   - 内置 Tool 必须有 `TOOL.md` 内容。
   - 未绑定 Tool 调用拒绝执行。
   - 权限不足 Tool 调用拒绝执行。
   - 每个功能分类至少有一个 `implemented` Tool。
   - `deferred/requires_config` Tool 不允许执行。
2. 新增 projection 测试：
   - `.weagent/tools/<runtime_id>/TOOL.md`
   - `.weagent/tools/<runtime_id>/manifest.json`
   - `.weagent/agents/<agent_id>/tool-index.json`
3. 新增前端契约测试：
   - 内置 Tool 不展示编辑/删除入口。
   - Tool 卡片/详情展示 `implemented/partial/requires_config/deferred` 状态。
   - 详情优先展示 `TOOL.md` 和摘要，不把 raw manifest 当成主要说明。

Verification:

```powershell
python -m pytest tests\test_capability_tool_contract.py tests\test_capability_projection.py -q
node tests\toolset-ui-contract.test.js
```

## Checkpoint B: Canonical Built-in Tool Definitions

**Goal:** 建立内置 Tool 的唯一事实来源，消除旧 `AgentTool` 和新 Capability 定义分叉。

Tasks:

1. 新增 canonical built-in Tool definition 模块，例如：
   - `backend/app/services/builtin_tool_definitions.py`
2. 每个 definition 包含：
   - `id/source_ref`
   - `name`
   - `category_id`
   - `description`
   - `runtime`
   - `handler`
   - `tool_names`
   - `input_schema`
   - `output_schema`
   - `permissions`
   - `audit`
   - `ui.status`
   - `TOOL.md` markdown
3. 更新 `tool_service.BUILTIN_TOOLS`：
   - 作为兼容视图读取 canonical definitions。
   - 不再作为 capability seed 的唯一来源。
4. 更新 `capability_service.seed_builtin_tool_capabilities()`：
   - 使用 canonical definitions。
   - 新 definition 生成新 version。
   - 不覆盖已绑定 Agent 的 pinned version。
5. 保留旧 `agent_tools` 和 `/api/tools` 兼容路径，但不让它们制造新的空壳能力。

Verification:

```powershell
python -m pytest tests\test_toolset_categories.py tests\test_capability_api.py -q
```

## Checkpoint C: Tool Runtime Projection and Progressive Disclosure

**Goal:** Tool 像 Skill 一样被投影，但采用轻量索引 + 按需读取 Markdown。

Tasks:

1. 扩展 `capability_projection_service`：
   - `_tool_record()` 包含 `doc_path`、`manifest_path`、`tool_names`、`ui.status`。
   - `_binding_view()` 保留 Tool manifest 和 runtime id。
   - Agent view 新增 `tool_index`。
2. 扩展 `backend/app/sandbox/container/capabilities.py`：
   - `write_projection()` 写入 `.weagent/tools/<runtime_id>/TOOL.md`。
   - 写入 `.weagent/tools/<runtime_id>/manifest.json`。
   - 写入 `.weagent/agents/<agent_id>/tool-index.json`。
3. 更新 orchestrator prompt：
   - 只列当前 Agent 已绑定 Tool 的简短索引。
   - 指示 Agent 在需要时读取 `doc_path`。
   - 不再把 registry 中所有工具当成可用工具展示给所有 Agent。

Verification:

```powershell
python -m pytest tests\test_capability_projection.py tests\test_capability_container_projection.py -q
```

## Checkpoint D: Runtime Gate and Audit Hardening

**Goal:** Tool 调用必须绑定、授权、审计。

Tasks:

1. 修改 `ToolRegistry.call_from_agent()`：
   - capability-aware session 中找不到绑定时拒绝执行。
   - 权限不足时拒绝执行。
   - deferred/requires_config Tool 拒绝执行。
   - legacy fallback 只在没有 `.weagent` projection 的老 session 中保留。
2. 扩展 `permissions_for_tool()`：
   - 按 canonical runtime tool name 返回权限。
   - 支持 Git、HTTP、CSV/JSON/SQLite、image info 等新工具。
3. 扩展 input/output summary：
   - 文件路径摘要。
   - 命令摘要与输出截断。
   - URL host 摘要，避免记录敏感 query/token。
   - 数据文件行数/字段摘要。
4. 确保 JSONL call record 和 DB sync service 兼容所有新 Tool。

Verification:

```powershell
python -m pytest tests\test_capability_tool_audit.py tests\test_capability_tool_contract.py -q
```

## Checkpoint E: First Implemented Tool Set by Category

**Goal:** 每个功能分类都有必要的、可验收的真实 Tool。

### 代码工具

Implement:

- `code_search`
  - Purpose: 在 workspace 内搜索代码/文本。
  - Permission: `read_workspace`
  - Handler: 优先 `rg`，缺失时 fallback 到 Python walk。
- `code_review_scan`
  - Purpose: 对指定文件做确定性静态风险扫描，例如 TODO/FIXME、危险 API、明显 secret、超长文件、二进制误传。
  - Permission: `read_workspace`
  - Note: 不是 LLM code review，不输出“智能评价”。

### 文件与文档

Implement:

- `read_file`
- `write_file`
- `list_files`
- `document_text_extract`
  - v1 支持 `.txt`、`.md`、`.json`、`.csv`；PDF/Word 标为 deferred 或 requires dependency。

### 网络与检索

Implement:

- `http_fetch`
  - GET only by default。
  - Requires `network`。
  - Timeout、content length limit、HTML/text summary。
- `api_request`
  - GET/POST allowlist。
  - Requires `network`，使用 secret 时 requires `use_secret`。

Defer:

- `web_search`
  - 需要搜索 provider 或 MCP server，默认 `requires_config`。

### 数据处理

Implement:

- `csv_profile`
  - 行数、列名、空值、示例行、基础类型推断。
- `json_query`
  - 安全读取 JSON path / key path。
- `sqlite_query_readonly`
  - 只允许 SELECT/PRAGMA table_info。

Defer:

- 生产数据库连接、写入 SQL。

### 图像/多媒体

Implement:

- `image_info`
  - 文件大小、mime、宽高、格式。

Optional if dependency is available:

- `image_convert`
  - 仅本地格式转换，不做 AI 视觉理解。

Defer:

- OCR、物体识别、图像理解，建议后续接 MCP 或模型能力。

### 系统与终端

Implement:

- `run_command_safe`
  - 替代泛化 `run_command` 给 Agent 使用。
  - Timeout、cwd 限制、denylist、输出截断。
- `git_status`
- `git_diff`
- `git_log`
- `report_progress`

Defer:

- `git_commit`、`git_push`、branch mutation。

### 自定义

Implement:

- 不内置执行 Tool。
- UI 提供“创建自定义 Tool”的入口和模板说明。
- 用户脚本 Tool runtime 标为后续阶段，除非已经通过安全审计发布。

Verification:

```powershell
python -m pytest tests\test_builtin_tool_handlers.py tests\test_capability_tool_audit.py -q
```

## Checkpoint F: Toolset UI Status and Documentation View

**Goal:** 用户能明确知道 Tool 是否真实可用、需要什么权限、如何给 Agent 使用。

Tasks:

1. 更新 `Tools.vue` Tool 卡片：
   - 展示状态：已实现、部分实现、需要配置、未实现。
   - 未实现 Tool 不展示“可调用”暗示。
2. 更新详情侧栏：
   - 默认展示 `TOOL.md` 渲染/文件内容。
   - 展示参数 schema 摘要。
   - 展示权限和风险。
   - 展示 runtime handler 和 tool_names 的产品化摘要。
   - raw manifest 仅放开发者详情折叠区域。
3. 内置 Tool：
   - 不显示编辑/删除。
   - 可显示“平台内置，只读”。
   - 可显示“有新版本可升级”。
4. 用户 Tool：
   - 可编辑 `TOOL.md` 草稿。
   - manifest 通过表单编辑；直接 JSON 编辑放专家模式。
   - 未发布草稿不进入 runtime projection。

Verification:

```powershell
node tests\toolset-ui-contract.test.js
npm run build
```

## Checkpoint G: Docker UAT Guide and Real Sandbox Smoke

**Goal:** 用户能按指南验证每类 Tool 确实可用，不再靠代码判断。

Tasks:

1. 新增 `.planning/phases/001-toolset/005-builtin-tool-runtime/REAL-TOOL-UAT-GUIDE.zh-CN.md`。
2. 指南覆盖：
   - 启动后端、前端、Docker sandbox。
   - 创建/编辑 Agent 并绑定 Tool。
   - 查看 `.weagent/tools`、`tool-index.json`。
   - 调用每类代表 Tool。
   - 查看 JSONL call records。
   - 同步/查询 DB call records。
   - 验证未绑定/权限不足/未实现 Tool 被拒绝。
3. 准备本地 UAT fixtures：
   - sample code file。
   - sample markdown/csv/json/sqlite/image。
   - git repo 状态样例。

Verification:

```powershell
python -m pytest tests\test_builtin_tool_handlers.py tests\test_capability_tool_audit.py tests\test_capability_projection.py -q
node tests\toolset-ui-contract.test.js
npm run build
```

## Checkpoint H: Integration Regression and Cleanup

**Goal:** 保证这次 Tool runtime 改造不破坏 001/002/003 已完成能力。

Tasks:

1. 回归 Capability API：
   - list/create/import/delete/bind/unbind。
2. 回归 Toolset categories：
   - counts 不包含 archived。
   - 每类 counts 和状态展示一致。
3. 回归 Agent create/edit：
   - 绑定 Tool、Skill、MCP、Plugin。
   - pinned version 默认不变。
4. 回归 sandbox：
   - Skill projection。
   - MCP runtime。
   - Plugin manifest-only boundary。
   - Tool call record。
5. 清理旧文案：
   - 不再把未实现 Tool 描述成“可执行”。
   - `database_query`、`web_search`、`code_generator` 根据真实状态调整为 `requires_config` 或 `deferred`。

Verification:

```powershell
python -m pytest tests\test_toolset_categories.py tests\test_capability_api.py tests\test_capability_projection.py tests\test_capability_tool_audit.py tests\test_capability_mcp_runtime.py -q
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
npm run build
git diff --check
```

## Risk Notes

- `run_command_safe` 是最高风险点，必须先限制再开放。
- `http_fetch/api_request` 可能泄漏 URL query 或 token，审计摘要必须脱敏。
- `sqlite_query_readonly` 必须解析并拒绝非只读 SQL，不能只靠字符串前缀。
- 图像处理依赖如果导致镜像变大，应先只做无外部依赖的 `image_info`。
- `code_review_scan` 不能冒充 LLM code review，名称和说明必须强调 deterministic scan。
- legacy fallback 如果保留过宽，会让 Agent 绕过 capability binding；需要用“是否存在 projection”明确分界。

## Done Definition

- 每个功能分类至少一个真实 implemented Tool 可在 sandbox 内调用。
- 内置 Tool 有 `TOOL.md`、manifest、handler、权限、状态、审计。
- Agent 只看到并只能调用自己绑定授权的 Tool。
- 未实现或需配置 Tool 在 UI 中不会被误认为可调用。
- Docker UAT 能验证真实调用、失败拒绝和 call record。
