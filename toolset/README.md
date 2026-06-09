# Toolset UAT Fixtures

`toolset/` 存放工具集能力导入流程的 UAT 示例材料。它不是运行时代码目录，而是给开发、测试和演示使用的输入样例。

## 覆盖范围

当前工具集能力包括：

- Skill：Markdown 或目录包形式的 AI 工作流说明。
- Tool：可执行工具定义和内置工具能力。
- Plugin：带 manifest、脚本、模板和引用资料的能力包。
- MCP：MCP server manifest 和工具发现配置。
- Provider Config：为需要外部服务的能力配置 profile。

## 文件说明

| 文件 | 用途 |
|---|---|
| `01-markdown-skill.md` | Markdown Skill 导入示例，可直接上传或粘贴 |
| `02-skill-bundle.zip` | zip bundle 导入示例 |
| `02-zipbundle-source/` | 生成 zip bundle 的源目录 |
| `03-repo-current-limitation.md` | 当前远程 repo 导入边界说明 |
| `04-npx-import-sources.md` | npx 导入源字符串示例 |
| `06-MCP-manifest.md` | MCP manifest 示例 |
| `COMMANDS.md` | Skill / Plugin / Tool / MCP 常用命令与支持边界 |

## 建议 UAT 流程

1. 启动后端、Web 前端，并登录测试账号。
2. 进入“工具集”页面。
3. 创建或选择分类。
4. 使用导入入口分别测试：
   - Markdown Skill
   - zip bundle
   - npx source
   - MCP manifest
5. 检查安全审计、检测结果、版本、权限和可绑定状态。
6. 进入“我的 Agent”，将能力绑定到 Agent。
7. 创建会话，确认能力能投影到沙箱容器。

## 当前边界

- 远程 GitHub repo URL 导入尚未作为正式 fixture 提供。
- 后端当前主要扫描本地 `repo_path` 或上传 bundle。
- 远程 repo clone、凭据处理、网络安全审计需要作为后续功能单独实现。

## 回归测试建议

导入能力后至少验证：

- 能力是否出现在工具集列表。
- 分类、类型、版本、来源是否正确。
- 安全审计是否能显示阻断项和风险项。
- 需要配置 provider 的能力是否正确显示“需要配置”。
- Agent 绑定后，创建会话时沙箱能力投影不报错。
- 旧沙箱镜像缺可选能力投影接口时，不应阻断容器创建。

## 相关代码

```text
backend/app/controllers/capability_controller.py
backend/app/services/capability_service.py
backend/app/services/capability_import_preview_service.py
backend/app/services/capability_import_confirm_service.py
backend/app/services/capability_projection_service.py
backend/app/services/tool_provider_config_service.py
frontend/src/views/Tools.vue
frontend/src/views/AgentManager.vue
clients/desktop/src/views/Tools.vue
clients/desktop/src/views/Agents.vue
```
