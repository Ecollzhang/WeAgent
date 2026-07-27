# H. 交付与工程化层方案

> 摘要：交付与工程化层负责保证 AgentHub 不是只有代码，而是有可运行 Demo、可解释文档、可复现流程、测试记录和演示材料。它连接全部业务模块，核心产出包括技术文档、产品设计文档、AI 协作开发记录、Demo 脚本、3 分钟视频和风险兜底方案。

## 1. 模块目标

本模块解决比赛交付问题：

- 12 天内如何安排开发节奏。
- 如何保证主链路可演示。
- 如何记录 AI 协作过程。
- 如何准备答辩材料。
- 如果真实 Agent 或部署失败，如何兜底。

## 2. 必交付物

| 交付物 | 优先级 | 说明 |
|---|---|---|
| 技术方案文档 | P0 | 当前 docs/tech |
| 产品设计文档 | P0 | IM 体验、页面流程、用户路径 |
| 可运行 Demo | P0 | Web 前端 + Python 后端 + 中台 |
| AI 协作开发记录 | P0 | 对应评审 30% |
| 3 分钟 Demo 视频 | P0 | 固定脚本录制 |
| Demo 脚本 | P0 | 答辩和录屏使用 |
| 测试记录 | P1 | 接口、主链路、Adapter |
| 兜底录屏 | P1 | 防现场环境失败 |

## 3. 推荐仓库结构

```text
agenthub/
  apps/
    web/
  services/
    api/
    middleware/
    adapter-gateway/
    runtime/
  packages/
    protocol/
  docs/
    product/
    tech/
    ai-collaboration/
    demo/
  specs/
  rules/
  skills/
  workspace-root/
```

## 4. 12 天计划

| 阶段 | 时间 | 目标 | 产出 |
|---|---|---|---|
| 阶段 1 | D1-D2 | 方案和协议定稿 | 架构图、模块文档、API、事件协议 |
| 阶段 2 | D3-D5 | IM 单聊跑通 | 会话、消息、Mock Adapter、SSE |
| 阶段 3 | D6-D8 | 多 Agent 跑通 | Codex、Claude Code、Orchestrator、@Agent |
| 阶段 4 | D9-D10 | 产物体验跑通 | ArtifactCard、Monaco、iframe、文件下载 |
| 阶段 5 | D11-D12 | 打磨和交付 | Demo 脚本、视频、文档、兜底方案 |

## 5. 测试策略

| 测试对象 | 方法 |
|---|---|
| API | 使用接口样例验证 Conversation、Message、Run、Artifact |
| SSE | 使用 Mock Adapter 验证事件顺序 |
| Orchestrator | 输入 @Agent 消息，检查 OrchestratorPlan |
| Adapter | 分别验证 Codex、Claude Code、Mock 输出 AgentEvent |
| 前端 | 手工演示主链路，必要时补 Playwright |
| Artifact | 验证代码、网页、文件三类卡片可打开 |

## 6. 日志与排障

至少保留三类日志：

- `run_logs`：一次 run 的状态变化。
- `agent_events`：所有标准事件。
- `adapter_raw_logs`：外部 Agent 原始输出。

答辩时可以展示：

```text
用户消息
 -> run
 -> orchestrator plan
 -> agent events
 -> artifact
```

## 7. Demo 主脚本

3 分钟演示建议：

1. 进入 AgentHub，展示会话列表和 Agent 联系人。
2. 新建群聊，选择 Codex 和 Claude Code。
3. 输入“@codex @claude-code 帮我做一个 Todo 网页，一个实现，一个检查”。
4. 展示 Orchestrator 分工。
5. 展示两个 Agent 依次流式回复。
6. 展示代码卡片和网页预览卡片。
7. 展示自建 Agent 页面。
8. 展示 AI 协作记录和 rules / skills。

完整脚本见 [Demo 脚本附录](../appendices/demo_script.md)。

## 8. 风险与兜底

| 风险 | 兜底 |
|---|---|
| 现场 Agent 调用失败 | 切 Mock Adapter |
| 网络或 API Key 问题 | 播放兜底录屏 |
| 部署预览失败 | 展示 ZIP 导出和静态预览 |
| SSE 中断 | 展示已落库事件和刷新恢复 |

## 9. 验收标准

- 文档能解释每个模块。
- Demo 能完整跑一遍主链路。
- 至少一个真实 Agent 接入成功。
- Mock Adapter 能在无外部依赖时完成演示。
- AI 协作材料可被评审看到。

## 10. 相关链接

- [I AI 协作规则层](./I_ai_collaboration_rules.md)
- [Demo 脚本附录](../appendices/demo_script.md)
- [风险兜底附录](../appendices/risk_and_fallback.md)

