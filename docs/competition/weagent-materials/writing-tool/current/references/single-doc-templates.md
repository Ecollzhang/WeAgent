# Single-Document Templates

Use these templates as starting points. Adapt headings to the project and reader. Keep the final deliverable as one Markdown file.

## Template Selection

Use this decision rule:

- If the reader must evaluate technical credibility, use `Architecture + Evidence`.
- If the reader must run the project, use `Operate + Verify`.
- If the reader must integrate an API or SDK, use `API + Integration`.
- If the document must cover a whole project, use `Complete Technical Document`.

When internet access is available, check The Good Docs Project templates for relevant pieces such as Concept, How-to, Reference, Troubleshooting, Tutorial, Quickstart, Installation guide, API getting started, API reference, and Glossary. Select only the parts that fit one document.

## Complete Technical Document

```markdown
# 项目技术文档

更新日期：YYYY-MM-DD

## 1. 结论：系统技术上是什么

一句话说明系统是什么、当前实现状态、本文覆盖范围。

## 2. 读者、范围与事实源

- 主要读者：
- 本文包含：
- 本文不包含：
- 待确认：
- 事实源：

## 3. 一张图看懂系统

放总体架构图片或清晰总览图，让读者先建立心智模型。

## 4. 技术分层总览

按客户端层、后端协调层、执行层、能力层、产物层、基础设施层说明系统边界。

## 5. 系统架构

先给 C4 Context / Container 图，再解释每条主要链路。

## 6. 核心模块

从大模块开始分层。每个模块先写结论和实现范围，再拆子模块。不要把 `背景 / 决策 / 方案内容` 当作固定标题。

## 7. 关键数据流

优先使用 Mermaid `sequenceDiagram` 或流程图表达用户操作、系统执行、异步事件、数据持久化和错误处理。

## 8. 开发者部署与运行

提供可执行步骤、命令、环境变量、预期输出和注意事项。

## 9. 关键接口与数据模型

只放关键接口、数据模型、配置项。完整接口表另行待确认或附录化，但仍在同一个文件中。

## 10. 开发者验证路径

列出已经运行、未运行、如何复现、失败如何排查。

## 11. 已知限制、风险与待确认项

只写真实风险。无法确认的内容标注 `待确认`。

## 12. 常见故障定位

按症状、可能原因、检查命令、处理方式组织。

## 13. 关键术语速查

列出项目特有术语。
```

## Layered Technical Document

Use this for complex systems with clients, backend, sandbox/runtime, tool/capability layers, and artifacts:

```markdown
# 项目技术文档

## 1. 结论：系统技术上是什么
## 2. 读者、范围与事实源
## 3. 一张图看懂系统
## 4. 技术分层总览

## 5. 系统架构
### 5.1 客户端层
### 5.2 后端协调层
### 5.3 执行层
### 5.4 能力层
### 5.5 产物层
### 5.6 基础设施层

## 6. 核心模块
### 6.1 客户端与多端连接
### 6.2 后端协调系统
### 6.3 会话与消息系统
### 6.4 Agent 执行系统
### 6.5 Sandbox 系统
### 6.6 Capability / Toolset 系统
### 6.7 Artifact 与 Workbench 系统
### 6.8 Service 与服务预览
### 6.9 实时推送与事件系统

## 7. 关键数据流
### 7.1 用户消息到 Agent 响应
### 7.2 Agent 调用工具 / MCP
### 7.3 Capability 投影到 Sandbox
### 7.4 Artifact 生成、展示与编辑
### 7.5 服务启动、代理与预览链接
### 7.6 多端客户端连接后端

## 8. 开发者部署与运行
## 9. 关键接口与数据模型
## 10. 开发者验证路径
## 11. 已知限制、风险与待确认项
## 12. 常见故障定位
## 13. 关键术语速查
```

## Architecture + Evidence

```markdown
# 系统架构技术说明

## 结论
## 背景与约束
## 事实源和可信边界
## C4 Context
## Container / Component View
## 模块决策说明
## 关键数据流
## 架构风险与取舍
## 验证证据
## 待确认
```

## Operate + Verify

```markdown
# 部署运行与验证文档

## 结论
## 环境要求
## 配置项
## 启动步骤
## 验证步骤
## 常见问题
## 回滚与降级
## 运维检查命令
## 待确认
```

## API + Integration

```markdown
# API 技术文档

## 结论
## 认证与权限
## 基础 URL 与版本
## 快速调用路径
## 核心资源模型
## 关键接口
## 错误码与重试
## 示例
## 限制
## 待确认
```

## Module Decision Block

Use this pattern inside module sections. `背景`, `决策`, and `方案内容` are content to cover, not mandatory headings:

```markdown
### 模块名

结论：该模块负责什么，以及当前采用什么实现。

实现范围：
- 包含：
- 不包含：
- 上游：
- 下游：

为什么这样设计：说明问题、约束、最终选择、关键取舍和读者必须知道的背景。

核心实现：

- `path/to/source`
- `path/to/test`
- `command`

#### 子模块 A
#### 子模块 B
```
