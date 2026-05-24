# Archive

版本 ：v1.0
更新时间：2026.5.24

## 1. 归档信息

- 归档名称：Diff 视图卡片实现与 artifacts 分层存储架构定稿
- 归档日期：2026-05-24
- 归档人：zby
- 对应 session：zby-session-v1.1-05-24.md
- 对应 session 记录范围：从确定 Diff 方向到完整数据链路验证

## 2. 归档原因

本次对话触发归档的原因：

- Diff 视图卡片实现已通过 MySQL 链路验证，是第一个跑通全链路的 P0 功能
- artifacts 分层存储架构（code/diff 分离）已完成设计并验证，是后续所有多模态数据的基础
- `elements` JSON 中 `diff` 子类型的接口定义已稳定，后续接入真实 AI 可复用

## 3. 对话主题

本轮对话主要主题为：

- 确定 Diff 实现方案（零依赖，Python difflib + 纯前端）
- 实现三路 mock 分支（写代码 / 优化代码 / 重构代码）
- 实现 DiffViewCard 前端组件（默认代码视图 + 切换 diff 对比）
- 重构 artifacts 存储为分层架构
- MySQL 端到端验证全链路

## 4. 归档提炼

从原始对话中提炼出的有效内容：

### 数据格式规范（后续模块可复用）

**elements diff 子类型**（messages 表，前端渲染用）：
```json
{
  "type": "diff",
  "data": {
    "after": "优化后的代码...",
    "diff_text": "@@ -1,7 +1,4 @@...",
    "language": "python",
    "filename": "utils.py",
    "artifact_id": "diff-uuid"
  }
}
```

**code 类型 artifact**（artifacts 表，存纯代码）：
```python
Artifact(artifact_type='code', title='utils.py', content='纯代码字符串', language='python', version=1)
```

**diff 类型 artifact**（artifacts 表，只存关联 + diff_text）：
```python
Artifact(artifact_type='diff', title='utils.py',
    content=json.dumps({'before_id': 'code-uuid-1', 'after_id': 'code-uuid-2', 'diff_text': '@@...'}),
    language='python', version=1)
```

### 设计原则

- `code` artifact 独立存储，可跨 diff 复用、可独立版本化
- `diff` artifact 只维护关联，不存完整代码，保持轻量
- `elements` 保留 `after` + `diff_text`，避免前端查表延迟

## 5. 已形成成果

本次归档已经形成的成果包括：

- `frontend/src/components/DiffViewCard/index.vue` — 通用 Diff 渲染组件
- `backend/app/services/message_service.py` — 三路 mock 分支 + 分层 artifact 写入
- `frontend/src/components/MessageBubble/index.vue` — 新增 diff 子类型渲染分支
- `backend/test_diff_flow.py` + `backend/query_db.py` — 验证脚本（已删除，数据保留在 MySQL）
- MySQL weagent 数据库：4 条 artifact + 4 条 message 验证数据

## 6. 后续去向

本次归档内容后续应落入：

- `spec/`
  - Diff 数据格式规范可作为 spec 补充
- `rules/`
  - 分层存储规则：code/diff 分离，elements 仅存渲染数据
- 仅保留在归档记录中
  - DiffViewCard 组件实现细节
  - 数据链路测试过程

## 7. 备注

本次归档的数据格式规范（elements diff 子类型、code/diff 分层存储）也是后续 WebPreviewCard、DeployStatusCard 等模块的参考模式。
