# Checkpoint G/H Report: UAT Guide, Regression, and Cleanup

日期：2026-06-02

## 已完成

### UAT 指南

新增：

- `006-CONFIGURABLE-TOOLS-UAT-GUIDE.zh-CN.md`

覆盖：

- 前端页面如何打开。
- 工具集页面如何查看需配置能力。
- 如何创建、测试、保存、启用、停用 provider profile。
- 如何用自动化命令验证真实 runtime 链路。
- 当前边界和后续真实 provider/Docker 注意事项。

### 自动化验证

后端全量通过：

```powershell
cd backend
python -m pytest -q
```

结果：

```text
102 passed
```

前端契约通过：

```powershell
cd frontend
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
node tests\tool-provider-config-ui-contract.test.js
node tests\capability-ui-contract.test.js
```

结果：

```text
toolset UI contract ok
agent capability selector contract ok
tool provider config UI contract ok
capability UI contract ok
```

前端构建通过：

```powershell
cd frontend
npm run build
```

结果：构建成功，仍有既有 bundle 体积 warning：

- `img/bg.d0047cc4.png`
- `js/chunk-vendors.aad3cdea.js`
- app entrypoint size

### Docker Smoke 状态

已执行轻量 Docker smoke。

执行：

```powershell
docker info --format "Docker daemon ready: {{.ServerVersion}}"
docker image ls weagent-sandbox:latest
docker build -t weagent-sandbox:latest backend\app\sandbox
docker run --rm -e PYTHONPATH=/app weagent-sandbox:latest python -c "from container.tools import ToolRegistry, register_builtin_tools; r=ToolRegistry('/workspace'); register_builtin_tools(r); names={t['name'] for t in r.list_tools()}; print(sorted(names & {'web_search','image_analysis','image_generate','database_query'}))"
```

结果：

```text
Docker daemon ready: 29.5.2
['database_query', 'image_analysis', 'image_generate', 'web_search']
```

说明：

- sandbox 镜像已重新 build，包含本轮 container adapter 改动。
- Docker 内部已能注册四个配置型 Tool adapter。
- 完整端到端 Docker Agent 会话 smoke 仍建议后续配合真实后端/前端/数据库会话手工执行。

## 006 完成状态

已完成：

- Checkpoint A: 默认 Tool 可见性和可绑定性。
- Checkpoint C: Provider profile 数据模型和 API。
- Checkpoint D: 前端配置窗口真实交互。
- Checkpoint E/F: runtime projection 和四个配置型 Tool adapter。
- Checkpoint G/H: UAT 指南、回归验证和过程报告。

仍建议后续单独开任务：

- 真实外部 provider secret vault。
- MySQL/Postgres 外部 DB driver。
- 真实视觉模型和图像生成模型 provider。
- 标准 Docker compose/fixture provider smoke。
