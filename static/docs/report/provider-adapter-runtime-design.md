# 多 Provider Sandbox Runtime 方案

更新时间：2026-05-28

## 1. 目标

在不破坏现有 Claude Code 沙箱能力的前提下，把 Agent 底层 provider 扩展为：

- Claude Code
- Codex
- OpenCode

不同 Agent 角色可以选择不同底层，但这个选择不是代码固定映射，而是来自 Agent 角色库配置。例如：

- 前端开发专家：Claude Code
- 文档助手：Codex
- 代码审查助手：OpenCode

这些只是配置示例，不代表角色和 provider 绑定。用户或系统预设可以在 Agent 角色库中为任意 Agent 配置底层 provider。同一个“前端开发专家”也可以被配置为 Claude、Codex 或 OpenCode。

无论底层 provider 是谁，都必须尽量拥有和现有 Claude Code 一致的能力：

- 在同一个会话 sandbox container 内执行。
- 每个 Agent 有自己的工作目录。
- 能访问 shared 目录和其他 Agent 工作目录。
- 能恢复上下文继续对话。
- 能实时流式输出。
- 能上报进度、结果、表格、文件、图片、代码。
- 能停止执行。
- 能记录日志。
- 能让前端刷新后恢复 raw output、result、产物卡片。
- 能让前端预览 HTML、图片、文件、下载产物、访问容器内服务。

队友的 adapters 代码可以大改、弃用或重构。这里不保留 local adapter 版本，不考虑 mock。所有正式 provider 都以现有 Claude Code 沙箱方案为基准来实现。

## 2. 核心结论

当前 Claude Code 方案已经是成功案例，应该把它抽象成通用 ProviderRunner，而不是改掉它。

推荐架构：

```text
message_service
  -> sandbox host manager/client
    -> container server
      -> container orchestrator
        -> AgentRuntime
          -> ProviderRunnerFactory
            -> ClaudeCodeRunner
            -> CodexRunner
            -> OpenCodeRunner
```

原则：

- 正式执行全部在 container 内。
- 不保留 host/local adapter 正式路径。
- 不让 `orchestrator_service` 直接在后端 host 启动 `claude/codex/opencode`。
- Claude Code 原有功能必须保持不变。
- Codex/OpenCode 的兼容要复制 Claude Code 的成功模式：
  - 同一 Agent 工作目录
  - provider 原生继续上下文
  - stdout/stderr 实时读取
  - heartbeat
  - stop
  - timeout
  - 事件落库
  - 产物上报
- provider 选择只来自 Agent 角色库/Agent 配置，不能按角色名称硬编码。

## 3. Provider 上下文恢复策略

已确认：

- Claude Code：`claude -c`
- Codex：`codex resume --last`
- OpenCode：`opencode -c`

因此三者都应优先使用 provider 原生恢复上下文，而不是默认依赖 WeAgent 自建上下文。

默认策略：

| Provider | 恢复命令 | 默认上下文策略 |
|---|---|---|
| Claude Code | `claude -c` | provider 原生恢复 |
| Codex | `codex resume --last` | provider 原生恢复 |
| OpenCode | `opencode -c` | provider 原生恢复 |

WeAgent 自建上下文只作为兜底或补充：

- provider resume 失败时。
- 新增 Agent 第一次运行时。
- 用户要求引用其他 Agent 产物时。
- 主持 Agent 给 worker 分派任务时。

不要默认把完整数据库历史塞进 prompt。否则会和 provider 原生上下文重复，导致重复生成、重复上报、上下文混乱。

## 4. 镜像和容器运行环境要求

要支持多 provider，sandbox 镜像必须在创建容器前就安装好 Claude Code、Codex、OpenCode 三套 CLI。Provider runner 不能依赖容器启动后临时联网安装，否则会导致：

- 创建会话慢。
- 离线/弱网环境不可用。
- 不同容器 CLI 版本不一致。
- 测试不可复现。

当前 `backend/app/sandbox/Dockerfile` 只安装了 Claude Code。需要改成“多 provider sandbox image”。

### 4.1 Dockerfile 安装要求

Dockerfile 应安装：

- Node.js 20+
- Claude Code CLI
- Codex CLI
- OpenCode CLI
- Python orchestrator 依赖
- `weagent-report`

示意：

