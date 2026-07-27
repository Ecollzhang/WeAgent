# Archive: toolset Docker UAT 排障链路

版本：v1.0
日期：2026-05-29

## 1. 归档信息

- 归档名称：toolset Docker UAT 排障链路
- 归档日期：2026-05-29
- 归档人：why
- 对应 session：`docs/ai-collab/sessions/why-session-v1.0-05-29.md`
- 对应 session 记录范围：MySQL80 root 重置授权、本地后端恢复、Docker sandbox 启动、网页 UAT 入口打开。

## 2. 归档原因

本次对话不只是一次临时环境修复，而是沉淀出了一条可以复用的真实 UAT 排障路径：从数据库密码不可用、服务权限不足、Python 依赖缺失，到 Docker sandbox session 创建成功。该路径对后续验证工具集能力、多人协作复现本地环境、定位 Docker/DB/后端边界问题都有长期价值。

## 3. 对话主题

本轮主题是：让 WeAgent 的 toolset 分支从“代码和测试已完成”进入“本地真实运行可验证”状态。

关键对象包括：

- MySQL80 Windows 服务；
- `backend/.env` 本地开发配置；
- Flask 后端 `http://localhost:5001`；
- Vue 前端 `http://localhost:8080`；
- Docker Desktop 与 `weagent-sandbox:latest`；
- sandbox session `toolset-smoke-001`；
- 工具集后续 UAT 所依赖的 `.weagent/*` runtime projection。

## 4. 归档提炼

- MySQL root 密码不能被“读出来”。如果忘记，只能尝试登录、查看本机保存连接，或在授权后重置。
- Windows 服务操作需要真正的管理员提升权限。属于管理员组但未提升时，`Stop-Service` / `Start-Service` 仍可能被拒绝。
- MySQL root 重置建议使用一次性 `--init-file`，不要把 `skip-grant-tables` 作为常规方案。
- Windows MySQL client 在本轮环境中对 `-h127.0.0.1` 解析异常，使用 `--host=localhost` 验证更稳定。
- 本地 `.env` 中如果存在 `DATABASE_URL=sqlite:///...`，会覆盖 MySQL 配置，使后端继续走 SQLite。切回 MySQL 时必须移除该行。
- 真实 Docker UAT 的最小通过条件不是只看前端页面，而是至少同时满足：
  - Docker daemon ready；
  - `weagent-sandbox:latest` 镜像存在；
  - 后端 `/api/health` healthy；
  - `/api/sandbox/status` 可返回；
  - `POST /api/sandbox/sessions` 能创建真实容器；
  - `docker ps` 中容器为 `Up / healthy`；
  - 后端能读取容器 `/workspace` 文件树。
- `backend/sql/init.sql` 和 ORM `db.create_all()` 可能出现能力差异。当前纯 SQL 初始化存在外键顺序问题，但 ORM 启动路径可以建表成功。这个差异必须记录，避免误判为 MySQL 密码或 Docker 问题。
- 本地密码、`.env`、临时 reset 脚本和 runtime DB 文件不应进入长期归档正文或 Git 提交。

## 5. 已形成成果

- MySQL80 已恢复运行。
- root 登录已验证成功，但归档不保存明文密码。
- `backend/.env` 已回到 MySQL 路径。
- 后端已启动并返回 healthy。
- 前端已启动并可打开 sandbox 页面。
- Docker sandbox session `toolset-smoke-001` 已创建成功。
- Docker 容器 `3ae82c15652a` 已验证为 healthy。
- 容器 workspace 文件树已通过后端 API 读取成功。
- 明确了后续真实工具集 UAT 仍需继续验证 capability 绑定、`.weagent/*` 投影、Tool/MCP 调用记录和 Skill draft sync。

## 6. 后续去向

- `rules/`：建议沉淀“本地 UAT 不记录明文密码”“服务级操作必须显式授权”“Docker UAT 先查 daemon/image/backend/session/container/files tree”的规则。
- `summaries/`：阶段结束时可将本轮作为 toolset 真实 UAT 阶段总结的一部分。
- `spec/`：暂不需要升级。本轮没有改变工具集需求边界。
- `skills/`：暂不需要升级。若后续反复执行本地环境恢复，可以整理成一个专门的 UAT 调试 Skill。
- 仅保留在归档记录中：MySQL root 重置过程、Docker session smoke 证据、`init.sql` 顺序问题。

## 7. 备注

本轮归档记录的是本机开发环境恢复与真实 sandbox smoke，不等价于完整工具集 UAT 完成。下一轮应由用户在网页端继续检查真实操作路径，并把发现的问题继续追加到 session 或升级为 bug/spec/rules。
