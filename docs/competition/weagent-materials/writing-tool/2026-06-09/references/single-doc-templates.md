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

## 结论

一句话说明系统是什么、当前实现状态、本文覆盖范围。

## 读者与范围

- 主要读者：
- 本文包含：
- 本文不包含：
- 待确认：

## 事实源

列出代码、配置、分支、测试、运行脚本、外部资料。

## 技术栈

用表格列出层级、技术、证据路径、状态。

## 系统架构

先给 C4 Context / Container 图，再解释每条主要链路。

## 核心模块

每个重要模块使用“结论 -> 背景 -> 决策 -> 方案内容 -> 证据”的 ADR/MADR 叙述块。

## 关键数据流

按用户操作、系统执行、异步事件、数据持久化、错误处理描述。

## API 与数据模型摘要

只放关键接口、数据模型、配置项。完整接口表另行待确认或附录化，但仍在同一个文件中。

## 部署与运行

提供可执行步骤、命令、环境变量、预期输出和注意事项。

## 测试与验证

列出已经运行、未运行、如何复现、失败如何排查。

## 风险、限制与降级

只写真实风险。无法确认的内容标注 `待确认`。

## Troubleshooting

按症状、可能原因、检查命令、处理方式组织。

## Glossary

列出项目特有术语。
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

Use this block inside module sections, not as a standalone table:

```markdown
### 模块名

结论：该模块负责什么，以及当前采用什么实现。

#### 背景

说明问题、约束、历史原因或上下游需求。

#### 决策

说明最终选择。必要时点到未采用方案，但不要展开成冗长比较。

#### 方案内容

说明包含哪些组件、接口、配置、数据、事件、生命周期、边界和限制。

#### 证据

- `path/to/source`
- `path/to/test`
- `command`
```
