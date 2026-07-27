# 风险与兜底方案

本文档汇总 AgentHub MVP 的主要风险和降级方案，用于开发排期和答辩说明。

## 1. 外部 Agent 风险

| 风险 | 影响 | 兜底 |
|---|---|---|
| Codex CLI 不可用 | 真实 Agent 无法演示 | 使用 Mock Adapter |
| Claude Code SDK 不稳定 | 双 Agent 链路不完整 | 使用 CLI 备用路线或 Mock |
| API Key / 网络问题 | 现场失败 | 提前录屏，现场切 Mock |
| 输出格式变化 | Event Normalizer 解析失败 | raw_log 事件展示原始输出 |

## 2. 实时通信风险

| 风险 | 影响 | 兜底 |
|---|---|---|
| SSE 连接中断 | 前端看不到流式输出 | 刷新后从 agent_events 恢复 |
| 事件类型过多 | 前端消费复杂 | P0 只支持核心事件 |
| 多 run 并发混乱 | 消息串线 | P0 单会话顺序执行 |

## 3. Orchestrator 风险

| 风险 | 影响 | 兜底 |
|---|---|---|
| 自动拆任务不准 | Agent 分工混乱 | 优先 direct_mention，让用户 @Agent |
| 并行调度复杂 | 时间不足 | P0 顺序调度 |
| Agent 失败导致 run 失败 | 主链路中断 | 单 Agent 失败后继续汇总并说明 |

## 4. Artifact 风险

| 风险 | 影响 | 兜底 |
|---|---|---|
| Web 预览启动失败 | 无法展示网页效果 | 展示静态 HTML 或代码卡片 |
| 产物路径不规范 | 无法登记 Artifact | 扫描 workspace 常见目录 |
| Diff 视图来不及 | 少一个增强点 | P0 只做代码全文预览 |

## 5. 工程交付风险

| 风险 | 影响 | 兜底 |
|---|---|---|
| 12 天时间不足 | 功能不完整 | 保 P0，P1/P2 写清楚预留 |
| 文档和代码不一致 | 答辩困难 | 每个模块写验收标准 |
| 现场环境失败 | 演示失败 | 准备兜底录屏和 Mock Adapter |

## 6. 最小可演示兜底链路

即使真实 Agent 全部不可用，也必须保证以下链路可演示：

```text
Vue 前端
 -> FastAPI Message API
 -> Run 创建
 -> Mock Adapter 流式事件
 -> SSE 推送
 -> 消息气泡更新
 -> artifact.created
 -> 产物卡片展示
```