```dockerfile
RUN apt-get update && apt-get install -y curl git ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && npm install -g <codex-package-name> \
    && npm install -g <opencode-package-name> \
    && npm cache clean --force \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

`<codex-package-name>` 和 `<opencode-package-name>` 需要按项目实际使用的 CLI 包名确认。不能在方案里假定包名。

### 4.2 构建期版本校验

镜像构建时要校验 CLI 存在：

```dockerfile
RUN claude --version
RUN codex --version
RUN opencode --version
```

如果某 CLI 的 `--version` 参数不同，应使用对应的健康命令。

### 4.3 容器启动期健康检查

container server 启动时要记录 provider 可用性：

```json
{
  "providers": {
    "claude": {"available": true, "version": "..."},
    "codex": {"available": true, "version": "..."},
    "opencode": {"available": true, "version": "..."}
  }
}
```

建议新增 endpoint：

```text
GET /api/providers
```

或在现有：

```text
GET /api/session
```

里返回 provider health。

### 4.4 创建会话时的 provider 校验

创建 sandbox session 时，host 传入 agents config。container 初始化 Agent 时应检查：

- `adapter_name` 是否支持。
- 对应 CLI 是否安装。
- 对应配置是否存在。

如果某 Agent 配置为 Codex，但镜像里没有 Codex CLI，应在创建会话或 Agent 初始化阶段返回明确错误：

```text
Provider codex is not available in this sandbox image.
```

不要静默降级到 Claude。

### 4.5 配置注入要求

当前容器配置偏 Claude：

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_MODEL`
- `DEEPSEEK_*`
- `.claude/settings.local.json`

多 provider 后需要支持 provider 通用配置注入：

```text
# Claude
ANTHROPIC_API_KEY
ANTHROPIC_AUTH_TOKEN
ANTHROPIC_BASE_URL
ANTHROPIC_MODEL

# Codex
CODEX_API_KEY
CODEX_BASE_URL
CODEX_MODEL
CODEX_HOME

# OpenCode
OPENCODE_API_KEY
OPENCODE_BASE_URL
OPENCODE_MODEL
OPENCODE_HOME
```

具体环境变量名称需要按实际 CLI 确认。设计上应允许 settings_service 输出多 provider env。

### 4.6 每个 Agent 的私有 provider home

虽然 CLI 安装在镜像全局，但运行状态必须隔离到 Agent 工作目录：

```text
/workspace/agents/<workspace_name>/.weagent/providers/<provider>/home
```

Provider runner 启动进程时设置：

```text
CODEX_HOME=<agent_private_codex_home>
OPENCODE_HOME=<agent_private_opencode_home>
```

Claude 如果支持 HOME/配置隔离，也可以逐步迁移；第一版为避免破坏原功能，Claude 保持当前 `.claude` 方案。

### 4.7 镜像版本可追踪

建议在镜像构建时写入：

```text
/app/provider_versions.json
```

内容示例：

```json
{
  "claude": "Claude Code x.y.z",
  "codex": "Codex x.y.z",
  "opencode": "OpenCode x.y.z"
}
```

这样前端、日志和问题排查能知道当前容器里的 provider 版本。

## 5. 现有 Claude Code 能力基线

所有 provider 都要对齐这个基线。

现有 `backend/app/sandbox/container/agent.py` 中 Claude Code 已具备：

- 工作目录：`/workspace/agents/<workspace_name>`
- 公共目录：`/workspace/shared`
- 角色提示词文件：
  - `.claude/agent.md`
  - `CLAUDE.md`
- WeAgent runtime instruction
- `weagent-report` 上报规范
- `claude -c` 上下文恢复
- `.weagent_claude_session` 标记
- stdout/stderr 逐 chunk 读取
- `claude_output_delta`
- `claude_error_delta`
- `agent_progress` heartbeat
- `claude_output`
- `claude_error`
- `claude_stopped`
- timeout
- stop
- auth/model error 检测
- resume 失败后删除 marker 并降级重试
- 日志写入

新 provider 不应绕开这些能力。

## 6. 重构方向

### 6.1 从 ClaudeRuntime 抽象出通用 AgentRuntime

当前 `ClaudeRuntime` 命名已经不准确。建议改为：

```text
AgentRuntime
```

职责：

- 管理 Agent 工作目录。
- 写入 provider 需要的角色/规则文件。
- 注入 WeAgent runtime instruction。
- 管理 stop/timeout/heartbeat。
- 调用具体 ProviderRunner。
- 把 provider 事件转换成 sandbox event。

### 6.2 新增 ProviderRunnerFactory

```python
class ProviderRunnerFactory:
    @staticmethod
    def create(provider_name, runtime):
        if provider_name == "claude":
            return ClaudeCodeRunner(runtime)
        if provider_name == "codex":
            return CodexRunner(runtime)
        if provider_name == "opencode":
            return OpenCodeRunner(runtime)
        raise ValueError(f"Unsupported provider: {provider_name}")
```

`provider_name` 来自 Agent 的 `adapter_name`。

兼容旧数据：

