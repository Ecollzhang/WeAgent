"""向量存储服务 — 向量 CRUD + 语义搜索.

使用 SimpleVectorStore (SQLite 后端)，无外部原生依赖，
避免 chromadb onnxruntime 在 Windows Python 3.12 上的 segfault.
"""
from services.simple_vector_store import simple_vector_store


class VectorService:
    """向量存储操作 (委托给 SimpleVectorStore)."""

    COLLECTION_NAME = 'weagent_rag'

    @property
    def collection(self):
        return simple_vector_store

    def add(self, ids: list[str], embeddings: list[list[float]],
            documents: list[str], metadatas: list[dict] = None):
        """批量添加向量."""
        self.collection.add(ids, embeddings, documents, metadatas or [{}] * len(ids))

    def search(self, query_embedding: list[float], top_k: int = 5,
               filter_meta: dict = None) -> list[dict]:
        """语义搜索."""
        return self.collection.search(query_embedding, top_k, filter_meta)

    def delete_by_ids(self, ids: list[str]):
        """删除指定向量."""
        self.collection.delete_by_ids(ids)

    def count(self) -> int:
        return self.collection.count()


# 模块级单例
vector_service = VectorService()
