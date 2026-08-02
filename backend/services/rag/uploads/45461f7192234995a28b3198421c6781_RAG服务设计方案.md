# WeAgent RAG 检索服务设计方案

## 一、概述

为 WeAgent 平台搭建 RAG（Retrieval-Augmented Generation）检索增强生成服务，使 Agent 在对话中能够检索外部知识库中的文档内容，提升回答的准确性和专业度。

### 核心能力

- **文档上传**：支持 PDF、TXT、Markdown、DOCX、CSV 等格式
- **链接下载**：输入 URL 自动下载文档内容
- **网页爬取**：爬取网页正文，自动去除导航、广告等噪音
- **预览确认**：解析后先预览内容，用户确认后再分块入库
- **语义搜索**：Agent 在对话中通过工具调用检索相关知识
- **领域隔离**：按领域（研发/教育/办公）和工作空间隔离文档

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 2)                        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ ChatWindow│  │知识库管理页面 │  │ 文档上传/预览/确认弹窗 │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
└──────────────┬──────────────────────┬───────────────────────┘
               │ SocketIO              │ HTTP REST
┌──────────────▼──────────────────────▼───────────────────────┐
│                     Main Backend (Flask :5000)               │
│  message_service → sandbox manager → Docker containers       │
│                    ┌──────────────────────┐                  │
│                    │   RAG Proxy Routes   │ (透传代理)       │
│                    └──────────┬───────────┘                  │
└───────────────────────────────┼──────────────────────────────┘
                                │ HTTP (内部)
┌───────────────────────────────▼──────────────────────────────┐
│                  RAG Microservice (:5104)                     │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────┐ │
│  │文档管理API│  │ 解析/分块  │  │ 向量化/索引 │  │ 语义搜索  │ │
│  └──────────┘  └───────────┘  └────────────┘  └──────────┘ │
│                         │                                    │
│               ┌─────────▼─────────┐                          │
│               │ SimpleVectorStore │  向量存储 (SQLite)        │
│               └───────────────────┘                          │
│               ┌───────────────────┐                          │
│               │  MySQL (weagent_rag) │  文档元数据            │
│               └───────────────────┘                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                Sandbox Container (Docker)                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Orchestrator (Agent Runtime)              │    │
│  │                                                       │    │
│  │  System Prompt: "你可以使用 rag_search 工具搜索知识库"  │    │
│  │                                                       │    │
│  │  Agent 决策 → 调用 rag_search("如何部署XX服务")        │    │
│  │                    ↓                                   │    │
│  │  ToolRegistry.rag_search() → HTTP → RAG Service       │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、Agent 如何查找 RAG 库内容

### 3.1 机制：内置工具（Built-in Tool）

在容器的 ToolRegistry 中注册 `rag_search` 工具。Agent 的系统提示词会列出所有可用工具，包含 `rag_search`。Agent 自主判断当前问题是否需要检索知识库，需要时主动调用该工具。

```
用户: "我们的微服务部署规范是什么？"

Agent 思考: 这个问题需要查内部文档
  → 调用 rag_search(query="微服务部署规范", top_k=5)
  → RAG Service 返回相关文档片段:
     1. "部署规范 v2.3: 所有微服务必须使用 Docker 容器化..."
     2. "端口分配: 服务端口范围 5000-6000..."
  → Agent 基于检索结果生成回答:
     "根据内部部署规范 v2.3，微服务部署需要: 1) Docker 容器化..."
```

### 3.2 什么时机获取？

| 时机 | 方式 | 说明 |
|------|------|------|
| **对话中 Agent 主动调用**（主力） | Agent 判断需要时调用 `rag_search` 工具 | 灵活按需，不浪费 token |
| 对话开始前自动注入（辅助） | 后端在消息分发时预检索，拼入系统提示词 | 适合"始终需要"的场景 |
| 用户手动 @提及文档 | 前端选择文档后，作为 context 随消息发送 | 用户明确指定参考某文档 |

**推荐主力使用 Agent 主动调用方式**，这是当前工具系统的自然扩展，Agent 自己判断何时需要检索。

