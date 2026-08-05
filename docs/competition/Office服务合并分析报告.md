# Office 服务合并分析报告

> 分支 `feature/smart-office-collaboration` → 合并到当前分支，提交 `d0948b9`

---

## 一、Office 服务概览

Office 是一个独立的 Flask 微服务，端口 **5103**，数据库 **`weagent_office`**（MySQL）。

### 1.1 目录结构

```
backend/services/office/
├── app.py                          # 入口, /api/office/spec, 启动时补列
├── config.py                       # SERVICE_NAME=weagent-office, PORT=5103
├── extensions.py                   # db = SQLAlchemy()
├── seed_data.py                    # 9 个公文模板种子数据
├── sql/
│   ├── 001_initial_schema.sql      # 7 表 (meetings/action_items/schedules/documents/receipts/templates/approvals)
│   └── 002_organization_collaboration.sql  # 4 表 (departments/groups/members/notifications)
├── models/ (11 表)
│   ├── base.py                     # OfficeBaseModel (UUID PK + created_at/updated_at)
│   ├── meeting.py                  # office_meetings
│   ├── action_item.py              # office_action_items
│   ├── schedule.py                 # office_schedules
│   ├── official_document.py        # office_documents
│   ├── document_receipt.py         # office_document_receipts
│   ├── document_template.py        # office_doc_templates
│   ├── approval.py                 # office_approvals
│   └── organization.py             # office_departments/groups/members/notifications
├── controllers/ (6 蓝图)
│   ├── meeting_controller.py       # CRUD + 确认/纪要/行动项
│   ├── schedule_controller.py      # CRUD + 冲突检测
│   ├── document_controller.py      # CRUD + 提交/发布/签收
│   ├── template_controller.py      # 模板 CRUD
│   ├── approval_controller.py      # 审批流转
│   └── organization_controller.py  # 三级组织架构 + 通知
└── services/ (6 服务)
    ├── meeting_service.py
    ├── schedule_service.py
    ├── document_service.py
    ├── approval_service.py
    ├── organization_service.py
    └── helpers.py
```

### 1.2 11 张数据库表

| 表 | 说明 |
|----|------|
| `office_meetings` | 会议（含纪要、转写、材料） |
| `office_action_items` | 行动项（关联会议） |
| `office_schedules` | 个人日程 |
| `office_documents` | 公文（含收件人、审批人） |
| `office_document_receipts` | 公文签收记录 |
| `office_doc_templates` | 公文模板 |
| `office_approvals` | 审批流程（多步骤串行/并行） |
| `office_departments` | 部门（每 workspace 一个） |
| `office_groups` | 小组 |
| `office_members` | 组织成员（member/team_lead/department_head） |
| `office_notifications` | 站内通知 |

---

## 二、主服务（weagent）集成点

### 2.1 蓝图注册 — `backend/app/__init__.py`

新增 3 个蓝图（行 508/525/526）：

```python
from app.controllers.office_ai_controller import office_ai_bp
from app.controllers.user_directory_controller import user_directory_bp

app.register_blueprint(office_ai_bp, url_prefix='/api/office-ai')
app.register_blueprint(user_directory_bp)
```

- `office_ai_bp`：提供 `/api/office-ai/meeting-draft`、`/api/office-ai/document-draft`、`/api/office-ai/weekly-draft` 三个 AI 起草接口，调用用户配置的 LLM 生成草稿文本
- `user_directory_bp`：提供 `/user-directory` 搜索接口，Office 用它在邀请成员时查找真实账号

### 2.2 新增控制器/服务 — 主服务内

| 文件 | 说明 |
|------|------|
| `backend/app/controllers/office_ai_controller.py` | AI 起草路由 |
| `backend/app/services/office_ai_service.py` | AI 起草逻辑（调 LLM） |
| `backend/app/controllers/user_directory_controller.py` | 用户目录搜索 |
| `backend/app/services/domain_base.py` | 领域服务基类（Office 继承此项） |

### 2.3 服务注册 — 4 个文件

所有位置均硬编码 `office → 5103`：

| 文件 | 位置 | 内容 |
|------|------|------|
| `backend/app/services/conversation_service.py` | 行 24 | `SERVICE_REGISTRY_URLS["office"] = "http://host.docker.internal:5103"` |
| `backend/app/services/conversation_service.py` | 行 28 | `SERVICE_DISPLAY_NAMES["office"] = "智慧办公"` |
| `backend/app/sandbox/service_spec.py` | 行 113 | `SERVICE_REGISTRY["office"] = "http://host.docker.internal:5103"` |
| `backend/app/sandbox/host/manager.py` | 行 249 | 容器 env `SERVICE_REGISTRY` JSON 含 office |
| `backend/app/controllers/domain_proxy_controller.py` | 行 9 | `DOMAIN_SERVICE_PORTS["office"] = 5103` |