- 如果 `adapter_name` 缺失，默认 `claude`。

### 6.3 ProviderRunner 接口

```python
class BaseProviderRunner:
    provider = ""

    def setup(self):
        """Create provider-specific config files."""

    def build_command(self, prompt, use_resume):
        """Return command list."""

    def should_resume(self):
        """Return whether to use provider resume mode."""

    def mark_success(self):
        """Persist resume marker/state after successful run."""

    def should_retry_without_resume(self, stderr):
        """Return whether resume failed and should retry fresh."""
```

大部分进程管理逻辑不要放在每个 runner 里重复写，应放在 `AgentRuntime._call_provider()`：

- `subprocess.Popen`
- stdout/stderr reader
- output queue
- heartbeat
- timeout
- stop
- ANSI 清理
- push delta events
- push final events
- logging

ProviderRunner 只负责差异：

- 命令怎么拼。
- resume 怎么开。
- provider 配置文件怎么写。
- 哪些错误表示 resume 失败。

## 7. 目录结构

建议新增：

```text
backend/app/sandbox/container/providers/
  __init__.py
  base.py
  factory.py
  claude_code.py
  codex.py
  opencode.py
```

Agent 私有状态目录：

```text
/workspace/agents/<workspace_name>/.weagent/
  provider_state.json
  providers/
    claude/
      session_marker
      logs/
    codex/
      session_marker
      home/
      logs/
    opencode/
      session_marker
      home/
      logs/
```

兼容旧 Claude marker：

```text
/workspace/agents/<workspace_name>/.weagent_claude_session
```

第一版可以继续写旧 marker，同时写新 marker，避免破坏现有会话。

## 8. Agent 配置

后端创建 sandbox session 时，应把 Agent 角色库里的 provider 配置传进 container。

关键原则：

- `adapter_name` 是 Agent 配置字段，不是角色类型推导结果。
- `role/name` 只用于展示和提示词，不用于选择底层 provider。
- 主持 Agent、文档 Agent、前端 Agent 都可以配置为任意 provider。
- 如果用户复制/自定义一个系统 Agent，应复制其默认 provider，同时允许用户修改。

传入 container 的 Agent config 示例：

```json
{
  "agent_id": "frontend",
  "role": "前端开发专家",
  "system_prompt": "...",
  "workspace_name": "前端开发专家",
  "adapter_name": "claude"
}
```

支持：

```json
"adapter_name": "claude" | "codex" | "opencode"
```

不考虑 mock。

运行时选择逻辑：

```python
provider_name = agent_config.get("adapter_name") or "claude"
runner = ProviderRunnerFactory.create(provider_name, runtime)
```

禁止这种逻辑：

```python
if "文档" in role:
    provider = "codex"
elif "前端" in role:
    provider = "claude"
```

角色能力、提示词、工具集和 provider 是四个独立维度：

| 维度 | 来源 | 示例 |
|---|---|---|
| 角色名称 | Agent 角色库 | 前端开发专家 |
| 能力/提示词 | Agent 角色库 | 负责 HTML/CSS/JS |
| 工具集 | Agent 角色库或用户配置 | 文件工具、脚本工具 |
| provider | Agent 角色库或用户配置 | claude/codex/opencode |

## 9. Provider 具体方案

### 9.1 ClaudeCodeRunner

目标：行为保持不变。

fresh command：

```bash
claude -p "<full_message>" --permission-mode bypassPermissions --dangerously-skip-permissions
```

resume command：

```bash
claude -c -p "<full_message>" --permission-mode bypassPermissions --dangerously-skip-permissions
```

resume 判断：

- 存在旧 marker：`.weagent_claude_session`
- 或存在新 marker：`.weagent/providers/claude/session_marker`

成功后：

- 写旧 marker。
- 写新 marker。

resume 失败关键词沿用现有逻辑：

- `no conversation`
- `conversation not found`
- `could not continue`
- `cannot continue`
- `no previous`
- `unknown option`
- `invalid option`

失败后：

- 删除 marker。
- fresh retry 一次。

### 9.2 CodexRunner

已确认 Codex 可用：

```bash
codex resume --last
```

fresh command 建议：

```bash
codex exec --json --cd /workspace/agents/<workspace_name> --sandbox workspace-write --skip-git-repo-check "<full_message>"
```

resume command 建议：

```bash
codex resume --last --json --cd /workspace/agents/<workspace_name> "<full_message>"
```

如果实际 Codex CLI 不支持在 `resume --last` 后直接带 prompt，需要改成 Codex 支持的传参方式，例如 stdin 或对应参数。实现前需要用真实 CLI 验证。

关键点：

