# 006 可配置工具验收指南

适用分支：`feature/toolset`

## 你要验证什么

这轮 006 的重点不是新增一个普通工具卡片，而是验证“需配置能力”真的能走完整生命周期：

1. 平台能展示需配置 Tool。
2. 用户能创建 provider profile。
3. 用户能测试、保存、启用、停用配置。
4. 配置启用后，该 Tool 才能绑定到 Agent。
5. 绑定后的 Tool 能进入 `.weagent/*` runtime projection。
6. sandbox 能调用配置型 Tool，并写入 call record。

## 启动页面

后端默认地址：

```text
http://127.0.0.1:5001
```

前端默认地址：

```text
http://localhost:8080
```

常规启动方式：

```powershell
cd backend
python run.py
```

另一个终端：

```powershell
cd frontend
npm run serve
```

打开浏览器：

```text
http://localhost:8080
```

如果你没有账号，先在注册页创建账号；如果已有账号，直接登录。

## 页面验收步骤

### 1. 工具目录可见性

进入“工具集”页面后检查：

- `代码生成` 不应该作为默认 Tool 出现在列表里。
- `网页搜索`、`图像分析`、`图像生成`、`数据库查询` 应该显示为需配置能力。
- 没有配置前，这些 Tool 不应该出现在新建/编辑 Agent 的可绑定能力选择器里。

### 2. 创建配置

在“工具集”页面点击一个需配置 Tool，例如“网页搜索”。

右侧详情中点击“配置能力”。

在弹窗中填写：

```json
{
  "endpoint": "https://example.com/search"
}
```

点击“保存”。

预期结果：

- 弹窗中的“已保存配置”出现一条记录。
- 状态为 `draft`。

### 3. 测试配置

点击“测试配置”。

预期结果：

- 对 HTTP provider，只要 endpoint 是 `http://` 或 `https://` 开头，静态测试通过。
- 通过后 `last_test_status` 为 `passed`。
- 状态仍可以是 `draft`，因为还没有启用。

### 4. 启用配置

点击“启用”或“保存并启用”。

预期结果：

- profile 状态变成 `valid`。
- 工具列表刷新后，该 Tool 的 `configured_profiles_count` 应为 1。
- 该 Tool 现在可以进入 Agent 能力绑定流程。

### 5. 停用配置

点击“停用”。

预期结果：

- profile 状态变成 `disabled`。
- 工具列表刷新后，该 Tool 的 `configured_profiles_count` 回到 0。
- 新的 Agent 绑定不应再允许选择该 Tool。

## 自动化真实运行验收

页面验收只证明“用户配置链路”可用。真实运行链路用后端测试验证：

```powershell
cd backend
python -m pytest tests\test_configured_tool_runtime_gate.py -q
```

这个测试会真实完成：

- 创建并启用 `web_search`、`image_analysis`、`image_generation`、`database_query` 的 provider profile。
- 绑定到 Agent。
- 生成 `.weagent/*` projection。
- 写入 run snapshot。
- 在 sandbox ToolRegistry 中调用 4 个工具。
- 检查 `.weagent/runs/<run_id>/calls.jsonl` 写入 4 条调用记录。

成功结果：

```text
1 passed
```

## Docker 镜像轻量验收

确认 Docker daemon：

```powershell
docker info --format "Docker daemon ready: {{.ServerVersion}}"
```

重新构建 sandbox 镜像：

```powershell
docker build -t weagent-sandbox:latest backend\app\sandbox
```

确认镜像中已经注册四个配置型 Tool adapter：

```powershell
docker run --rm -e PYTHONPATH=/app weagent-sandbox:latest python -c "from container.tools import ToolRegistry, register_builtin_tools; r=ToolRegistry('/workspace'); register_builtin_tools(r); names={t['name'] for t in r.list_tools()}; print(sorted(names & {'web_search','image_analysis','image_generate','database_query'}))"
```

成功结果：

```text
['database_query', 'image_analysis', 'image_generate', 'web_search']
```

## 全量回归命令

后端：

```powershell
cd backend
python -m pytest tests\test_capability_models.py tests\test_capability_service.py tests\test_capability_api.py tests\test_capability_projection.py tests\test_capability_tool_audit.py tests\test_default_tool_catalog.py tests\test_tool_provider_config_api.py tests\test_configured_tool_runtime_gate.py -q
```

前端：

```powershell
cd frontend
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
node tests\tool-provider-config-ui-contract.test.js
npm run build
```

## 当前已知边界

- “测试配置”当前是静态校验，不直接调用真实第三方 provider。
- `image_analysis` 和 `image_generate` 的 runtime adapter 是 deterministic fixture，用来验证运行链路，不等同于真实模型生成。
- `database_query` 的 runtime smoke 支持 SQLite fixture；MySQL/Postgres 外部连接还需要后续 secret vault 和 driver 接入。
- 真实 Docker Agent 容器验收仍然依赖当前项目的 Docker Desktop、后端、前端、数据库和 Redis 运行状态。