**文档处理流程**：`confirm` 接口采用**后台线程异步处理**模式——接口立即返回 `status: "processing"`，实际的"分块 → 向量化 → 入库"在后台线程中执行。前端通过轮询文档列表/详情来判断处理完成（`status` 变为 `ready` 或 `error`）。这样避免了长文档（50KB+）处理时 HTTP 超时的问题。

### 3.3 容器如何访问 RAG 服务

```
容器内 Agent
  → rag_search("查询词")
  → ToolRegistry.execute("rag_search", {query: "查询词"})
  → HTTP POST http://host.docker.internal:5104/api/rag/search
  → RAG Service 查询向量数据库
  → 返回相关文档片段给 Agent
```

- **Windows/Mac Docker Desktop**：`host.docker.internal` 默认可用
- **Linux**：启动容器时需添加 `--add-host host.docker.internal:host-gateway`

### 3.4 搜索接口定义

```json
// 请求
POST /api/rag/search
{
  "query": "微服务部署规范",
  "top_k": 5,
  "domain": "rd",           // 可选，按领域过滤
  "workspace_id": "xxx",    // 可选，按工作空间过滤
  "collection": "deploy"    // 可选，指定集合
}

// 响应
{
  "code": 200,
  "data": {
    "results": [
      {
        "chunk_id": "chunk_001",
        "document_id": "doc_001",
        "document_name": "微服务部署规范 v2.3.pdf",
        "content": "所有微服务必须使用 Docker 容器化部署...",
        "score": 0.92,
        "metadata": { "page": 3, "source_url": "..." }
      }
    ],
    "query_time_ms": 45
  }
}
```

---

## 四、文档上传 → 存储完整流程

```
步骤1: 选择来源
  用户选择: [上传文件] [从链接下载] [爬取网页]

步骤2: 上传/输入
  ┌─ 上传文件 ─────────────────────────┐
  │  拖拽或选择 PDF/TXT/MD/DOCX 等文件   │
  │  选择所属领域: [研发 ▼]              │
  └────────────────────────────────────┘
  ┌─ 从链接下载 ───────────────────────┐
  │  输入文档URL: [________________]    │
  │  所属领域: [研发 ▼]                 │
  └────────────────────────────────────┘
  ┌─ 爬取网页 ─────────────────────────┐
  │  输入网页URL: [________________]    │
  │  所属领域: [研发 ▼]                 │
  └────────────────────────────────────┘

步骤3: 预览确认
  ┌──────────────────────────────────────────┐
  │  文档名称: 微服务部署规范 v2.3.pdf         │
  │  来源类型: PDF 上传                        │
  │  页数: 12   大小: 2.3MB   约8500字         │
  │  ─────────────────────────────────────── │
  │  内容预览 (前500字):                       │
  │  1. 概述                                  │
  │  本文档定义了微服务的标准部署流程...          │
  │  ...                                      │
  │  ─────────────────────────────────────── │
  │       [取消]    [确认存入知识库]            │
  └──────────────────────────────────────────┘

步骤4: 后台处理
  确认后 RAG Service 异步执行:
  → 分块(chunking): 按语义边界拆分，每块500~1000 tokens
  → 向量化: 调用 nomic-embed-text (Ollama) 生成 Embedding (768维)
  → 存储: SimpleVectorStore (SQLite) 存向量 + MySQL 存元数据
  → 前端轮询状态直到 "ready"
```

### 4.1 支持的文档来源

| 来源类型 | 说明 | 后端实现方式 |
|----------|------|-------------|
| **文件上传** | PDF, TXT, MD, DOCX, CSV, JSON, 代码文件 | 前端 FormData → 保存文件 → 解析提取文本 |
| **URL 下载** | 通过链接下载文档 | `requests.get(url)` → 根据 Content-Type 解析 |
| **网页爬取** | 爬取网页正文 | `requests` + `BeautifulSoup` → 提取正文内容 |

### 4.2 文档分块策略