- 不要默认使用 `--ephemeral`，因为目标是保留上下文。
- 设置 `CODEX_HOME` 到 Agent 私有 provider 目录：

```text
CODEX_HOME=/workspace/agents/<workspace_name>/.weagent/providers/codex/home
```

这样不同 Agent 的 Codex 会话不会互相污染。

resume 判断：

- 存在 `.weagent/providers/codex/session_marker`
- 或 `CODEX_HOME` 下存在 Codex 会话状态。

成功后：

- 写 `.weagent/providers/codex/session_marker`

resume 失败处理：

- 如果 stderr/stdout 包含以下类似内容：
  - `no previous`
  - `no session`
  - `conversation not found`
  - `cannot resume`
  - `resume failed`
- 删除 marker。
- fresh retry 一次。

事件解析：

- 如果 Codex JSON 输出稳定，复用队友 `normalize_codex_event()` 的思路。
- 如果 JSON 输出不稳定，第一版先按 stdout 文本 delta 推。
- stderr 必须实时推给前端 raw output 或 error stream。

### 9.3 OpenCodeRunner

已确认 OpenCode 可用：

```bash
opencode -c
```

fresh command 需要按真实 OpenCode CLI 确认，建议抽象为：

```bash
opencode "<full_message>"
```

resume command：

```bash
opencode -c "<full_message>"
```

如果 OpenCode 支持工作目录参数则使用参数；否则通过 `cwd=/workspace/agents/<workspace_name>` 保证运行目录。

建议设置私有 home/config：

```text
OPENCODE_HOME=/workspace/agents/<workspace_name>/.weagent/providers/opencode/home
```

如果 OpenCode 不认 `OPENCODE_HOME`，则需要确认它的 session 存储目录是否可配置。不能让所有 Agent 共用同一个全局 OpenCode session。

resume 判断：

- 存在 `.weagent/providers/opencode/session_marker`
- 或 OpenCode 私有状态目录存在会话记录。

成功后：

- 写 `.weagent/providers/opencode/session_marker`

resume 失败处理：

- 删除 marker。
- fresh retry 一次。

## 10. Prompt 和规则文件

### 10.1 通用 WeAgent runtime instruction

当前 Claude 的 `agent.md` 里写了大量 WeAgent 工作规范。这个规范应该抽成 provider 无关方法：

```python
format_runtime_instruction(workspace_name, provider_name)
```

每个 provider 都必须收到这些规则：

- 你的私有工作目录是 `/workspace/agents/<workspace_name>/`
- 公共目录是 `/workspace/shared/`
- 可读取其他 Agent 工作目录协作。
- 产物优先写入自己的私有工作目录。
- 需要共享时写入 shared。
- 必须通过 `weagent-report` 上报进度和结果。
- 文件、图片、表格、代码上报格式。
- HTML/CSS/JS 项目必须写入文件，不要只输出文字。

### 10.2 Provider 特定规则文件

Claude：

- `.claude/agent.md`
- `CLAUDE.md`

Codex：

- 如果 Codex 支持类似 `AGENTS.md`，写入 `AGENTS.md`。
- 否则每次 prompt 前拼接 runtime instruction。

OpenCode：

- 如果支持项目规则文件，写入对应规则文件。
- 否则每次 prompt 前拼接 runtime instruction。

第一版保守做法：

- 所有 provider 的 prompt 都拼接 runtime instruction。
- Claude 继续保留 `CLAUDE.md`，不破坏原行为。

## 11. 事件命名

为了不破坏前端，第一版继续复用现有事件名：

- stdout delta：`claude_output_delta`
- stderr delta：`claude_error_delta`
- final output：`claude_output`
- final stderr：`claude_error`
- start：`claude_started`
- stopped：`claude_stopped`

但 event data 中增加：

```json
{
  "provider": "codex"
}
```

这样前端和 `sandbox_event_bridge` 不需要大改，后续再改 provider 中性事件名。

第二版再引入中性事件：

- `provider_started`
- `provider_output_delta`
- `provider_error_delta`
- `provider_output`
- `provider_error`
- `provider_stopped`

并让 `sandbox_event_bridge` 同时兼容旧名和新名。

## 12. 消息持久化

不改变现有持久化模型：

- `messages.raw_output`
- `messages.elements`
- `messages.meta.events`
- `messages.status`
- `agent_runs`

Provider runner 只负责 push event。落库仍由：

```text
sandbox_event_bridge
```

负责。

刷新页面后，前端必须从数据库恢复：

- raw output
- 当前进度
- result
- table
- file
- image
- code

## 13. Stop / Timeout / Logs

Stop、timeout、logs 必须 provider 无关。

`AgentRuntime` 维护：

```python
self._process
self._stop_signaled
self._lock
```

