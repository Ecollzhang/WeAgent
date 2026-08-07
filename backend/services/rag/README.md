# RAG 知识库服务

RAG（检索增强生成）服务为 WeAgent 平台提供私有知识库管理能力，支持文档上传、自动解析、向量化存储与语义检索，让 Agent 的回答始终基于您的专属数据。

## 功能预览

<!-- TODO: 替换为实际截图 -->

| 文档管理 | 知识检索 |
|---|---|
| ![文档管理](../../../static/image/rag_service.png) | ![知识检索](placeholder) |

## 架构

```
frontend/src/views/KnowledgeBase.vue     backend/services/rag/
                                         ├─ app.py              # Flask 应用入口
                                         ├─ config.py           # 配置（Embedding 模型等）
                                         ├─ models/             # 数据模型
                                         │  ├─ database.py      # 数据库实例
                                         │  ├─ document.py      # 文档模型
                                         │  └─ chunk.py         # 文本块模型
                                         ├─ controllers/        # API 路由
                                         │  ├─ document_controller.py
                                         │  ├─ search_controller.py
                                         │  └─ status_controller.py
                                         ├─ services/           # 核心服务
                                         │  ├─ chunker.py       # 文本分割
                                         │  ├─ embedding_service.py # 向量化
                                         │  ├─ vector_service.py   # 向量索引
                                         │  └─ simple_vector_store.py # 本地向量存储
                                         └─ utils/              # 工具
                                            ├─ parser.py        # 文档解析
                                            └─ scraper.py       # 网页抓取
```

## 核心流程

```
文档上传 → 解析 (markitdown) → 文本分割 (chunk) → 向量化 (sentence-transformers)
→ 向量存储 (FAISS) → 语义检索 → Agent 上下文召回
```

## 功能模块

### 文档管理 (`/api/rag/documents`)

- 支持多种文档格式上传（PDF、Word、Markdown、TXT、HTML 等）。
- 文档自动解析为结构化纯文本（基于 markitdown）。
- 文档分级：按知识库域名 (`kb_domain`) 组织，支持按文档 ID 过滤。
- 文档列表、详情查询与删除。

### 文本分割

- 智能分块策略：按段落、句子边界分割，支持重叠窗口。
- 每块保留上下文元数据（源文档 ID、位置、页码）。

### 向量化与存储

- 使用 sentence-transformers 模型生成文本向量。
- 基于 FAISS 的本地向量索引，支持快速近似最近邻搜索。
- 向量索引持久化到磁盘。

### 语义检索 (`/api/rag/search`)

- 输入查询文本，返回语义最相似的 Top-K 文本块。
- 支持按知识库域名 (`kb_domain`) 和文档 ID 列表 (`document_ids`) 过滤检索范围。
- 返回结果包含源文档信息、文本内容与相似度分数。

### 服务状态 (`/api/rag/status`)

- 返回文档总量、向量索引大小、Embedding 模型名称。
- 健康检查接口 `GET /api/rag/health`。

## Agent 集成

- **`rag_search` 工具**：Agent 在沙箱中调用此工具检索知识库，获取相关上下文后再生成回答。
- **会话级 KB 配置**：创建会话时可指定 `kb_domain` 和 `kb_document_ids`，限定 Agent 检索的知识范围。
- **上下文注入**：RAG 检索结果作为额外上下文注入到 Agent 的系统提示词中。

## API 路由一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/api/rag/documents` | 文档列表/上传文档 |
| GET/DELETE | `/api/rag/documents/<id>` | 文档详情/删除文档 |
| POST | `/api/rag/search` | 语义检索 |
| GET | `/api/rag/status` | 服务状态 |
| GET | `/api/rag/spec` | 服务能力描述 |
| GET | `/api/rag/health` | 健康检查 |

## 搜索请求示例

```json
{
  "query": "微服务架构的最佳实践",
  "kb_domain": "tech-docs",
  "document_ids": ["doc-001", "doc-002"],
  "top_k": 5
}
```

## 启动

```powershell
cd backend/services/rag
pip install -r requirements.txt
python app.py
```

首次启动会自动下载 Embedding 模型（默认 `sentence-transformers/all-MiniLM-L6-v2`），请确保网络可用。向量索引文件存储在 `backend/services/rag/data/` 目录下。
