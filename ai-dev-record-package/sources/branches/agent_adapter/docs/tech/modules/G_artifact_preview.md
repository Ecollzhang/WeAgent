# G. Artifact 产物层方案

> 摘要：Artifact 产物层负责把 Agent 的输出变成用户能看、能点、能预览、能下载的内容。它连接 Runtime、后端 API、前端 Web 和数据协议，核心接口是 `ArtifactRef`、Artifact API、`artifact.created` 事件和预览 URL。

## 1. 模块目标

AgentHub 的产物不能只停留在聊天文本里。用户需要在聊天流中看到 Agent 生成了什么，并能直接打开。

核心目标：

- 将 Agent 输出文件登记为 Artifact。
- 在聊天流内显示产物卡片。
- 支持代码预览。
- 支持网页 iframe 预览。
- 支持文件下载。
- 支持 ZIP 导出和部署状态卡片作为 P1。

## 2. 功能清单

| 功能 | 优先级 | 说明 |
|---|---|---|
| Artifact 创建 | P0 | 中台或后端登记产物 |
| 代码卡片 | P0 | 展示文件名、语言、摘要，点击进入 Monaco |
| 网页预览卡片 | P0 | iframe 展示静态页面 |
| 文件卡片 | P0 | 支持下载 |
| Artifact Panel | P0 | 右侧或全屏预览 |
| ZIP 导出 | P1 | 打包 workspace 或 artifacts |
| 部署状态卡片 | P1 | 模拟或真实部署状态 |
| Diff 视图 | P1/P2 | 代码差异查看 |

## 3. 模块边界

Artifact 层不负责生成内容，生成由 Agent 完成。Artifact 层负责发现、登记、预览和交付。

## 4. 相连模块

| 相连模块 | 连接方式 | 说明 |
|---|---|---|
| [F Runtime](./F_runtime_sandbox.md) | artifacts path | 读取 Agent 生成的文件 |
| [B 后端 API](./B_backend_api_realtime.md) | Artifact API | 查询、预览、下载 |
| [A 前端 Web](./A_frontend_web.md) | ArtifactCard、ArtifactPanel | 展示产物 |
| [C 数据协议](./C_data_protocol.md) | ArtifactRef | 统一产物引用 |
| [E Agent Adapter](./E_agent_adapter.md) | artifact.created | Adapter 可主动上报产物 |

## 5. 产物类型

| 类型 | P0 | 展示方式 |
|---|---|---|
| `code` | 是 | Monaco Editor |
| `web_preview` | 是 | iframe |
| `file` | 是 | 文件卡片 + 下载 |
| `diff` | P1 | Diff Viewer |
| `deployment` | P1 | 部署状态卡片 |
| `text_document` | P1 | Markdown 或纯文本预览 |

## 6. ArtifactRef

```ts
type ArtifactRef = {
  id: string;
  type: 'code' | 'web_preview' | 'file' | 'diff' | 'deployment' | 'text_document';
  title: string;
  previewUrl?: string;
  url?: string;
  language?: string;
  storagePath?: string;
  metadata?: Record<string, unknown>;
};
```

## 7. Artifact Service 流程

```text
Agent 生成文件
 -> 文件进入 workspace/artifacts 或 workspace/src
 -> Artifact Service 扫描或接收 Adapter 上报
 -> 创建 artifacts 记录
 -> 生成 preview_url / download_url
 -> 发出 artifact.created 事件
 -> 前端显示 ArtifactCard
```

## 8. 预览方案

### 8.1 代码产物

- 使用 Monaco Editor。
- 显示文件路径、语言、内容。
- P1 支持复制和下载。

### 8.2 网页产物

- 静态 HTML 使用 iframe。
- 如果是 Vue/React 项目，P0 可以展示生成文件，P1 再启动预览服务。
- 真实预览不稳定时，使用截图或静态入口页兜底。

### 8.3 文件产物

- 文件名、大小、类型。
- 下载按钮。
- 文本文件可以直接预览。

## 9. P0 / P1 / P2 范围

| 等级 | 内容 |
|---|---|
| P0 | code、web_preview、file、ArtifactCard、ArtifactPanel |
| P1 | ZIP 导出、部署状态卡片、Diff Viewer |
| P2 | 版本历史、在线二次编辑、真实生产部署 |

## 10. 风险与降级方案

| 风险 | 降级 |
|---|---|
| Web 预览服务不稳定 | iframe 静态 HTML 或展示文件结构 |
| Agent 产物路径不规范 | Artifact Service 扫描常见路径并允许手动登记 |
| Diff 来不及 | P0 只做代码全文预览 |

## 11. 验收标准

- Agent 生成代码后，聊天流出现代码卡片。
- 点击代码卡片能看到代码内容。
- 网页产物可以 iframe 打开或有清晰预览入口。
- 文件产物可以下载。
- Artifact 与 conversation、run、agent 关联清楚。

## 12. 相关链接

- [A 前端 Web 层](./A_frontend_web.md)
- [F Runtime 与 Sandbox 层](./F_runtime_sandbox.md)
- [API 附录](../appendices/api_reference.md)

