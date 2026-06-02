# 002 Checkpoint 1 Summary: 工具集与能力库合并

## 完成内容

- 新增工具集分类模型 `toolset_categories`，支持系统内置分类和用户自建分类。
- `Capability` 增加 `category_id`，Skill / MCP / Plugin / Tool 作为同一工具集下的四种能力类型并行存在。
- 新增 `/api/toolsets/categories`：
  - 列出分类和四类能力计数。
  - 创建、更新、删除用户分类。
  - 删除用户分类时将能力移动到内置 `tool_custom`。
- 扩展 `/api/capabilities`：
  - 支持按 `category_id` 过滤。
  - 新建 Skill、导入 Markdown、导入 npx manifest 时可指定分类。
  - npx manifest 单项可通过 `category` 覆盖顶层分类。
- `/tools` 改为统一工具集页面：
  - 左侧一级分类。
  - 右侧 Skill / MCP / Plugin / Tool 页签。
  - 支持新建 Skill、导入 Markdown、导入 npx manifest、编辑 Skill Markdown 版本。
  - 支持用户分类创建、编辑、删除。
- `/capabilities` 保留兼容路由，但重定向到 `/tools`。
- 侧边栏只保留“工具集”，不再单独展示“能力库”。

## 验证

- `python -m pytest tests\test_toolset_categories.py`
- `python -m pytest tests\test_capability_api.py tests\test_capability_projection.py tests\test_toolset_categories.py`
- `python -m pytest tests\test_capability_service.py`
- `python -m pytest tests\test_model_config_custom_model.py tests\test_sandbox_model_config_timeout.py tests\test_toolset_regression_contract.py`
- `node tests\toolset-ui-contract.test.js`
- `node tests\capability-ui-contract.test.js`
- `node tests\model-settings-contract.test.js`
- `node tests\toolset-regression-contract.test.js`
- `npm run build`
- `git diff --check`

## 已知边界

- 旧 `agent_tools` 表和 `/api/tools` 仍保留，避免破坏已有 Agent `tool_ids` 兼容路径。
- 本次未实现完整 npx 包下载和执行安装，只支持 manifest 导入后的记录和展示。
- 本次未重构 Agent 创建页的能力绑定选择器；后续应让 Agent 创建页直接从统一工具集选择默认能力配置。
- 本次未做浏览器人工点击验收，需要在本地页面进入 `/tools` 后检查分类切换、导入弹窗和详情侧栏。