```
原始文档
  → 提取纯文本 (pdfplumber / python-docx / markdown)
  → 按语义边界拆分:
     - 优先按段落 / 标题拆分
     - 每块 500~1000 tokens
     - 相邻块 overlap 100 tokens（保持上下文连续性）
  → 每块调用 nomic-embed-text (Ollama) 生成 768 维向量
  → 存入 SimpleVectorStore (SQLite) (id=vector_id, embedding=vector, metadata={doc_id, chunk_index, ...})
```

---

## 五、前端页面设计

### 5.1 知识库管理页面（路由 `/knowledge-base`）

```
┌───────────────────────────────────────────────────────┐
│  知识库管理                            [侧边栏: 公共]   │
│                                                       │
│  [上传文件]  [从链接添加]  [爬取网页]                    │
│                                                       │
│  领域: [全部 ▼]   搜索: [________________] 🔍           │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 文档名称          │ 来源   │ 领域 │ 分块 │ 时间    │  │
│  │ 部署规范 v2.3.pdf │ upload │ 研发 │ 45   │ 07-26  │  │
│  │ API设计文档.md    │ url   │ 研发 │ 32   │ 07-25  │  │
│  │ 教学大纲.docx     │ upload │ 教育 │ 18   │ 07-24  │  │
│  │ React最佳实践     │ scrape │ 研发 │ 28   │ 07-24  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  共 4 个文档                                          │
└───────────────────────────────────────────────────────┘
```

### 5.2 对话中展示 RAG 引用

Agent 使用 RAG 搜索结果回复时，消息气泡底部展示引用来源：

```
┌─────────────────────────────────────┐
│ Agent 回复:                          │
│ 根据内部部署规范，微服务部署需要...    │
│                                     │
│ 📎 参考文档:                         │
│  · 微服务部署规范 v2.3.pdf — P3      │
│  · Docker 最佳实践.md — P7           │
└─────────────────────────────────────┘
```

---

## 六、数据库设计（weagent_rag 库）

```sql
-- 文档表
CREATE TABLE rag_documents (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL COMMENT '上传者',
    workspace_id VARCHAR(36) COMMENT '所属工作空间',
    domain VARCHAR(50) NOT NULL COMMENT 'rd / edu / office',

    name VARCHAR(500) NOT NULL COMMENT '文档名称',
    source_type ENUM('upload', 'url', 'scrape') NOT NULL,
    source_url VARCHAR(2000) COMMENT '来源URL',
    file_type VARCHAR(50) COMMENT 'pdf/txt/md/docx/csv等',
    file_size BIGINT COMMENT '文件字节数',

    status ENUM('pending','processing','ready','error') DEFAULT 'pending',
    chunk_count INT DEFAULT 0,
    total_tokens INT DEFAULT 0,

    description TEXT COMMENT '用户备注',
    extra_meta JSON COMMENT '原始网页标题/作者等元数据',

    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_domain (domain),
    INDEX idx_workspace (workspace_id)
);

-- 文档分块表
CREATE TABLE rag_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    chunk_index INT NOT NULL COMMENT '分块序号',

    content TEXT NOT NULL COMMENT '分块文本',
    token_count INT DEFAULT 0,

    vector_id VARCHAR(200) COMMENT 'ChromaDB 中对应的向量ID',

    page_number INT COMMENT '来源页码',
    extra_meta JSON,

    FOREIGN KEY (document_id) REFERENCES rag_documents(id) ON DELETE CASCADE,
    INDEX idx_doc (document_id)
);
```

---

## 七、RAG 服务 API 总览

### 7.1 文档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/documents/upload` | 上传文件 |
| POST | `/api/rag/documents/fetch-url` | 从 URL 下载文档 |
| POST | `/api/rag/documents/scrape-url` | 爬取网页内容 |
| GET | `/api/rag/documents/:id/preview` | 预览解析内容 |
| POST | `/api/rag/documents/:id/confirm` | 确认存储（后台异步分块+向量化） |
| POST | `/api/rag/documents/:id/reprocess` | 重新处理（用于 error 状态重试） |
| DELETE | `/api/rag/documents/:id` | 删除文档及所有分块 |
| GET | `/api/rag/documents` | 文档列表（分页、搜索、按领域筛选） |
| GET | `/api/rag/documents/:id` | 文档详情 + 分块列表 |

