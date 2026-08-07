# AI Collaboration Archive

`docs/ai-collab/` 用于归档 WeAgent 项目中的 AI 协作过程、关键决策、阶段成果和复盘材料。它的目标是让后续开发者能追溯“需求如何形成、方案如何选择、代码为什么这样改”。

## 目录用途

```text
docs/ai-collab/
├─ archive/       # 阶段性归档和复盘
├─ sessions/      # 单次或连续 AI 协作会话记录
└─ README.md
```

如果本地存在个人归档索引，例如 `archive-register.md`，它通常用于个人工作流，不建议提交到仓库。请提交通用归档文档，不提交个人私有配置。

## 什么时候归档

建议在以下节点归档：

- 完成一个阶段性需求。
- 合并远程分支并解决冲突。
- 修复影响范围较大的缺陷。
- 引入新的架构、工作流或工具链。
- AI 协作中形成了可复用的 spec、rule、skill 或测试策略。

长时间协作建议每 30-60 分钟做一次轻量归档，避免上下文丢失。

## 推荐归档结构

```markdown
# 标题

## 背景

这次协作要解决什么问题，涉及哪些模块。

## 需求与约束

- 用户目标
- 明确不做的范围
- 技术约束

## 方案

- 分阶段计划
- 关键权衡
- 需要确认的问题及结论

## 实现摘要

- 修改文件
- 新增接口/组件/数据结构
- 兼容处理

## 验证

- 已运行测试
- 未运行测试及原因
- 回归范围

## 后续

- 遗留风险
- 下一阶段建议
```

## 与项目规约的关系

项目中已经沉淀了 AI Coding 相关文档，例如：

- `CollaborationFlowSkill.md`
- `CollaborationFlowSkill_zh-CN.md`
- `Spec.md`
- `Spec_zh-CN.md`
- `Rules.md`
- `Rules_zh-CN.md`
- `AI-Coding模式选择.md`
- `AI-Coding-Mode-Selection.md`
- `Merge-Branch-Guidelines.md`
- `合并分支规范.md`

协作归档应遵循这些规约：先明确需求，再写方案，分阶段实现，阶段完成后做验证和受影响功能回归。

## Git 提醒

归档前建议先查看工作区：

```powershell
git status --short
```

已经完成并验证通过的功能，建议先提交，保持暂存区和工作区清晰，再进入下一阶段。归档文档可以和对应功能提交放在同一个 commit，也可以作为单独文档提交。

## 不建议归档的内容

- API Key、Token、Cookie、私有代理地址。
- 用户个人账号密码。
- 未脱敏的生产数据。
- 个人 IDE 配置、临时缓存和本地路径依赖。

## 文件命名建议

```text
YYYY-MM-DD-topic.md
phase-XX-topic.md
why-topic-v1.0-MM-DD.md
```

命名应体现主题和时间，便于检索。
