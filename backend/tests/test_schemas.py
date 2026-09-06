"""test_schemas.py — Unit tests for Pydantic models in models/schemas.py."""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from models.schemas import (
    Citation,
    DocumentResponse,
    QueryRequest,
    QueryResponse,
    TokenUsage,
    UsageStats,
)


class TestDocumentResponse:
    """Test suite for DocumentResponse schema."""

    def test_valid_document_response(self) -> None:
        """Verify initialization with required fields and defaults."""
        now = datetime.now(timezone.utc)
        doc = DocumentResponse(
            id="doc-abc-123",
            filename="sample.pdf",
            status="completed",
            upload_time=now,
            page_count=5,
            chunk_count=12,
        )
        assert doc.id == "doc-abc-123"
        assert doc.filename == "sample.pdf"
        assert doc.status == "completed"
        assert doc.page_count == 5
        assert doc.chunk_count == 12
        assert doc.upload_time == now

    def test_default_counts(self) -> None:
        """Verify default values for page_count, chunk_count, and upload_time."""
        doc = DocumentResponse(
            id="doc-1",
            filename="test.pdf",
            status="processing",
        )
        assert doc.page_count == 0
        assert doc.chunk_count == 0
        assert doc.upload_time is None

    def test_from_attributes(self) -> None:
        """Verify ORM object compatibility via from_attributes."""
        class MockORM:
            id = "orm-id-456"
            filename = "orm_file.pdf"
            status = "completed"
            upload_time = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
            page_count = 10
            chunk_count = 25

        doc = DocumentResponse.model_validate(MockORM())
        assert doc.id == "orm-id-456"
        assert doc.filename == "orm_file.pdf"
        assert doc.status == "completed"
        assert doc.page_count == 10
        assert doc.chunk_count == 25


class TestQueryRequest:
    """Test suite for QueryRequest schema validation."""

    def test_valid_query_request(self) -> None:
        """Verify valid query string and document IDs."""
        req = QueryRequest(query="What is RAG?", document_ids=["id-1", "id-2"])
        assert req.query == "What is RAG?"
        assert req.document_ids == ["id-1", "id-2"]

    def test_default_empty_document_ids(self) -> None:
        """Verify document_ids defaults to empty list."""
        req = QueryRequest(query="Explain Qdrant.")
        assert req.query == "Explain Qdrant."
        assert req.document_ids == []

    def test_empty_query_fails(self) -> None:
        """Verify empty query string triggers validation error (min_length=1)."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_excessive_query_length_fails(self) -> None:
        """Verify query string exceeding 2000 chars triggers validation error."""
        oversized_query = "x" * 2001
        with pytest.raises(ValidationError):
            QueryRequest(query=oversized_query)


class TestCitation:
    """Test suite for Citation schema."""

    def test_citation_structure(self) -> None:
        """Verify correct instantiation of Citation."""
        cite = Citation(
            document_id="doc-999",
            filename="paper.pdf",
            page_number=3,
            text_snippet="Semantic search retrieves relevant context.",
        )
        assert cite.document_id == "doc-999"
        assert cite.filename == "paper.pdf"
        assert cite.page_number == 3
        assert cite.text_snippet == "Semantic search retrieves relevant context."

    def test_missing_required_fields_fails(self) -> None:
        """Verify missing fields raise ValidationError."""
        with pytest.raises(ValidationError):
            Citation(document_id="doc-999", filename="paper.pdf")  # missing page & snippet


class TestTokenUsageAndQueryResponse:
    """Test suite for TokenUsage and QueryResponse schemas."""

    def test_token_usage_defaults(self) -> None:
        """Verify default token counts are zero."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_query_response_serialization(self) -> None:
        """Verify QueryResponse complete object construction."""
        resp = QueryResponse(
            answer="Here is the retrieved answer [Doc: doc.pdf, Page: 1].",
            citations=[
                Citation(
                    document_id="id-1",
                    filename="doc.pdf",
                    page_number=1,
                    text_snippet="Test excerpt",
                )
            ],
            usage=TokenUsage(prompt_tokens=100, completion_tokens=25, total_tokens=125),
            latency_ms=145.8,
            contributing_docs=["doc.pdf"],
        )
        assert resp.answer.startswith("Here is the retrieved answer")
        assert len(resp.citations) == 1
        assert resp.usage.total_tokens == 125
        assert resp.latency_ms == 145.8
        assert resp.contributing_docs == ["doc.pdf"]


class TestUsageStats:
    """Test suite for UsageStats schema."""

    def test_usage_stats_defaults(self) -> None:
        """Verify default aggregate metrics."""
        stats = UsageStats()
        assert stats.total_queries == 0
        assert stats.total_tokens == 0
        assert stats.avg_latency_ms == 0.0
        assert stats.documents == 0
        assert stats.vectors_stored == 0

    def test_usage_stats_custom_values(self) -> None:
        """Verify populated aggregate metrics."""
        stats = UsageStats(
            total_queries=15,
            total_prompt_tokens=1500,
            total_completion_tokens=450,
            total_tokens=1950,
            avg_latency_ms=310.5,
            documents=4,
            vectors_stored=42,
        )
        assert stats.total_queries == 15
        assert stats.total_tokens == 1950
        assert stats.avg_latency_ms == 310.5
        assert stats.documents == 4
        assert stats.vectors_stored == 42