stop 时：

- kill 当前 process。
- push stopped event。
- 不清空已有 raw output。
- 不覆盖已有 result/artifacts。

timeout：

- 默认沿用 `CLAUDE_EXEC_TIMEOUT_SECONDS`，建议重命名：

```text
AGENT_EXEC_TIMEOUT_SECONDS
```

兼容旧 env：

```python
timeout = AGENT_EXEC_TIMEOUT_SECONDS or CLAUDE_EXEC_TIMEOUT_SECONDS or 7200
```

logs：

- 统一用 `log_agent`
- event 名增加 provider 字段。

## 14. 对队友 adapters 代码的处理

可以这样处理：

### 14.1 可复用

- `AgentAdapterFactory` 的工厂思路。
- `AgentRequest` 的请求结构思路。
- `normalizers.py` 中 Codex/Claude 事件归一化逻辑。
- Codex subprocess JSONL 读取思路。

### 14.2 可弃用

- host/local `ClaudeAdapter`
- host/local `CodexAdapter`
- host/local `OpenCodeAdapter`
- `orchestrator_service` 里直接用 `AgentAdapterFactory` 调 provider 的正式执行路径。

### 14.3 重建位置

把 adapter 能力迁移到：

```text
backend/app/sandbox/container/providers/
```

这才是正式 runtime。

## 15. 分阶段实现计划

接下来按阶段实现。每个阶段都必须独立可测试，测试通过后再进入下一阶段。

### 阶段 0：合并前基线和保护测试

目标：

- 在改 provider 架构前，先固定当前 Claude Code 沙箱能力的基线。
- 后续每阶段都用这组测试防回归。

改动范围：

- 可以新增测试脚本、测试文档、轻量测试工具。
- 尽量不改业务逻辑。

需要覆盖的基线：

- 创建 sandbox 会话。
- 单 Agent Claude 发送消息成功。
- 多 Agent 会话主持 Agent 分派任务成功。
- 第二轮 Claude 使用 `claude -c`。
- Claude stdout/stderr 能进入前端 raw output。
- `weagent-report` 上报 table/file/result 后能进入 `elements`。
- 页面刷新后产物不丢。
- stop Agent 后不覆盖停止前输出。
- HTML/图片/文件预览仍可用。

建议测试：

- 后端编译：

```bash
python -m compileall backend/app
```

- 针对 sandbox 事件桥写单元测试：
  - `agent_report_element(table)` 能落入 `message.elements`
  - `file_write` 能落入 `message.elements`
  - `claude_output_delta` 能追加 `raw_output`

- 真实集成测试：
  - 创建会话
  - 发送“你好”
  - 再发送“你记得我刚才说了什么吗”
  - 检查日志中 `use_continue=true`

通过标准：

- 不引入 provider 改动时，当前 Claude 功能全部可复现。
- 如果某项当前已经坏了，先记录为已知问题，不把它混进 provider 重构。

不做：

- 不接 Codex。
- 不接 OpenCode。
- 不改前端协议。

### 阶段 1：多 provider sandbox 镜像准备

目标：

- 创建容器前，镜像里已经安装 Claude Code、Codex、OpenCode。
- 容器启动后能报告三种 provider 的可用性和版本。
- 不改变当前 Claude 运行逻辑。

建议改动：

- 修改 `backend/app/sandbox/Dockerfile`：
  - 保留当前 Claude Code 安装方式。
  - 增加 Codex CLI 安装。
  - 增加 OpenCode CLI 安装。
  - 增加构建期版本校验。

- 新增 container provider health 工具：

```text
backend/app/sandbox/container/provider_health.py
```

- `server.py` 启动时记录 provider health。

- 新增或扩展接口：

```text
GET /api/providers
```

或在：

```text
GET /api/session
```

返回：

```json
{
  "providers": {
    "claude": {"available": true, "version": "..."},
    "codex": {"available": true, "version": "..."},
    "opencode": {"available": true, "version": "..."}
  }
}
```

建议测试：

- 镜像构建测试：

```bash
python -c "from app.sandbox import build_image; build_image()"
```

- 容器内 CLI 测试：

```bash
claude --version
codex --version
opencode --version
```

- API 测试：
  - 创建 sandbox session。
  - 调 `/api/providers` 或 `/api/session`。
  - 确认三种 provider health 都返回。

- 回归测试：
  - Claude Agent 仍能正常发送消息。

通过标准：

- 新镜像中三种 CLI 都可执行。
- provider health 可查询。
- Claude 原有功能不受影响。

不做：

- 不实现 CodexRunner。
- 不实现 OpenCodeRunner。
- 不改变 Claude 执行命令。

阻塞问题：

