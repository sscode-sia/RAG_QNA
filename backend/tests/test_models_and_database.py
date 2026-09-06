"""test_models_and_database.py — Unit tests for SQLAlchemy ORM models and database setup."""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from database import init_db, engine
from models.db_models import Document, QueryLog


class TestDatabaseAndModels:
    """Test suite for database tables, models, and operations."""

    def test_init_db_idempotence(self) -> None:
        """Verify init_db executes safely without errors."""
        init_db()
        init_db()  # Verify idempotent repeated call

    def test_create_document_defaults(self, test_db_session: Session) -> None:
        """Verify Document creation with default UUID, status, timestamp, and counts."""
        doc = Document(filename="research_report.pdf")
        test_db_session.add(doc)
        test_db_session.commit()
        test_db_session.refresh(doc)

        assert doc.id is not None
        assert len(doc.id) == 36  # Standard UUID4 string length
        assert doc.filename == "research_report.pdf"
        assert doc.status == "processing"
        assert doc.page_count == 0
        assert doc.chunk_count == 0
        assert isinstance(doc.upload_time, datetime)
        assert "<Document(id=" in repr(doc)

    def test_update_document_status_and_metrics(self, test_db_session: Session) -> None:
        """Verify updating processing status, page_count, and chunk_count."""
        doc = Document(filename="manual.pdf")
        test_db_session.add(doc)
        test_db_session.commit()

        doc.status = "completed"
        doc.page_count = 12
        doc.chunk_count = 34
        test_db_session.commit()
        test_db_session.refresh(doc)

        assert doc.status == "completed"
        assert doc.page_count == 12
        assert doc.chunk_count == 34

    def test_create_query_log(self, test_db_session: Session) -> None:
        """Verify QueryLog creation, token metrics, and __repr__ formatting."""
        log_entry = QueryLog(
            query_text="What are vector embeddings?",
            answer_chars=250,
            prompt_tokens=180,
            completion_tokens=45,
            total_tokens=225,
            latency_ms=315.4,
        )
        test_db_session.add(log_entry)
        test_db_session.commit()
        test_db_session.refresh(log_entry)

        assert log_entry.id is not None
        assert log_entry.query_text == "What are vector embeddings?"
        assert log_entry.answer_chars == 250
        assert log_entry.prompt_tokens == 180
        assert log_entry.completion_tokens == 45
        assert log_entry.total_tokens == 225
        assert log_entry.latency_ms == 315.4
        assert isinstance(log_entry.created_at, datetime)
        assert "<QueryLog(id=" in repr(log_entry)

    def test_query_log_query_aggregation(self, test_db_session: Session) -> None:
        """Verify multiple QueryLog records can be summed and aggregated."""
        log1 = QueryLog(
            query_text="Q1",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=100.0,
        )
        log2 = QueryLog(
            query_text="Q2",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            latency_ms=200.0,
        )
        test_db_session.add_all([log1, log2])
        test_db_session.commit()

        logs = test_db_session.query(QueryLog).all()
        assert len(logs) == 2
        total_tokens = sum(l.total_tokens for l in logs)
        assert total_tokens == 450
