# WeAgent Documentation TODO

更新日期：2026-06-09

本文用于跨会话追踪 WeAgent 产品文档与技术文档的撰写状态。继续工作时，先读本文，再读 `docs/PRODUCT_DOCUMENTATION.md` 和 `docs/TECHNICAL_DOCUMENTATION.md`。

## 1. 当前状态

状态：技术文档重写后审查中。

本轮已经完成：

- [x] 重新执行 `git fetch origin --prune`。
- [x] 确认当前本地分支为 `combine/toolset_v1.1.0`。
- [x] 确认 `origin/feature/user_manual_and_product_introduction_v1.1.1` 最新提交为 `403bb1a`，提交时间为 `2026-06-07 19:25:10 +08:00`。
- [x] 确认 `origin/combine/toolset_v1.1.0` 最新提交为 `14d7d4b`，提交时间为 `2026-06-06 23:17:44 +08:00`。
- [x] 按用户要求修正事实源规则：除 Toolset / Capability 外，其余模块以 `origin/feature/user_manual_and_product_introduction_v1.1.1` 为根本依据。
- [x] Toolset / Capability 只以 `origin/combine/toolset_v1.1.0` 为事实来源。
- [x] 生成 5 张 imagegen 架构图，并复制到 `docs/assets/`。
- [x] 重写 `docs/TECHNICAL_DOCUMENTATION.md`，把未确认内容移出正式技术正文。

本轮仍需完成：

- [ ] 对 `docs/TECHNICAL_DOCUMENTATION.md` 做一致性校验。
- [ ] 检查旧技术栈、`待确认`、跨分支错误归属是否仍误入正文。
- [ ] 检查图片引用路径是否正确。
- [ ] 根据技术文档变更，决定是否同步调整 `docs/PRODUCT_DOCUMENTATION.md` 中的状态表述。

## 2. 硬规则

- 文档与项目实际冲突时，以代码、配置、运行脚本、测试和已确认分支事实为准。
- 不能从事实源确认的内容不写进正式技术文档正文。
- 不用“待确认”填充正式技术文档；待确认内容只保留在 TODO 或人工问题清单里。
- 不把产品文案当作实现事实，必须回到代码路径、路由、模型、组件或服务确认。
- `imagegen` 生成图只能作为架构理解辅助，精确事实以正文和代码路径为准。
- 旧 `docs/tech/` 只作结构参考，不作当前技术事实来源。

## 3. 文档目标

| 文档 | 路径 | 第一读者 | 第二读者 | 目标 |
|---|---|---|---|---|
| TODO | `docs/DOCUMENTATION_TODO.md` | 后续协作 agent | 项目成员 | 记录状态、规则、事实源、待办和恢复提示 |
| 产品文档 | `docs/PRODUCT_DOCUMENTATION.md` | 比赛评审 | 真实用户 | 说明 WeAgent 是什么、解决什么问题、能如何使用 |
| 技术文档 | `docs/TECHNICAL_DOCUMENTATION.md` | 比赛评审 | 开发维护者 | 说明真实架构、关键模块、数据流、运行验证和风险 |

## 4. 事实源优先级

1. 代码、配置、运行脚本、路由、模型、测试和 lockfile。
2. 已拉取远程分支中的代码差异和提交记录。
3. `.planning/`、`docs/report/`、README、用户手册。
4. 旧 `docs/tech/`。
5. 外部 skill / workflow，只作写作方法参考，不作 WeAgent 功能事实来源。

## 5. 分支事实矩阵

| 范围 | 事实源 | 本轮确认 |
|---|---|---|
| Toolset / Capability | `origin/combine/toolset_v1.1.0` | 导入预览、确认导入、安全审查、高风险专家确认、Provider 配置、Agent 绑定、`.weagent` 投影、调用记录同步 |
| 客户端、多端、Agent 管理、会话收藏、Artifact / Workbench、服务预览、实时事件 | `origin/feature/user_manual_and_product_introduction_v1.1.1` | Web、Desktop、Android、Agent 分类/卡片/拖拽/只读查看、收藏页搜索过滤、ArtifactWorkbench、Diff、FileMigrationDialog、服务面板、服务代理 |
| Artifact editing 合并线 | 已合并进 `origin/feature/user_manual_and_product_introduction_v1.1.1` | 通过 `403bb1a` merge commit 确认 |
| 当前本地分支 | `combine/toolset_v1.1.0` | 只作为 toolset 主线和当前工作区状态确认 |

## 6. 本轮图片资产

| 图片 | 路径 | 用途 |
|---|---|---|
| 总览图 | `docs/assets/weagent-architecture-overview.png` | `一张图看懂 WeAgent` |
| Agent 执行层 | `docs/assets/weagent-execution-layer.png` | Agent Runtime、Provider Runner、Event Bridge |
| Toolset / Capability | `docs/assets/weagent-toolset-capability.png` | 导入、审查、绑定、投影 |
| Artifact / Workbench | `docs/assets/weagent-artifact-workbench.png` | 产物、Workbench、编辑、Diff、复用 |
| Service / Realtime | `docs/assets/weagent-service-realtime.png` | `weagent-service`、代理链接、日志、实时事件 |

