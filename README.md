# WeAgent - 多 Agent 协作平台

一个基于 IM 聊天界面的多 Agent 协作平台，支持多种 AI Agent 的接入、调度和消息流式输出。

## 技术栈

### 后端
- **框架**: Flask 2.3.x + Flask-SQLAlchemy + Flask-Migrate
- **数据库**: MySQL 8.0 + Redis 7.x
- **认证**: Flask-JWT-Extended (JWT Token)
- **实时通信**: Flask-SocketIO
- **架构**: Controller → Service → Repository (分层架构)

### 前端
- **核心**: Vue 2.7 + Vue Router 3 + Vuex 3
- **UI**: Element UI
- **HTTP**: Axios

### 桌面端
- **核心**: Electron 29 + Vite + Vue 2.7
- **打包**: electron-builder
- **定位**: 独立桌面客户端，仅连接外部后端服务，不内置后端

## 环境要求

- Python 3.10+
- Node.js 16+
- MySQL 8.0+
- Redis 7.x
- Docker Desktop（Agent 容器运行必需）

Docker Desktop 需要提前安装并保持运行，后端会通过 Docker SDK 为每个正式对话创建独立容器。启动项目前可先检查 Docker 是否可用：

```bash
docker version
docker info
```

## Agent 容器环境

正式 Agent 对话依赖 `weagent-sandbox:latest` 镜像。该镜像位于 `backend/app/sandbox/Dockerfile`，会安装：

- Python 3.11
- Node.js 20
- Claude Code CLI（`@anthropic-ai/claude-code`）
- 容器内 Orchestrator 运行依赖（Flask、requests）

每个对话对应一个 Docker 容器，容器内工作目录为 `/workspace`。单 Agent 会在 `/workspace/agents/<agent名称>/` 下工作，多 Agent 后续会在此基础上加入共享目录。当前 Docker workspace 不做持久化，删除对话或销毁容器后容器内文件会随之清理。

首次运行或修改了 `backend/app/sandbox/container/`、`backend/app/sandbox/Dockerfile` 后，需要重新构建 Agent 镜像：

```bash
cd backend
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

也可以在安装后端依赖后使用项目封装的构建入口：

```bash
cd backend
python -c "from app.sandbox import build_image; build_image()"
```

Agent 调用模型所需的 API Key、Base URL、模型名等配置来自前端 Settings 页面保存的模型配置。创建 Agent 对话前，请先登录系统并在 Settings 中完成模型配置；后端创建容器时会把配置注入到容器环境变量中。

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd WeAgent
```

### 2. 数据库初始化

```bash
# 创建数据库（MySQL 8.0+）
mysql -u root -p
CREATE DATABASE IF NOT EXISTS weagent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

# 导入表结构
mysql -u root -p weagent < backend/sql/init.sql
```

### 3. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 构建 Agent 沙箱镜像（Docker Desktop 需处于运行状态）
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库和 Redis 配置

# Flask 数据库迁移（在已有表基础上创建迁移版本）
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 启动服务
python run.py
```

后端默认运行在 `http://localhost:5000`

### 4. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run serve
```

前端默认运行在 `http://localhost:8080`

### 5. 桌面端启动与打包

桌面端代码位于 `clients/desktop`，使用 Electron 承载独立的 Vue 客户端。桌面端不内置后端，启动后需要配置后端服务地址；局域网测试时可以填写类似 `http://192.168.1.8:5000` 的地址，本机测试可以填写 `http://127.0.0.1:5000`。

```bash
cd clients/desktop

# 安装依赖
npm install

# 开发调试
npm run dev

# 打包 Windows 桌面应用
npm run electron:build
```

打包产物默认输出到：

```text
clients/desktop/release/
```

常用产物：

- `WeAgent Setup 0.1.0.exe`：Windows 安装包
- `win-unpacked/WeAgent.exe`：免安装可执行程序
- `WeAgent-win-unpacked.zip`：免安装版本压缩包

