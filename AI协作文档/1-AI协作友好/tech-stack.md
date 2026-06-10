# Tech Stack

> 本文件记录项目实际使用的技术栈与关键依赖。所有技术决策以此为准。

---

## 后端

| 项 | 实际使用 | 注意事项 |
|----|---------|---------|
| 语言 | Python 3.10+ | — |
| 框架 | Flask 2.3.3 | 不要替换为 FastAPI |
| ORM | Flask-SQLAlchemy 3.1.1 | — |
| 认证 | Flask-JWT-Extended 4.5.3 | JWT Token |
| 实时通信 | Flask-SocketIO 5.3.4 | SocketIO，非 SSE |
| 序列化 | Marshmallow / Flask-Marshmallow | — |
| 数据库 | MySQL 8.0 + Redis 7.x | — |
| 容器 | Docker SDK（docker>=7.0） | Agent 运行沙箱 |

### 后端目录分层

```
Controller → Service → Repository → Model
```

| 层 | 职责 | 不负责 |
|----|------|--------|
| Controller | API 路由、请求校验、响应 | 不含业务逻辑 |
| Service | 业务编排、多步操作 | 不含 HTTP 细节 |
| Repository | 数据查询与持久化 | 不含业务编排 |
| Model | 数据库表映射 | — |

---

## 前端

| 项 | 实际使用 | 注意事项 |
|----|---------|---------|
| 框架 | Vue 2.7.15 | 不要升级到 Vue 3 |
| 构建 | Vue CLI（vue-cli-service） | 非 Vite |
| UI 组件库 | Element UI 2.15.14 | 非 Naive UI |
| 状态管理 | Vuex 3 | — |
| 路由 | Vue Router 3 | — |
| HTTP | Axios 1.6.2 | — |
| 实时通信 | Socket.IO Client 4.7.2 | — |
| 代码编辑器 | CodeMirror 5.65.0 | Monaco 编辑器未启用 |

### 前端组件组织

```
components/{功能名}/index.vue
```

每个功能组件放在同名目录下，目录内包含 `index.vue` 作为入口。

---

## 桌面端

| 项 | 内容 |
|----|------|
| 框架 | Electron 29 + Vite |
| 定位 | 独立客户端，仅连接外部后端，不内置后端 |

---

## Android 端

| 项 | 内容 |
|----|------|
| 框架 | Capacitor + Vue 2.7 + Vite |
| 定位 | 通过 WebView 连接后端 API |

---

## 开发约束

- 所有新依赖必须显式加到 `requirements.txt`（后端）或 `package.json`（前端）
- 不要轻易替换的基础设施：Flask、MySQL、Redis、Docker
- Agent 容器镜像名：`weagent-sandbox:latest`
- 前端开发服务器端口：8080；后端端口：5000

---

## 常见命令

| 用途 | 命令 |
|------|------|
| 启动后端 | `cd backend && python run.py`（Windows: `venv\Scripts\python run.py`）|
| 后端虚拟环境 | Linux/Mac: `source venv/bin/activate`；Windows: `venv\Scripts\activate` |
| 启动前端 | `cd frontend && npm run serve`（默认 http://localhost:8080）|
| 构建 Docker 镜像 | `cd backend && docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox` |
| 桌面端开发 | `cd clients/desktop && npm run dev` |
| Android 端开发 | `cd clients/android && npm run dev` |
| 数据库迁移（初始化） | `cd backend && flask db init && flask db migrate -m "init" && flask db upgrade` |
| Debug 日志 | `cd backend && Get-Content debug.log -Wait -Tail 30`（Powershell）|

---

## 自我迭代

> 版本：v1.0 | 最后更新：2026-06-08 | 更新人：zby

### 修改流程

1. 技术栈变更（新增依赖、框架升级、端口变更）时更新本文件
2. 更新后 bump 版本号并修改日期
3. 修改需至少一人 review 确认

### 触发条件

- 新增后端/前端/客户端依赖
- 框架版本升级
- 基础设施变更（数据库、消息队列等）
- 启动方式或端口变化
