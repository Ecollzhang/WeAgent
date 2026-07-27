# Checkpoint H Report: Agent 创建和编辑能力选择器

## 目标

让“先创建能力，再创建/编辑 Agent 时勾选默认工具能力”的闭环可用。UI 默认使用 pinned 版本，并保留手动升级提示。

## 已完成

- 重写 `AgentEditForm` 的默认能力区域：
  - 一级按工具集分类筛选。
  - 二级按 Skill / MCP / Plugin / Tool 分组。
  - 点击能力卡片即可加入 Agent 默认绑定。
  - 已绑定能力会禁用，避免重复绑定。
- 保存格式继续使用现有 `capability_bindings`：
  - `capability_version_id`
  - `granted_permissions`
  - `version_policy`
  - `enabled`
- 新增绑定默认：
  - `version_policy = pinned`
  - 自动带入必需权限。
  - 用户可勾选可选权限。
- 编辑已有 Agent：
  - 继续读取 `getAgentCapabilities`。
  - 继续读取 `getAgentCapabilityUpgrades` 展示“可升级”提示。
  - 删除已有 binding 时改为 `enabled=false`，避免直接丢失服务端 binding 上下文。
- AgentManager 保存流程仍提交 `capability_bindings`。

## 验证

```powershell
node tests\agent-capability-selector-contract.test.js
node tests\capability-ui-contract.test.js
node tests\toolset-ui-contract.test.js
npm run build
```

结果：

- `agent capability selector contract ok`
- `capability UI contract ok`
- `toolset UI contract ok`
- `npm run build` 成功

## 注意事项

- UI 暂不暴露 `follow_latest` 主路径，符合 v1 推荐的固定版本策略。
- “手动升级”目前是提示和后端 API 能力，进一步的逐项升级按钮可作为后续增强。
- 前端 build 仍有既有 asset size 警告，未在本 checkpoint 中处理。
