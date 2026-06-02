# 002 Toolset Library Merge PLAN

## Checkpoint A: 规划与合同测试

- 写入本阶段 SPEC/PLAN。
- 增加后端测试：
  - 内置分类 seed 和计数。
  - 用户分类 CRUD。
  - Skill / Markdown / npx manifest 按分类写入。
  - 删除用户分类迁移能力。
- 增加前端合同测试：
  - `/tools` 作为统一入口。
  - `/capabilities` 重定向到 `/tools`。
  - `Tools.vue` 包含分类视图和 Skill/MCP/Plugin/Tool 四类型。

## Checkpoint B: 后端模型和 API

- 新增 `ToolsetCategory` 模型。
- `Capability` 增加 `category_id`。
- `create_app` 自动建表和轻量迁移补列。
- 新增 `toolset_category_service`：
  - seed 内置分类。
  - 列表和类型计数。
  - 用户分类创建、更新、删除。
  - 分类解析 helper。
- 新增 `toolset_controller` 并注册 `/api/toolsets/categories`。
- 扩展 `capability_service` 和 schema/controller，使能力导入与创建支持分类。
- 更新 `backend/sql/init.sql`。

## Checkpoint C: 前端统一工具集页面

- 新增 `src/api/toolsets.js`。
- 改造 `src/views/Tools.vue`：
  - 左侧分类。
  - 类型页签。
  - 能力列表与详情。
  - Skill/Markdown/npx 导入表单携带当前分类。
  - 用户分类管理。
- 更新 router：`/capabilities` 重定向 `/tools`。
- 更新 Sidebar：移除能力库独立入口，只保留工具集。

## Checkpoint D: 验证

- `python -m pytest tests\test_toolset_categories.py tests\test_capability_api.py tests\test_capability_projection.py`
- `node tests\toolset-ui-contract.test.js`
- `node tests\capability-ui-contract.test.js`
- `npm run build`
- `git diff --check`

## 风险与约束

- 当前工作区已有模型配置/沙盒修复改动，本阶段不得回滚。
- 旧 `agent_tools` 仍保留，避免破坏已有 Agent `tool_ids` 兼容路径。
- 本阶段使用 `Capability` 作为统一工具集项，后续再把 Agent 创建页的绑定 UI 合并到同一工具集选择器。
