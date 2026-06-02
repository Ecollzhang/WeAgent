# 006 可配置 Tool Catalog PR 交接文档

更新时间：2026-06-02
目标分支：`feature/toolset`
模块范围：工具集默认 Tool 目录、可配置能力、Agent 能力绑定、sandbox runtime projection、配置型 Tool 调用链路。

## 1. 本轮做了什么

本轮把默认工具集从“展示一批静态 Tool 卡片”推进到“只展示真实可用或配置后可用的能力”。核心变化是：

- 降级并隐藏 `code_generator`。代码生成更适合作为 Skill/Agent workflow，不再作为默认可绑定 Tool 出现在工具集中。
- 保留已实现的确定性内置 Tool，例如代码搜索、代码审查、文件操作、网页抓取、API 调用、本地数据分析、图像信息、终端安全执行、Git 只读操作。
- 把 `web_search`、`image_analysis`、`image_generation`、`database_query` 统一定义为“需配置能力”。
- 新增 provider profile 保存、测试、启用、停用、删除 API 和前端配置窗口。
- 未配置的 `requires_config` Tool 可以在工具集页面展示配置入口，但不能绑定到 Agent。
- 配置通过并启用后，该 Tool 会变成可绑定能力，并进入 `.weagent/*` runtime projection。
- sandbox 内新增配置型 Tool adapter，可以验证 Web Search、Image Analysis、Image Generate、Database Query 的最小真实调用链路。
- 修复工具集分类 badge 计数与前端卡片显示不一致的问题。
- 同批补充模型配置页的“自定义模型名”输入保存链路，使自定义模型配置能进入 DB 和 sandbox 镜像配置。

## 2. 新增和修改的主要内容

### 后端

主要文件：

- `backend/app/models/tool_provider_config.py`
- `backend/app/services/tool_provider_config_service.py`
- `backend/app/controllers/capability_controller.py`
- `backend/app/schemas/capability_schema.py`
- `backend/app/services/builtin_tool_definitions.py`
- `backend/app/services/capability_service.py`
- `backend/app/services/capability_projection_service.py`
- `backend/app/services/toolset_category_service.py`
- `backend/app/sandbox/container/capabilities.py`
- `backend/app/sandbox/container/tools/__init__.py`
- `backend/app/sandbox/host/client.py`
- `backend/app/sandbox/host/manager.py`
- `backend/sql/init.sql`

新增能力：

- `ToolProviderConfig` 数据模型，保存用户对某个可配置 Tool 的 provider profile。
- provider config API：
  - `GET /api/capabilities/<id>/provider-configs`
  - `POST /api/capabilities/<id>/provider-configs`
  - `PUT /api/capabilities/<id>/provider-configs/<config_id>`
  - `POST /api/capabilities/<id>/provider-configs/<config_id>/test`
  - `POST /api/capabilities/<id>/provider-configs/<config_id>/enable`
  - `POST /api/capabilities/<id>/provider-configs/<config_id>/disable`
  - `DELETE /api/capabilities/<id>/provider-configs/<config_id>`
- 可配置 Tool manifest 字段：
  - `ui.status`
  - `ui.visibility`
  - `ui.configurable`
  - `ui.bindable`
  - `ui.provider_types`
  - `ui.config_schema`
- Agent 绑定规则：
  - hidden/deferred 不可绑定。
  - 未配置的 `requires_config` 不可绑定。
  - 有 `valid` provider profile 后可绑定。
- runtime projection：
  - `.weagent/tools/*` 保留 Tool manifest。
  - `.weagent/agents/<agent_id>/capabilities.json` 和 `tool-index.json` 投影 Agent 视图。
  - provider config 只投影非敏感配置和 profile 信息，不写入明文 secret。
- sandbox adapter：
  - `web_search`：当前真实可跑的是 HTTP provider，调用 `endpoint?q=<query>&limit=<n>`。
  - `image_analysis`：当前为 deterministic fixture，读取本地图像信息并生成分析摘要。
  - `image_generate`：当前为 deterministic fixture，生成有效 PNG 文件。
  - `database_query`：当前支持 SQLite fixture 只读查询。

### 前端

主要文件：

- `frontend/src/views/Tools.vue`
- `frontend/src/api/capabilities.js`
- `frontend/src/components/AgentEditForm/index.vue`
- `frontend/src/views/Settings.vue`
- `frontend/src/components/Sidebar/index.vue`
- `frontend/src/router/index.js`

新增能力：

- 工具集页面新增配置型 Tool 的“配置能力”窗口。
- 支持创建、编辑、测试、保存、启用、停用、删除 provider profile。
- `web_search` 默认打开 HTTP provider 配置，避免用户误以为当前 MCP search 已完全接通。
- 工具卡片只展示 visible 或可配置的 Tool。
- Agent 创建/编辑页只允许选择 bindable 能力。
- 修复侧边栏图标显示异常。
- 修复删除 Skill 后 tab badge 数字不同步的问题。
- 模型配置页新增自定义模型输入，并保存到后端/投影到 sandbox 配置。

### 文档和测试材料

新增或更新：