### 2.4 Agent prompt 注入 — `conversation_service.py`

`_build_services_summary()` 新增 office 分支（行 98-105）：当会话勾选 office 服务时，向 Agent 系统提示注入 office 卡片格式指引和流行 API 端点。

office 卡片类型定义：
```json
{"type":"office_card","data":{"id":"...","kind":"meeting/action_item/document/approval","title":"...","status":"...","summary":"...","meta":{...}}}
```

### 2.5 卡片类型注册 — 3 个文件

| 文件 | 改动 |
|------|------|
| `backend/app/sandbox/container/orchestrator.py` | `REPORT_TYPES` + `DOMAIN_CARD_TYPES` 加入 `office_card`（行 1558/1625） |
| `backend/app/sandbox/container/agent.py` | 上报类型列表 + `office_card` 格式示例（行 90/104-105） |
| `backend/app/sandbox/bin/weagent-report` | 同上（行 18/66） |

### 2.6 数据库迁移 — `backend/sql/migration_v2.sql`

- `domain` 列注释改为 `'rd / edu / office'`（workspaces/grayscale_config）
- 新增 office 灰度配置（见第四部分）
- 新增 office 默认工作空间种子数据

### 2.7 模型 schema 变更 — 主服务

| 文件 | 改动 |
|------|------|
| `backend/app/models/workspace.py` | `domain` 注释含 `office` |
| `backend/app/models/grayscale_config.py` | `domain` 注释含 `office` |
| `backend/app/models/conversation.py` | `kb_domain` 注释含 `office`；`services` 注释含 `office` |
| `backend/app/models/toolset_category.py` | `domain` 列注释含 `office` |
| `backend/app/models/agent.py` | `domain` 列注释含 `office` |
| `backend/app/models/agent_category.py` | `domain` 列注释含 `office` |
| `backend/app/models/capability.py` | `domain` 列注释含 `office` |
| `backend/app/schemas/conversation_schema.py` | `kb_domain` 校验加入 `'office'`；`services` 校验加入 `'office'` |

### 2.8 Agent 分类 & 工具集分类

- `backend/app/services/agent_service.py`：新增 `OFFICE_SYSTEM_AGENTS`（5个系统Agent：公文撰写助手、会议助理、报表分析助手、邮件起草助手、日程管理助手）和 5 个 office Agent 分类，领域隔离
- `backend/app/services/toolset_category_service.py`：新增 3 个 office 工具分类（公文处理/会议管理/报表分析）

### 2.9 对话管理

- `backend/app/services/workspace_service.py`：`VALID_DOMAINS = ('rd','edu','office')`
- `backend/app/services/grayscale_service.py`：office 加入合法 domain 列表
- `backend/app/controllers/grayscale_controller.py`：同上

### 2.10 数据库初始化 — `__init__.py`

- `_migrate_existing_tables()`：`domain` 列注释改为 `'rd / edu / office'`
- `_seed_grayscale_configs()`：新增 office domain 灰度 configs，common 域 `domains` JSON 都含 `'office'`
- `_seed_default_workspaces()`：新增 `('office', '我的办公空间', ...)`

---

## 三、前端集成点

### 3.1 新增文件

| 文件 | 用途 |
|------|------|
| `frontend/src/api/office.js` | Office API 封装，走 `/domain/office/*` 代理 |
| `frontend/src/store/modules/office.js` | Office Vuex 模块（~30 actions） |
| `frontend/src/views/OfficeDocumentsDense.vue` | 公文审批页面（路由 `/documents`） |
| `frontend/src/views/OfficeMeetingTasks.vue` | 会议任务页面（路由 `/meetings`） |
| `frontend/src/views/OfficeWorkspace.vue` | 多功能页面（路由 `/approvals`、`/schedules`） |
| `frontend/src/views/OfficeOrganizationCompact.vue` | 组织协同页面（路由 `/organization`） |
| `frontend/src/views/OfficeNotifications.vue` | 通知页面（路由 `/notifications`） |
| `frontend/src/views/OfficeDocuments.vue` | **（未路由，僵尸文件）** |
| `frontend/src/views/OfficeTasks.vue` | **（未路由，僵尸文件）** |
| `frontend/src/views/OfficeScheduleDense.vue` | **（未路由，僵尸文件）** |
| `frontend/src/views/OfficeOrganization.vue` | **（未路由，僵尸文件）** |

### 3.2 修改文件