### 7.2 搜索

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/search` | 语义搜索（cosine 相似度） |

### 7.3 服务状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/rag/status` | 检查 MySQL、向量存储、Embedding 服务状态 |

> **注意**：`/api/rag/search/hybrid` 混合搜索、集合管理 API 等为后续迭代功能，当前版本未实现。

### 7.3 搜索请求/响应示例

```json
// 请求
POST /api/rag/search
{
  "query": "微服务部署规范",
  "top_k": 5,
  "domain": "rd",
  "workspace_id": "xxx",
  "collection": "deploy"
}

// 响应
{
  "code": 200,
  "data": {
    "results": [
      {
        "chunk_id": "chunk_001",
        "document_id": "doc_001",
        "document_name": "微服务部署规范 v2.3.pdf",
        "content": "所有微服务必须使用 Docker 容器化部署...",
        "score": 0.92,
        "metadata": { "page": 3, "source_url": "https://..." }
      }
    ],
    "query_time_ms": 45
  }
}
```

---

## 八、技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| 向量数据库 | **SimpleVectorStore (SQLite)** | 自研轻量向量存储，基于 SQLite + cosine 相似度搜索。避免 ChromaDB 依赖 onnxruntime 在 Windows Python 3.12 上的 segfault 问题。适合知识库规模 < 10K chunks |
| Embedding 模型 | **nomic-embed-text (Ollama)** | 本地部署，768 维向量，免费无限制。备选：OpenAI `text-embedding-3-small`（1536 维） |
| 文档解析 | **pdfplumber** + **python-docx** + **markdown** | 各格式专用解析库 |
| 网页爬取 | **requests** + **BeautifulSoup** | 提取正文内容 |
| 分块 | 自实现 | 按语义边界拆分，可配 chunk_size / overlap |
| 服务框架 | **Flask**（手动创建 app） | 与核心服务架构一致，但不使用 DomainServiceBase（RAG 有独立数据库和配置需求） |

---

## 九、实施计划

| 阶段 | 内容 | 任务分解 |
|------|------|---------|
| **Phase 1: 核心服务** | RAG 微服务核心能力 | ① 文档解析（PDF/TXT/MD/DOCX）<br>② 分块逻辑<br>③ ChromaDB 集成<br>④ Embedding 调用<br>⑤ `/api/rag/search` 搜索接口 |
| **Phase 2: 文档管理** | 文档存储流程 | ① `/api/rag/documents/upload` 文件上传<br>② `/api/rag/documents/fetch-url` URL下载<br>③ `/api/rag/documents/scrape-url` 网页爬取<br>④ 预览+确认存储流程<br>⑤ 文档 CRUD API |
| **Phase 3: Agent 集成** | 容器内工具注册 | ① `rag_search` 工具注册到 ToolRegistry<br>② 容器→RAG 服务 HTTP 通信<br>③ Agent 提示词中注入工具说明<br>④ 测试端到端检索流程 |
| **Phase 4: 前端** | 用户界面 | ① 知识库管理页面（`/knowledge-base`）<br>② 文档上传/预览/确认弹窗<br>③ 对话中 RAG 引用展示<br>④ 领域筛选、搜索 |
| **Phase 5: 增强** | 进阶能力 | ① 混合搜索（语义+关键词）<br>② 集合管理<br>③ 文档自动更新（URL 定时重新下载）<br>④ 引用高亮 |

---

## 十、决策记录

### 🔴 高优先级（已决策）

1. **领域隔离粒度**：✅ 同时支持 `domain` + `workspace_id` 两级隔离。

2. **Embedding 模型**：✅ 默认使用 Ollama `nomic-embed-text:latest`（768 维），备选 OpenAI `text-embedding-3-small`（1536 维）。通过 `EMBEDDING_PROVIDER` 环境变量切换。

3. **向量存储**：✅ 使用自研 `SimpleVectorStore`（SQLite 后端 + cosine 相似度搜索）。ChromaDB 因 onnxruntime 在 Windows Python 3.12 上的 segfault 被弃用。