- `.planning/phases/001-toolset/006-default-tool-catalog-SPEC.md`
- `.planning/phases/001-toolset/006-default-tool-catalog-PLAN.md`
- `.planning/phases/001-toolset/006-default-tool-catalog/CHECKPOINT-A-REPORT.md`
- `.planning/phases/001-toolset/006-default-tool-catalog/CHECKPOINT-C-D-REPORT.md`
- `.planning/phases/001-toolset/006-default-tool-catalog/CHECKPOINT-E-F-REPORT.md`
- `.planning/phases/001-toolset/006-default-tool-catalog/CHECKPOINT-G-H-REPORT.md`
- `.planning/phases/001-toolset/006-default-tool-catalog/006-CONFIGURABLE-TOOLS-UAT-GUIDE.zh-CN.md`
- `toolset/`：003 外部导入 UAT fixtures，包含 Markdown Skill、zip bundle、npx 输入样例和 MCP manifest 样例。
- `docs/ai-collab/archive/why-archive-v1.0-05-29.md`
- `docs/ai-collab/sessions/why-session-v1.0-05-29.md`

## 3. 如何本地运行

后端：

```powershell
cd backend
python run.py
```

默认地址：

```text
http://localhost:5001
```

健康检查：

```text
http://localhost:5001/api/health
```

前端：

```powershell
cd frontend
npm run serve -- --host 0.0.0.0 --port 8080
```

默认地址：

```text
http://localhost:8080
```

如果看不到最新 Tool 卡片或 badge 数字不对，先确认后端已重启。内置 Tool seed/update 在后端启动时执行。

## 4. Web Search 配置交接

当前 Web Search 的实际运行路径建议使用 HTTP provider。

前端路径：

```text
工具集 -> 网络与检索 -> Tool -> 网页搜索 -> 配置能力
```

配置 JSON 示例：

```json
{
  "endpoint": "http://host.docker.internal:18089/search"
}
```

runtime 调用约定：

```text
GET /search?q=<query>&limit=<n>
```

期望返回：

```json
{
  "results": [
    {
      "title": "标题",
      "url": "https://example.com",
      "snippet": "摘要"
    }
  ]
}
```

注意：当前配置测试是静态校验，只检查配置结构和必填字段；真正调用时才会请求 endpoint。MCP provider 形态已保留，但 `web_search` sandbox adapter 当前只完整支持 HTTP provider。

## 5. 当前验证结果

已经执行并通过：

```powershell
python -m pytest tests\test_default_tool_catalog.py tests\test_tool_provider_config_api.py tests\test_toolset_categories.py -q
```

结果：

```text
11 passed
```

此前同轮还验证过：

```powershell
python -m pytest -q
npm run build
docker build -t weagent-sandbox:latest backend\app\sandbox
docker run --rm -e PYTHONPATH=/app weagent-sandbox:latest python -c "from container.tools import ToolRegistry, register_builtin_tools; r=ToolRegistry('/workspace'); register_builtin_tools(r); print(sorted({t['name'] for t in r.list_tools()} & {'web_search','image_analysis','image_generate','database_query'}))"
```

结果摘要：

- 后端全量测试此前通过：`102 passed`。
- 前端 build 成功，有 bundle size warning。
- Docker sandbox 镜像可构建。
- 镜像内已注册 `database_query`、`image_analysis`、`image_generate`、`web_search`。

## 6. PR 审查重点

建议 reviewer 重点看：

- `ToolProviderConfig` 是否满足后续 secret vault 接入边界。
- provider profile 的 `valid/invalid/disabled/draft` 状态转换是否足够清晰。
- 未配置 `requires_config` Tool 是否在所有路径都不可绑定。
- `.weagent/*` projection 是否没有泄露明文 secret。
- `toolset_category_service` 的分类计数是否和前端可见卡片口径一致。
- `web_search` 当前 HTTP-only runtime 边界是否在 PR 描述中写清楚。
- `image_analysis`、`image_generate` 当前是 deterministic fixture，不应被误解为真实模型能力。
- `database_query` 当前 runtime smoke 只支持 SQLite fixture，MySQL/Postgres 需要后续 driver/secret/vault 补齐。

## 7. 已知边界和后续 TODO

- Web Search 的 MCP provider 形态尚未完整接入 runtime adapter。
- 图像分析和图像生成当前主要验证“配置、绑定、投影、调用、记录”链路，不等同于真实模型服务。
- 数据库查询当前实际 adapter 支持 SQLite fixture，只读策略需要继续扩展到真实 MySQL/Postgres provider。
- provider config 测试当前是静态校验，后续可升级为带超时和审计的真实 provider smoke。
- `toolset/` fixtures 是 UAT 用例材料，不是产品运行时依赖。
- `.claude/logs/` 是本地会话日志，不应进入 PR。

## 8. PR 建议说明模板

```text
本 PR 在 feature/toolset 上完成 006 默认 Tool Catalog 与可配置 Tool provider 链路：

- 隐藏/降级 code_generator，避免未实现 Tool 误导用户。
- 新增 ToolProviderConfig 模型/API/service，支持 provider profile 创建、测试、启用、停用、删除。
- 将 web_search、image_analysis、image_generation、database_query 标记为需配置能力。
- 配置通过前不可绑定到 Agent，配置通过后可进入 Agent 能力选择和 .weagent runtime projection。
- 新增 sandbox adapter，验证配置型 Tool 的最小真实调用链路。
- 更新工具集页面配置窗口、Agent 能力选择器、模型配置自定义输入。
- 补充 006 checkpoint 报告、UAT 指南和 PR handoff。

验证：
- python -m pytest tests\test_default_tool_catalog.py tests\test_tool_provider_config_api.py tests\test_toolset_categories.py -q
- 结果：11 passed
```
