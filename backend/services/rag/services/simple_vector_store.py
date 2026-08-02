"""轻量级向量存储 — 使用 SQLite 存储向量，cosine 相似度搜索.

不依赖 chromadb（避免 onnxruntime segfault on Windows Python 3.12），
适合知识库规模（< 10K chunks）的场景。
"""
import json
import math
import os
import sqlite3
import threading

_EMBEDDING_DIM = 768


class SimpleVectorStore:
    """基于 SQLite 的向量存储，支持 cosine 相似度检索."""

    def __init__(self, db_path: str = './simple_vector_store.db'):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,   -- JSON array of floats
                    document TEXT,
                    metadata TEXT               -- JSON object
                )
            ''')
            conn.commit()
            conn.close()

    def add(self, ids: list[str], embeddings: list[list[float]],
            documents: list[str], metadatas: list[dict] = None):
        """批量添加向量."""
        if not ids:
            return
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            rows = []
            for i, vid in enumerate(ids):
                emb_json = json.dumps(embeddings[i])
                doc = documents[i] if i < len(documents) else ''
                meta = json.dumps(metadatas[i]) if metadatas and i < len(metadatas) else '{}'
                rows.append((vid, emb_json, doc, meta))
            conn.executemany(
                'INSERT OR REPLACE INTO vectors (id, embedding, document, metadata) VALUES (?, ?, ?, ?)',
                rows,
            )
            conn.commit()
            conn.close()

    def search(self, query_embedding: list[float], top_k: int = 5,
               filter_meta: dict = None, document_ids: list[str] = None) -> list[dict]:
        """Brute-force cosine 相似度搜索，支持按 document_ids 过滤."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute('SELECT id, embedding, document, metadata FROM vectors').fetchall()
            conn.close()

        if not rows:
            return []

        # 预计算 document_ids 过滤集合
        doc_id_set = set(document_ids) if document_ids else None

        # 计算所有向量的 cosine 相似度
        scored = []
        for row in rows:
            vid, emb_json, doc, meta_json = row
            meta = json.loads(meta_json) if meta_json else {}
            # metadata 按需过滤
            if filter_meta:
                if not all(meta.get(k) == v for k, v in filter_meta.items()):
                    continue
            # document_ids 过滤
            if doc_id_set:
                if meta.get('document_id') not in doc_id_set:
                    continue
            emb = json.loads(emb_json)
            similarity = _cosine_similarity(query_embedding, emb)
            scored.append((similarity, vid, doc, meta_json))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return [
            {
                'chunk_id': vid,
                'content': doc,
                'score': round(score, 4),
                'metadata': json.loads(meta) if meta else {},
            }
            for score, vid, doc, meta in top
        ]

    def delete_by_ids(self, ids: list[str]):
        if not ids:
            return
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            placeholders = ','.join('?' for _ in ids)
            conn.execute(f'DELETE FROM vectors WHERE id IN ({placeholders})', ids)
            conn.commit()
            conn.close()

    def count(self) -> int:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            count = conn.execute('SELECT COUNT(*) FROM vectors').fetchone()[0]
            conn.close()
            return count

    def delete_collection(self):
        """清空所有数据."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute('DELETE FROM vectors')
            conn.commit()
            conn.close()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的 cosine 相似度."""
    if len(a) != len(b):
        raise ValueError(f'Vector dimension mismatch: {len(a)} vs {len(b)}')
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# 模块级单例
simple_vector_store = SimpleVectorStore(
    db_path=os.path.join(os.path.dirname(__file__), '..', 'simple_vector_store.db'),
)
