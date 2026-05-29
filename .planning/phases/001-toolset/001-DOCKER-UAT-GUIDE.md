# WeAgent Toolset Docker UAT Guide

**Audience:** First-time Docker user validating Toolset Capabilities v1.
**Branch:** `feature/toolset`
**Purpose:** Help you run the real WeAgent stack, start Docker-backed sandbox sessions, and debug the common failure points.

## 1. What Docker Does In This Project

WeAgent does not use `docker compose` for the whole application.

The normal development stack is:

- Backend Flask server runs on your Windows machine at `http://127.0.0.1:5001`.
- Frontend Vue dev server runs on your Windows machine at `http://localhost:8080`.
- MySQL and Redis are normal local services.
- Docker is used only when WeAgent creates an Agent sandbox session.

The sandbox rule is:

- 1 conversation/session = 1 Docker container.
- The container runs the internal orchestrator on port `8080`.
- The host backend maps that container port to a random local port.
- The container workspace is `/workspace`.
- Toolset runtime files are written inside the container under `/workspace/.weagent/*`.
- Destroying the session/container deletes the runtime workspace, but DB records remain.

This is why Docker matters for the real toolset test: `.weagent/*`, MCP npx runtime, built-in Tool call audit, Skill draft sync, and artifact files all happen in or through the sandbox.

## 2. Current Repo State

The implementation has already been pushed.

```powershell
git branch --show-current
# feature/toolset

git log --oneline -5
# 185735e test: add toolset regression contracts
# 538c67b feat: sync runtime skill drafts
# 6d38fc0 feat: add plugin install records
# 4dc8027 feat: add minimal mcp runtime
# 650d5b9 feat: audit builtin tool calls
```

Expected local untracked files that should not be committed:

```text
.claude/logs/
.planning/STATE.md.lock
```

## 3. Required Local Services

You need these running:

- Docker Desktop
- MySQL 8.x
- Redis 7.x
- Backend Flask server
- Frontend Vue dev server

Docker CLI is installed on this machine, but Docker Desktop must also be running. The command below only checks the CLI version:

```powershell
docker --version
```

The real readiness check is:

```powershell
docker info
```

If `docker --version` works but `docker info` fails, Docker is installed but the Docker engine is not ready.

## 4. Start Docker Desktop

You can start Docker Desktop from the Start Menu, or with:

```powershell
Start-Process -FilePath "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

Wait until Docker Desktop says it is running. Then check:

```powershell
docker info --format "Docker daemon ready: {{.ServerVersion}}"
```

Expected:

```text
Docker daemon ready: 29.5.2
```

The exact version can differ.

## 5. Common Docker Readiness Errors

### Error: Cannot connect to docker_engine

Example:

```text
failed to connect to the docker API at npipe:////./pipe/docker_engine
```

Meaning:

Docker Desktop is not running, or the engine has not finished starting.

What to do:

1. Open Docker Desktop.
2. Wait until it finishes starting.
3. Run `docker info` again.

### Error: Permission denied on dockerDesktopLinuxEngine

Example:

```text
permission denied while trying to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Meaning:

Docker Desktop is installed, but the current shell cannot access the selected Docker engine pipe. This can happen while Docker Desktop is still switching engines, after a fresh launch, or when Windows/Docker permissions are out of sync.

What to try:

1. Wait 20-30 seconds and run `docker info` again.
2. Open Docker Desktop visibly and check whether it asks for permission, WSL setup, update, or restart.
3. Close and reopen the terminal after Docker Desktop is ready.
4. Restart Docker Desktop.
5. If it persists, run the terminal as the same Windows user that launched Docker Desktop.

Do not debug WeAgent until `docker info` succeeds.

## 6. Build The Sandbox Image

The sandbox image name must be:

```text
weagent-sandbox:latest
```

Build it from the backend directory:

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

