# 沙箱服务代理与项目预览方案

## 目标

Agent 在沙箱容器内完成项目开发后，可以启动项目服务，并把一个可访问 URL 返回给前端。前端和外部系统通过这个 URL 访问容器内服务。

第一版只做后端代理，不做 Docker 真实端口映射。

目标能力：

- 一个 session 对应一个容器，服务生命周期跟 session 绑定。
- 一个 session 内允许同时运行多个服务。
- 支持前端 dev server 和轻量后端服务：
  - Vue / Vite
  - React
  - Next
  - Flask
  - FastAPI
- 前端能拿到服务 URL，并能在新窗口或 iframe 中访问。
- 服务访问需要登录态、token 和过期控制。
- Agent 可以通过工具或 `weagent-report` 上报服务产物卡片。

## 非目标

第一版不做这些事情：

- 不直接暴露宿主机真实端口，例如 `http://host:30001`。
- 不支持运行中容器动态新增 Docker `-p` 端口映射。
- 不支持公网隧道、frp、ngrok。
- 不做 Kubernetes / Docker Compose 编排。
- 不把服务进程做成长期生产部署，只作为 session 内的预览服务。

## 总体架构

外部访问链路：

```text
Browser / External System
  -> Host Backend
  -> Sandbox Container Server
  -> 127.0.0.1:{service_port}
```

示例 URL：

```text
/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/?token={preview_token}
```

如果访问容器内服务的静态资源：

```text
/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/assets/index.css?token={preview_token}
```

这样不需要容器暴露真实端口，所有访问都通过已有后端鉴权和代理链路完成。

## 核心对象

### Service

服务记录绑定到 session。

```json
{
  "id": "svc_xxx",
  "session_id": "session_xxx",
  "agent_id": "frontend",
  "name": "商城前端预览",
  "type": "vite",
  "cwd": "/workspace/agents/frontend",
  "command": "npm run dev -- --host 0.0.0.0 --port 5173",
  "port": 5173,
  "status": "running",
  "pid": 123,
  "proxy_url": "/api/sandbox/sessions/session_xxx/services/svc_xxx/proxy/",
  "preview_token": "preview_xxx",
  "token_expires_at": "2026-05-30T12:00:00Z",
  "created_at": "2026-05-30T10:00:00Z",
  "updated_at": "2026-05-30T10:01:00Z",
  "last_error": "",
  "logs_tail": []
}
```

### Service 状态

```text
created
starting
running
failed
stopped
exited
```

状态含义：

- `created`：服务记录已创建，但还未启动。
- `starting`：进程已启动，等待端口健康检查。
- `running`：端口可访问。
- `failed`：启动失败或健康检查失败。
- `stopped`：用户主动停止。
- `exited`：进程自行退出。

## 容器内设计

容器内新增 ServiceManager，负责服务进程生命周期。

职责：

- 启动服务进程。
- 停止服务进程。
- 重启服务进程。
- 查询服务状态。
- 收集 stdout / stderr 日志。
- 做端口健康检查。
- 把服务信息通过 API 返回给 host backend。

容器内 API：

```text
POST   /api/services/start
POST   /api/services/{service_id}/stop
POST   /api/services/{service_id}/restart
GET    /api/services
GET    /api/services/{service_id}
GET    /api/services/{service_id}/logs
ANY    /api/services/{service_id}/proxy/<path>
```

启动请求：

```json
{
  "agent_id": "frontend",
  "name": "商城前端预览",
  "type": "vite",
  "cwd": "/workspace/agents/frontend",
  "command": "npm run dev -- --host 0.0.0.0 --port 5173",
  "port": 5173,
  "env": {}
}
```

启动响应：

```json
{
  "status": "ok",
  "service": {
    "id": "svc_xxx",
    "status": "running",
    "port": 5173,
    "proxy_url": "/api/services/svc_xxx/proxy/"
  }
}
```

## Host Backend 设计

Host backend 负责把前端请求路由到目标 session 容器。

Host API：