| 文件 | 改动 |
|------|------|
| `frontend/src/router/index.js` | 行 160-186：7 个 office 路由 + 2 个重定向 |
| `frontend/src/store/index.js` | 行 10：注册 `office` 模块 |
| `frontend/src/components/Sidebar/index.vue` | 行 102-106：`DOMAIN_NAV.office`（3项） |
| `frontend/src/views/Dashboard.vue` | 行 19/374/416/459：office 领域卡片、服务多选框、上下文标签 |
| `frontend/src/components/MessageBubble/index.vue` | 行 189/595/667/2285：`office_card` 渲染 + 路由跳转 |
| `frontend/src/components/ChatWindow/index.vue` | KB domain 标签增加 office |
| `frontend/src/components/KbDocumentSelector/index.vue` | 领域 tab 增加 office |
| `frontend/src/views/KnowledgeBase.vue` | 领域 tab 增加 office |
| `frontend/src/views/GrayscaleConsole.vue` | 领域 tab 增加 office |

---

## 四、灰度配置变更

### 4.1 Office 领域独有灰度（domain='office'）

```
ui.sidebar.documents / meetings / approvals / reports / schedules
ui.chat.toolbar.doc_draft / meeting_mins / report_gen
ui.workspace.welcome_office
feature.document.create / review
feature.meeting.transcribe
feature.approval.flow / report.template
agent.doc_writer_office / meeting_assistant / report_analyst / email_drafter / schedule_manager
tool.doc_template_engine / format_checker / transcript_parser
```

### 4.2 Common 域跨领域灰度（新增 office）

所有已有 `domain='common'` 的配置的 `domains` JSON 从 `["rd","edu"]` 改为 `["rd","edu","office"]`，包括：

```
ui.chat.workspace / services / attachments
ui.chat.tabs.agent_config / artifacts / logs / workflow / knowledge_base
ui.sidebar.agents / tools / favorites / knowledge
ui.chat.card.requirement / bug / iteration / project
```

新增 common 配置：`ui.chat.card.office`（仅 office 领域可见）。

---

## 五、冲突与问题

### 5.1 [严重] 灰度配置双写问题

`migration_v2.sql` 中 **sidebar 公共项仍按旧模式每领域各写一份**：

```sql
-- migration_v2.sql 现状 (3个领域各自重复)
('ui.sidebar.agents', '...', 'ui', 'rd', 1, 1),
('ui.sidebar.agents', '...', 'ui', 'edu', 1, 1),
('ui.sidebar.agents', '...', 'ui', 'office', 1, 1),
```

但 `__init__.py` 的 `_seed_grayscale_configs()` 已经重构为 `domain='common'` + `domains JSON` 模式：

```python
('ui.sidebar.agents', '...', 'ui', 'common', 1, 1, ['rd', 'edu', 'office']),
```

**影响**：新数据库通过 `__init__.py` 初始化是正确的，但如果有同事直接跑 `migration_v2.sql`，会产生旧的 per-domain 冗余数据，且灰度控制台查询时会出现数据不一致（一个 key 既有 per-domain 版本又有 common 版本）。

**建议**：统一 `migration_v2.sql` 与 `__init__.py` 的灰度数据格式，全部改用 common + domains JSON 模式。

### 5.2 [中等] Sidebar 导航与灰度 key 不匹配

Sidebar `DOMAIN_NAV.office` 只有 3 项：

| 侧边栏 key | 显示名称 | 灰度控制 |
|------------|----------|----------|
| `organization` (裸字符串) | 组织协同 | **无灰度配置**，永久可见 |
| `ui.sidebar.meetings` | 会议任务 | 有配置 |
| `ui.sidebar.documents` | 公文审批 | 有配置 |

但灰度配置中有 5 个 office 侧边栏 key：`ui.sidebar.documents/meetings/approvals/reports/schedules`。

**问题**：
- `approvals`、`reports`、`schedules` 虽然页面存在，但**侧边栏无法导航过去**（没有入口）
- `organization` 没有灰度控制，无法被禁用

### 5.3 [中等] 4 个僵尸 Vue 组件

以下组件文件存在于 `frontend/src/views/` 但未被路由引用：

- `OfficeDocuments.vue`
- `OfficeTasks.vue`
- `OfficeScheduleDense.vue`
- `OfficeOrganization.vue`

路由实际使用的是 `OfficeDocumentsDense.vue`、`OfficeMeetingTasks.vue`、`OfficeOrganizationCompact.vue`、`OfficeWorkspace.vue`。

**问题**：这些是旧版设计，猜测是重构为 Dense/Compact 版本后遗留。占用包体积，且容易让人误以为这些是活动页面。

### 5.4 [中等] `route.name` vs `meta` 路由设计隐患

