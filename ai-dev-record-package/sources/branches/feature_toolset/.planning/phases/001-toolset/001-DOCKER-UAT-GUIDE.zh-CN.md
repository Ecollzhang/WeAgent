# WeAgent 工具集 Docker 真实验收手册

**适用分支：** `feature/toolset`
**读者：** 第一次接触 Docker、但需要真实跑通 WeAgent 工具集的人
**目标：** 让你知道 Docker 在这里负责什么、怎么启动项目、打开哪个网页、点哪里、看到什么才算通过。

## 1. 先理解一句话

这个项目不是把整个系统都放进 Docker 里跑。

WeAgent 的真实运行方式是：

- 后端 Flask 在 Windows 本机运行，地址是 `http://127.0.0.1:5001`。
- 前端 Vue 在 Windows 本机运行，地址是 `http://localhost:8080`。
- MySQL 和 Redis 是本机服务。
- Docker 只负责 Agent 沙箱。

也就是说：

- 你打开网页看平台：主要看前端 `8080`。
- 前端调用后端 API：走后端 `5001`。
- 当你创建一个真实 Agent 会话时：后端会用 Docker 创建一个沙箱容器。
- 工具集的 `.weagent/*`、Skill 运行副本、MCP npx 调用、工具调用记录，都发生在这个 Docker 沙箱里。

## 2. 你到底需要启动几个东西

真实验收需要 5 个东西都正常：

| 组件 | 用途 | 检查方式 |
|---|---|---|
| Docker Desktop | 创建 Agent 沙箱容器 | `docker info` |
| MySQL | 保存用户、Agent、Skill、绑定、调用记录 | 登录或 API 不报 DB 错 |
| Redis | 后端运行依赖 | 后端启动不报 Redis 连接问题 |
| 后端 | 提供 API 和创建沙箱 | `http://127.0.0.1:5001/api/health` |
| 前端 | 网页平台 | `http://localhost:8080` |

如果只是看页面样式，不一定需要 Docker。

如果要验证工具集真实落地，一定需要 Docker，因为 Agent 沙箱和 `.weagent/*` 投影依赖 Docker。

## 3. 当前代码是否已经上传

已经上传到远端：

```powershell
git branch --show-current
# feature/toolset

git log --oneline -3
# af6594e docs: add docker uat guide
# 185735e test: add toolset regression contracts
# 538c67b feat: sync runtime skill drafts
```

远端分支是：

```text
origin/feature/toolset
```

当前允许存在两个本地未跟踪文件，不需要提交：

```text
.claude/logs/
.planning/STATE.md.lock
```

## 4. 第一步：确认 Docker Desktop 是否真的可用

只看 `docker --version` 不够。

这个命令只能说明 Docker CLI 装了：

```powershell
docker --version
```

真正要看 Docker 后台服务是否启动：

```powershell
docker info
```

如果成功，会输出很多 Docker 信息。

也可以用短版本：

```powershell
docker info --format "Docker daemon ready: {{.ServerVersion}}"
```

正常结果类似：

```text
Docker daemon ready: 29.5.2
```

如果你看到：

```text
failed to connect to the docker API at npipe:////./pipe/docker_engine
```

说明 Docker Desktop 没开，或者还没启动完成。

如果你看到：

```text
permission denied while trying to connect to the docker API
```

说明 Docker Desktop 可能开了，但当前终端没有连上 Docker engine。通常可以这样处理：

1. 打开 Docker Desktop，等左下角或首页显示 Docker 正常运行。
2. 关闭当前 PowerShell，重新打开一个新的 PowerShell。
3. 再运行 `docker info`。
4. 如果还不行，重启 Docker Desktop。
5. 如果 Docker Desktop 弹出 WSL、权限、更新、重启提示，先按它的提示处理。

在 `docker info` 成功之前，不要继续调 WeAgent 的沙箱问题。

## 5. 第二步：构建 WeAgent 沙箱镜像

Docker Desktop 正常后，构建 Agent 沙箱镜像。

进入后端目录：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
```

构建镜像：

```powershell
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

构建成功后检查：

```powershell
docker image ls weagent-sandbox:latest
```

你应该看到类似：

```text
REPOSITORY        TAG       IMAGE ID       CREATED        SIZE
weagent-sandbox   latest    xxxxxxxxxxxx   ...
```

