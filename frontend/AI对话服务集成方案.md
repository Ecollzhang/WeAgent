# AI 对话服务集成方案（修订版）

## 一、决策记录

| # | 问题 | 决策 |
|---|------|------|
| Q1 | 项目绑定策略 | **创建时绑定**，整个对话周期不变，后续可升级为运行时切换 |
| Q2 | 服务摘要详细度 | **能力 + 5~10 个常用接口**（约 500 token/服务），常用接口由各服务 `spec.popular_endpoints` 定义 |
| Q3 | 服务选择 & 认证 | **动态注入服务**：创建对话时多选需要的领域服务，选不同领域 → 不同上下文注入。所有服务统一使用 JWT 认证 |
| Q4 | 上下文获取方式 | **实时查询**：Agent 通过 API 实时获取最新数据，不存储快照 |
| Q5 | 字段可空性 | `project_id` 允许 NULL（不选项目 = 全局视角，Agent 可自行创建项目），在 `migration_v2.sql` 中追加 |
| Q6 | 前端数据来源 | 复用现有 `GET /api/rd/projects` 等接口 |
| Q7 | Spec 格式约束 | 定义 `ServiceSpec` dataclass 放在 `backend/app/sandbox/` 下作为共享约定 |

---

## 二、现状分析

### 2.1 当前架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Vue.js)                                              │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌─────────────┐ │
│  │Dashboard │  │ChatWindow │  │KbSelector  │  │ RD Pages    │ │
│  │(创建对话) │  │(聊天界面) │  │(KB域/文档) │  │(项目管理)   │ │
│  └────┬─────┘  └─────┬─────┘  └─────┬──────┘  └──────┬──────┘ │
└───────┼──────────────┼──────────────┼────────────────┼─────────┘
        │              │              │                │
   POST /api/convs  PATCH /api/convs/{id}/kb      各种 CRUD API
        │              │              │                │
┌───────▼──────────────▼──────────────▼────────────────▼─────────┐
│  Backend (Flask)                                                │
│  ┌────────────────────┐  ┌──────────────────────────────────┐  │
│  │conversation_service│  │  sandbox/host/manager.py          │  │
│  │ _create_agent_     │  │  create_session()                 │  │
│  │ sandbox()          │  │  → 注入 SERVICE_REGISTRY          │  │
│  │ → 构建system_prompt│  │  → 注入 USER_AUTH_TOKEN           │  │
│  │ → 注入kb_context   │  │  → 启动 Docker 容器               │  │
│  └────────┬───────────┘  └──────────────┬───────────────────┘  │
└───────────┼──────────────────────────────┼──────────────────────┘
            │ agents_config, env_vars      │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Docker Container (weagent-sandbox)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Orchestrator (Flask :8080)                              │  │
│  │  ├─ AgentRuntime → claude -p (agent.md)                  │  │
│  │  ├─ ToolRegistry → rag_search / list_services /          │  │
│  │  │                  call_service_api                     │  │
│  │  └─ 每轮对话注入 _tool_instructions                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│     call_service_api("rd", "GET", "/api/rd/projects/xxx")       │
│     call_service_api("rag", "POST", "/api/rag/search", {...})   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 已有基础设施

| 能力 | 状态 | 说明 |
|------|------|------|
| `SERVICE_REGISTRY` 环境变量 | ✅ 已实现 | `{"rag":"...:5104","rd":"...:5101",...}` 注入容器 |
| `list_services` 工具 | ✅ 已实现 | Agent 可列出可用服务 |
| `call_service_api` 工具 | ✅ 已实现 | 通用 HTTP 调用，自动带 JWT |
| `/api/rag/spec` | ✅ 已实现 | RAG 服务自描述 |
| `/api/rd/spec` | ✅ 已实现 | RD 服务自描述 |
| KB 上下文注入 | ✅ 已实现 | `kb_domain` → system_prompt |
| KB 文档过滤 | ✅ 已实现 | `kb_document_ids` → 环境变量 |
| 用户 JWT 传递 | ✅ 已实现 | `USER_AUTH_TOKEN` → 容器环境变量 |

### 2.3 当前缺失