```text
POST   /api/sandbox/sessions/{session_id}/services/start
POST   /api/sandbox/sessions/{session_id}/services/{service_id}/stop
POST   /api/sandbox/sessions/{session_id}/services/{service_id}/restart
GET    /api/sandbox/sessions/{session_id}/services
GET    /api/sandbox/sessions/{session_id}/services/{service_id}
GET    /api/sandbox/sessions/{session_id}/services/{service_id}/logs
ANY    /api/sandbox/sessions/{session_id}/services/{service_id}/proxy/<path>
POST   /api/sandbox/sessions/{session_id}/services/{service_id}/token
```

Host backend 做这些校验：

- 用户必须有当前 session 的访问权限。
- preview token 必须有效。
- preview token 未过期。
- service 必须属于当前 session。
- proxy path 不能访问非目标服务。

## 代理设计

代理目标：

```text
http://127.0.0.1:{service.port}/{path}
```

代理要求：

- 保留 method：GET / POST / PUT / DELETE / OPTIONS。
- 透传 query string。
- 透传 request body。
- 透传大部分响应 header。
- 过滤危险 header：
  - `Host`
  - `Connection`
  - `Transfer-Encoding`
  - `Upgrade` 第一版可先不支持，WebSocket 阶段再打开。
- 支持 HTML / CSS / JS / image / font / JSON。
- 支持重定向改写。

第一版只支持 HTTP。WebSocket / HMR 放到后续阶段。

## URL 和 Token

服务启动后生成 preview token。

URL 示例：

```text
/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/?token={preview_token}
```

Token 规则：

- token 绑定 `session_id + service_id + user_id`。
- token 有过期时间，默认 2 小时。
- 用户主动刷新 token 时，旧 token 可立即失效。
- session 销毁时，所有 token 失效。
- 服务停止时，token 不一定失效，但 proxy 返回服务不可用。

是否需要登录态：

- 登录用户访问：校验登录态 + session 权限。
- 外部系统访问：使用 token。
- 如果同时有登录态和 token，二者满足其一即可，具体可由配置控制。

推荐默认策略：

```text
登录态访问：允许
token 访问：允许，但必须未过期
匿名无 token：拒绝
```

## Agent 协议

Agent 生成项目后，如果用户要求运行/预览/部署，应执行：

1. 确认项目目录。
2. 安装依赖。
3. 选择端口。
4. 启动服务。
5. 上报 service 产物。
6. 最终回复用户服务地址。

新增 `weagent-report` 类型：`service`。

```json
{
  "type": "service",
  "title": "商城前端预览",
  "content": "服务已启动，可以访问预览页面",
  "status": "running",
  "data": {
    "service_id": "svc_xxx",
    "name": "商城前端预览",
    "port": 5173,
    "url": "/api/sandbox/sessions/session_xxx/services/svc_xxx/proxy/?token=preview_xxx"
  }
}
```

也可以提供内部工具：

```text
start_service(name, cwd, command, port, type)
stop_service(service_id)
restart_service(service_id)
list_services()
get_service_logs(service_id)
```

推荐优先实现 HTTP API，再把工具封装给 Agent 使用。

## 前端设计

ChatWindow 需要展示服务产物卡片。

服务卡片内容：

- 服务名称。
- 服务状态。
- 运行端口。
- 访问 URL。
- 打开预览按钮。
- iframe 预览按钮。
- 复制链接按钮。
- 查看日志按钮。
- 停止按钮。
- 重启按钮。
- 刷新 token 按钮。

服务卡片应该作为产物展示，不应该折叠进进度。

建议 UI：

```text
┌───────────────────────────────┐
│ 商城前端预览       running    │
│ Port: 5173                    │
│ /api/sandbox/.../proxy/       │
│ [打开] [预览] [日志] [重启] [停止] │
└───────────────────────────────┘
```

## 支持框架

### Vite / Vue / React

启动命令：

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

### Next

启动命令：

```bash
npm run dev -- -H 0.0.0.0 -p 3000
```

### Flask

启动命令：

```bash
flask run --host 0.0.0.0 --port 5000
```

### FastAPI

启动命令：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 多服务策略

同一个 session 可以运行多个服务。

端口分配规则：