4. **RAG 工具权限**：✅ 所有 Agent 默认都能调用 `rag_search`，通过系统提示词注入工具说明。

### 🟡 中优先级（已决策）

5. **预览是否必须**：✅ 必须预览确认后才能入库。文档状态流：`pending → processing → ready/error`。

6. **文件大小限制**：✅ 上限 20MB。

7. **网页爬取深度**：✅ 当前仅爬取单页。

8. **Agent 不调用 RAG**：✅ 在系统提示词和工具描述中引导 Agent 主动使用，同时支持预检索注入作为 fallback。

### 🟢 低优先级（后续迭代）

9. **文档更新策略**：⏳ URL 来源的文档定时重新下载（待实现）

10. **引用格式**：⏳ Agent 回复中的引用格式化展示（待实现）

11. **混合搜索**：⏳ 语义搜索 + 关键词搜索（待实现）

---

## 十一、使用方式（开发完成后）

### 用户侧

1. 进入侧边栏「知识库」页面
2. 点击「上传文件」/「从链接添加」/「爬取网页」
3. 选择文件或输入 URL，选择所属领域
4. 预览解析后的内容，确认无误后点击「确认存入知识库」
5. 在对话中直接提问，Agent 会自动检索相关知识库内容并引用

### 开发者侧

1. 在灰度控制台「公共」tab 新建一个 RAG 工具配置（如 `feature.rag.search`）
2. 根据需要启用/禁用 RAG 搜索功能
3. 在容器 `tools/__init__.py` 中通过 `registry.register()` 注册新的 RAG 相关工具

### 运维侧

```bash
# 启动 RAG 服务（必须从 backend/ 目录启动）
cd backend
python services/rag/app.py
# → 启动在 http://127.0.0.1:5104

# 确保 Ollama 已运行并拉取了 Embedding 模型
ollama pull nomic-embed-text:latest

# 验证服务
curl http://127.0.0.1:5104/api/rag/status
# → {"code":200, "data":{"status":"healthy","components":{"mysql":"ok","vector_store":"ok (0 vectors)","embedding":"ok (...)"}}}
```

---

## 十二、目录结构规划

```
backend/
├── services/rag/                    # RAG 微服务
│   ├── .env                         # 环境变量（EMBEDDING_PROVIDER 等）
│   ├── app.py                       # 服务入口（手动创建 Flask app）
│   ├── config.py                    # 配置（DB / Embedding / Ollama）
│   ├── models/
│   │   ├── database.py              # db = SQLAlchemy(app)
│   │   ├── document.py              # 文档 ORM 模型
│   │   └── chunk.py                 # 分块 ORM 模型
│   ├── controllers/
│   │   ├── document_controller.py   # 文档管理 API（上传/下载/爬取/确认/删除/列表）
│   │   ├── search_controller.py     # 语义搜索 API
│   │   └── status_controller.py     # 服务健康状态 API
│   ├── services/
│   │   ├── chunker.py               # 文本分块逻辑
│   │   ├── embedding_service.py     # Embedding 调用（Ollama / OpenAI）
│   │   ├── vector_service.py        # 向量存储操作封装
│   │   └── simple_vector_store.py   # SQLite 向量存储（cosine 相似度搜索）
│   └── utils/
│       ├── parser.py                # 多格式文档解析（pdf/txt/md/docx/csv）
│       └── scraper.py               # 网页爬取（requests + BeautifulSoup）
│
├── app/sandbox/container/tools/
│   └── __init__.py                  # + rag_search 工具注册
│
frontend/src/
├── views/
│   └── KnowledgeBase.vue            # 知识库管理页面
├── api/
│   └── knowledge.js                 # RAG API 封装
└── router/
    └── index.js                     # + /knowledge-base 路由
```

> **与设计方案的差异**：实际实现中未使用 `document_service.py`（文档解析逻辑在 `utils/parser.py`，处理流程在 `document_controller.py`）。未使用 ChromaDB/Hybrid Search/集合管理，由 `SimpleVectorStore` + `status_controller` 替代。