| 缺失 | 影响 |
|------|------|
| 创建对话时无法选择服务 | 用户不能控制 Agent 能访问哪些领域能力 |
| 无项目上下文 | Agent 不知道在哪个 RD 项目下工作 |
| 无用户元数据 | Agent 不知道用户名/角色 |
| 无服务能力摘要 | Agent 每次都要 `GET /spec` 才能了解 API |
| 服务选择无差异化上下文 | 选了 RD 和选 RAG 应该有不同配置项 |

---

## 三、核心设计：动态服务注入

### 3.1 概念模型

```
创建对话时用户选择：
┌─────────────────────────────────────────────┐
│  领域服务（多选）:                           │
│  ☑ RD  ──→  选择项目: [教学管理系统 ▼]      │
│  ☑ RAG ──→  KB领域: [RD ▼]  文档: [...]    │
│  ☐ EDU                                     │
│  ☐ OFFICE                                  │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  后端根据选择构建差异化上下文:                 │
│                                             │
│  RD 被选中  →  注入项目ID + RD服务摘要       │
│  RAG 被选中 →  注入kb_domain + RAG服务摘要   │
│  EDU 被选中 →  注入课程上下文 + EDU服务摘要   │
│  OFFICE 被选中 → 注入文档上下文 + OFFICE摘要  │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Agent system_prompt:                       │
│  ...                                        │
│  用户信息: Ecollzhang (团队管理员)            │
│                                             │
│  项目上下文:                                 │
│  - 项目: 教学管理系统 (id: proj_xxx)         │
│  - 可通过 API 实时查询项目详情                │
│                                             │
│  知识库上下文:                               │
│  - 领域: 智能研发 (rd)                       │
│  - 可用 rag_search 检索文档                  │
│                                             │
│  可用微服务:                                 │
│  1. rd (智能研发) — 常用接口...              │
│  2. rag (知识库) — 常用接口...               │
│  ...                                        │
└─────────────────────────────────────────────┘
```

### 3.2 服务 → 上下文映射表

| 服务 | 创建时可配 | 注入的环境变量 | 注入 prompt 的上下文 |
|------|-----------|---------------|---------------------|
| **RD** | 项目选择（可选） | `RD_PROJECT_ID` | 项目摘要 + RD 服务能力摘要 |
| **RAG** | KB 域 + 文档选择 | `KB_DOCUMENT_IDS` | KB 上下文 + RAG 服务能力摘要 |
| **EDU** | 课程/班级（未来） | `EDU_COURSE_ID` | 课程上下文 + EDU 服务能力摘要 |
| **OFFICE** | 文档/文件夹（未来） | `OFFICE_FOLDER_ID` | 文档上下文 + OFFICE 服务能力摘要 |

> 不选项目时 `RD_PROJECT_ID` 为 NULL，Agent 处于全局视角，可自行调用 API 创建或查询项目。

---

## 四、服务发现协议标准化

### 4.1 ServiceSpec Dataclass（共享约定）

文件位置：`backend/app/sandbox/service_spec.py`

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ServiceEndpoint:
    method: str           # GET / POST / PUT / PATCH / DELETE
    path: str             # /api/{service}/xxx
    description: str      # 一句话描述
    params: Optional[dict] = None   # query 参数说明
    body: Optional[dict] = None     # request body 说明

@dataclass
class ServiceCapability:
    name: str             # 能力名称（如"需求管理"）
    description: str      # 一句话描述

@dataclass
class ServiceSpec:
    service: str                        # 服务名: rd / rag / edu / office
    version: str                        # 语义版本号
    description: str                    # 一句话描述
    base_url: str                       # 服务 base URL
    status: str = "healthy"             # healthy / degraded / unavailable
    capabilities: list[ServiceCapability] = field(default_factory=list)
    popular_endpoints: list[ServiceEndpoint] = field(default_factory=list)  # 5~10 个最常用接口
    all_endpoints: list[ServiceEndpoint] = field(default_factory=list)      # 完整接口列表（/spec 返回）

    def to_dict(self) -> dict:
        """序列化为 JSON，供 /spec 端点返回"""
        ...

    @staticmethod
    def from_dict(data: dict) -> "ServiceSpec":
        """从 JSON 反序列化"""
        ...
