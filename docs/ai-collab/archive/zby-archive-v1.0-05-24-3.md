# Archive

版本 ：v1.0
更新时间：2026.5.24

## 1. 归档信息

- 归档名称：部署状态卡片实现与 Mock 部署链路验证
- 归档日期：2026-05-24
- 归档人：zby
- 对应 session：zby-session-v1.11-05-24-4.md
- 对应 session 记录范围：从部署卡片方向到完整链路验证

## 2. 归档原因

本次对话触发归档的原因：

- 部署状态卡片是 spec 中 P0 的最后一个功能，至此 3 个 P0 功能全部完成
- 发现了线程内 SQLAlchemy session 不可用的关键限制，修复经验对后续所有后台任务有参考价值
- 验证脚本 4 项全通过，证明链路真实跑通

## 3. 对话主题

本轮对话主要主题为：

- 部署状态卡片的需求分析和技术方案
- Deployment 模型设计与 deploy_service 实现
- 线程内 session 隔离问题的定位与修复
- 前后端 SSE + 轮询双通道方案
- 全链路验证：DB 写入/进度模拟/持久化/broadcast

## 4. 归档提炼

从原始对话中提炼出的有效内容：

### 线程 session 隔离问题

Flask-SQLAlchemy 的 `db.session` 是应用上下文绑定的。后台线程内的 `with app.app_context()` 创建新的上下文和 session，无法看到主线程提交的数据。

**结论**：涉及 DB 操作的长时间后台任务，如 Mock 部署进度，应在主线程同步执行（`_mock_agent_response` 循环 sleep + broadcast），或在线程内使用独立数据库连接（raw SQL）。

### 部署双通道方案

| 通道 | 适用场景 | 实现 |
|------|---------|------|
| SSE `deploy_status` | 实时进度（主 Mock 流程内） | `broadcast()` 推送 |
| HTTP Poll `GET /api/deploys/<id>` | 页面刷新/断开重连 | DeployStatusCard 每 2 秒轮询 |

### 新增文件清单

| 文件 | 说明 |
|------|------|
| `backend/app/models/deployment.py` | Deployment 模型 |
| `backend/app/services/deploy_service.py` | `run_mock_deploy` + `DeployService` |
| `backend/app/controllers/deploy_controller.py` | deploy API 路由 |
| `backend/app/schemas/deploy_schema.py` | 请求校验 |
| `frontend/src/components/DeployStatusCard/index.vue` | 部署进度卡片 |
| `frontend/src/api/deploy.js` | 前端 API |

### 修改文件清单

| 文件 | 改动 |
|------|------|
| `backend/app/__init__.py` | 注册 blueprint + `_ensure_deployments_table()` |
| `backend/app/services/message_service.py` | "部署"分支 + `run_mock_deploy` 调用 |
| `frontend/src/store/modules/message.js` | `UPDATE_DEPLOY_STATUS` mutation |
| `frontend/src/views/Dashboard.vue` | SSE `deploy_status` 事件处理 |
| `frontend/src/components/MessageBubble/index.vue` | `deploy_status` 渲染分支 |

## 5. 已形成成果

本次归档已经形成的成果包括：

- `backend/app/services/deploy_service.py` — 部署服务（含 Mock 进度模拟）
- `frontend/src/components/DeployStatusCard/index.vue` — 实时进度卡片
- MySQL `deployments` 表 — 持久化部署记录
- 验证数据（保留在库中）：多条 deployment 记录含完整 status/progress/logs

## 6. 后续去向

本次归档内容后续应落入：

- `rules/`
  - 后台线程 session 不可用主线程数据 → 同步调用
  - SSE + HTTP Poll 双通道模式
- 仅保留在归档记录中
  - 部署卡片具体实现细节

## 7. 备注

至此 spec 中 P0 的三个功能（Diff 视图卡片、Web 网页预览卡片、部署状态卡片）全部完成并验证。后续可推进 P1（文档/PPT 预览）和 P2（版本历史/对话式修改/部署流程完整实现）。