- 需要确认 Codex CLI 的安装包名。
- 需要确认 OpenCode CLI 的安装包名。
- 如果其中一个 CLI 不能通过 npm 安装，需要改 Dockerfile 安装方式。

### 阶段 2：无行为变化重构 Claude 为 AgentRuntime + ClaudeCodeRunner

目标：

- 把现有 `ClaudeRuntime` 的成功逻辑拆出通用骨架。
- 引入工厂模型，但当前只注册 Claude。
- Claude 行为必须零破坏。

建议改动：

- 新增：

```text
backend/app/sandbox/container/providers/
  __init__.py
  base.py
  factory.py
  claude_code.py
```

- 保留 `backend/app/sandbox/container/agent.py` 对外类名兼容。
  - 可以暂时让 `ClaudeRuntime` 包裹新的 `AgentRuntime`。
  - 避免一次性改 `orchestrator.py` 太多调用点。

- 抽象通用进程执行逻辑：
  - stdout/stderr reader
  - heartbeat
  - timeout
  - stop
  - output cleanup
  - push delta/final/error/stopped event

- `ClaudeCodeRunner` 只保留 Claude 差异：
  - `setup()`
  - `build_command(prompt, use_resume)`
  - `should_resume()`
  - `mark_success()`
  - `should_retry_without_resume(stderr)`

必须保持：

- `.weagent_claude_session`
- `claude -c`
- `CLAUDE.md`
- `.claude/agent.md`
- `.claude/settings.local.json`
- `claude_output_delta`
- `claude_error_delta`
- `claude_output`
- `claude_stopped`

建议测试：

- 单元测试：
  - provider factory 创建 Claude runner。
  - Claude runner fresh command 不含 `-c`。
  - marker 存在时 command 含 `-c`。
  - resume 失败关键词触发 fresh retry。

- 集成测试：
  - 重建镜像。
  - 创建 Claude Agent 会话。
  - 连续两轮消息，第二轮日志显示 `use_resume/use_continue=true`。
  - 生成一个 HTML 文件，前端可预览。
  - stop 后 raw output 不丢。

通过标准：

- 用户侧看不出 Claude 行为变化。
- 所有阶段 0 基线测试仍通过。

不做：

- 不传 `adapter_name`。
- 不启用 Codex/OpenCode。
- 不改前端展示。

### 阶段 3：Agent 角色库 provider 配置传入 container

目标：

- provider 来源改为 Agent 角色库/Agent 实例配置。
- container 知道每个 Agent 的 `adapter_name`。
- 仍然只实际运行 Claude，非 Claude 暂时返回明确错误或不开放运行。

建议改动：

- 后端创建 sandbox session 时读取 Agent 的 `adapter_name`。
- `conversation_service.createConversation` 或创建 session 的相关逻辑传入：

```json
{
  "agent_id": "...",
  "role": "...",
  "system_prompt": "...",
  "workspace_name": "...",
  "adapter_name": "claude"
}
```

- container `session.save_agent_config()` 保存 `adapter_name`。
- container `orchestrator.add_agent()` / `restore agents` 支持 `adapter_name`。
- container `/api/session` 返回每个 Agent 的 provider。
- 缺失 `adapter_name` 默认 `claude`。

必须避免：

- 不按角色名推导 provider。
- 不写 `if "文档" in role then codex`。
- 主持 Agent 也读取自身 `adapter_name`。

建议测试：

- 单元测试：
  - `save_agent_config/load_agent_config` 保留 `adapter_name`。
  - 缺失 `adapter_name` 时默认 `claude`。
  - 同名角色不同配置能保存不同 provider。

- 集成测试：
  - 创建会话，选择两个 Agent，分别配置不同 `adapter_name`。
  - 调 `/api/session`，确认 provider 正确。
  - Claude Agent 仍能运行。
  - 如果 Codex/OpenCode 尚未实现，运行时返回“provider not supported yet”而不是静默用 Claude。

通过标准：

- provider 配置链路打通。
- 旧 Agent/旧会话默认 Claude 不坏。
- Claude 基线测试仍通过。

不做：

- 不实现 CodexRunner。
- 不实现 OpenCodeRunner。
- 不改消息事件名。

### 阶段 4：CodexRunner 第一版

目标：

- 在 container 内实现 Codex provider。
- 使用 `codex resume --last` 做上下文恢复。
- 行为尽量对齐 Claude Code。

建议改动：

- 新增：

```text
backend/app/sandbox/container/providers/codex.py
```

- Codex 工作目录：

```text
/workspace/agents/<workspace_name>
```

- Codex 私有状态目录：

```text
/workspace/agents/<workspace_name>/.weagent/providers/codex/
```

- 优先设置：

