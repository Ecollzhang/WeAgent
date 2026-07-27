# WeAgent - 多 Agent 协作平台

一个基于 IM 聊天界面的多 Agent 协作平台，支持多种 AI Agent 的接入、调度和消息流式输出。

## 技术栈

### 后端
- **框架**: Flask 2.3.x + Flask-SQLAlchemy + Flask-Migrate
- **数据库**: MySQL 8.0 + Redis 7.x
- **认证**: Flask-JWT-Extended (JWT Token)
- **实时通信**: Server-Sent Events (SSE) + 内存队列
- **架构**: Controller → Service → Repository (分层架构)

### 前端
- **核心**: Vue 2.7 + Vue Router 3 + Vuex 3
- **UI**: Element UI
- **HTTP**: Axios

## 环境要求

- Python 3.10+
- Node.js 16+
- MySQL 8.0+
- Redis 7.x

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

### 5. 访问平台

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
| GET | `/api/messages/stream/<id>` | SSE 流式获取新消息 |
| GET | `/api/messages/poll/<id>` | 轮询新消息 |
| GET | `/api/agents` | 获取 Agent 列表 |
| POST | `/api/agents` | 创建自定义 Agent |
| GET | `/api/agents/categories` | 获取 Agent 分类 |
| GET | `/api/artifacts/<id>` | 获取产物详情 |
| POST | `/api/upload` | 上传文件 |
| GET | `/api/health` | 健康检查 |

## 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```
