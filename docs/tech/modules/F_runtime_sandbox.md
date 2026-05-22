# F. Runtime 与 Sandbox 层方案

> 摘要：Runtime 与 Sandbox 层负责为每个会话创建独立 workspace，并限制 Agent 的文件访问、命令执行和产物输出范围。它连接 Orchestrator、Agent Adapter 和 Artifact 服务，核心接口是 Workspace API、Permission Policy 和文件操作封装。

## 1. 模块目标

Agent 会生成代码、修改文件、运行命令。如果所有会话共享一个目录，就会互相污染，也难以复现 Demo。Runtime 层负责给每个会话准备隔离工作区。

核心目标：

- 每个 Conversation 有独立 workspace。
- 每个 run 可以写 logs 和 artifacts。
- Agent 默认只能读写当前 workspace。
- 命令执行有权限策略。
- 产物输出可被 Artifact Service 发现。

## 2. 功能清单

| 功能 | 优先级 | 说明 |
|---|---|---|
| Workspace 创建 | P0 | 为 conversation 创建目录 |
| Workspace 查询 | P0 | 根据 conversationId 获取路径 |
| Artifacts 目录 | P0 | 存放可预览和下载的产物 |
| Logs 目录 | P0 | 存放 Agent 原始日志 |
| 文件读写封装 | P0 | 限制在 workspace 内 |
| 命令执行封装 | P1 | 控制 shell 命令权限 |
| Git worktree | P1 | 更强隔离和版本追踪 |
| 容器 Sandbox | P2 | 生产级隔离 |

## 3. 模块边界

Runtime 不负责 UI 展示，不负责业务 API，不负责 Agent 输出解析。

它只负责：

- 创建目录。
- 校验路径。
- 封装文件访问。
- 封装命令执行。
- 提供产物目录给 Artifact 层。

## 4. 相连模块

| 相连模块 | 连接方式 | 说明 |
|---|---|---|
| [D Orchestrator](./D_orchestrator.md) | Workspace API | 执行任务前申请工作区 |
| [E Agent Adapter](./E_agent_adapter.md) | workspace path | Agent 在该路径下运行 |
| [G Artifact](./G_artifact_preview.md) | artifacts path | 扫描和读取产物 |
| [B 后端 API](./B_backend_api_realtime.md) | Workspace metadata | 查询 workspace 状态 |

## 5. 目录结构

```text
workspace-root/
  conversations/
    conv_001/
      src/
      artifacts/
      logs/
      .agenthub/
        run_001.json
        permissions.json
    conv_002/
      src/
      artifacts/
      logs/
```

## 6. Workspace API

```ts
type Workspace = {
  id: string;
  conversationId: string;
  path: string;
  status: 'ready' | 'locked' | 'archived' | 'error';
  createdAt: string;
};
```

```ts
interface WorkspaceService {
  ensureWorkspace(conversationId: string): Promise<Workspace>;
  getWorkspace(conversationId: string): Promise<Workspace>;
  resolvePath(workspaceId: string, relativePath: string): Promise<string>;
  archiveWorkspace(conversationId: string): Promise<void>;
}
```

## 7. 权限策略

| 操作 | P0 策略 |
|---|---|
| 读取 workspace 内文件 | allow |
| 写入 workspace 内文件 | allow |
| 访问 workspace 外路径 | deny |
| 执行 shell | ask 或 P1 |
| 读取环境变量 | deny |
| 网络访问 | 由 Agent 工具自身限制，文档中标风险 |
| 部署 | P1，需要用户确认 |

## 8. 路径安全规则

所有文件路径必须经过 `resolvePath`：

```text
workspace root + relative path
 -> normalize
 -> 校验最终路径仍在 workspace root 下
 -> allow
```

如果最终路径逃逸 workspace，直接拒绝。

## 9. P0 / P1 / P2 范围

| 等级 | 内容 |
|---|---|
| P0 | 本地目录隔离、路径校验、artifacts/logs 目录 |
| P1 | git worktree、命令执行封装、任务取消 |
| P2 | 容器隔离、资源限额、审计追踪 |

## 10. 风险与降级方案

| 风险 | 降级 |
|---|---|
| Sandbox 实现过重 | MVP 使用本地目录隔离 |
| shell 命令风险高 | P0 不开放任意 shell，或只允许 Adapter 自己执行 |
| 多 run 同时写文件冲突 | P0 顺序调度，P1 加 workspace lock |

## 11. 验收标准

- 每个会话都有独立目录。
- Agent 写出的文件不会出现在其他会话目录。
- Artifact Service 能从 artifacts 目录读取产物。
- 非法路径访问会被拒绝。
- 日志能按 run 保存。

## 12. 相关链接

- [E Agent Adapter 层](./E_agent_adapter.md)
- [G Artifact 产物层](./G_artifact_preview.md)
- [风险兜底附录](../appendices/risk_and_fallback.md)

