# WeAgent RAG 检索服务 Docker 镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖 (pdfplumber 需要 libstdc++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制服务代码
COPY . .

# 创建 chromadb 持久化目录
RUN mkdir -p /app/chroma_data

EXPOSE 5104

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5104/health').read())"

CMD ["python", "app.py"]
