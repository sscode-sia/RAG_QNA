"""
api/dependencies.py — FastAPI dependency injection functions.

Each function is a generator that yields a service or resource and cleans up
after the request completes.  Endpoints use ``Depends(...)`` to receive these
instances automatically.
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from database import SessionLocal
from services.document_processor import DocumentProcessor
from services.embedding_service import EmbeddingService
from services.rag_engine import RAGEngine
from services.vector_store import VectorStoreService

# ── Singleton-style caches (lazy-initialised on first request) ────────────────
_embedding_service: EmbeddingService | None = None
_vector_store: VectorStoreService | None = None
_rag_engine: RAGEngine | None = None
_doc_processor: DocumentProcessor | None = None


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it when the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_embedding_service() -> EmbeddingService:
    """Return the singleton ``EmbeddingService``."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_vector_store() -> VectorStoreService:
    """Return the singleton ``VectorStoreService``."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService(
            embedding_service=get_embedding_service()
        )
    return _vector_store


def get_rag_engine() -> RAGEngine:
    """Return the singleton ``RAGEngine``."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine


def get_document_processor() -> DocumentProcessor:
    """Return the singleton ``DocumentProcessor``."""
    global _doc_processor
    if _doc_processor is None:
        _doc_processor = DocumentProcessor()
    return _doc_processor