- Agent 可以指定端口。
- 如果端口被占用，ServiceManager 自动选择下一个可用端口。
- 推荐端口范围：
  - 前端：5173、5174、3000、3001
  - Flask：5000、5001
  - FastAPI：8000、8001
- 每个 service_id 绑定最终实际端口。

冲突处理：

```text
请求端口 5173 被占用
-> 尝试 5174
-> 更新 service.port
-> 返回实际 URL
```

## 日志策略

每个服务有独立日志文件：

```text
/workspace/.session/services/{service_id}/stdout.log
/workspace/.session/services/{service_id}/stderr.log
/workspace/.session/services/{service_id}/meta.json
```

前端日志接口返回 tail：

```json
{
  "service_id": "svc_xxx",
  "stdout_tail": "...",
  "stderr_tail": "...",
  "status": "running"
}
```

## 安全策略

必须做：

- 校验 session 权限。
- 校验 service 属于 session。
- 校验 token 和过期时间。
- proxy path 禁止访问非 HTTP 服务。
- 启动命令 cwd 必须在 `/workspace` 下。
- 不允许服务启动命令访问宿主机路径。
- 停止 session 时停止所有服务。

可选增强：

- 限制每 session 最大服务数。
- 限制每服务最大运行时间。
- 限制日志大小。
- 限制代理请求体大小。
- 限制只允许代理到 service.port。

## 分阶段实现

### 阶段 1：容器内 ServiceManager（已实现）

目标：

- 支持启动、停止、重启、列表、日志。
- 服务生命周期跟 session 绑定。
- 支持多服务。

实现内容：

- 新增 `container/service_manager.py`。
- 在 `Orchestrator` 中持有 `ServiceManager`。
- 增加容器内 `/api/services/*` 接口。
- 服务元信息写入 `/workspace/.session/services/`。

测试：

- 启动 `python -m http.server 5173`。
- 验证状态从 `starting` 到 `running`。
- 验证停止服务后进程退出。
- 验证多个服务可同时运行。

实现文件：

- `backend/app/sandbox/container/service_manager.py`
- `backend/app/sandbox/container/orchestrator.py`
- `backend/app/sandbox/container/server.py`
- `backend/tests/test_sandbox_service_manager_stage1.py`

### 阶段 2：Host 服务管理 API（已实现）

目标：

- 前端可以通过 host backend 管理 session 内服务。

实现内容：

- 在 host client 中增加 services API。
- 在 host manager/controller 中增加路由。
- 根据 `session_id` 找到目标容器并转发。
- 管理接口统一使用 `service_id`，避免继续把容器内端口当作服务身份。
- Host 不再依赖预映射 `service_ports` 启停服务，服务真实运行状态以容器内 `ServiceManager` 为准。
- 支持获取单个服务、停止、重启、读取日志。

测试：

- 创建 session。
- 调用 host API 启动服务。
- 调用 host API list services。
- 调用 host API stop service。
- 调用 host API get/restart/logs service。

实现文件：

- `backend/app/sandbox/host/client.py`
- `backend/app/sandbox/host/manager.py`
- `backend/app/sandbox/api/routes.py`
- `backend/tests/test_sandbox_service_host_stage2.py`

### 阶段 3：HTTP Proxy（已实现）

目标：

- 前端可以通过 URL 访问容器内服务。

实现内容：

- 容器内实现 service proxy。
- Host backend 实现 session service proxy。
- 支持 query、body、headers、状态码透传。
- 支持常见静态资源 MIME。
- Host proxy URL：`/api/sandbox/sessions/{session_id}/services/{service_id}/proxy/<path>`。
- Host 代理到容器 orchestrator，容器再代理到 `http://127.0.0.1:{service.port}/<path>`。
- 管理 API 返回的 service 会附带 `proxy_url`，前端后续可以直接展示访问入口。
- 已过滤 hop-by-hop header，避免 `Connection`、`Transfer-Encoding`、`Upgrade` 等破坏代理响应。
- 已支持 30x `Location` 改写，容器内相对跳转会回到同一个 proxy URL 前缀。
- 第一版仍只支持 HTTP；WebSocket/HMR 继续放到阶段 7。

