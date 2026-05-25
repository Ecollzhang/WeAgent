# WeAgent Sandbox — Docker 容器化多 Agent 沙箱

## 架构概述

```
┌─────────────────────────────────────────────────────────────────────┐
│ 宿主机 (你的系统)                                                    │
│                                                                     │
│  Flask API ←→ Docker SDK ←→ Docker Container(s)                     │
│                                                                     │
│  POST /api/sandbox/sessions  ──→ docker run ...                      │
│  POST /api/sandbox/sessions/xxx/send ──→ HTTP → localhost:17xxx     │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
                   ▼ (docker run, port mapping)
┌─────────────────────────────────────────────────────────────────────┐
│ Docker 容器 (1 会话 = 1 容器)                                        │
│                                                                     │
│  Port 8080 ──→ Orchestrator Server (Flask)                          │
│                  │                                                   │
│               Agent 管理器                                           │
│               ├── Agent A (产品经理)  → claude 持久进程              │
│               ├── Agent B (前端)      → claude 持久进程              │
│               └── Agent C (后端)      → claude 持久进程              │
│                  │                                                   │
│              工具注册表 ←→ 工具脚本 (web_search, progress, ...)      │
│                  │                                                   │
│              会话持久化 → /workspace/.session/history.jsonl          │
│                                                                     │
│  Volume: /workspace/ ←→ 宿主机 /data/weagent/sessions/{conv_id}/   │
│    ├── projects/     Agent 创建的前后端项目                          │
│    ├── tools/        注入的工具脚本                                  │
│    ├── outputs/      Agent 输出产物                                  │
│    └── .session/     持久化对话历史 (容器删了还在)                   │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心原则

- **1 会话 = 1 Docker 容器**：每个对话窗口对应一个独立容器
- **Agent = `claude` 持久进程**：每个 Agent 是一个 `claude` 子进程，通过 stdin/stdout 通信
- **Volume 持久化**：项目文件、对话历史、Agent 配置全部存在 volume 中，容器销毁不丢失
- **工具注入**：通过 volume 或 `put_archive` 将工具脚本传入容器
- **Orchestrator 内部路由**：Agent 间不直接通信，通过 Orchestrator 中转

## 数据流

### 创建会话
```
用户 → POST /api/sandbox/sessions
  → DockerManager.create_session(user_id, conv_id, agents_config)
    → docker run -d --rm -p 8080 -v /data/...:/workspace weagent-sandbox
    → 容器内 OrchestratorServer 启动 (Flask :8080)
    → DockerManager 为每个 agent 调用 POST /agents/create
      → 容器内启动 claude 子进程
  → 返回 container_id, port, agents
```

### 发送消息
```
用户 → POST /api/sandbox/sessions/{id}/send {agent_id, message}
  → DockerManager.send_message(session_id, agent_id, message)
    → HTTP POST localhost:{port}/api/agents/{agent_id}/send {message}
    → 容器内 Orchestrator 查找 agent
      → 构建上下文 (其他 agent 的最新输出)
      → 拼接完整 prompt → 发给 Claude 进程 (stdin)
      → 从 stdout 读取回复
      → 保存到 .session/history.jsonl
    → HTTP 返回回复文本
  → 返回给用户
```

### Agent 间协作
```
用户请求 "做一个登录功能"
  → 发给 Agent A (产品经理)
    → A 输出 PRD
    → Orchestrator 保存到 history
  → 把 A 的输出作为 context，发给 Agent B (前端)
    → B 输出前端代码
  → 把 A 的输出作为 context，发给 Agent C (后端)
    → C 输出后端代码
  → 汇总返回
```

### 持久会话 (下次继续问)
```
用户再次打开会话
  → DockerManager 检查容器是否在运行
    → 是 → 直接复用
    → 否 → docker start 或重跑容器
      → 容器启动 → Orchestrator 读取 .session/config.json
      → 重新创建 Agent 进程 (传入角色 prompt)
      → 从 .session/history.jsonl 重放历史给 Claude
      → 可以继续对话
```

## 目录结构

```
backend/app/sandbox/
├── __init__.py              模块入口
├── host/
│   ├── __init__.py
│   ├── manager.py           Docker 容器生命周期管理
│   └── client.py            宿主机→容器的 HTTP 客户端
├── container/               以下代码会被打包进 Docker 镜像
│   ├── __init__.py
│   ├── server.py            容器内 Orchestrator HTTP 服务
│   ├── agent.py             ClaudeRuntime (claude 持久进程)
│   ├── orchestrator.py      多 Agent 管理器 + 路由
│   ├── tools.py             工具注册与执行
│   └── session.py           会话持久化
├── api/
│   ├── __init__.py
│   └── routes.py            宿主机端 Flask 蓝图
├── Dockerfile               容器镜像定义
└── tools/
    └── builtin/              内置工具脚本 (注入到容器)
        ├── web_search.py
        └── progress.py
```

## 容器镜像依赖

| 组件 | 安装方式 |
|------|---------|
| Python 3.11 | 基础镜像 `python:3.11-slim` |
| Node.js | apt-get |
| Claude CLI | `npm install -g @anthropic-ai/claude-code` |
| Flask | pip install (供 orchestrator server 使用) |
| requests | pip install (供工具脚本 HTTP 回调) |

## 宿主机依赖

| 组件 | 用途 |
|------|------|
| Python `docker` SDK | 管理容器生命周期 |
| Docker Desktop | 运行容器 |
