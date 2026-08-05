"""Embedding service with local, Ollama, and OpenAI-compatible providers."""
from collections import Counter
import hashlib
import math
import re
import unicodedata

import requests
from config import Config

API_TIMEOUT = 120
HEALTH_TIMEOUT = 5

# 已知模型的维度映射
_MODEL_DIMS = {
    'text-embedding-3-small': 1536,
    'text-embedding-3-large': 3072,
    'text-embedding-ada-002': 1536,
    'nomic-embed-text': 768,
    'nomic-embed-text:latest': 768,
    'bge-m3': 1024,
    'mxbai-embed-large': 1024,
    'local-hash-embedding-v1': 768,
}


class EmbeddingService:
    """Embedding API wrapper with a dependency-free local provider."""

    def __init__(self):
        self.model = Config.EMBEDDING_MODEL
        self.api_key = Config.EMBEDDING_API_KEY or ''
        self.base_url = Config.EMBEDDING_BASE_URL or ''
        self.provider = Config.EMBEDDING_PROVIDER
        self._dimension = None

    @property
    def configured(self) -> bool:
        """检查是否已配置."""
        if self.provider == 'local':
            return True
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
        if self.provider == 'local':
            return [self._embed_local(text) for text in texts]
        if self.provider == 'ollama':
            return self._embed_ollama(texts)
        if self.provider == 'openai':
            return self._embed_openai(texts)
        raise ValueError(f'Unsupported embedding provider: {self.provider}')

    def embed_single(self, text: str) -> list[float]:
        """生成单个文本的 embedding."""
        return self.embed([text])[0]

    def health_status(self) -> dict:
        """Probe the provider instead of treating configuration as health."""
        base = {
            'provider': self.provider,
            'model': self.model,
            'dimension': self.dimension,
        }
        if not self.configured:
            return {**base, 'healthy': False, 'error': 'not configured'}
        if self.provider == 'local':
            return {'healthy': True, **base}

        try:
            if self.provider == 'ollama':
                response = requests.get(
                    f"{self.base_url.rstrip('/')}/api/tags",
                    timeout=HEALTH_TIMEOUT,
                )
            elif self.provider == 'openai':
                response = requests.get(
                    f"{self.base_url.rstrip('/')}/models",
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    timeout=HEALTH_TIMEOUT,
                )
            else:
                return {
                    **base,
                    'healthy': False,
                    'error': f'unsupported provider: {self.provider}',
                }
            response.raise_for_status()
        except Exception as exc:
            return {**base, 'healthy': False, 'error': str(exc)}
        return {'healthy': True, **base}

    def _embed_local(self, text: str) -> list[float]:
        """Create a stable lexical embedding using signed feature hashing."""
        normalized = unicodedata.normalize('NFKC', str(text or '')).lower()
        words = re.findall(
            r"[a-z0-9]+(?:[-'][a-z0-9]+)*|[\u3400-\u9fff]",
            normalized,
        )
        compact = ''.join(
            character
            for character in normalized
            if character.isalnum() or '\u3400' <= character <= '\u9fff'
        )

        features = [f'w:{word}' for word in words]
        features.extend(
            f'wb:{words[index]}_{words[index + 1]}'
            for index in range(len(words) - 1)
        )
        for width in (3, 4, 5):
            features.extend(
                f'c{width}:{compact[index:index + width]}'
                for index in range(max(0, len(compact) - width + 1))
            )

        vector = [0.0] * self.dimension
        for feature, count in Counter(features).items():
            digest = hashlib.blake2b(
                feature.encode('utf-8'),
                digest_size=8,
                person=b'weagent',
            ).digest()
            bucket = int.from_bytes(digest[:4], 'little') % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign * (1.0 + math.log(count))

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

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
