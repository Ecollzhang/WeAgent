# WeAgent 技术文档

`docs/tech/` 存放 WeAgent 的技术方案、模块设计和实现约束。这里的文档用于解释“为什么这样设计”和“模块之间如何协作”，不替代根目录 README 的启动说明。

## 当前技术基线

| 层级 | 技术 |
|---|---|
| 后端 | Flask, SQLAlchemy, JWT, Socket.IO |
| Web | Vue 2, Vuex, Vue Router, Element UI |
| Desktop | Electron, Vite, Vue 2 |
| Android | Capacitor, Vite, Vue 2 |
| 沙箱 | Docker, Orchestrator Server, Claude Code, Codex, OpenCode |
| 数据 | MySQL, Redis |

## 推荐阅读顺序

1. `00_agenthub_rules.md`：总体规则、范围和技术边界。
2. `01_problem_scope.md`：问题拆解、MVP 范围和优先级。
3. `02_architecture_overview.md`：整体架构、主链路和数据流。
4. `03_module_index.md`：模块索引和上下游关系。
5. `modules/`：具体模块方案。
6. `appendices/`：API、事件、数据库、演示脚本、风险兜底等补充资料。

如果旧文档中仍出现 `AgentHub`、`FastAPI`、`Vue 3` 等早期方案名称，请以当前代码和根 README 为准。当前项目名称为 `WeAgent`，主技术栈是 Flask + Vue 2。

## 文档结构

```text
docs/tech/
├─ 00_agenthub_rules.md
├─ 01_problem_scope.md
├─ 02_architecture_overview.md
├─ 03_module_index.md
├─ modules/
└─ appendices/
```

## 重点模块

- 会话与消息：Conversation、Message、Socket.IO、结构化元素流。
- Agent 管理：Agent CRUD、能力标签、Skill、会话级配置。
- 工具集能力：Skill/Tool/Plugin/MCP 导入、审计、配置、绑定、沙箱投影。
- 沙箱容器：每会话独立容器、文件树、服务代理、日志、产物上报。
- 多端客户端：Web 主站、Electron 桌面端、Capacitor Android 端。
- 产物系统：文件、表格、HTML、Raw Output、Diff、工作流图。

## 写作约定

- 技术文档应区分“已实现”“进行中”“计划中”。
- 涉及接口时写清请求路径、关键字段、错误处理和回归测试点。
- 涉及多端时写清 Web、Desktop、Android 的差异。
- 涉及沙箱时写清宿主端和容器端的边界。
- 若方案与当前代码不一致，应在文档开头标注“历史方案”或更新为当前实现。

## 功能图引用

可以复用 Web 手册中的图片：

```text
frontend/src/assets/登录.png
frontend/src/assets/模型设置.png
frontend/src/assets/对话.png
frontend/src/assets/主持人Agent.png
frontend/src/assets/前端Agent.png
```

示例：

```markdown
![对话界面](../../frontend/src/assets/对话.png)
```

## 维护建议

- 新增大功能时同步补充模块文档。
- 合并远程分支后先分析功能冲突，再更新技术文档。
- 完成阶段工作后，记录验收标准和回归范围。
- 文档和代码不一致时，优先修正文档，不要让旧方案继续误导后续开发。
