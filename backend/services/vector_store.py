"""
services/vector_store.py — Qdrant vector database interface.

Manages the lifecycle of document vectors inside a Qdrant collection:
    * Creating / ensuring the collection exists.
    * Upserting document chunks (with metadata) as named vectors.
    * Running filtered similarity searches at query time.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointStruct,
    VectorParams,
)

from config import settings
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Upper bound on how many document groups a grouped query may return.
MAX_GROUPS = 64

# Embedding API batch size — keeps requests within payload/rate limits.
EMBED_BATCH_SIZE = 100


class VectorStoreService:
    """CRUD + search interface for the Qdrant vector collection.

    Usage::

        store = VectorStoreService()
        store.upsert_documents(doc_id="abc", chunks=langchain_docs)
        results = store.similarity_search("what is X?", document_ids=["abc"])
    """

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        """Initialise the Qdrant client and ensure the collection exists.

        Args:
            embedding_service: An :class:`EmbeddingService` instance.  If
                ``None``, a default one is created.
        """
        self._embedding = embedding_service or EmbeddingService()
        self._collection = settings.QDRANT_COLLECTION_NAME

        # Initialise Qdrant client — in-memory or remote.
        if settings.QDRANT_URL == ":memory:":
            self._client = QdrantClient(location=":memory:")
            logger.info("Qdrant running in-memory mode")
        else:
            self._client = QdrantClient(url=settings.QDRANT_URL)
            logger.info("Qdrant connected to %s", settings.QDRANT_URL)

        self._ensure_collection()

    # ── Private helpers ───────────────────────────────────────────────────

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        collections = [
            c.name for c in self._client.get_collections().collections
        ]
        if self._collection not in collections:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._embedding.dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'", self._collection)

    # ── Public API ────────────────────────────────────────────────────────

    def upsert_documents(
        self,
        doc_id: str,
        chunks: list,  # List[langchain_core.documents.Document]
    ) -> int:
        """Embed and store document chunks in Qdrant.

        Chunks are embedded and upserted in batches of ``EMBED_BATCH_SIZE``
        so large PDFs don't produce one huge API request, and each chunk is
        stored as a separate point whose payload contains the full metadata
        needed for citation reconstruction.

        Args:
            doc_id: The parent document UUID.
            chunks: LangChain ``Document`` objects produced by
                    :meth:`DocumentProcessor.chunk_documents`.

        Returns:
            The number of points upserted.
        """
        points: List[PointStruct] = []

        # Embed + build points in batches to bound memory and request size.
        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[start : start + EMBED_BATCH_SIZE]
            texts = [chunk.page_content for chunk in batch]
            vectors = self._embedding.embed_texts(texts)

            for chunk, vector in zip(batch, vectors):
                point_id = str(uuid.uuid4())
                payload: Dict[str, Any] = {
                    "document_id": doc_id,
                    "filename": chunk.metadata.get("filename", ""),
                    "page_number": chunk.metadata.get("page_number", 0),
                    "text": chunk.page_content,
                }
                points.append(
                    PointStruct(id=point_id, vector=vector, payload=payload)
                )

            # Upsert this batch immediately — memory stays flat regardless
            # of how many chunks the PDF produced.
            self._client.upsert(
                collection_name=self._collection,
                points=points[start : start + EMBED_BATCH_SIZE],
            )

        logger.info("Upserted %d vectors for document %s", len(points), doc_id)
        return len(points)

    def similarity_search(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        per_document_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find the most relevant chunks for a given query.

        Retrieval is balanced across documents: Qdrant's grouped query
        returns the top ``per_document_k`` chunks per document, then the
        merged list is re-ranked by score and truncated to ``top_k``.
        This prevents a single long document from monopolising the context
        when querying multiple documents at once.

        Args:
            query:          Natural-language search query.
            document_ids:   Optional list of document UUIDs to restrict the
                            search to.  When ``None`` or empty, all documents
                            are searched.
            top_k:          Maximum number of results to return overall.
            per_document_k: Maximum number of chunks to take from each
                            document before the final re-rank.

        Returns:
            A list of dicts with keys ``text``, ``document_id``, ``filename``,
            ``page_number``, and ``score``.
        """
        query_vector = self._embedding.embed_query(query)

        # Build an optional filter to scope results to specific documents.
        search_filter: Optional[Filter] = None
        if document_ids:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=document_ids),
                    )
                ]
            )

        # Group by document so every doc gets a fair share of slots.
        groups = self._client.query_points_groups(
            collection_name=self._collection,
            query=query_vector,
            query_filter=search_filter,
            group_by="document_id",
            limit=len(document_ids) if document_ids else MAX_GROUPS,
            group_size=per_document_k,
            with_payload=True,
        )

        # Flatten groups, re-rank by score, and truncate to top_k.
        candidates: List[Dict[str, Any]] = []
        for group in groups.groups:
            for point in group.hits:
                payload = point.payload or {}
                candidates.append(
                    {
                        "text": payload.get("text", ""),
                        "document_id": payload.get("document_id", ""),
                        "filename": payload.get("filename", ""),
                        "page_number": payload.get("page_number", 0),
                        "score": point.score,
                    }
                )

        candidates.sort(key=lambda h: h["score"], reverse=True)
        hits = candidates[:top_k]

        logger.info(
            "Similarity search returned %d results (query=%r)",
            len(hits),
            query[:60],
        )
        return hits

    def delete_document(self, doc_id: str) -> None:
        """Remove all vectors belonging to a specific document.

        Args:
            doc_id: The UUID of the document whose vectors should be deleted.
        """
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=[doc_id]),
                    )
                ]
            ),
        )
        logger.info("Deleted vectors for document %s", doc_id)

    def count_vectors(self) -> int:
        """Return the total number of vectors in the collection.

        Returns:
            The point count reported by Qdrant, or 0 if unavailable.
        """
        try:
            info = self._client.get_collection(self._collection)
            return info.points_count or 0
        except Exception:
            logger.warning("Could not retrieve vector count from Qdrant")
            return 0
