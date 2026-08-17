from __future__ import annotations

from abc import ABC, abstractmethod
from itertools import islice

from app.core.config import Settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def _batched(items: list[str], batch_size: int) -> list[list[str]]:
    batches: list[list[str]] = []
    iterator = iter(items)
    while batch := list(islice(iterator, batch_size)):
        batches.append(batch)
    return batches


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for batch in _batched(texts, 100):
            for text in batch:
                response = self._client.models.embed_content(model=self._model, contents=text)
                vectors = getattr(response, "embeddings", None)
                if vectors:
                    embeddings.extend([list(vector.values) for vector in vectors])
                    continue

                vector = getattr(response, "embedding", None)
                if vector is not None:
                    embeddings.append(list(vector.values))
                    continue

                raise RuntimeError("Gemini embedding response did not include an embedding")
        return embeddings


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    return GeminiEmbeddingProvider(api_key=settings.gemini_api_key, model=settings.gemini_embedding_model)
