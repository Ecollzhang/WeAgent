# Checkpoint A Report: Catalog Visibility Contract

日期：2026-06-02

## 目标

锁定默认 Tool 目录的可见性、可绑定性和前端入口规则：

- `code_generator` 不再作为默认可见 Tool 暴露。
- 未完成或隐藏的 Tool 不进入列表、分类计数和 Agent 绑定选择器。
- `web_search`、`image_analysis`、`image_generation`、`database_query` 作为“需配置能力”展示配置入口，但在配置通过前不可绑定。
- 系统内置 Tool 本体不可编辑；用户后续只能编辑 provider/profile 配置。

## 已完成

### 后端目录契约

- 在 `backend/app/services/builtin_tool_definitions.py` 中扩展 Tool definition 元数据：
  - `visibility`
  - `configurable`
  - `bindable`
  - `provider_types`
  - `config_schema`
- 将 `code_generator` 标记为 `hidden` 且不可绑定。
- 将 `web_search`、`image_analysis`、`image_generation`、`database_query` 统一定义为 `requires_config`。
- 新增 `image_generation` 默认 Tool 定义，但只作为需配置能力出现。
- `builtin_tools_for_legacy_view()` 过滤 hidden Tool，避免旧视图继续暴露。

### 后端 API 和绑定规则

- `capability_service.list_capabilities()` 通过 `_visible_capability_query()` 排除 `archived` 和 `hidden`。
- Tool 序列化新增：
  - `tool_status`
  - `visibility`
  - `configurable`
  - `bindable`
  - `configured_profiles_count`
  - `configuration_required_reason`
- Agent 绑定前新增 `_is_capability_bindable()` 判定：
  - hidden/archived 不可绑定。
  - `requires_config` 在没有配置 profile 前不可绑定。
  - 已实现或 partial 的内置 Tool 继续可绑定。
- 分类计数排除 hidden/archived capability。

### 前端工具集页

- `frontend/src/views/Tools.vue` 主列表过滤 hidden/deferred Tool。
- 对需配置 Tool 显示“配置能力”入口。
- 新增配置窗口骨架，包含：
  - provider 类型选择。
  - profile 名称。
  - JSON 配置文本框。
  - 测试配置、保存并启用按钮占位。
- 当前窗口只完成 Checkpoint A 的可见交互入口，真实创建、测试、保存、启用/停用 API 留到 Checkpoint C/D。

### Agent 能力选择器

- `frontend/src/components/AgentEditForm/index.vue` 新增 `bindableCapabilities` 过滤。
- hidden 和未配置的 `requires_config` Tool 不出现在可绑定列表。
- `addCapability()` 对不可绑定能力做前端保护并提示。

### 测试

- 新增 `backend/tests/test_default_tool_catalog.py`。
- 扩展：
  - `frontend/tests/toolset-ui-contract.test.js`
  - `frontend/tests/agent-capability-selector-contract.test.js`
- 调整 `backend/tests/test_capability_api.py` 中内置 Tool 删除测试，显式选择可见的 `code_search`，避免被隐藏的 `code_generator` 干扰旧断言。

## 验证结果

通过：

```powershell
python -m pytest tests\test_default_tool_catalog.py tests\test_capability_api.py tests\test_toolset_categories.py -q
```

结果：20 passed。

通过：

```powershell
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
node tests\capability-ui-contract.test.js
node tests\toolset-regression-contract.test.js
```

结果：全部 ok。

通过：

```powershell
npm run build
```

结果：构建成功。仍有既有 bundle 体积 warning：

- `img/bg.d0047cc4.png`
- `js/chunk-vendors.aad3cdea.js`
- app entrypoint size

这些 warning 不是本次 Checkpoint A 改动引入的功能失败。

## 当前边界

- “需配置能力”的配置窗口目前是前端骨架，不会真实写入 DB。
- `configured_profiles_count` 目前固定为 0，等待 Checkpoint C 的 provider profile 数据模型接入。
- `requires_config` Tool 当前不可绑定，这是有意行为。等 profile 测试通过并启用后，再进入可绑定状态。
- Runtime projection 和 sandbox 调用仍留给 Checkpoint E/F。

## 下一步

进入 Checkpoint C/D：

1. 新增 provider profile 数据模型和 API。
2. 支持创建、测试、保存、启用/停用配置。
3. 前端配置窗口接真实 API。
4. 配置通过后更新 Tool 的 `configured_profiles_count` 和 `bindable`。
5. 后续再接 Runtime projection 和真实 Tool 调用记录。