```

### 4.2 Spec 端点规范

每个服务 **必须** 提供 `GET /api/{service}/spec`，返回 `ServiceSpec.to_dict()`：

```json
{
  "service": "rd",
  "version": "1.0.0",
  "description": "智能研发领域服务",
  "base_url": "http://host.docker.internal:5101",
  "status": "healthy",
  "capabilities": [
    { "name": "项目管理", "description": "创建和管理研发项目" },
    { "name": "需求管理", "description": "需求的CRUD、状态流转、分配" },
    { "name": "缺陷跟踪", "description": "Bug的CRUD、状态流转、分配" },
    { "name": "迭代管理", "description": "迭代规划与进度跟踪" },
    { "name": "代码审查", "description": "AI辅助代码审查" },
    { "name": "构建管理", "description": "触发和监控CI/CD构建" }
  ],
  "popular_endpoints": [
    { "method": "GET",  "path": "/api/rd/projects",                    "description": "获取项目列表", "params": { "workspace_id": "可选" } },
    { "method": "GET",  "path": "/api/rd/projects/{id}",               "description": "获取项目详情" },
    { "method": "GET",  "path": "/api/rd/projects/{id}/requirements",  "description": "获取需求列表", "params": { "status": "可选", "iteration_id": "可选" } },
    { "method": "POST", "path": "/api/rd/projects/{id}/requirements",  "description": "创建需求",     "body": { "title": "标题", "description": "描述", "priority": "high/medium/low" } },
    { "method": "GET",  "path": "/api/rd/projects/{id}/bugs",          "description": "获取缺陷列表", "params": { "status": "可选", "severity": "可选" } },
    { "method": "POST", "path": "/api/rd/projects/{id}/bugs",          "description": "创建缺陷",     "body": { "title": "标题", "description": "描述", "severity": "critical/major/minor" } },
    { "method": "GET",  "path": "/api/rd/projects/{id}/iterations",    "description": "获取迭代列表" },
    { "method": "GET",  "path": "/api/rd/projects/{id}/builds",        "description": "获取构建列表" },
    { "method": "POST", "path": "/api/rd/projects/{id}/reviews",       "description": "提交代码审查", "body": { "title": "标题", "code_content": "代码", "language": "语言" } }
  ],
  "all_endpoints": [
    { "method": "GET", "path": "/api/rd/projects", "description": "获取项目列表" }
    // ... 全部 40+ 接口
  ]
}
```

**字段说明**：

| 字段 | 用途 | 是否必需 |
|------|------|----------|
| `service` | 服务标识 | ✅ |
| `version` | 版本号 | ✅ |
| `description` | 一句话描述，注入 prompt 摘要 | ✅ |
| `status` | `healthy`/`degraded`/`unavailable`，Agent 据此决定是否调用 | ✅ |
| `capabilities` | 面向 LLM 的能力摘要，比接口列表更易理解 | ✅ |
| `popular_endpoints` | 5~10 个最常用接口，注入 prompt | ✅ |
| `all_endpoints` | 完整接口列表，`/spec` 返回 | ✅ |

### 4.3 健康检查端点（建议实现）

`GET /api/{service}/health`：

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "dependencies": { "database": "connected" }
}
```

### 4.4 统一错误响应

```json
{
  "code": 400,
  "message": "参数错误: title 不能为空",
  "error_type": "validation_error"
}
```

`error_type`: `validation_error` | `not_found` | `permission_denied` | `service_unavailable` | `internal_error`

### 4.5 认证模型

所有服务统一使用 **单一 JWT** 认证：

```
call_service_api 发出的请求:
  Authorization: Bearer {USER_AUTH_TOKEN}
  Content-Type: application/json
```

- 所有微服务共享同一个 JWT secret
- 服务端通过 JWT 解析 `user_id`，进行权限控制
- 不再需要 `X-Internal-API-Key`（简化架构）
  - 保留 `X-Internal-API-Key` 作为可选的内部服务直连通道（如后台任务无用户上下文时使用）

---

## 五、Agent 上下文注入方案

### 5.1 上下文注入总览

```
┌──────────────────────────────────────────────┐
│  Agent system_prompt 结构（改进后）            │
├──────────────────────────────────────────────┤
│  1. Agent 角色定义 (system_prompt)            │
│  2. 协同 Agent 列表 (仅 moderator)            │
│  3. 工作流/技能 (skill)                       │
│  4. [NEW] 用户身份信息                        │
│  5. [NEW] 项目上下文 (若选了 RD + 项目)        │
│  6. [NEW] 知识库上下文 (若选了 RAG)            │
│  7. [NEW] 可用微服务能力摘要 (仅选中服务)       │
│  8. 文件产物要求                              │
│  + WeAgent 工作规范 (agent.py 追加)            │
│  + 工具指令 (每轮 orchestrator 追加)           │
└──────────────────────────────────────────────┘
```

