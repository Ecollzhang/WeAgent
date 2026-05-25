# ============================================================
# WeAgent Sandbox — Docker 镜像
# 每个会话 = 一个容器，容器内运行 Orchestrator + Claude CLI
# ============================================================

FROM python:3.11-slim

# ---- 安装 Node.js + Claude CLI ----
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && cd /usr/lib/node_modules/@anthropic-ai/claude-code \
    && npm install @anthropic-ai/claude-code-linux-x64 --no-save \
    && node install.cjs \
    && cd / \
    && npm cache clean --force \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && claude --version

# ---- 安装 Orchestrator Python 依赖 ----
RUN pip install --no-cache-dir flask requests

# ---- 复制容器端代码 (保持 container/ 包结构) ----
COPY container/ /app/container/

# ---- 工作目录 (volume mount 点) ----
WORKDIR /workspace

# ---- 创建非 root 用户 (Claude Code 的 --dangerously-skip-permissions 需要) ----
RUN useradd -m -s /bin/bash agent && \
    chown -R agent:agent /app /workspace

# Orchestrator 端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/api/health').read())"

# 以非 root 用户运行
USER agent

# 启动 Orchestrator Server
CMD ["python", "/app/container/server.py"]
