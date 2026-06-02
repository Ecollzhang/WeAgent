# Checkpoint C/D Report: Provider Profile API and Frontend Configuration UI

日期：2026-06-02

## 目标

让“需配置能力”不只是前端标签，而是用户可以在平台里创建、测试、保存、启用/停用的真实配置记录。

## 已完成

### Provider Profile 数据模型

- 新增 `ToolProviderConfig` 模型：
  - `user_id`
  - `capability_id`
  - `profile_name`
  - `provider_type`
  - `config`
  - `secret_refs`
  - `status`: `draft`、`valid`、`invalid`、`disabled`
  - `last_test_status`
  - `last_test_error`
  - `last_test_result`
- 更新 `backend/sql/init.sql`，Docker/MySQL 初始化路径也会创建 `tool_provider_configs` 表。
- secret 仅保存 alias/ref，不保存明文。

### 后端 API

新增以下 API：

```text
GET    /api/capabilities/<id>/provider-configs
POST   /api/capabilities/<id>/provider-configs
PUT    /api/capabilities/<id>/provider-configs/<config_id>
POST   /api/capabilities/<id>/provider-configs/<config_id>/test
POST   /api/capabilities/<id>/provider-configs/<config_id>/enable
POST   /api/capabilities/<id>/provider-configs/<config_id>/disable
DELETE /api/capabilities/<id>/provider-configs/<config_id>
```

测试逻辑为 Docker-stable 的静态校验：

- `http`: endpoint 必须是 `http://` 或 `https://`。
- `mcp`: 必须有 runtime/command/package 之一，并有 `tool_name`。
- `model`: 必须有 `model`。
- `database`: 必须有 `connection_alias`，且 `readonly` 必须为 `true`。

启用规则：

- 创建后为 `draft`。
- 测试通过后 `last_test_status=passed`，仍需启用。
- 启用后 `status=valid`。
- 停用后 `status=disabled`，新绑定不可用。

### 能力目录联动

- `configured_profiles_count` 现在从 DB 中统计当前用户的 `valid` profile。
- `requires_config` Tool 只有在当前用户存在 `valid` profile 后才返回 `bindable=true`。
- Agent 绑定时同样按用户 profile 校验，未配置时返回 `Capability requires configuration before binding`。

### 前端配置窗口

- `frontend/src/views/Tools.vue` 的“配置能力”窗口已接真实 API。
- 支持：
  - 查看已保存配置。
  - 新建配置。
  - 编辑配置。
  - 测试配置。
  - 保存。
  - 保存并启用。
  - 启用/停用。
  - 删除。
- 默认 JSON 从 schema 展示改为可填写样例。
- 系统内置 Tool 本体仍不可编辑，用户只编辑 provider profile。

## 验证结果

通过：

```powershell
python -m pytest tests\test_tool_provider_config_api.py -q
```

结果：2 passed。

通过：

```powershell
node tests\tool-provider-config-ui-contract.test.js
node tests\toolset-ui-contract.test.js
npm run build
```

结果：契约测试通过，前端构建成功。

## 当前边界

- `test` API 是静态配置校验，不直接连接外部 provider。
- 明文 secret vault 尚未实现，v1 只保存 alias/ref。
- 真正 provider 调用由 Checkpoint E/F 的 runtime adapter 验证。