### 5.2 用户身份信息

```text
用户信息:
- 用户名: Ecollzhang
- 角色: 团队管理员
- 你可以通过 call_service_api 以该用户身份调用微服务 API
```

实现：从 JWT 解析 `user_id`，查询数据库获取 `username`、`display_name`，注入 prompt。

### 5.3 项目上下文（当 RD 被选中且指定了项目）

```text
项目上下文:
- 项目名称: 教学管理系统
- 项目 ID: proj_xxx
- 项目描述: 在线教育平台的研发项目
- 你可以通过 call_service_api("rd", ...) 访问该项目的需求、缺陷、迭代、代码仓库等
- 需要最新项目数据时，通过 API 实时查询: GET /api/rd/projects/proj_xxx
```

> 不选项目 → 不注入项目上下文。Agent 可通过 API 获取用户可见的项目列表，或创建新项目。

### 5.4 知识库上下文（当 RAG 被选中）

复用并增强现有逻辑：

```text
知识库上下文:
- 当前领域: 智能研发 (rd)
- 你可以使用 rag_search 工具检索知识库文档
- 检索时建议使用 domain="rd" 参数过滤当前领域文档
- 如果用户问题涉及专业领域知识，优先检索知识库
```

### 5.5 服务能力摘要（仅注入选中的服务）

后端在 `_create_agent_sandbox()` 时，根据 `conversation.services` 列表，调用各服务的 `/spec` 获取 `capabilities` + `popular_endpoints`，组装为摘要注入 prompt：

```text
可用微服务:

1. rd (智能研发服务)
   能力: 项目管理、需求管理、缺陷跟踪、迭代管理、代码审查、构建管理
   常用接口:
   - GET  /api/rd/projects                    — 获取项目列表
   - GET  /api/rd/projects/{id}               — 获取项目详情
   - GET  /api/rd/projects/{id}/requirements  — 获取需求列表
   - POST /api/rd/projects/{id}/requirements  — 创建需求
   - GET  /api/rd/projects/{id}/bugs          — 获取缺陷列表
   - POST /api/rd/projects/{id}/bugs          — 创建缺陷
   - GET  /api/rd/projects/{id}/iterations    — 获取迭代列表
   - GET  /api/rd/projects/{id}/builds        — 获取构建列表
   - POST /api/rd/projects/{id}/reviews       — 提交代码审查
   完整文档: GET /api/rd/spec

2. rag (知识库服务)
   能力: 文档检索、语义搜索
   常用接口:
   - POST /api/rag/search  — 知识库检索 {query, top_k, domain, document_ids}
   完整文档: GET /api/rag/spec
```

> 服务摘要按 `conversation.services` 顺序排列，未选中的服务不出现。

---

## 六、前端：新建对话对话框增强

### 6.1 新增交互流程

```
创建对话的步骤:
┌────────────────────────────────────────┐
│  Step 1: 基本信息                       │
│  会话标题: [自动生成              ]     │
│  选择 Agent: ☑架构师 ☑前端 ☐后端       │
├────────────────────────────────────────┤
│  Step 2: 选择领域服务（多选）            │
│  ☑ 智能研发 (RD)                       │
│  ☑ 知识库 (RAG)                        │
│  ☐ 智慧教育 (EDU)     [待上线]          │
│  ☐ 智慧办公 (OFFICE)   [待上线]          │
├────────────────────────────────────────┤
│  Step 3: 服务配置（根据选择动态展示）     │
│                                        │
│  ┌─ RD 配置 ─────────────────────────┐ │
│  │ 关联项目: [教学管理系统 ▼] (可选)  │ │
│  │ 不选 = 全局视角，可自行创建项目     │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌─ RAG 配置 ────────────────────────┐ │
│  │ 知识库领域: ○ 继承工作空间         │ │
│  │            ○ 全部  ○ RD  ○ EDU    │ │
│  │ 限定文档: [选择特定文档...] (可选)  │ │
│  └──────────────────────────────────┘ │
├────────────────────────────────────────┤
│  预览: 👤 Ecollzhang  🤖架构师 🤖前端  │
│        📋教学管理系统  📚RD知识库       │
├────────────────────────────────────────┤
│              [取消]    [创建会话]       │
└────────────────────────────────────────┘
```