```text
CODEX_HOME=/workspace/agents/<workspace_name>/.weagent/providers/codex/home
```

- fresh command 根据真实 CLI 验证后确定，候选：

```bash
codex exec --json --cd <agent_dir> --sandbox workspace-write --skip-git-repo-check "<full_message>"
```

- resume command 根据真实 CLI 验证后确定，候选：

```bash
codex resume --last --json --cd <agent_dir> "<full_message>"
```

- 如果 `resume --last` 不支持直接带 prompt，改用 Codex 支持的 stdin 或参数。

- 成功后写：

```text
.weagent/providers/codex/session_marker
```

- resume 失败后：
  - 删除 marker。
  - fresh retry 一次。

- 事件：
  - 第一版复用 `claude_output_delta`，data 增加 `provider: "codex"`。
  - stderr 复用 `claude_error_delta`。
  - final 复用 `claude_output`。

建议测试：

- 单元测试：
  - Codex runner fresh/resume command。
  - marker 存在时使用 resume。
  - resume 失败关键词触发 fresh retry。
  - env 包含私有 `CODEX_HOME`。

- container 集成测试：
  - 创建 Codex Agent。
  - 第一轮发送“你好，请记住数字 12345”。
  - 第二轮发送“我刚才让你记住什么数字”，检查能回答 12345。
  - 让 Codex 生成 `/workspace/agents/<agent>/codex_test.md` 并上报 file。
  - 前端刷新后文件卡片仍存在。
  - stop Codex 后保留已有 raw output。

通过标准：

- Codex Agent 能在 container 内跑。
- 第二轮能恢复上下文。
- 产物进入 `/workspace`。
- 前端展示链路不需要大改。
- Claude 基线测试仍通过。

不做：

- 不接 OpenCode。
- 不引入 provider 中性事件名。
- 不启用 host/local adapters。

### 阶段 5：OpenCodeRunner 第一版

目标：

- 在 container 内实现 OpenCode provider。
- 使用 `opencode -c` 做上下文恢复。
- 对齐 Claude/Codex 的工作目录、事件、停止、产物能力。

建议改动：

- 新增：

```text
backend/app/sandbox/container/providers/opencode.py
```

- OpenCode 工作目录：

```text
/workspace/agents/<workspace_name>
```

- OpenCode 私有状态目录：

```text
/workspace/agents/<workspace_name>/.weagent/providers/opencode/
```

- 如果 OpenCode 支持 home 环境变量，设置：

```text
OPENCODE_HOME=/workspace/agents/<workspace_name>/.weagent/providers/opencode/home
```

- fresh command 需要先确认。
- resume command：

```bash
opencode -c "<full_message>"
```

- 成功后写：

```text
.weagent/providers/opencode/session_marker
```

- resume 失败后 fresh retry 一次。

建议测试：

- 单元测试：
  - OpenCode runner fresh/resume command。
  - marker 存在时使用 `-c`。
  - env/state 目录隔离。
  - resume 失败触发 fresh retry。

- container 集成测试：
  - 创建 OpenCode Agent。
  - 第一轮记住一个信息。
  - 第二轮确认能恢复。
  - 生成文件并上报。
  - stop 后输出不丢。

通过标准：

- OpenCode Agent 能在 container 内跑。
- 第二轮能恢复上下文。
- 产物和 raw output 走现有前端展示链路。
- Claude、Codex 基线仍通过。

不做：

- 不改前端大 UI。
- 不启用 SSE 替代 socket。

### 阶段 6：多 provider 混合会话测试

目标：

- 验证同一会话多个 Agent 使用不同 provider 时，调度、上下文、工作目录和产物互不污染。

测试场景：

- 创建三 Agent 会话：
  - 主持 Agent：Claude/Codex/OpenCode 任一配置
  - 前端 Agent：Claude
  - 文档 Agent：Codex 或 OpenCode

- 发送任务：

```text
写一个商城登录页面，并写开发文档
```

检查：

- 主持 Agent 按自身 provider 运行。
- 前端 Agent 按自身 provider 运行。
- 文档 Agent 按自身 provider 运行。
- 每个 Agent 的 session marker 在自己的 provider 目录。
- 不同 Agent 的 provider home 不互相污染。
- 产物优先在各自工作目录。
- shared 目录只放明确共享的产物。
- 前端展示每个 Agent 的 raw output、进度、result、文件卡片。
- 刷新后所有产物仍在。

通过标准：

- 同一会话 provider 混用稳定。
- 不出现角色名决定 provider 的行为。
- 不出现文档 Agent 和前端 Agent 互相覆盖同名文件的问题。

### 阶段 7：Provider 标识和中性事件名

目标：

