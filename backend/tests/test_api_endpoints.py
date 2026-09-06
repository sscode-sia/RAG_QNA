"""test_api_endpoints.py — Integration and endpoint unit tests for FastAPI routes."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest

from models.db_models import Document, QueryLog
from api.routes import _process_document_background


class TestAPIEndpoints:
    """Test suite for FastAPI REST API endpoints."""

    def test_health_check(self, test_client: TestClient) -> None:
        """Verify GET /health returns status ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_upload_pdf_success(
        self,
        test_client: TestClient,
        test_db_session: Session,
        tmp_path: Path,
    ) -> None:
        """Verify POST /api/upload accepts valid PDF and creates DB record."""
        pdf_content = b"%PDF-1.4 dummy pdf content stream"
        files = {
            "file": ("test_upload.pdf", io.BytesIO(pdf_content), "application/pdf")
        }

        response = test_client.post("/api/upload", files=files)
        assert response.status_code == 202
        data = response.json()
        assert data["filename"] == "test_upload.pdf"
        assert data["status"] == "processing"
        assert "id" in data

        # Check DB record exists
        doc = test_db_session.query(Document).filter(Document.id == data["id"]).first()
        assert doc is not None
        assert doc.filename == "test_upload.pdf"

    def test_upload_non_pdf_fails(self, test_client: TestClient) -> None:
        """Verify POST /api/upload rejects non-PDF file extensions with 400."""
        text_content = b"This is a text file."
        files = {
            "file": ("notes.txt", io.BytesIO(text_content), "text/plain")
        }

        response = test_client.post("/api/upload", files=files)
        assert response.status_code == 400
        assert "Only PDF files are accepted" in response.json()["detail"]

    def test_list_documents(
        self,
        test_client: TestClient,
        test_db_session: Session,
    ) -> None:
        """Verify GET /api/documents returns documents ordered by upload time."""
        doc1 = Document(filename="first.pdf", status="completed", page_count=2)
        doc2 = Document(filename="second.pdf", status="processing", page_count=0)
        test_db_session.add_all([doc1, doc2])
        test_db_session.commit()

        response = test_client.get("/api/documents")
        assert response.status_code == 200
        docs = response.json()
        assert len(docs) == 2
        filenames = [d["filename"] for d in docs]
        assert "first.pdf" in filenames
        assert "second.pdf" in filenames

    def test_query_documents_success(
        self,
        test_client: TestClient,
        test_db_session: Session,
    ) -> None:
        """Verify POST /api/query runs RAG pipeline and logs token usage."""
        payload = {
            "query": "What is RAG?",
            "document_ids": [],
        }

        response = test_client.post("/api/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "usage" in data
        assert data["usage"]["total_tokens"] > 0
        assert "latency_ms" in data

        # Verify QueryLog was recorded in DB
        logs = test_db_session.query(QueryLog).all()
        assert len(logs) == 1
        assert logs[0].query_text == "What is RAG?"

    def test_query_documents_validation_error(self, test_client: TestClient) -> None:
        """Verify POST /api/query returns 422 Unprocessable Entity on empty query."""
        payload = {"query": ""}
        response = test_client.post("/api/query", json=payload)
        assert response.status_code == 422

    def test_get_stats(
        self,
        test_client: TestClient,
        test_db_session: Session,
    ) -> None:
        """Verify GET /api/stats computes aggregate counts, tokens, and latency."""
        doc = Document(filename="stats_doc.pdf", status="completed", page_count=5)
        log = QueryLog(
            query_text="Sample Query",
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            latency_ms=250.0,
        )
        test_db_session.add_all([doc, log])
        test_db_session.commit()

        response = test_client.get("/api/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_queries"] == 1
        assert stats["total_prompt_tokens"] == 100
        assert stats["total_completion_tokens"] == 20
        assert stats["total_tokens"] == 120
        assert stats["avg_latency_ms"] == 250.0
        assert stats["documents"] == 1

    def test_delete_document_success(
        self,
        test_client: TestClient,
        test_db_session: Session,
    ) -> None:
        """Verify DELETE /api/documents/{id} deletes DB record and returns 204."""
        doc = Document(filename="to_delete.pdf")
        test_db_session.add(doc)
        test_db_session.commit()
        doc_id = doc.id

        response = test_client.delete(f"/api/documents/{doc_id}")
        assert response.status_code == 204

        # Verify deleted in DB
        found = test_db_session.query(Document).filter(Document.id == doc_id).first()
        assert found is None

    def test_delete_document_not_found(self, test_client: TestClient) -> None:
        """Verify DELETE /api/documents/{id} returns 404 for non-existent document ID."""
        response = test_client.delete("/api/documents/non-existent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_process_document_background_task(
        self,
        test_db_session: Session,
        synthetic_pdf: Path,
    ) -> None:
        """Verify background processing extracts pages, upserts chunks, and updates DB status."""
        doc = Document(filename="sample_test_doc.pdf", status="processing")
        test_db_session.add(doc)
        test_db_session.commit()
        doc_id = doc.id

        mock_processor = MagicMock()
        mock_processor.extract_text.return_value = [{"page_number": 1, "text": "Content"}]
        mock_processor.chunk_documents.return_value = [MagicMock()]

        mock_store = MagicMock()
        mock_store.upsert_documents.return_value = 1

        # Patch SessionLocal inside _process_document_background to use test_db_session
        from unittest.mock import patch
        with patch("database.SessionLocal", return_value=test_db_session):
            _process_document_background(
                doc_id=doc_id,
                file_path=synthetic_pdf,
                filename="sample_test_doc.pdf",
                processor=mock_processor,
                vector_store=mock_store,
            )

        updated_doc = test_db_session.query(Document).filter(Document.id == doc_id).first()
        assert updated_doc.status == "completed"
        assert updated_doc.page_count == 1
        assert updated_doc.chunk_count == 1