### 6.2 Vue 数据模型

```javascript
// Dashboard.vue data
newConversation: {
  title: '',
  type: 'group',
  selectedAgents: [],
  // [NEW]
  services: [],           // ['rd', 'rag']
  projectId: '',          // RD 项目ID（可选）
  kbDomain: '',           // RAG 知识库域
  kbDocumentIds: [],      // RAG 限定文档
}
```

### 6.3 动态表单逻辑

```javascript
computed: {
  showProjectSelector() {
    return this.newConversation.services.includes('rd')
  },
  showKbSelector() {
    return this.newConversation.services.includes('rag')
  }
},
watch: {
  'newConversation.services'(val) {
    // 取消勾选 RD 时清空项目选择
    if (!val.includes('rd')) this.newConversation.projectId = ''
    // 取消勾选 RAG 时清空 KB 配置
    if (!val.includes('rag')) {
      this.newConversation.kbDomain = ''
      this.newConversation.kbDocumentIds = []
    }
  }
}
```

### 6.4 API 请求体

```json
{
  "title": "用户1、架构师、前端工程师 的对话",
  "type": "group",
  "participant_ids": ["agent_abc123", "agent_def456"],
  "workspace_id": "ws_xxx",
  "services": ["rd", "rag"],
  "project_id": "proj_yyy",
  "kb_domain": "rd",
  "kb_document_ids": ["doc1", "doc2"]
}
```

---

## 七、后端数据模型

### 7.1 Conversation 表新增字段

```sql
-- 在 migration_v2.sql 中追加
ALTER TABLE conversations
  ADD COLUMN services JSON DEFAULT NULL
    COMMENT '启用的领域服务列表，如 ["rd","rag"]';

ALTER TABLE conversations
  ADD COLUMN project_id VARCHAR(36) DEFAULT NULL
    COMMENT '关联的RD项目ID，NULL=全局视角';
```

> 不存 `project_context` 快照 —— Agent 通过 API 实时查询最新数据。

### 7.2 SQLAlchemy 模型

```python
# backend/app/models/conversation.py 新增
services = db.Column(db.JSON, nullable=True, comment='启用的领域服务列表')
project_id = db.Column(db.String(36), nullable=True, comment='关联的RD项目ID')
```

### 7.3 Schema 扩展

```python
# backend/app/schemas/conversation_schema.py
class CreateConversationSchema(Schema):
    # ... 现有字段 ...
    services = fields.List(fields.Str(), required=False,
                           validate=validate.ContainsOnly(['rd', 'rag', 'edu', 'office']))
    project_id = fields.Str(required=False, allow_none=True)
```

---

## 八、后端核心逻辑

### 8.1 `_create_agent_sandbox()` 改造