注意：这些图片由 imagegen 生成，图内标签只做架构级辅助。正文中的模块边界和事实仍以代码证据为准。

## 7. 已确认写作原则

- 先说结论，再给细节。
- 每节只解决一个问题。
- 每个模块先写实现范围，再拆子模块。
- 模块必须说明包含什么、不包含什么、上游是什么、下游是什么、证据在哪里。
- ADR / MADR 的背景、决策、方案内容融入模块正文，不作为固定标题。
- 数据流优先用 Mermaid `sequenceDiagram`。
- 标题要让读者一眼看懂，例如“常见故障定位”“关键术语速查”。
- 技术文档中文为主，保留必要英文术语。
- 参数、变量、文件名、命令、路径、接口使用代码格式。
- 每个代码块前说明用途，代码块后说明预期结果或注意事项。

## 8. 技术文档当前结构

```markdown
# WeAgent 技术文档
## 1. 结论：WeAgent 技术上是什么
## 2. 读者、范围与事实源
## 3. 一张图看懂 WeAgent
## 4. 技术分层总览
## 5. 系统架构
### 5.1 客户端层：Web、Desktop、Android
### 5.2 后端协调层：Flask API、Socket.IO、业务服务
### 5.3 会话与消息系统
### 5.4 Agent 执行系统
### 5.5 Docker Sandbox 系统
## 6. 核心模块
### 6.1 Capability / Toolset 系统
### 6.2 Artifact 与 Workbench 系统
### 6.3 WeAgent Service 与服务预览
### 6.4 实时推送与事件系统
## 7. 关键数据流
## 8. 开发者部署与运行
## 9. 关键接口与数据模型
## 10. 开发者验证路径
## 11. 已知限制与风险
## 12. 常见故障定位
## 13. 关键术语速查
```

## 9. 待办清单

### 9.1 技术文档审查

- [ ] 运行 `rg -n "待确认" docs/TECHNICAL_DOCUMENTATION.md`，结果应为空。
- [ ] 运行 `rg -n "FastAPI|Vue 3|SQLite|Postgres" docs/TECHNICAL_DOCUMENTATION.md`，确认只出现在文档漂移说明中。
- [ ] 检查 `docs/TECHNICAL_DOCUMENTATION.md` 中图片路径都能指向 `docs/assets/`。
- [ ] 检查 Toolset 内容只引用 `origin/combine/toolset_v1.1.0`。
- [ ] 检查 Toolset 以外内容以 `origin/feature/user_manual_and_product_introduction_v1.1.1` 为根本依据。
- [ ] 检查 Agent 页面能力没有误写成“Agent 页面收藏/搜索”。
- [ ] 检查收藏/搜索只写为“会话收藏页”能力。
- [ ] 检查 Artifact / Workbench 内容是否做到一眼看懂。

### 9.2 产品文档同步

- [ ] 检查产品文档是否仍使用旧的联合事实源说法。
- [ ] 检查产品文档是否误把 toolset 外的本地分支作为根本依据。
- [ ] 检查产品文档是否需要加入本轮 imagegen 架构图引用或说明。
- [ ] 检查产品文档是否误写未确认能力。

### 9.3 最终交付前验证

- [ ] 运行后端 `python -m pytest`。
- [ ] 运行 Web `npm run build`。
- [ ] 运行 Desktop `npm run build`。
- [ ] 构建或检查 Sandbox 镜像。
- [ ] 如有最终比赛演示材料，补充真实截图、GIF、视频或演示链接。

## 10. 决策记录

| 决策 | 结果 |
|---|---|
| 是否把未确认内容写进技术正文 | 不写。未确认只进入 TODO。 |
| 总览图是否必须 imagegen | 必须。已生成并放入 `docs/assets/`。 |
| 是否使用 Mermaid 替代 imagegen 总览图 | 不替代。Mermaid 只用于关键数据流。 |
| Toolset 来源 | 只使用 `origin/combine/toolset_v1.1.0`。 |
| 其他模块来源 | 使用 `origin/feature/user_manual_and_product_introduction_v1.1.1`。 |
| Agent 页面收藏/搜索 | 未确认，不写。已确认的是会话收藏页搜索和过滤。 |

## 11. Open Questions

这些问题需要人工决定，不应在正式文档中编造：

- 最终比赛提交是否需要真实截图、GIF 或演示视频。
- 是否需要把产品文档也改成和技术文档相同的图片结构。
- 最终交付分支是否会把 `toolset` 和 `user_manual` 两条事实源合并成单一分支。
- 是否需要为技术文档补充完整 API 表和 ER 图。

## 12. Resume Prompt

```text
继续 WeAgent 文档工作。先读 docs/DOCUMENTATION_TODO.md，再读 docs/TECHNICAL_DOCUMENTATION.md 和 docs/PRODUCT_DOCUMENTATION.md。硬规则：未确认内容不写入正式技术文档；Toolset / Capability 只以 origin/combine/toolset_v1.1.0 为事实源；其他模块以 origin/feature/user_manual_and_product_introduction_v1.1.1 为事实源；imagegen 图已生成在 docs/assets/。下一步先做技术文档一致性校验，再决定是否同步产品文档。
```