测试：

- 代理访问 HTML。
- 代理访问 CSS / JS。
- 代理访问图片。
- 代理访问 JSON API。
- 验证不存在服务返回 404。
- 验证服务停止后返回 502。
- 验证 query string、request body、状态码和 response header 透传。
- 验证 redirect `Location` 改写。

实现文件：

- `backend/app/sandbox/container/server.py`
- `backend/app/sandbox/host/client.py`
- `backend/app/sandbox/host/manager.py`
- `backend/app/sandbox/api/routes.py`
- `backend/tests/test_sandbox_service_proxy_stage3.py`

### 阶段 4：Token 和权限（已实现）

目标：

- 支持带 token、过期、登录态。

实现内容：

- 为 service 生成 preview token。
- token 存储在后端数据库或 session meta。
- proxy 校验登录态或 token。
- 增加刷新 token API。
- token 当前存储在 host session meta 中，绑定 `session_id + service_id + user_id`，默认 2 小时过期。
- 每个 service 同时保留一个有效 token；刷新 token 会让旧 token 立即失效。
- 管理 API 返回的 `proxy_url` 默认带 `?token=...`，外部系统可直接访问。
- proxy 支持 `?token=`、`X-Preview-Token`、以及服务 proxy path 下的 `weagent_preview_token` Cookie。
- 首次使用 query/header token 成功访问时，会写入 HttpOnly path-scoped Cookie，保证页面内相对资源请求继续可访问。
- proxy 会移除转发到容器服务的 `token` query 参数，避免 preview token 泄露给用户项目。
- 登录态访问会通过 JWT 获取 `user_id`，并在存在 `Conversation.sandbox_session_id` 时校验会话 owner。

测试：

- 登录态访问成功。
- 无登录态但 token 有效访问成功。
- token 过期访问失败。
- token 不属于 service 访问失败。
- session 销毁后访问失败。
- 刷新 token 后旧 token 失效。
- 无 token 且无登录态访问 proxy 返回 401。

实现文件：

- `backend/app/sandbox/host/manager.py`
- `backend/app/sandbox/api/routes.py`
- `backend/tests/test_sandbox_service_token_stage4.py`

### 阶段 5：前端服务卡片（已实现）

目标：

- ChatWindow 展示服务产物。

实现内容：

- 支持 `service` 类型消息元素。
- 展示状态、URL、端口、日志、停止、重启。
- 支持 iframe 预览。
- 支持复制链接。
- `service` 元素作为产物卡片展示，不进入进度折叠区。
- 服务卡片兼容 `service_id/id`、`proxy_url/url`、`service/data` 嵌套结构。
- 服务抽屉已同步切换到 `service_id` 后端接口，并支持打开、复制、日志、停止、重启。
- sandbox 前端 API 会携带登录 JWT，刷新 token API 可识别登录态。

测试：

- service artifact 持久化后刷新仍显示。
- 点击打开能访问项目。
- 停止服务后卡片状态更新。
- 日志面板能显示 stdout/stderr。
- 前端生产构建通过。

实现文件：

- `frontend/src/components/MessageBubble/index.vue`
- `frontend/src/views/Dashboard.vue`
- `frontend/src/api/sandbox.js`

### 阶段 6：Agent 工具和指令（已实现）

目标：

- Agent 能主动启动项目服务并上报。

实现内容：

- 给 Agent 注入 `start_service` 工具说明。
- 或者允许 Agent 调用容器内服务启动 API。
- `weagent-report` 支持 `service` 类型。
- 任务完成时将 service artifact 持久化到 message。

实现结果：

- 新增容器内命令 `weagent-service`，支持 `start/list/stop/restart/logs`。
- `weagent-service start` 会调用容器 `/api/services/start` 启动服务，并自动通过 `/api/report` 上报 `type=service` 产物。
- `weagent-report` 和容器 `Orchestrator._normalize_report_element` 都已支持 `service` 类型、`running/starting/stopping/failed/exited` 等服务状态，并校验 `data.service_id`。
- `SandboxEventBridge` 收到 `agent_report_element` 的 `service` 产物后，会在入库和推送前向 host manager 查询服务，并补充带 preview token 的 `proxy_url/url`。
- Agent 运行时提示词已写入 `weagent-service start` 使用方式，要求服务绑定 `0.0.0.0` 和明确端口。
- Docker 镜像构建时会把 `weagent-service` 复制到 `/usr/local/bin/weagent-service`。

