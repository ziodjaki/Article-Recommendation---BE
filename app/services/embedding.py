from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from app.config import Settings

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if settings.gemini_api_key and genai is not None:
            self._client = genai.Client(api_key=settings.gemini_api_key)

    def _source_signature(self, journals: list[dict]) -> str:
        digest = hashlib.sha256()
        for item in journals:
            digest.update(item["id"].encode("utf-8"))
            digest.update(item["full_text"].encode("utf-8"))
        return digest.hexdigest()

    def _extract_vector(self, response: Any) -> list[float]:
        if response is None:
            return []

        if hasattr(response, "embeddings") and response.embeddings:
            first = response.embeddings[0]
            if hasattr(first, "values"):
                return list(first.values)
            if isinstance(first, dict) and "values" in first:
                return list(first["values"])

        if isinstance(response, dict):
            items = response.get("embeddings") or []
            if items and isinstance(items[0], dict) and "values" in items[0]:
                return list(items[0]["values"])

        return []

    def _embed_with_gemini(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            return []

        vectors: list[list[float]] = []
        for text in texts:
            response = self._client.models.embed_content(
                model=self.settings.gemini_embedding_model,
                contents=text,
            )
            vector = self._extract_vector(response)
            if not vector:
                raise RuntimeError("Empty embedding vector from Gemini API")
            vectors.append(vector)
        return vectors

    def _embed_with_hash(self, texts: list[str], dim: int = 256) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = np.zeros(dim, dtype=float)
            tokens = [tok for tok in text.lower().split() if tok]
            for token in tokens:
                h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                idx = h % dim
                sign = 1.0 if (h % 2 == 0) else -1.0
                vec[idx] += sign

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec.tolist())
        return vectors

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            vectors = self._embed_with_gemini(texts)
            if vectors:
                return vectors
        except Exception:
            pass

        return self._embed_with_hash(texts)

    def ensure_journal_embeddings(self, journals: list[dict], cache_path: Path) -> dict[str, list[float]]:
        signature = self._source_signature(journals)

        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            same_model = data.get("embedding_model") == self.settings.gemini_embedding_model
            same_signature = data.get("source_signature") == signature
            if same_model and same_signature:
                return {item["journal_id"]: item["vector"] for item in data.get("items", [])}

        texts = [item["full_text"] for item in journals]
        vectors = self.embed_texts(texts)
        mapping = {journal["id"]: vector for journal, vector in zip(journals, vectors)}

        payload = {
            "embedding_model": self.settings.gemini_embedding_model,
            "source_signature": signature,
            "items": [
                {"journal_id": journal_id, "vector": vector}
                for journal_id, vector in mapping.items()
            ],
        }

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return mapping


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))

    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
