# Provider Runtime 阶段 0 基线测试记录

更新时间：2026-05-28

## 目标

阶段 0 不改 provider 运行逻辑，只建立保护测试，防止后续 Claude/Codex/OpenCode runtime 重构破坏现有 Claude Code 沙箱能力。

## 已新增自动化测试

新增文件：

```text
backend/tests/test_sandbox_stage0_baseline.py
```

覆盖内容：

- `claude_output_delta` 能追加到 `messages.raw_output`。
- `agent_report_element(table)` 能落入 `messages.elements`。
- `file_write` 能落入 `messages.elements`。
- `meta.events` 能持久保存 report/file 事件。
- 消息读取时能从历史 `meta.events` 回填 `table/file/result` 到 `elements`。
- 回填后的 `elements` 会写回数据库。
- Claude session marker 存在时，命令包含 `claude -c`。
- Claude session marker 不存在时，命令不包含 `-c`。
- Claude resume 失败关键词仍会触发 fresh retry 判断。

## 已执行自动化测试

在 `backend` 目录执行：

```bash
python -m compileall app tests
python -m unittest discover -s tests
```

结果：

```text
Ran 31 tests
OK
```

说明：

- 测试输出中存在 SQLAlchemy `LegacyAPIWarning`、`DeprecationWarning` 和 sqlite drop table cycle warning。
- 这些是当前仓库已有警告，不影响阶段 0 通过。

## 后续每阶段必须保留的自动化基线

后续阶段完成后至少执行：

```bash
cd backend
python -m compileall app tests
python -m unittest discover -s tests
```

如果某阶段涉及 frontend，还需要执行 frontend build/test。

## 需要人工执行的真实集成基线

以下测试需要真实 Docker sandbox、Claude Code 登录/模型配置和前端环境，阶段 0 未自动执行。

### 1. 创建会话

步骤：

- 启动后端和前端。
- 创建一个单 Agent Claude 会话。
- 确认 sandbox container 创建成功。

通过标准：

- 后端 conversation 记录有 `sandbox_session_id`。
- container `/api/health` 正常。
- 前端没有创建会话失败。

### 2. Claude 第一轮输出

发送：

```text
你好
```

通过标准：

- 前端显示 Claude 真实输出。
- raw output 有内容。
- 后端日志能看到 `claude_process_started`、`claude_stdout_chunk` 或 final output。

### 3. Claude 上下文恢复

继续发送：

```text
你记得我刚才问了什么吗？
```

通过标准：

- Agent 能基于上一轮回答。
- container 日志中 `claude_context_mode` 显示 `use_continue=true`。
- 没有创建新的孤立上下文。

### 4. 产物上报和刷新恢复

发送：

```text
生成一个简单 HTML 登录页，并用 weagent-report 上报文件和一个功能表格
```

通过标准：

- 前端实时显示 raw output。
- 前端显示 table 卡片。
- 前端显示 file 卡片。
- 刷新页面后 table/file/result 仍存在。
- 数据库返回的 message `elements` 不为空，且包含 `table/file/result`。

### 5. 文件预览

步骤：

- 点击 Agent 工作目录。
- 打开生成的 HTML 文件。
- 下载该文件。

通过标准：

- 文件树能看到 Agent 目录产物。
- HTML iframe 能渲染 CSS/JS。
- 下载正常。

### 6. Stop 保留输出

步骤：

- 发送一个较长任务。
- Claude 输出部分内容后点击 stop。

通过标准：

- 前端状态为 stopped。
- stop 前 raw output 不丢。
- stop 前已生成/上报的产物仍显示。
- 不被单独的 “stopped” 文案覆盖全部结果。

### 7. 多 Agent 分派

创建多 Agent 会话，发送：

```text
写一个商城登录界面，并写开发文档
```

通过标准：

- 主持 Agent 返回分派说明。
- worker Agent 各自执行任务。
- 前端能分别显示每个 Agent 的进度、raw output、结果和产物。
- Agent 私有目录和 shared 目录没有无意义重复产物。

## 阶段 0 结论

阶段 0 已完成自动化保护测试。后续阶段如果修改 sandbox event、message elements、Claude command、Agent runtime，必须保证本阶段测试继续通过。