测试：

- 让 Agent 生成 Vite 项目并启动。
- 前端收到 service 卡片。
- raw output 中包含访问地址。
- 刷新页面后 service artifact 仍存在。

自动化测试：

- `backend/tests/test_sandbox_service_agent_stage6.py`
  - `weagent-report` 接受合法 service payload。
  - `weagent-report` 拒绝缺少 `data.service_id` 的 service payload。
  - 容器 orchestrator 能归一化 service report。
  - host event bridge 能为 service element 补充带 token 的 `proxy_url`。
  - `weagent-service start` 能自动上报 service 卡片。

### 阶段 7：WebSocket / HMR（已实现）

目标：

- 支持 Vite / Next dev server 的 HMR。

实现内容：

- Host proxy 支持 WebSocket upgrade。
- Container proxy 支持 WebSocket upgrade。
- 必要时重写 HMR client URL。

实现结果：

- Host service proxy 在收到 `Upgrade: websocket` 时，不再走普通 HTTP 代理，改为接受浏览器 WebSocket 并连接容器 WebSocket proxy。
- Container service proxy 在收到 `Upgrade: websocket` 时，连接到容器内 `ws://127.0.0.1:{service.port}/{path}`。
- Host 和 Container 两段代理都使用 `simple-websocket` 做双向消息转发，支持文本和二进制消息。
- WebSocket 代理复用阶段 4 的 preview token 校验；HTTP 首次访问设置的 preview cookie 可供后续 HMR WebSocket 使用。
- WebSocket 转发会过滤 `Connection/Upgrade/Sec-WebSocket-*` 等握手头，由代理端重新建立上游握手。
- 当前没有强制改写 Vite/Next client URL；在 iframe 或新窗口使用同源 proxy URL 访问时，HMR 默认会连接当前 host/path，优先保持透明代理。
- Docker 镜像构建时安装 `simple-websocket`，后端 `requirements.txt` 也显式声明该依赖。

测试：

- Vite 页面打开后无 WebSocket 报错。
- 修改文件后 HMR 生效。
- Next dev server 可访问。

自动化测试：

- `backend/tests/test_sandbox_service_websocket_stage7.py`
  - Host client 能构造 `ws://.../api/services/{service_id}/proxy/...` 上游地址并双向转发消息。
  - Host route 能识别 WebSocket upgrade，校验 token 后委托 manager 代理。
  - Container route 能把 WebSocket 连接转发到 `ws://127.0.0.1:{service.port}/...`。

## 推荐优先级

第一轮实现顺序：

```text
阶段 1 -> 阶段 2 -> 阶段 3 -> 阶段 4 -> 阶段 5 -> 阶段 6 -> 阶段 7
```

原因：

- 先跑通服务启动和代理访问。
- 再接前端展示和 Agent 上报。
- token 可以在代理可用后补上。
- WebSocket/HMR 是体验增强，不影响第一版可访问。

如果必须一开始就支持外部系统访问，则阶段 4 提前到阶段 3 后立刻做。

## 验收标准

基础验收：

- Agent 生成一个 Vite 项目。
- Agent 启动服务。
- 前端出现服务卡片。
- 点击服务 URL 可以访问页面。
- 刷新前端后服务卡片仍存在。
- 同一个 session 同时运行两个服务。
- 停止 session 后所有服务停止。

安全验收：

- 未登录不能访问未公开服务。
- token 过期不能访问。
- token 不能跨 session 使用。
- service_id 不能跨 session 使用。

稳定性验收：

- 服务启动失败时前端能看到错误日志。
- 服务进程退出后状态变为 `exited`。
- 重启服务后 URL 仍可访问。
- 大文件资源不会把后端内存打爆。
