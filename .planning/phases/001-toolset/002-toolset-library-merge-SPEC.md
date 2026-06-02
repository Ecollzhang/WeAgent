# 002 Toolset Library Merge SPEC

## 背景

当前系统同时存在两个入口：

- `/tools`：旧的 AgentTool demo，按工具分类展示内置工具和用户自建工具。
- `/capabilities`：真实能力库，已经支持 `skill`、`tool`、`mcp`、`plugin` 四类能力，支持 Skill Markdown、npx manifest、Agent 默认绑定、权限声明和调用记录。

产品决策：对用户只保留“工具集”概念。“能力库”不是独立产品入口，而是工具集的底层能力模型。

## 目标

本阶段将工具集设计收束为：

1. 一级按分类展示，例如代码工具、文件与文档、网络与检索、数据处理、图像/多媒体、系统与终端、自定义。
2. 点击分类后，在该分类下继续按 `Skill`、`MCP`、`Plugin`、`Tool` 四种类型查看和管理。
3. 系统内置分类只读，用户可以新建、重命名、删除自己的分类。
4. Skill/MCP/Plugin/Tool 继续使用 `Capability` 作为统一数据模型，分类只是视图和管理维度。
5. `/tools` 成为统一入口；`/capabilities` 仅作为兼容重定向，不再作为侧边栏独立入口。

## 非目标

- 本阶段不实现完整 npx 包下载和执行安装，只保留 manifest 导入和记录。
- 本阶段不修改 workspace runtime projection 目录结构。
- 本阶段不重构 Agent 创建页的绑定交互，只保证能力数据和分类能被后续绑定页消费。
- 本阶段不删除旧 `agent_tools` 表，保持兼容和回滚空间。

## 数据模型

新增 `toolset_categories`：

- `id`
- `user_id nullable`：空值表示系统内置分类。
- `name`
- `slug`
- `icon`
- `color`
- `sort_order`
- `is_builtin`

扩展 `capabilities`：

- `category_id nullable`，指向 `toolset_categories.id`。

分类规则：

- 内置 Tool capability 根据旧 `AgentTool.category` 映射到同 ID 的内置分类。
- 用户新建 Skill / 导入 Markdown / 导入 npx manifest 时，默认使用当前选中分类；未传分类则进入 `tool_custom`。
- 删除用户分类时，不删除能力项，而是迁移到内置 `tool_custom`。

## API

新增 `/api/toolsets/categories`：

- `GET`：返回系统内置分类 + 当前用户分类，并附带四类能力计数。
- `POST`：创建用户分类。
- `PUT /<category_id>`：更新用户分类。
- `DELETE /<category_id>`：删除用户分类并迁移能力。

扩展 `/api/capabilities`：

- `GET` 支持 `category_id` 过滤。
- `POST /skills` 支持 `category_id` / `category_slug`。
- `POST /import/markdown` 支持 `category_id` / `category_slug`。
- `POST /import/npx-manifest` 支持 `category_id` / `category_slug`，manifest 内单项可通过 `category` 覆盖。

## UI

统一 `/tools` 页面：

- 左侧为工具集分类列表，可新建用户分类，可编辑/删除用户分类。
- 右侧头部展示当前分类，并提供 Skill 新建、Markdown 导入、npx manifest 导入入口。
- 右侧主体用四个类型页签：Skill、MCP、Plugin、Tool。
- 列表展示名称、说明、来源、版本、权限摘要和安装状态。
- 详情侧栏展示权限、来源、Markdown 或 manifest。

导航：

- 侧边栏只保留“工具集”。
- `/capabilities` 路由重定向到 `/tools`。

## 验收标准

- 内置分类可以被 seed，并能统计各类型能力数量。
- 用户分类可以创建、更新、删除；删除后能力迁移到 `tool_custom`。
- 新建 Skill / 导入 Markdown / 导入 npx manifest 可落到指定分类。
- 内置工具 capability 带有正确分类。
- `/tools` 页面包含分类 + 四类型视图，`/capabilities` 不再是独立入口。
- 原有 Capability API、Agent 绑定、Skill draft、Tool 调用记录测试继续通过。
