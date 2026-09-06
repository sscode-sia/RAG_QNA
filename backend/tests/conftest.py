"""conftest.py — Shared pytest fixtures for backend unit tests.

Configures:
- sys.path manipulation to ensure backend modules are importable.
- In-memory SQLite database sessions with StaticPool.
- Synthetic PDF file generation using PyMuPDF.
- Isolated Mock Embedding and RAG services.
- FastAPI TestClient with isolated dependency injection overrides.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database
import api.routes
from database import Base
from main import app
from models.schemas import Citation, TokenUsage
from services.document_processor import DocumentProcessor
from services.embedding_service import EmbeddingService
from services.rag_engine import RAGEngine
from services.vector_store import VectorStoreService
from api.dependencies import (
    get_db,
    get_document_processor,
    get_embedding_service,
    get_rag_engine,
    get_vector_store,
)

# Test in-memory SQLite engine with StaticPool
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Create all database tables and patch database.SessionLocal for every test."""
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(api.routes, "SessionLocal", TestingSessionLocal)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_db_session(setup_test_db: None) -> Generator[Session, None, None]:
    """Provide an isolated, in-memory SQLite database session for tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def synthetic_pdf(tmp_path: Path) -> Path:
    """Generate a clean, multi-page synthetic PDF file for document processing tests."""
    pdf_path = tmp_path / "sample_test_doc.pdf"
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Retrieval-Augmented Generation (RAG) combines search retrieval with generative AI. "
        "It enhances language models by grounding them in external factual documents. "
        "This is the first page of our test documentation.",
        fontsize=11,
    )

    # Page 2
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "Vector databases such as Qdrant index semantic text embeddings. "
        "LangChain splits incoming text into manageable chunks with overlap. "
        "This is the second page of our test documentation.",
        fontsize=11,
    )

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Return a mocked EmbeddingService producing deterministic 3072-dim vectors."""
    mock = MagicMock(spec=EmbeddingService)
    mock.dimension = 3072

    def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 3072 for _ in texts]

    def fake_embed_query(query: str) -> list[float]:
        return [0.1] * 3072

    mock.embed_texts.side_effect = fake_embed_texts
    mock.embed_query.side_effect = fake_embed_query
    return mock


@pytest.fixture
def in_memory_vector_store(mock_embedding_service: MagicMock) -> VectorStoreService:
    """Return a real VectorStoreService backed by an in-memory Qdrant instance."""
    store = VectorStoreService(embedding_service=mock_embedding_service)
    return store


@pytest.fixture
def mock_rag_engine() -> MagicMock:
    """Return a mocked RAGEngine returning deterministic answer and citations."""
    mock = MagicMock(spec=RAGEngine)
    mock.generate_answer.return_value = (
        "RAG combines retrieval with generative AI [Doc: sample_test_doc.pdf, Page: 1].",
        [
            Citation(
                document_id="doc-12345",
                filename="sample_test_doc.pdf",
                page_number=1,
                text_snippet="RAG combines search retrieval with generative AI.",
            )
        ],
        TokenUsage(prompt_tokens=150, completion_tokens=30, total_tokens=180),
        ["sample_test_doc.pdf"],
    )
    return mock


@pytest.fixture
def test_client(
    mock_embedding_service: MagicMock,
    in_memory_vector_store: VectorStoreService,
    mock_rag_engine: MagicMock,
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with all dependencies overridden with mock/in-memory fixtures."""
    doc_processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)

    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
    app.dependency_overrides[get_vector_store] = lambda: in_memory_vector_store
    app.dependency_overrides[get_rag_engine] = lambda: mock_rag_engine
    app.dependency_overrides[get_document_processor] = lambda: doc_processor

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