- 在前后端明确 provider 信息。
- 逐步摆脱 `claude_output_delta` 这种 Claude 专用事件名。

建议改动：

- `sandbox_event_bridge` 兼容新事件：
  - `provider_started`
  - `provider_output_delta`
  - `provider_error_delta`
  - `provider_output`
  - `provider_error`
  - `provider_stopped`

- 旧事件继续兼容：
  - `claude_output_delta`
  - `claude_output`
  - etc.

- 前端消息头可展示：

```text
前端开发专家 · Claude
文档助手 · Codex
```

- `meta.events` 中保留 provider 字段。

建议测试：

- 新旧事件都能落库。
- 前端显示 provider。
- 刷新后 provider 信息仍在。
- 老 Claude 会话仍能显示。

通过标准：

- 中性事件可用。
- 旧事件不坏。
- 前端没有重复消息。

### 阶段 8：清理队友 host/local adapters 正式路径

目标：

- 删除或停用不再作为正式执行路径的 host/local adapter 调用。
- 避免未来有人误用 `orchestrator_service` 绕过 sandbox。

建议处理：

- `backend/app/adapters/*`：
  - 可删除。
  - 或移动为 tests/dev only。
  - 或保留 normalizer，但不能作为正式 runtime。

- `orchestrator_service`：
  - 不允许正式会话调用 host provider。
  - 如果保留，明确标注 deprecated/dev only。

- 文档更新：
  - provider 正式实现位置是 `backend/app/sandbox/container/providers/`。

建议测试：

- 全局搜索没有正式路径调用 host/local adapter。
- 所有正式会话仍走 sandbox manager。
- Claude/Codex/OpenCode 集成测试仍通过。

通过标准：

- 代码路径清晰。
- 不存在两个 runtime 抢同一会话的风险。

## 16. 需要你确认的问题

1. Codex 的真实命令是否支持：

```bash
codex resume --last --json --cd <dir> "<prompt>"
```

如果不支持，正确传 prompt 的方式是什么？

2. Codex 是否支持 `CODEX_HOME` 隔离不同 Agent 的会话？

3. OpenCode 的 fresh 命令是什么？

当前只确认：

```bash
opencode -c
```

但还需要确认第一轮不恢复上下文时怎么调用。

4. OpenCode 是否支持类似 `OPENCODE_HOME` 的隔离目录？

5. Codex/OpenCode 的 API key/baseURL/model 配置分别是什么环境变量？

6. 同一会话中不同 Agent 使用不同 provider 时，是否允许每个 Agent 使用不同模型配置？

7. 如果 Codex/OpenCode resume 失败，是否允许自动删除 marker 后 fresh retry 一次？

8. 第一版是否接受继续复用 `claude_output_delta` 这类事件名，只在 data 里加 provider？

9. 前端是否需要在 Agent 卡片/消息头展示 provider？

10. 是否允许暂时删除或停用队友的 host/local adapters 正式调用路径？

11. Agent 角色库里 provider 配置的字段名是否就沿用 `adapter_name`？

12. 系统预设 Agent 被用户复制后，是否允许用户修改 provider？

13. 主持 Agent 的 provider 是否也从角色库配置读取，而不是固定 Claude？

## 17. 推荐决策

建议你确认以下默认决策：

1. 正式 runtime 只走 sandbox container。
2. 队友 host/local adapters 不作为正式执行路径。
3. 第一版支持 Claude、Codex、OpenCode，不考虑 mock。
4. Claude 行为零破坏，先重构再扩展。
5. Codex 使用 `codex resume --last`。
6. OpenCode 使用 `opencode -c`。
7. 第一版复用现有 Claude 事件名，减少前端和后端 bridge 改动。
8. 第二版再改 provider 中性事件名。
9. 所有 provider 的产物必须写入 `/workspace`。
10. 所有 provider 都必须遵守 `weagent-report` 上报规范。
11. 每个 Agent 的 provider 从角色库配置读取，不做角色名称硬编码。
12. 主持 Agent 也按自身配置选择 provider。

这样实现后，Adapter 的价值会真正体现在“不同 Agent 底层 provider 可替换”，同时不会牺牲你现在已经跑通的 Claude Code 沙箱、上下文恢复、产物展示和多 Agent 协作能力。


我也把阶段编号调整了：

阶段 0：基线保护测试
阶段 1：多 provider sandbox 镜像准备
阶段 2：无行为变化重构 Claude
阶段 3：传 adapter_name 到 container
阶段 4：CodexRunner
阶段 5：OpenCodeRunner
阶段 6：多 provider 混合会话测试
阶段 7：Provider 标识和中性事件名
阶段 8：清理 host/local adapters 正式路径