如果没有这一行，说明沙箱镜像还没构建成功。

什么时候需要重新构建镜像：

- 改了 `backend/app/sandbox/Dockerfile`。
- 改了 `backend/app/sandbox/container/*`。
- 拉了新代码，不确定本地镜像是不是最新。
- 真实验收前想确保容器里是最新逻辑。

## 6. 第三步：准备后端环境

进入后端目录：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
```

如果还没有 `.env`：

```powershell
Copy-Item .env.example .env
```

编辑 `backend/.env`，至少要有：

```env
FLASK_ENV=development

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的MySQL密码
MYSQL_DB=weagent

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

JWT_SECRET_KEY=change-this-to-a-random-secret-key
SECRET_KEY=change-this-to-another-random-key
PORT=5001
```

注意：

- 后端实际端口是 `5001`。
- 前端代理也指向 `127.0.0.1:5001`。
- README 里有些旧描述可能写 `5000`，以当前 `backend/run.py` 和 `frontend/vue.config.js` 为准。

如果数据库还没初始化：

```powershell
mysql -u root -p
CREATE DATABASE IF NOT EXISTS weagent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit
```

然后导入表：

```powershell
mysql -u root -p weagent < "E:\code for project\seedance-competition\agentshub\WeAgent\backend\sql\init.sql"
```

工具集相关表至少包括：

```text
capabilities
capability_versions
agent_capability_bindings
capability_call_records
plugin_install_records
skill_revision_drafts
```

## 7. 第四步：启动后端

开一个 PowerShell 窗口，运行：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python run.py
```

后端正常时，这个窗口会一直占用，不要关。

另开一个 PowerShell 检查：

```powershell
Invoke-RestMethod http://127.0.0.1:5001/api/health
```

如果返回健康信息，后端可用。

如果失败：

- 先看启动后端的终端报错。
- 如果是 MySQL 报错，检查 `.env` 的账号密码和数据库。
- 如果是端口占用，检查是否已经有一个后端在跑。
- 如果是 Docker 报错，先跑 `docker info`。

## 8. 第五步：启动前端

