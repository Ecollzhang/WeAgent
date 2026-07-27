# SPEC / SKILL / RULE 体系解读

## 总览

本项目中的 Spec、Skill、Rules 有两层含义：

- AI 协作层：用于记录任务定义、AI 角色能力、稳定协作规则和归档方法。
- 产品能力层：WeAgent 自身把 Skill、Tool、MCP、Plugin 作为 capability 类型管理和投影到 Agent runtime。

这两层互相呼应：项目一边用 AI 协作规范管理开发过程，一边把类似的规范思想产品化为 Agent 可绑定能力。

## Spec

Spec 用于回答“这一轮要解决什么、范围是什么、验收标准是什么”。

关键材料包括：

- `docs/ai-collab/spec/agent-adapter-message-stream-spec.md`
- `.planning/phases/001-toolset/*-SPEC.md`
- `.planning/phases/03-toolset/03-SPEC.md`
- `.planning/phases/04-desktop-toolset-adapter/04-SPEC.md`

例如 Agent Adapter Spec 明确了：本轮只建立 adapter/factory 和消息流规范，不实现完整 runtime、前端展示、orchestrator 任务拆解或 sandbox 隔离。这种写法避免了 AI 输出失控扩张。

Toolset 相关 Spec 则把 Skill、Tool、MCP、Plugin 的关系、权限、版本、导入、安全审查和运行时投影写成可验收要求。

## Skill

Skill 在协作层表示 AI 角色的职责和边界，在产品层表示可被 Agent 绑定和投影的能力资产。

协作层材料：

- `docs/ai-collab/skills/skill-template.md`

产品层材料：

- `toolset/01-markdown-skill.md`
- `toolset/02-zipbundle-source/bundle-review-skill/SKILL.md`
- `toolset/02-zipbundle-source/bundle-review-skill/references/review-policy.md`
- `toolset/02-zipbundle-source/bundle-review-skill/templates/report-template.md`

`bundle-review-helper` 这个 Skill 示例包含 description、workflow 和 safety，体现了可复用 AI 能力的基本结构：何时使用、读取哪些参考、是否允许执行脚本、产出什么报告。

## Rules

Rules 用于沉淀稳定做法和协作约束。关键材料包括：

- `docs/ai-collab/archive-schema.md`
- `docs/ai-collab/rules/rule-template.md`
- `.planning/PROJECT.md`
- `.planning/STATE.md`

`archive-schema.md` 是最重要的规则文件。它规定 session 必有，archive 按需升级，并区分 spec、skill、session、archive、summary、rules 的用途。

`.planning/PROJECT.md` 和 `STATE.md` 则体现工程协作规则，例如当前架构、工作约束、已做决策、最新验证和待办边界。

本包不纳入 `.claude/settings.local.json` 或其他本地 settings 文件。settings 属于开发机工具配置，不是协作过程记录；本包以 `docs/ai-collab`、`.planning`、阶段报告、验证记录、UAT 证据和分支提交索引作为 AI 协作证据。

## Session / Archive / Summary

这些目录体现“对话过程如何被沉淀”：

- `sessions/`：记录一次具体协作过程。
- `archive/`：把高价值对话整理为长期资产。
- `summaries/`：做阶段性复盘和方法总结。

从现有文件看，归档负责人包括 why、zby 等成员，符合 archive registry 对人类负责人命名的要求。

## Verification 作为协作闭环

仅有 Spec 和 Skill 还不够。本项目把验证也写入协作记录：

- Phase 03 `03-VERIFY.md` 记录 merge 后测试、build、Docker smoke。
- Phase 04 `04-VERIFY.md` 记录桌面端 Toolset Adapter 的 checkpoint、provider evidence、build 和 backend 全量测试。
- `.planning/tmp` 中保存截图、日志和 UAT JSON。

因此，本项目的协作体系不是“AI 给建议后结束”，而是“定义目标、拆计划、执行、验证、归档”的闭环。