```python
# backend/app/services/conversation_service.py

def _create_agent_sandbox(conversation, ...):
    env_vars = settings_service.get_container_env_vars(user_id)
    env_vars["USER_AUTH_TOKEN"] = auth_header
    env_vars["CONVERSATION_SERVICES"] = json.dumps(conversation.services or [])
    env_vars["RD_PROJECT_ID"] = conversation.project_id or ""

    # 构建 system_prompt 各模块
    system_prompt_parts = [agent.system_prompt or '']

    # 1. 用户信息
    system_prompt_parts.append(_build_user_context(user))

    # 2. 项目上下文 (仅当 RD 被选中且指定了项目)
    if 'rd' in services and conversation.project_id:
        system_prompt_parts.append(_build_project_context(conversation.project_id))

    # 3. 知识库上下文 (仅当 RAG 被选中)
    if 'rag' in services:
        system_prompt_parts.append(_build_kb_context(conversation))
        if conversation.kb_document_ids:
            env_vars['KB_DOCUMENT_IDS'] = json.dumps(conversation.kb_document_ids)

    # 4. 服务能力摘要 (仅注入选中服务)
    if services:
        system_prompt_parts.append(_build_services_summary(services))

    # ... 后续 agent_config 构建不变


def _build_user_context(user):
    return f"""用户信息:
- 用户名: {user.username}
- 显示名: {user.display_name or user.username}
- 你可以通过 call_service_api 以该用户身份调用微服务 API"""


def _build_project_context(project_id):
    """实时查询项目信息注入 prompt"""
    try:
        from services.rd.services.project_service import project_service
        project = project_service.get_project(project_id)
        if not project:
            return ""
        return f"""项目上下文:
- 项目名称: {project['name']}
- 项目 ID: {project['id']}
- 项目描述: {project.get('description', '暂无描述')}
- 你可以通过 call_service_api("rd", ...) 访问该项目的需求、缺陷、迭代、代码仓库、构建、审查等
- 需要最新数据时通过 API 实时查询，如 GET /api/rd/projects/{project['id']}"""
    except Exception as e:
        current_app.logger.warning(f"查询项目上下文失败: {e}")
        return f"项目 ID: {project_id}（服务暂不可达，稍后可通过 API 查询）"


def _build_services_summary(service_names):
    """根据选中的服务列表构建能力摘要"""
    # 从 SERVICE_REGISTRY 获取 base_url，调用各服务的 /spec，缓存结果
    registry = {
        "rag":  "http://host.docker.internal:5104",
        "rd":   "http://host.docker.internal:5101",
        "edu":  "http://host.docker.internal:5102",
        "office": "http://host.docker.internal:5103",
    }
    lines = ["可用微服务:"]
    for i, name in enumerate(service_names, 1):
        url = registry.get(name, "")
        spec = _fetch_service_spec_cached(name, url)
        if not spec:
            lines.append(f"\n{i}. {name} — 服务暂不可达")
            continue

        caps = ', '.join(c['name'] for c in spec.get('capabilities', []))
        lines.append(f"\n{i}. {name} ({spec.get('description', '')})")
        lines.append(f"   能力: {caps}")

        popular = spec.get('popular_endpoints', [])
        if popular:
            lines.append("   常用接口:")
            for ep in popular:
                lines.append(f"   - {ep['method']:6s} {ep['path']:45s} — {ep['description']}")

        lines.append(f"   完整文档: GET /api/{name}/spec")

    return '\n'.join(lines)
```

### 8.2 Spec 缓存

为避免每次创建会话都调用多个服务的 `/spec`，加入简单的内存缓存：

```python
# backend/app/services/conversation_service.py

_spec_cache = {}  # {service_name: (spec_dict, expire_time)}

def _fetch_service_spec_cached(name, base_url, ttl=300):
    """获取服务 spec，带 5 分钟缓存"""
    import time
    now = time.time()
    if name in _spec_cache:
        cached, expire = _spec_cache[name]
        if now < expire:
            return cached
    try:
        resp = requests.get(f"{base_url}/api/{name}/spec", timeout=5,
                           headers={"Authorization": USER_AUTH_TOKEN})
        if resp.status_code == 200:
            spec = resp.json().get('data', resp.json())
            _spec_cache[name] = (spec, now + ttl)
            return spec
    except Exception:
        pass
    return None
```

---

## 九、Agent 端使用流程

### 场景：用户说 "帮我查一下教学管理系统有哪些未处理的高优先级缺陷"

**改进前**（5 个 round-trip）：
```
→ list_services()
→ call_service_api("rd", "GET", "/api/rd/spec")
→ call_service_api("rd", "GET", "/api/rd/projects")        // 不知道项目ID
→ 人工匹配找到项目ID
→ call_service_api("rd", "GET", "/api/rd/projects/{id}/bugs?...")
```

**改进后**（1 个 round-trip）：
```
(system_prompt 已有: 项目ID=proj_xxx, RD 服务接口摘要)
→ call_service_api("rd", "GET",
    "/api/rd/projects/proj_xxx/bugs?severity=critical&status=open")
→ 返回 3 条缺陷 → 组织回复
```

### 场景：用户说 "帮我创建一个新项目叫 电商平台"

**改进前**：Agent 不知道有没有 RD 服务，需要先发现再查 spec
**改进后**：Agent 已知道 RD 服务存在且有 `POST /api/rd/projects` 接口

```
→ call_service_api("rd", "POST", "/api/rd/projects",
    {"name": "电商平台", "description": "...", "workspace_id": "ws_xxx"})
→ 返回项目详情 → 回复用户
```

