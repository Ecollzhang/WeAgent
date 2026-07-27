# I. AI 协作规则层方案

> 摘要：AI 协作规则层用于沉淀 AgentHub 项目如何使用 AI 完成开发。它连接所有功能模块，并面向原命题中权重最高的“AI 协作能力”评分项。核心产出包括 Spec、rules、skills、AI 协作开发记录、AI 产出审核规范和可展示的协作链路。

## 1. 模块目标

原命题明确要求沉淀和 AI 协作的 Spec、skill、rules 等协作规范。该模块不是附属文档，而是评分核心之一。

目标：

- 证明团队不是“随便问 AI”，而是有结构化协作方法。
- 让 AI 协作过程可复盘、可审核、可展示。
- 把高频开发任务沉淀成规则和技能。
- 让评审看到 AI 如何提升开发效率和质量。

## 2. 功能清单

| 内容 | 优先级 | 说明 |
|---|---|---|
| Spec 模板 | P0 | 功能、接口、验收标准 |
| Rules 模板 | P0 | 编码规则、文档规则、模块规则 |
| Skills 模板 | P0 | 前端、后端、Adapter、Demo 等可复用技能 |
| 协作日志 | P0 | 记录每次 AI 参与做了什么 |
| 人工审核记录 | P0 | 说明人如何校验 AI 产出 |
| Prompt 样例 | P1 | 展示关键任务如何指令化 |
| 质量评估表 | P1 | 记录 AI 产出质量 |

## 3. 推荐目录

```text
docs/ai-collaboration/
  README.md
  collaboration-log.md
  prompt-examples.md
  review-records.md

specs/
  frontend-chat.spec.md
  backend-api.spec.md
  adapter.spec.md
  artifact.spec.md

rules/
  coding-rules.md
  documentation-rules.md
  agent-usage-rules.md
  demo-rules.md

skills/
  frontend-component-skill.md
  backend-api-skill.md
  adapter-debug-skill.md
  demo-script-skill.md
```

## 4. Spec 规则

每个 Spec 至少包含：

```markdown
# 功能 Spec

## 背景
## 目标
## 用户故事
## P0 / P1 / P2
## 接口
## 数据结构
## 验收标准
## 风险与降级
```

Spec 不是写给 AI 的一次性提示词，而是写给团队和 AI 共同遵守的任务契约。

## 5. Rules 规则

Rules 用来约束 AI 产出，例如：

- 前端必须使用 Vue 3 + TypeScript。
- 所有模块必须使用统一 AgentEvent。
- 后端 API 必须写请求和响应样例。
- Adapter 不允许把 raw output 直接传给前端。
- 产物必须登记 ArtifactRef。
- 文档必须写风险和验收标准。

## 6. Skills 规则

Skill 是可复用的 AI 工作流程。示例：

| Skill | 用途 |
|---|---|
| frontend-component-skill | 根据 Spec 生成 Vue 组件和 Pinia store |
| backend-api-skill | 根据 API 设计生成 FastAPI router 和 schema |
| adapter-debug-skill | 调试 Codex / Claude Code 流式输出 |
| artifact-preview-skill | 生成 ArtifactCard 和预览逻辑 |
| demo-script-skill | 根据当前功能生成 3 分钟 Demo 脚本 |

## 7. 协作日志模板

```markdown
## 日期

### 任务

### 使用的 AI / Agent

### 输入给 AI 的上下文

### AI 产出

### 人工修改

### 最终结果

### 可复用经验
```

## 8. 人工审核规则

AI 产出必须经过人工审核：

| 类型 | 审核点 |
|---|---|
| 代码 | 是否能运行、是否符合模块边界、是否有明显安全风险 |
| 接口 | 请求响应是否和协议一致 |
| 文档 | 是否符合原命题、是否可答辩 |
| Demo | 是否可演示、是否有兜底 |

## 9. 和功能模块的关系

| 功能模块 | AI 协作沉淀 |
|---|---|
| A 前端 | 前端组件生成 Skill、UI 规则 |
| B 后端 | API 生成 Skill、接口验收 Spec |
| C 协议 | 数据协议规则、字段命名规则 |
| D 编排 | Orchestrator Spec、调度策略记录 |
| E Adapter | Adapter 调试 Skill、raw output 映射记录 |
| F Runtime | Sandbox 风险规则 |
| G Artifact | 产物识别和预览规则 |
| H 交付 | Demo 脚本 Skill、协作日志汇总 |

## 10. 验收标准

- 至少有 4 个 Spec 文件。
- 至少有 4 个 Rules 文件。
- 至少有 4 个 Skills 文件。
- 有完整 AI 协作开发记录。
- 答辩时能展示一次“AI 接收 Spec -> 产出 -> 人工审核 -> 合入”的完整过程。

## 11. 相关链接

- [总规则文件](../00_agenthub_rules.md)
- [H 交付与工程化层](./H_delivery_engineering.md)
- [Demo 脚本附录](../appendices/demo_script.md)

