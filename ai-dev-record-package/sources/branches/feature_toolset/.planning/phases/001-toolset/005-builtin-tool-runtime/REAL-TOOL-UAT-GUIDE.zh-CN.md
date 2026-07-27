# 005 内置 Tool Runtime 真实环境验收指南

## 目标

验证内置 Tool 不再只是工具集卡片，而是能被 Agent 绑定、投影到 `.weagent/*`、按权限调用，并写入调用记录。

## 前置条件

- 当前分支：`feature/toolset`
- 后端可用：`http://127.0.0.1:5001/api/health`
- 前端可用：`http://localhost:8080/`
- Docker 可用，并能启动 WeAgent sandbox。
- 已登录平台账号。

## 需要重点观察的页面

打开工具集页面：

```text
http://localhost:8080/tools
```

逐个点击分类：

- 代码工具
- 文件与文档
- 网络与检索
- 数据处理
- 图像/多媒体
- 系统与终端
- 自定义

验收点：

- 每个功能分类至少有一个 Tool 显示 `已实现`。
- `自定义`分类可以为空或显示用户导入项；它不是必须内置执行 Tool 的功能分类。
- `代码生成`、`网页搜索`、`数据库查询`、`图像分析` 等未完整接入项不能显示为“已实现”。
- 内置 Tool 详情中没有编辑/删除入口。
- 内置 Tool 文件页能看到 `TOOL.md`、`tool-definition.json`、`manifest.json`。

## 分类与代表 Tool

| 分类 | 代表 Tool | 预期状态 |
|---|---|---|
| 代码工具 | 代码搜索 / 代码审查 | 已实现 |
| 文件与文档 | 文件操作 / 文档解析 | 已实现 |
| 网络与检索 | 网页抓取 / API调用 | 已实现 |
| 数据处理 | 数据分析 | 已实现 |
| 图像/多媒体 | 图像信息 | 已实现 |
| 系统与终端 | 终端执行 / Git操作 | 已实现 |
| 自定义 | 用户自建/导入 Tool | 不要求内置 Tool |

## 创建 Agent 并绑定 Tool

1. 打开“我的 Agent”。
2. 新建或编辑一个测试 Agent。
3. 在工具能力选择区域勾选代表 Tool，例如：
   - 代码搜索
   - 文件操作
   - 数据分析
   - 图像信息
   - 终端执行
4. 保存 Agent。
5. 确认保存后再刷新 Agent 页面，绑定仍然存在。

## 启动 Sandbox 后检查投影文件

启动一次会话/sandbox 后，检查 workspace 中是否存在：

```text
/workspace/.weagent/tools/<runtime_id>/TOOL.md
/workspace/.weagent/tools/<runtime_id>/manifest.json
/workspace/.weagent/agents/<agent_id>/tool-index.json
/workspace/.weagent/agents/<agent_id>/capabilities.json
/workspace/.weagent/agents/<agent_id>/permissions.json
```

验收点：

- `tool-index.json` 只包含该 Agent 绑定的 Tool。
- `TOOL.md` 是给 Agent 阅读的使用说明。
- `manifest.json` 包含 `schema_version: weagent.tool/v1`、`handler`、`tool_names`、`permissions`、`ui.status`。

## 建议的真实调用样例

### 代码工具

让 Agent 调用代码搜索：

```json
{"name":"code_search","args":{"query":"TODO","path":"","max_results":20}}
```

预期：

- 返回 `matches`。
- 没有匹配时返回空列表，而不是报错。
- call record 中 `tool_name = code_search`。

### 文件与文档

读取一个 Markdown 或文本文件：

```json
{"name":"document_text_extract","args":{"path":"README.md","max_chars":4000}}
```

预期：

- 返回 `text`。
- 不支持的二进制文档会明确报错。

### 网络与检索

抓取已知 URL：

```json
{"name":"http_fetch","args":{"url":"https://example.com","max_bytes":20000}}
```

预期：

- 有网络权限时返回 `status_code` 和 `body_preview`。
- 没有 `network` 授权时拒绝执行。

### 数据处理

对 CSV 文件做 profile：

```json
{"name":"csv_profile","args":{"path":"data/sample.csv"}}
```

预期：

- 返回 `columns`、`row_count`、`empty_counts`、`sample_rows`。

### 图像/多媒体

读取图像元信息：

```json
{"name":"image_info","args":{"path":"assets/logo.png"}}
```

预期：

- 返回 `format`、`mime_type`、`size`、`width`、`height`。
- OCR/图像理解不属于本阶段。

### 系统与终端

执行受限命令：

```json
{"name":"run_command_safe","args":{"command":"echo hello","timeout":10}}
```

预期：

- 返回 `exit_code = 0` 和 stdout。
- 包含 `;`、`&&`、`|`、重定向、删除、移动、安装依赖等高风险命令会被拒绝。

Git 只读：

```json
{"name":"git_status","args":{}}
```

预期：

- 返回 Git 状态。
- 不允许 commit、push、checkout 等写操作。

## 验证调用记录

在 sandbox workspace 中查看：

```text
/workspace/.weagent/runs/<run_id>/calls.jsonl
```

每条记录应包含：

- `session_id`
- `run_id`
- `agent_id`
- `capability_id`
- `capability_version_id`
- `call_type`
- `tool_name`
- `permissions_used`
- `input_summary`
- `output_summary`
- `status`
- `error`
- `started_at`
- `completed_at`

## 负向验收

必须验证以下失败路径：

- Agent 未绑定某 Tool 时调用该 Tool：应拒绝。
- Agent 未授权所需权限时调用该 Tool：应拒绝。
- `deferred` 或 `requires_config` Tool：应拒绝。
- `run_command_safe` 中出现 shell 操作符或高风险命令：应拒绝。
- `sqlite_query_readonly` 中出现写入 SQL：应拒绝。

## 通过标准

- 每个功能分类至少一个已实现 Tool 能完成真实调用。
- Tool 调用前必须经过 Agent 绑定和权限授权。
- 成功调用和失败调用都能形成审计记录。
- 页面不会把未实现 Tool 展示成可调用能力。
