"""Embedding 服务 — 支持 Ollama 和 OpenAI 兼容 API."""
import os
import requests
from config import Config

API_TIMEOUT = 120

# 已知模型的维度映射
_MODEL_DIMS = {
    'text-embedding-3-small': 1536,
    'text-embedding-3-large': 3072,
    'text-embedding-ada-002': 1536,
    'nomic-embed-text': 768,
    'nomic-embed-text:latest': 768,
    'bge-m3': 1024,
    'mxbai-embed-large': 1024,
}


class EmbeddingService:
    """Embedding API 封装 — 支持 Ollama (本地) 和 OpenAI (云端)."""

    def __init__(self):
        self.model = Config.EMBEDDING_MODEL
        self.api_key = Config.EMBEDDING_API_KEY or ''
        self.base_url = Config.EMBEDDING_BASE_URL or ''
        self.provider = Config.EMBEDDING_PROVIDER  # 'ollama' | 'openai'
        self._dimension = None

    @property
    def configured(self) -> bool:
        """检查是否已配置."""
        if self.provider == 'ollama':
            return bool(self.base_url)
        return bool(self.api_key)

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._dimension = _MODEL_DIMS.get(self.model, 768)
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embeddings."""
        if self.provider == 'ollama':
            return self._embed_ollama(texts)
        return self._embed_openai(texts)

    def embed_single(self, text: str) -> list[float]:
        """生成单个文本的 embedding."""
        return self.embed([text])[0]

    # ── Ollama ────────────────────────────────────────────

    def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        """Ollama 本地 embedding — 逐条调用（Ollama 不支持批量）."""
        url = f"{self.base_url.rstrip('/')}/api/embeddings"
        embeddings = []
        for text in texts:
            resp = requests.post(
                url,
                json={'model': self.model, 'prompt': text},
                headers={'Content-Type': 'application/json'},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings.append(data['embedding'])
        return embeddings

    # ── OpenAI ────────────────────────────────────────────

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """OpenAI 兼容 API — 支持批量."""
        if not self.api_key:
            raise ValueError(
                'EMBEDDING_API_KEY not configured. '
                'Set EMBEDDING_API_KEY in .env'
            )
        url = f"{self.base_url.rstrip('/')}/embeddings"
        resp = requests.post(
            url,
            json={'model': self.model, 'input': texts},
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = sorted(data['data'], key=lambda x: x['index'])
        return [item['embedding'] for item in items]


# 模块级单例
embedding_service = EmbeddingService()
