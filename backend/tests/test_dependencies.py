"""test_dependencies.py — Unit tests for FastAPI dependency providers in api/dependencies.py."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from api.dependencies import (
    get_db,
    get_document_processor,
    get_embedding_service,
    get_rag_engine,
    get_vector_store,
)


class TestDependencies:
    """Test suite for dependency injection providers."""

    def test_get_db_generator(self) -> None:
        """Verify get_db yields a database session and closes it on exit."""
        gen = get_db()
        db = next(gen)
        assert db is not None
        with pytest.raises(StopIteration):
            next(gen)

    def test_get_embedding_service_singleton(self) -> None:
        """Verify get_embedding_service lazily creates and caches instance."""
        with patch("api.dependencies.EmbeddingService") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst

            # Reset singleton cache for test isolation
            import api.dependencies
            api.dependencies._embedding_service = None

            svc1 = get_embedding_service()
            svc2 = get_embedding_service()
            assert svc1 is svc2
            assert mock_cls.call_count == 1

    def test_get_vector_store_singleton(self) -> None:
        """Verify get_vector_store lazily creates and caches instance."""
        with patch("api.dependencies.VectorStoreService") as mock_cls, \
             patch("api.dependencies.get_embedding_service"):
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst

            import api.dependencies
            api.dependencies._vector_store = None

            store1 = get_vector_store()
            store2 = get_vector_store()
            assert store1 is store2
            assert mock_cls.call_count == 1

    def test_get_rag_engine_singleton(self) -> None:
        """Verify get_rag_engine lazily creates and caches instance."""
        with patch("api.dependencies.RAGEngine") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value = mock_inst

            import api.dependencies
            api.dependencies._rag_engine = None

            engine1 = get_rag_engine()
            engine2 = get_rag_engine()
            assert engine1 is engine2
            assert mock_cls.call_count == 1

    def test_get_document_processor_singleton(self) -> None:
        """Verify get_document_processor lazily creates and caches instance."""
        import api.dependencies
        api.dependencies._doc_processor = None

        proc1 = get_document_processor()
        proc2 = get_document_processor()
        assert proc1 is proc2
