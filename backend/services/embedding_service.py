"""
services/embedding_service.py — Google Gemini embedding wrapper.

Provides a thin, reusable wrapper around the Google Generative AI embeddings
API so that the rest of the codebase can treat embedding as a simple function
call without worrying about model names or API keys.
"""

from __future__ import annotations

import logging
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates vector embeddings for text using Google's Gemini API.

    Usage::

        svc = EmbeddingService()
        vectors = svc.embed_texts(["hello world", "another sentence"])
        query_vec = svc.embed_query("what is the meaning of life?")
    """

    def __init__(self, model: str | None = None) -> None:
        """Initialise the embedding client.

        Args:
            model: Google embedding model name.  Defaults to the value in
                   ``settings.EMBEDDING_MODEL`` (``models/text-embedding-004``).
        """
        self._model_name = model or settings.EMBEDDING_MODEL
        self._client = GoogleGenerativeAIEmbeddings(
            model=self._model_name,
            google_api_key=settings.GOOGLE_API_KEY,
        )
        logger.info("EmbeddingService initialised with model=%s", self._model_name)

    # ── Public API ────────────────────────────────────────────────────────

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts.

        Args:
            texts: A list of plain-text strings.

        Returns:
            A list of embedding vectors (each a list of floats), in the same
            order as the input.
        """
        return self._client.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """Embed a single query string.

        Args:
            query: The search/question string.

        Returns:
            A single embedding vector.
        """
        return self._client.embed_query(query)

    @property
    def dimension(self) -> int:
        """Return the dimensionality of the chosen model's output vectors.

        For ``models/gemini-embedding-001`` this is 3072.
        """
        _dims = {
            "models/gemini-embedding-001": 3072,
            "models/gemini-embedding-2-preview": 3072,
            "models/gemini-embedding-2": 3072,
        }
        return _dims.get(self._model_name, 3072)