再开一个 PowerShell 窗口，运行：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
npm run serve
```

正常情况下会看到前端开发服务器地址：

```text
http://localhost:8080
```

浏览器打开：

```text
http://localhost:8080
```

如果打不开：

- 看前端终端有没有编译错误。
- 确认端口是不是 `8080`。
- 如果页面打开但 API 报错，检查后端 `5001` 是否启动。

## 9. 网页怎么打开、怎么看

打开浏览器：

```text
http://localhost:8080
```

你会进入登录页。

### 页面 1：登录 / 注册

路径：

```text
http://localhost:8080/login
http://localhost:8080/register
```

要验证：

- 可以注册或登录。
- 登录后跳转到聊天页或主界面。

如果登录失败：

- 看后端终端是否有数据库错误。
- 确认 MySQL 已启动并导入了表。

### 页面 2：设置

左侧菜单点：

```text
设置
```

路径：

```text
http://localhost:8080/settings
```

要验证：

- 模型设置页面能打开。
- API Key、Base URL、模型名可以填写并保存。

为什么这一步重要：

Docker 沙箱里的 Agent 最终要调用模型。如果模型设置错了，容器可能能启动，但 Agent 无法正常回复。

### 页面 3：能力库

左侧菜单点：

```text
能力库
```

路径：

```text
http://localhost:8080/capabilities
```

要验证：

- 能看到 Skill、Tool、MCP、Plugin 四类能力。
- 可以新建 Skill Markdown。
- 可以导入 Markdown Skill。
- 可以导入 npx manifest。
- Plugin 能导入并显示安装记录，但不能执行 Plugin 代码。

通过标准：

- 四类能力是并列展示，不是把 MCP/Plugin 塞进 Skill 下面。
- Skill 有 Markdown 内容。
- 导入后刷新页面仍然存在，说明进 DB 了。

### 页面 4：我的 Agent

左侧菜单点：

```text
我的Agent
```

路径：

```text
http://localhost:8080/agents
```

要验证：

- 可以新建 Agent。
- 创建或编辑 Agent 时可以选择工具集能力。
- 绑定能力时能看到权限授权。
- 绑定后 Agent 保存成功。

通过标准：

- Agent 的能力绑定是默认配置，不是只在某次对话里临时选择。
- 绑定的是 pinned 版本。
- 需要权限的能力必须显式授权。

### 页面 5：聊天主界面

左侧菜单点：

```text
聊天
```

路径：

```text
http://localhost:8080/dashboard
```

要验证：

- 点击新建会话。
- 选择一个或多个 Agent。
- 创建会话。
- 发送消息。
- 可以看到 Agent 消息。
- 多 Agent 时，多个 Agent 回复能分开展示。
- Agent 运行中有进度显示。
- 如果 Agent 生成文件或 artifact，页面能展示。

通过标准：

- 会话创建成功。
- 后端创建了 sandbox session。
- Docker 里出现 WeAgent 沙箱容器。

检查 Docker 容器：

```powershell
docker ps --filter "label=weagent.sandbox=true"
```

如果有容器，说明真实 sandbox 启动了。

### 页面 6：沙箱测试

左侧菜单点：

```text
沙箱测试
```

路径：

```text
http://localhost:8080/sandbox
```

这个页面更适合直接观察 Docker 沙箱。

要验证：

- 左侧填写 API Key 和 Agent 配置。
- 点击「启动会话」。
- 页面出现当前会话。
- 右侧出现 Agent 实时状态条。
- 默认是主持分派模式。
- 输入任务后可以看到每个 Agent 的执行状态。

通过标准：

- 页面提示会话创建成功。
- Docker 里能看到沙箱容器。
- Agent 面板状态从等待任务变成思考中、工作中、完成或错误。
- 有错误时页面和后端终端都能看到原因。

## 10. 如何确认 `.weagent/*` 真的写进 Docker 容器

先查容器：

```powershell
docker ps --filter "label=weagent.sandbox=true"
```

拿到 `CONTAINER ID` 后进入容器：

```powershell
docker exec -it <container_id> bash
```

在容器里执行：

```bash
find /workspace/.weagent -maxdepth 4 -type f
```

你应该看到类似：

```text
/workspace/.weagent/capabilities/index.json
/workspace/.weagent/skills/<runtime_id>/SKILL.md
/workspace/.weagent/skills/<runtime_id>/manifest.json
/workspace/.weagent/agents/<agent_id>/capabilities.json
/workspace/.weagent/agents/<agent_id>/skill-index.json
/workspace/.weagent/agents/<agent_id>/permissions.json
```

查看 Agent 视图：

```bash
cat /workspace/.weagent/agents/<agent_id>/capabilities.json
cat /workspace/.weagent/agents/<agent_id>/skill-index.json
cat /workspace/.weagent/agents/<agent_id>/permissions.json
```

通过标准：

- `.weagent` 存在。
- Agent 有自己的 `agents/<agent_id>/` 视图。
- Skill 是共享运行副本，不是每个 Agent 重复复制一份。
- v1 不生成 `.claude/skills`、`.codex/skills`、`.mcp.json`。

检查没有兼容目录：

```bash
find /workspace -maxdepth 3 -name ".claude" -o -name ".codex" -o -name ".mcp.json"
```

正常情况下不应该出现这些 v1 之外的兼容文件。

## 11. 如何验证 Skill 草稿同步

真实逻辑是：

- 用户库里的 Skill 存在 DB。
- 会话启动时投影到 Docker 的 `/workspace/.weagent/skills/<runtime_id>/SKILL.md`。
- Agent 或平台可以改这个运行副本。
- 改动不能直接覆盖用户库。
- 改动应该同步为 `pending_review` 草稿。

操作：

进入容器：

```powershell
docker exec -it <container_id> bash
```

找到 Skill 文件：

```bash
find /workspace/.weagent/skills -name SKILL.md -type f
```

追加一行：

```bash
cat >> /workspace/.weagent/skills/<runtime_id>/SKILL.md <<'EOF'

## UAT runtime edit
This line was added during manual UAT.
EOF
```

回到网页，再给这个 Agent 发一条消息。

通过标准：

- 后端同步出一条 `SkillRevisionDraft(status='pending_review')`。
- 用户库原 Skill 不会被自动覆盖。
- Agent 原来的 pinned binding 不会自动升级到新版本。
- 用户可以后续选择发布为新版本，或另存为 fork。

如果页面暂时没有清晰的草稿入口，可以后续用 API 或数据库确认 `skill_revision_drafts` 表。

## 12. 如何验证内置 Tool 调用记录

目标：

- Agent 通过能力绑定调用内置 Tool。
- 容器写 `.weagent/runs/<run_id>/calls.jsonl`。
- 后端同步成 `capability_call_records`。

容器里检查：

```bash
find /workspace/.weagent/runs -name calls.jsonl -type f -print -exec cat {} \;
```

通过标准：

- 有 `calls.jsonl`。
- 记录里有 Agent、session、capability/version、status、input summary、output summary。
- 后端 DB 有 `capability_call_records`。

## 13. 如何验证 MCP

v1 的 MCP 规则是：

1. 先导入 manifest。
2. 解析权限和工具列表。
3. 再允许绑定到 Agent。
4. 在 sandbox 容器内用 npx 启动。
5. list tools。
6. 做一次最小调用。
7. 写调用记录。

通过标准：

- MCP 不是直接在宿主机后端执行。
- 需要 `run_command` 这类权限时，必须显式授权。
- 调用后有 call record。

如果失败，优先看：

```powershell
docker logs <container_id>
```

常见原因：

- manifest 包名不对。
- Docker 容器里网络访问 npm/npx 失败。
- Agent 没授权 required permission。
- MCP server 启动后没有返回 tools。

## 14. 如何验证 Plugin 边界

v1 的 Plugin 只做：

- manifest 导入；
- install record；
- 页面展示。

v1 不做：

- Plugin 代码执行；
- Plugin hook；
- UI extension 执行。

通过标准：

- Plugin 可以导入。
- 能看到安装记录。
- 找不到执行 Plugin 的按钮或 API。

如果你发现可以直接执行 Plugin 代码，那就是 v1 边界 bug。

## 15. 如何判断失败属于哪里

按这个顺序排查：

1. `docker info` 不通过：Docker Desktop 问题。
2. `docker image ls weagent-sandbox:latest` 没镜像：沙箱镜像没构建。
3. 后端打不开：`.env`、MySQL、Redis、Python 依赖或端口问题。
4. 前端打不开：前端 dev server 或端口 `8080` 问题。
5. 前端能开但 API 报错：后端 `5001` 没启动或代理失败。
6. 会话创建失败：Docker 镜像、Docker 权限、容器启动问题。
7. 容器启动但 Agent 不回复：模型设置、API Key、Base URL、模型名问题。
8. `.weagent` 不存在：能力绑定或投影逻辑问题。
9. Skill 改了没有草稿：draft sync 问题。
10. Artifact 或进度不显示：消息事件桥或前端渲染问题。

不要跳着修。

比如 `docker info` 都不通过，就不要先看能力库页面。

## 16. 最短真实验收路线

如果你只想快速判断“这套东西是不是能跑起来”，按这个做：

1. 启动 Docker Desktop。
2. 运行：

```powershell
docker info
```

3. 构建镜像：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

4. 启动后端：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python run.py
```

5. 启动前端：

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
npm run serve
```

6. 打开网页：

```text
http://localhost:8080
```

7. 登录或注册。
8. 进入「设置」，填模型配置。
9. 进入「能力库」，创建一个 Skill。
10. 进入「我的Agent」，创建 Agent 并绑定 Skill。
11. 进入「聊天」或「沙箱测试」，创建会话。
12. 运行：

```powershell
docker ps --filter "label=weagent.sandbox=true"
```

13. 如果看到容器，进入容器：

```powershell
docker exec -it <container_id> bash
```

14. 检查：

```bash
find /workspace/.weagent -maxdepth 4 -type f
```

如果能看到 `.weagent` 里的能力文件，说明工具集运行投影真实进入了 Docker sandbox。

## 17. 你验收时可以把这些信息发给我

如果某一步失败，把下面这些给我：

- 失败发生在哪一步。
- 网页上看到的错误。
- 后端 PowerShell 输出。
- 前端 PowerShell 输出。
- `docker info` 输出。
- `docker ps --filter "label=weagent.sandbox=true"` 输出。
- 如果有容器，`docker logs <container_id>` 输出。

我会根据这些判断是 Docker、后端配置、数据库、模型设置、sandbox 镜像、能力绑定，还是前端展示的问题。