桌面端应用名为 `WeAgent`，图标来源为 `clients/desktop/logo.png`，打包时会自动生成 Windows 使用的 `logo.ico`。为避免国内网络访问 GitHub 下载 NSIS / winCodeSign 失败，桌面端打包脚本已默认使用 `npmmirror` 的 electron-builder 二进制镜像，并跳过 Windows exe 资源编辑/签名步骤。

如果必须让 Windows 资源管理器中的 exe 文件图标也被完整写入资源，请在 Windows 中启用“开发者模式”或以管理员身份打包，再恢复 `signAndEditExecutable` 配置。

### 6. 访问平台

打开浏览器访问 `http://localhost:8080`

## 项目结构

```
WeAgent/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── controllers/        # 控制器层（API 路由）
│   │   ├── services/           # 业务逻辑层
│   │   ├── repositories/       # 数据访问层
│   │   ├── models/             # 数据库模型
│   │   ├── schemas/            # 序列化/校验
│   │   ├── adapters/           # Agent 适配器
│   │   └── utils/              # 工具函数
│   ├── sql/
│   │   └── init.sql            # 数据库表结构初始化脚本
│   ├── config.py
│   └── run.py
├── frontend/                   # 前端代码
│   └── src/
│       ├── api/                # API 请求封装
│       ├── components/         # 公共组件
│       ├── views/              # 页面视图
│       ├── store/              # Vuex 状态管理
│       └── router/             # 路由配置
├── clients/
│   └── desktop/                # Electron 桌面端客户端
│       ├── electron/           # Electron 主进程与 preload
│       ├── scripts/            # 桌面端构建辅助脚本
│       ├── src/                # 桌面端 Vue 页面与服务封装
│       ├── logo.png            # 桌面端应用图标源文件
│       └── package.json        # 桌面端依赖与打包配置
├── .gitignore
└── README.md
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| PUT | `/api/auth/profile` | 更新用户信息 |
| GET | `/api/conversations` | 获取会话列表 |
| POST | `/api/conversations` | 创建会话 |
| GET | `/api/conversations/<id>` | 获取会话详情 |
| DELETE | `/api/conversations/<id>` | 删除会话 |
| POST | `/api/messages` | 发送消息 |
| GET | `/api/messages/conversation/<id>` | 获取消息历史 |
| POST | `/api/messages/<id>/pin` | 置顶/取消置顶消息 |
| GET | `/api/messages/stream/<id>` | SSE 兼容接口 |
| GET | `/api/messages/poll/<id>` | 轮询兼容接口 |
| GET | `/api/agents` | 获取 Agent 列表 |
| POST | `/api/agents` | 创建自定义 Agent |
| GET | `/api/agents/categories` | 获取 Agent 分类 |
| GET | `/api/artifacts/<id>` | 获取产物详情 |
| POST | `/api/upload` | 上传文件 |
| GET | `/api/sandbox/status` | 查看沙箱运行状态 |
| POST | `/api/sandbox/image/build` | 构建 Agent 沙箱镜像 |
| GET | `/api/sandbox/sessions/<id>/files/tree` | 查看容器工作目录 |
| GET | `/api/health` | 健康检查 |

## SocketIO 事件

正式聊天实时通信以 SocketIO 为主。前端加入会话房间后接收 Agent 流式输出和状态变化：

| 事件 | 方向 | 说明 |
|------|------|------|
| `join` | 前端 → 后端 | 加入指定 conversation room |
| `leave` | 前端 → 后端 | 离开指定 conversation room |
| `send_message` | 前端 → 后端 | 发送用户消息 |
| `conversation_message_created` | 后端 → 前端 | 创建用户或 Agent 消息 |
| `conversation_message_element_stream` | 后端 → 前端 | 流式追加结构化消息元素 |
| `conversation_message_step` | 后端 → 前端 | 推送 Agent 执行步骤 |
| `conversation_message_status` | 后端 → 前端 | 推送消息状态变化 |

## 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```
