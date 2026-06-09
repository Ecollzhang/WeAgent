# WeAgent Sandbox

`backend/app/sandbox/` 是 WeAgent 的 Docker 沙箱模块。正式 Agent 会话会创建独立容器，容器内运行 Orchestrator Server，宿主后端通过 HTTP 调用容器内接口。

## 核心模型

```text
用户创建会话
  -> Flask 后端创建 Conversation
  -> DockerContainerManager 创建 Docker 容器
  -> 容器内启动 Orchestrator Server (:8080)
  -> 宿主端注入能力投影和 Agent 配置
  -> 用户消息通过 Socket.IO / REST 进入容器
  -> Agent 在 /workspace 下生成文件、表格、服务和日志
```

## 目录说明

```text
backend/app/sandbox/
├─ api/routes.py              # 宿主后端暴露给前端的沙箱 API
├─ host/
│  ├─ manager.py              # Docker 生命周期、文件读写、服务代理
│  └─ client.py               # 宿主端访问容器 Orchestrator 的 HTTP client
├─ container/
│  ├─ server.py               # 容器内 Flask Orchestrator HTTP 服务
│  ├─ orchestrator.py         # 多 Agent 管理、消息路由、产物上报
│  ├─ agent.py                # Agent Runtime
│  ├─ capabilities.py         # 能力投影、Skill/Tool/Plugin/MCP 运行时
│  ├─ providers/              # Claude Code / Codex / OpenCode runner
│  ├─ tools/                  # 内置工具实现
│  └─ service_manager.py      # 容器内预览服务管理
├─ bin/
│  ├─ weagent-report          # Agent 上报结构化产物
│  └─ weagent-service         # 启动/上报预览服务
└─ Dockerfile
```

## 构建镜像

```powershell
cd backend
python -c "from app.sandbox import build_image; build_image()"
```

等价命令：

```powershell
cd backend
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

修改以下内容后需要重建镜像：

- `backend/app/sandbox/Dockerfile`
- `backend/app/sandbox/container/**`
- `backend/app/sandbox/bin/**`
- 容器内 Python/Node/CLI 依赖

## 容器运行时

镜像内包含：

- Python 3.11
- Node.js 20
- Claude Code CLI
- OpenAI Codex CLI
- OpenCode CLI
- `codex-relay`
- Flask / requests / simple-websocket

容器工作目录：

```text
/workspace
├─ agents/<workspace_name>/   # 每个 Agent 的工作目录
├─ shared/                    # 多 Agent 可共享目录
└─ .weagent/                  # 平台内部状态和日志
```

## 宿主端 API

前端访问宿主后端：

```text
/api/sandbox/sessions/<session_id>/files/tree
/api/sandbox/sessions/<session_id>/files/raw
/api/sandbox/sessions/<session_id>/services
/api/sandbox/sessions/<session_id>/services/<service_id>/logs
/api/sandbox/sessions/<session_id>/services/<service_id>/proxy/
```

这些路由在 `api/routes.py` 中定义，实际读写由 `host/manager.py` 完成。

## 容器内 Orchestrator API

宿主端通过 `host/client.py` 调用容器内接口：

```text
GET  /api/health
POST /api/capabilities/projection
POST /api/agents/create
POST /api/agents/<agent_id>/send
POST /api/agents/delegate
GET  /api/files/tree
GET  /api/files/raw
GET  /api/services
POST /api/services/start
GET  /api/services/<service_id>/logs
```

注意：如果当前 `weagent-sandbox:latest` 是旧镜像，可能缺少 `/api/capabilities/projection`。宿主端已对这个可选接口做兼容跳过，但工具集能力完整投影需要重建镜像。

## 常见问题

### Docker image not found

错误：

```text
Docker image 'weagent-sandbox:latest' not found
```

处理：

```powershell
cd backend
python -c "from app.sandbox import build_image; build_image()"
```

### 创建容器时 HTTP 404

如果错误类似：

```text
创建沙箱容器失败：HTTP 404: <!doctype html> ...
```

通常是宿主后端调用了容器内旧镜像不存在的新接口。处理顺序：

1. 重启后端，确保加载最新 `host/manager.py` 和 `host/client.py`。
2. 重建 `weagent-sandbox:latest`。
3. 停掉旧的 `weagent-*` 容器后重试。

排查命令：

```powershell
docker images weagent-sandbox:latest
docker ps --filter name=weagent
curl http://localhost:<orchestrator_port>/api/health
```

### 容器可以创建，但 Agent 无响应

检查：

- 用户模型配置是否保存。
- 容器环境变量是否注入。
- 对应 provider CLI 是否可用。
- 容器日志和服务日志。

```powershell
docker logs <container_id>
docker exec -it <container_id> sh
```

### 文件或 HTML 预览打不开

检查：

- 文件路径必须在 `/workspace/` 下。
- 前端请求应走宿主 `/api/sandbox/sessions/...` 代理。
- HTML 静态资源相对路径应与文件所在目录一致。

## 开发注意事项

- 宿主端 Python 代码修改后需要重启后端。
- 容器端代码修改后需要重建镜像。
- 新增容器内接口时，建议在 `host/client.py` 增加清晰错误处理。
- 对旧镜像可选功能应做兼容，但核心接口失败应抛出明确错误。
- 涉及沙箱的改动，需要回归：创建会话、发送消息、文件查看、HTML 预览、服务日志、工作流展示。
