"""test_vector_store.py — Unit tests for Qdrant vector database interface and embeddings."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from langchain_core.documents import Document as LCDocument
import pytest

from services.embedding_service import EmbeddingService
from services.vector_store import VectorStoreService


class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    def test_dimensions_lookup(self) -> None:
        """Verify dimension property for supported and default models."""
        with patch("services.embedding_service.GoogleGenerativeAIEmbeddings"):
            svc1 = EmbeddingService(model="models/gemini-embedding-001")
            assert svc1.dimension == 3072

            svc2 = EmbeddingService(model="models/gemini-embedding-2-preview")
            assert svc2.dimension == 3072

            svc_custom = EmbeddingService(model="custom-model")
            assert svc_custom.dimension == 3072

    def test_embed_texts_and_query(self) -> None:
        """Verify embed_texts and embed_query delegate to the underlying client."""
        with patch("services.embedding_service.GoogleGenerativeAIEmbeddings") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.embed_documents.return_value = [[0.1] * 3072, [0.2] * 3072]
            mock_instance.embed_query.return_value = [0.3] * 3072
            mock_client_cls.return_value = mock_instance

            svc = EmbeddingService()
            docs = svc.embed_texts(["hello", "world"])
            assert len(docs) == 2
            assert len(docs[0]) == 3072

            query_vec = svc.embed_query("test query")
            assert len(query_vec) == 3072
            assert query_vec[0] == 0.3


class TestVectorStoreService:
    """Test suite for VectorStoreService with in-memory Qdrant client."""

    def test_collection_creation(self, mock_embedding_service: MagicMock) -> None:
        """Verify in-memory vector store creates collection on initialization."""
        store = VectorStoreService(embedding_service=mock_embedding_service)
        assert store.count_vectors() == 0

    def test_upsert_and_count_vectors(
        self,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Verify upserting document chunks into Qdrant."""
        store = VectorStoreService(embedding_service=mock_embedding_service)
        chunks = [
            LCDocument(
                page_content=f"Chunk content line {i}",
                metadata={"filename": "sample.pdf", "page_number": 1},
            )
            for i in range(5)
        ]

        count = store.upsert_documents(doc_id="doc-uuid-1", chunks=chunks)
        assert count == 5
        assert store.count_vectors() == 5

    def test_similarity_search_all_docs(
        self,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Verify similarity search returns results formatted with score and metadata."""
        store = VectorStoreService(embedding_service=mock_embedding_service)
        chunks = [
            LCDocument(
                page_content="LangChain handles document chunking.",
                metadata={"filename": "langchain.pdf", "page_number": 1},
            ),
            LCDocument(
                page_content="Qdrant provides vector similarity search.",
                metadata={"filename": "qdrant.pdf", "page_number": 2},
            ),
        ]
        store.upsert_documents(doc_id="doc-1", chunks=chunks)

        results = store.similarity_search(query="How does search work?", top_k=2)
        assert len(results) == 2
        first = results[0]
        assert "text" in first
        assert "document_id" in first
        assert "filename" in first
        assert "page_number" in first
        assert "score" in first

    def test_similarity_search_filtered_by_doc_id(
        self,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Verify similarity search with document_ids filter restricts results."""
        store = VectorStoreService(embedding_service=mock_embedding_service)
        chunks1 = [
            LCDocument(
                page_content="Content from document A",
                metadata={"filename": "doc_a.pdf", "page_number": 1},
            )
        ]
        chunks2 = [
            LCDocument(
                page_content="Content from document B",
                metadata={"filename": "doc_b.pdf", "page_number": 1},
            )
        ]
        store.upsert_documents(doc_id="id-a", chunks=chunks1)
        store.upsert_documents(doc_id="id-b", chunks=chunks2)

        results_a = store.similarity_search(
            query="test", document_ids=["id-a"], top_k=5
        )
        assert all(r["document_id"] == "id-a" for r in results_a)

    def test_delete_document(
        self,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Verify deleting a document removes its points from the collection."""
        store = VectorStoreService(embedding_service=mock_embedding_service)
        chunks = [
            LCDocument(
                page_content="Temporary content to be deleted",
                metadata={"filename": "temp.pdf", "page_number": 1},
            )
        ]
        store.upsert_documents(doc_id="to-delete", chunks=chunks)
        assert store.count_vectors() == 1

        store.delete_document("to-delete")
        assert store.count_vectors() == 0

    def test_count_vectors_handles_exception(
        self,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Verify count_vectors returns 0 when an unexpected exception occurs."""
        store = VectorStoreService(embedding_service=mock_embedding_service)
        store._client.get_collection = MagicMock(side_effect=Exception("Qdrant error"))
        assert store.count_vectors() == 0