`OfficeWorkspace.vue` 同时服务于 `/approvals` 和 `/schedules` 两个路由，依赖 `route.name` 区分 section。但 `/reports` 和 `/tasks` 被 redirect 到 `/meetings`，而 `OfficeWorkspace.vue` 中仍有未引用的 dashboard/meetings/documents sections。

如果未来需要独立页面，当前设计需要拆解。

### 5.5 [低] Office AI 起草端点 vs 微服务数据端点

主服务上存在 `/api/office-ai/*`（AI 起草，端口 5002），而办公业务数据走 `/api/domain/office/*`（代理到 5103）。两条路径完全独立：

```
/api/office-ai/meeting-draft       → 主服务 LLM 调用 → 返回草稿文本
/api/domain/office/meetings        → 代理 → office:5103 → 读写业务数据
```

前端需要记住哪个功能走哪个根路径。`office.js` API 封装已处理好，但后端维护者需要注意这种分裂。

### 5.6 [低] SQL 迁移文件与模型不同步

`001_initial_schema.sql` 的 `office_documents` 表缺少 `approvers` 列，`office_meetings` 表缺少 `meeting_link` 和 `materials` 列。这些列在 `app.py` 启动时通过 `ALTER TABLE` 补上。

**问题**：如果有人直接执行 .sql 文件建库而不通过 app.py 启动（或 app.py 的 ALTER 失败），表结构会与 SQLAlchemy 模型不一致。建议补一份完整的 `sql/init.sql`（一站式建库脚本，像 RD/RAG 那样）。

### 5.7 [低] Cross-DB 直接写入

`organization_service.py` 直接打开 `MAIN_DATABASE_URL` 连接，手写 SQL 插入 `workspace_members`。如果主库 `workspace_members` 表结构发生变化（比如新增 NOT NULL 列），此操作会静默失败。

### 5.8 [低] `domain` 列默认值

所有模型的 `domain` 列默认值都是 `'rd'`（而非 `'common'` 或无默认值）。这在创建 office/edu 领域数据时需要显式传入 `domain='office'`/`domain='edu'`，否则会错误落到 rd。目前代码中已显式传入，但未来新增领域依赖需注意。

---

## 六、缺失项（对比 RD 服务）

| 项目 | RD | Office | 建议 |
|------|-----|--------|------|
| 一站式 init.sql | `sql/init.sql` | 无（仅有增量迁移 sql） | 补充 `sql/init.sql`，含完整建库+12表 |
| 种子数据 | `seed_edu.py`（完整项目数据） | 仅 9 个公文模板 | 如需演示，补充办公示例数据 |

---

## 七、总结

Office 服务的接入模式与 RD 一致：独立微服务 + 主服务代理 + 前端领域路由 + 灰度控制。代码质量整体良好，主要问题是：

1. **migration_v2.sql 与 `__init__.py` 的灰度数据格式不一致**（per-domain vs common + domains）
2. **侧边栏缺少 approvals/reports/schedules 入口**，organization 缺少灰度控制
3. **4 个僵尸 Vue 组件**待清理
4. **缺一站式 init.sql**（队友建立开发环境不便）

---

## 八、修复记录（2026-08-05）

以下问题已修复：

### 8.1 ✅ migration_v2.sql 灰度数据统一为 common+domains 模式
- 移除了 `ui.sidebar.agents/tools/favorites/knowledge` 在 rd/edu/office 下的 per-domain 重复数据
- 移除了各领域的 chat.toolbar/welcome/feature/agent/tool 等非核心灰度配置（这些不在 wired_keys 中，启动时也会被清理）
- 将所有跨领域共享配置集中到 common 域，使用 `domains` JSON 字段控制生效范围
- `grayscale_config` CREATE TABLE 增加 `domains` JSON 列
- 兼容老表增加 `ALTER TABLE ADD COLUMN IF NOT EXISTS domains`
- 各领域仅保留领域独有侧边栏配置（rd 4项, edu 5项, office 6项）

### 8.2 ✅ Sidebar 修复
- `organization` key 从裸字符串改为 `ui.sidebar.organization`，可通过灰度控制
- 增加 `ui.sidebar.approvals`（审批流程）和 `ui.sidebar.schedules`（日程管理）导航项
- `__init__.py` wired_keys 和种子数据增加 `ui.sidebar.organization`

### 8.3 ✅ 僵尸组件清理
- 删除 `OfficeDocuments.vue`、`OfficeTasks.vue`、`OfficeScheduleDense.vue`、`OfficeOrganization.vue`

### 8.4 ✅ Office 一站式 init.sql
- 创建 `backend/services/office/sql/init.sql`，含完整 `CREATE DATABASE` + 11 张表，与 SQLAlchemy 模型一致（含 `approvers`/`recipients`/`meeting_link`/`materials` 等列）