Alternative Python entry:

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python -c "from app.sandbox import build_image; build_image()"
```

Check the image:

```powershell
docker image ls weagent-sandbox:latest
```

Expected: one image row with repository `weagent-sandbox` and tag `latest`.

When to rebuild:

- after changing `backend/app/sandbox/Dockerfile`;
- after changing `backend/app/sandbox/container/*`;
- after changing sandbox CLI/runtime dependencies;
- before real UAT if you are unsure whether the local image contains the latest branch code.

## 7. Prepare Backend Environment

Backend config reads `backend/.env`.

Start from:

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
Copy-Item .env.example .env
```

Edit `backend/.env`:

```env
FLASK_ENV=development
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=<your_mysql_password>
MYSQL_DB=weagent

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

JWT_SECRET_KEY=change-this-to-a-random-secret-key
SECRET_KEY=change-this-to-another-random-key
PORT=5001
```

Important:

- The frontend proxy expects backend port `5001`.
- `backend/run.py` defaults to `5001`, not `5000`.
- MySQL schema is `backend/sql/init.sql`.

Initialize DB if needed:

```powershell
mysql -u root -p
CREATE DATABASE IF NOT EXISTS weagent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

mysql -u root -p weagent < backend/sql/init.sql
```

If you already have an old `weagent` DB, make sure it includes the new capability tables:

- `capabilities`
- `capability_versions`
- `agent_capability_bindings`
- `capability_call_records`
- `plugin_install_records`
- `skill_revision_drafts`

## 8. Start Backend

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python run.py
```

Expected:

- Flask/SocketIO server starts.
- Backend listens on `http://127.0.0.1:5001`.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:5001/api/health
```

If the backend fails on MySQL:

- verify MySQL is running;
- verify `MYSQL_PASSWORD`;
- verify the `weagent` database exists;
- verify `backend/.env` is in the backend directory.

If the backend fails on Docker:

- first run `docker info`;
- then build `weagent-sandbox:latest`.

## 9. Start Frontend

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
npm run serve
```

Expected:

- Vue dev server starts at `http://localhost:8080`.
- API calls proxy to `http://127.0.0.1:5001`.

Open:

```text
http://localhost:8080
```

## 10. Real Toolset UAT Flow

This is the recommended manual test path.

### Step 1: Login

Open `http://localhost:8080`.

Login or register a test user.

### Step 2: Configure Model Settings

Before starting a real Agent session, configure the model provider in Settings.

The sandbox container receives model settings from the backend and uses them for Claude Code / Agent calls.

Check:

- API key is present.
- Base URL is correct if you use a proxy or compatible provider.
- Model name is correct.

If the Agent replies fail with model/auth errors, debug Settings first, not Docker.

### Step 3: Open Capability Library

Go to the Capability Library page.

Validate:

- Skill, Tool, MCP, and Plugin appear as peer capability types.
- You can create a Skill from Markdown.
- You can import Markdown text as a Skill.
- You can import an npx manifest.
- Plugin import creates install visibility but no execute button.

### Step 4: Create Or Edit An Agent With Capabilities

Go to Agent management.

Create or edit an Agent.

Bind:

- one Skill;
- one built-in Tool if available;
- optionally one MCP manifest-backed capability;
- optionally one Plugin manifest-backed record.

Check:

- bindings are Agent-level defaults;
- version policy is pinned;
- required permissions must be explicitly granted.

### Step 5: Start A Sandbox Conversation

Create a conversation/session using the Agent.

Expected backend behavior:

- backend creates one Docker container;
- container runs orchestrator;
- backend projects Agent capabilities into `/workspace/.weagent/*`;
- conversation stores sandbox session/container metadata.

Useful Docker checks:

```powershell
docker ps --filter "label=weagent.sandbox=true"
```

Get logs:

```powershell
docker logs <container_id>
```

Inspect inside container:

```powershell
docker exec -it <container_id> bash
```

Inside the container:

```bash
ls -la /workspace
find /workspace/.weagent -maxdepth 4 -type f
cat /workspace/.weagent/capabilities/index.json
cat /workspace/.weagent/agents/<agent_id>/capabilities.json
cat /workspace/.weagent/agents/<agent_id>/skill-index.json
```

Expected:

- `.weagent/capabilities/index.json` exists.
- `.weagent/skills/<runtime_id>/SKILL.md` exists.
- `.weagent/agents/<agent_id>/capabilities.json` exists.
- `.weagent/agents/<agent_id>/skill-index.json` exists.
- `.weagent/agents/<agent_id>/permissions.json` exists.

There should be no v1 compatibility files like:

- `.claude/skills`
- `.codex/skills`
- `.mcp.json`

### Step 6: Validate Built-In Tool Call Record

Ask the Agent to do something that triggers a bound built-in Tool, or use the sandbox API/UI path that calls a Tool.

Expected:

- `.weagent/runs/<run_id>/calls.jsonl` appears in the container.
- Backend sync creates a DB `CapabilityCallRecord`.
- Capability call list API/UI shows status, Agent, session, capability version, input summary, and output summary.

Container check:

```bash
find /workspace/.weagent/runs -name calls.jsonl -type f -print -exec cat {} \;
```

### Step 7: Validate Skill Draft Sync

Inside the container, edit a projected Skill:

```bash
cat >> /workspace/.weagent/skills/<runtime_id>/SKILL.md <<'EOF'

## Runtime note
This was edited during UAT.
EOF
```

Then send another message to that Agent from the UI.

Expected:

- container detects the runtime Skill change;
- host sync creates a `SkillRevisionDraft(status='pending_review')`;
- DB user Skill library is not overwritten automatically;
- existing pinned Agent binding remains on the original version.

Check in UI/API:

- draft appears in Capability Library draft list if the page exposes it;
- publish draft creates a new Skill version;
- save as fork creates a new Skill capability;
- Agent binding does not move unless explicitly upgraded.

### Step 8: Validate MCP Runtime

For v1, MCP must follow this rule:

1. import manifest first;
2. inspect permission/tool declarations;
3. bind to Agent with explicit permission grant;
4. start/call inside sandbox;
5. record call.

Expected:

- npx server is started inside the sandbox, not on the host backend;
- list-tools succeeds;
- one minimal call succeeds;
- call record is written and synced.

If MCP fails:

- check npx package name/version in manifest;
- check network access from Docker container;
- check `run_command` permission grant;
- check `docker logs <container_id>`.

### Step 9: Validate Plugin Boundary

Plugin v1 is manifest/install-record only.

Expected:

- Plugin manifest imports.
- Plugin install record is visible.
- No Plugin execution endpoint/button/path exists.

If you find a way to execute Plugin code directly, that is a bug for v1.

### Step 10: Validate Existing Product Behavior

The toolset work must not break:

- multi-agent message display;
- Agent realtime progress display;
- artifact display.

Manual checks:

- Start a multi-Agent chain/delegation flow.
- Confirm multiple Agent replies still show separately.
- Confirm realtime progress/status updates appear while running.
- Ask an Agent to create or modify a file and confirm artifact/file display still works.

## 11. Useful Debug Commands

### Docker engine

```powershell
docker info
docker context ls
docker ps
docker ps -a
```

### Sandbox containers

```powershell
docker ps --filter "label=weagent.sandbox=true"
docker logs <container_id>
docker inspect <container_id>
docker exec -it <container_id> bash
```

### Sandbox image

```powershell
docker image ls weagent-sandbox:latest
docker build -t weagent-sandbox:latest -f app/sandbox/Dockerfile app/sandbox
```

### Backend

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python run.py
```

### Frontend

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
npm run serve
```

### Tests before/after fixes

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\backend"
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py tests/test_capability_tool_audit.py tests/test_capability_mcp_runtime.py tests/test_capability_skill_draft_sync.py tests/test_toolset_regression_contract.py -q
```

```powershell
cd "E:\code for project\seedance-competition\agentshub\WeAgent\frontend"
node tests\capability-ui-contract.test.js
node tests\toolset-regression-contract.test.js
npm run build
```

## 12. How To Tell Where A Failure Is

Use this order:

1. `docker info` fails: Docker Desktop/engine problem.
2. `docker image ls weagent-sandbox:latest` empty: image not built.
3. Backend does not start: `.env`, MySQL, Redis, Python dependency, or port issue.
4. Frontend page loads but API fails: backend not on `5001` or proxy issue.
5. Conversation creates but sandbox fails: Docker image/container issue.
6. Agent starts but cannot reply: model Settings/API key/provider issue.
7. Tool/MCP call fails: capability binding permission, manifest, container network, or runtime error.
8. Skill edit does not draft: `.weagent` projection/draft sync path issue.
9. Artifact/progress missing: message event bridge or frontend rendering issue.

This order keeps debugging grounded. Do not fix the UI if Docker cannot start; do not debug Docker if the model provider credentials are wrong.

## 13. What I Can Debug With You

When you try the real flow, send me:

- the exact step where it failed;
- the visible UI error;
- backend terminal output;
- frontend terminal output;
- `docker ps --filter "label=weagent.sandbox=true"`;
- `docker logs <container_id>` if a container exists.

Then I can diagnose whether the failure belongs to Docker, backend config, sandbox image, model settings, capability binding, or frontend rendering.