---

## 十、chat_window 服务状态展示

```
┌──────────────────────────────────────────────────────┐
│  📋 教学管理系统   📚 RD知识库(3文档)   🔗 RD● RAG●  │
└──────────────────────────────────────────────────────┘
```

- 点击项目名 → 跳转 `/rd/projects/proj_xxx`
- 点击知识库 → 打开 KB 文档选择器
- 服务状态指示灯：● 健康  ○ 不可用

数据来源：`conversation.services` + `conversation.project_id` + `conversation.kb_domain`

---

## 十一、实现计划

### Phase 1: 协议 + 后端（本次）

| # | 内容 | 涉及文件 |
|---|------|----------|
| 1.1 | 定义 `ServiceSpec` dataclass | `backend/app/sandbox/service_spec.py` (**新建**) |
| 1.2 | Conversation 表 + 模型增加 `services`, `project_id` | `backend/app/models/conversation.py`, `migration_v2.sql` |
| 1.3 | 创建对话 Schema 增加 `services`, `project_id` | `backend/app/schemas/conversation_schema.py` |
| 1.4 | RD `/spec` 标准化（使用 ServiceSpec，增加 capabilities、popular_endpoints） | `backend/services/rd/main.py` |
| 1.5 | RAG `/spec` 标准化（同上） | `backend/services/rag/app.py` |
| 1.6 | RD `/health` 端点 | `backend/services/rd/main.py` |
| 1.7 | RAG `/health` 端点 | `backend/services/rag/app.py` |
| 1.8 | `_create_agent_sandbox()` 注入用户信息 | `backend/app/services/conversation_service.py` |
| 1.9 | `_create_agent_sandbox()` 注入项目上下文 | `backend/app/services/conversation_service.py` |
| 1.10 | `_create_agent_sandbox()` 注入服务能力摘要（按选中服务） | `backend/app/services/conversation_service.py` |
| 1.11 | 新增 `CONVERSATION_SERVICES`、`RD_PROJECT_ID` 环境变量注入 | `backend/app/services/conversation_service.py` |
| 1.12 | `call_service_api` 工具升级：统一 JWT，去掉 Internal-API-Key 强依赖 | `backend/app/sandbox/container/tools/__init__.py` |

### Phase 2: 前端（后续）

| # | 内容 | 涉及文件 |
|---|------|----------|
| 2.1 | 新建对话弹窗增加服务多选 | `frontend/src/views/Dashboard.vue` |
| 2.2 | 动态项目选择器（选 RD 时展示） | `frontend/src/views/Dashboard.vue` |
| 2.3 | 动态 KB 配置（选 RAG 时展示） | `frontend/src/views/Dashboard.vue` |
| 2.4 | 聊天窗口顶部服务/项目上下文栏 | `frontend/src/components/ChatWindow/index.vue` |
| 2.5 | 服务状态指示灯 | `frontend/src/components/ChatWindow/index.vue` |
| 2.6 | 前端 API 模块更新 | `frontend/src/api/conversation.js` |

### Phase 3: EDU & OFFICE 集成（后续）

| # | 内容 |
|---|------|
| 3.1 | EDU/OFFICE 实现 `/spec` + `/health`，使用 ServiceSpec |
| 3.2 | 注册到 SERVICE_REGISTRY |
| 3.3 | 前端服务选择器中启用 EDU/OFFICE 选项 |
| 3.4 | 各服务的差异化上下文配置（EDU→课程，OFFICE→文件夹） |

---

## 十二、风险与注意事项

| 风险 | 缓解措施 |
|------|----------|
| Token 消耗增加（每服务约 500 token） | 仅注入选中服务；2 个服务约 1000 token，可接受 |
| `/spec` 调用增加创建会话延迟 | 内存缓存（TTL 5min），首次创建约 +200ms |
| 服务不可达时 spec 获取失败 | 降级：prompt 中标注"服务暂不可达"，Agent 会跳过或提示用户 |
| 项目被删除后 ID 失效 | Agent 通过 API 实时查询会发现 404，引导用户重新选择 |
| EDU/OFFICE 未上线 | 前端标注 `[待上线]`，后端 SERVICE_REGISTRY 中初始不包含 |
