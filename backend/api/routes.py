"""
api/routes.py — FastAPI router with all REST endpoints.

Endpoints:
    POST   /upload           Upload a PDF and ingest it into the vector store.
    POST   /query            Ask a question over one or more documents.
    GET    /documents         List all uploaded documents.
    DELETE /documents/{id}   Remove a document and its vectors.
"""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.db_models import Document, QueryLog
from models.schemas import (
    DocumentResponse,
    QueryRequest,
    QueryResponse,
    UsageStats,
)
from api.dependencies import (
    get_db,
    get_document_processor,
    get_rag_engine,
    get_vector_store,
)
from services.document_processor import DocumentProcessor
from services.rag_engine import RAGEngine
from services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Upload ────────────────────────────────────────────────────────────────────


def _process_document_background(
    doc_id: str,
    file_path: Path,
    filename: str,
    processor: DocumentProcessor,
    vector_store: VectorStoreService,
) -> None:
    """Background task: parse PDF → chunk → embed → upsert → update DB status.

    This runs outside the request lifecycle so that large PDFs don't block the
    upload response.
    """
    from database import SessionLocal

    db = SessionLocal()
    doc = None
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc is None:
            logger.error("Document %s not found in DB during background processing", doc_id)
            return

        # Extract & chunk
        pages = processor.extract_text(str(file_path))
        chunks = processor.chunk_documents(pages, doc_id=doc_id, filename=filename)

        # Upsert into vector store
        n_chunks = vector_store.upsert_documents(doc_id=doc_id, chunks=chunks)

        # Update DB record
        doc.status = "completed"
        doc.page_count = len(pages)
        doc.chunk_count = n_chunks
        db.commit()
        logger.info(
            "Document %s processed successfully (%d pages, %d chunks)",
            doc_id,
            len(pages),
            n_chunks,
        )

    except Exception:
        logger.exception("Failed to process document %s", doc_id)
        if doc is not None:
            doc.status = "failed"
            db.commit()
    finally:
        db.close()


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a PDF document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    processor: DocumentProcessor = Depends(get_document_processor),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> DocumentResponse:
    """Accept a PDF upload, save it to disk, and kick off background processing.

    The response is returned immediately with ``status='processing'``.  The
    client can poll ``GET /documents`` to check when processing completes.

    Args:
        file: The uploaded PDF file (multipart form-data).

    Returns:
        A :class:`DocumentResponse` with the assigned document ID.

    Raises:
        HTTPException 400: If the file is not a PDF.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    # Persist to disk
    doc_id = str(uuid.uuid4())
    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}.pdf"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {exc}",
        ) from exc

    # Create DB record
    document = Document(id=doc_id, filename=file.filename, status="processing")
    db.add(document)
    db.commit()
    db.refresh(document)

    # Schedule background processing
    background_tasks.add_task(
        _process_document_background,
        doc_id=doc_id,
        file_path=file_path,
        filename=file.filename,
        processor=processor,
        vector_store=vector_store,
    )

    return DocumentResponse.model_validate(document)


# ── Query ─────────────────────────────────────────────────────────────────────


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question about uploaded documents",
)
async def query_documents(
    request: QueryRequest,
    vector_store: VectorStoreService = Depends(get_vector_store),
    rag_engine: RAGEngine = Depends(get_rag_engine),
) -> QueryResponse:
    """Run the full RAG pipeline: retrieve context → generate cited answer.

    Also measures latency and records token usage, which is returned with the
    answer and persisted for the aggregate ``/stats`` endpoint.

    Args:
        request: Contains the natural-language *query* and optional
                  *document_ids* to restrict the search.

    Returns:
        A :class:`QueryResponse` with the answer, citations, token usage,
        and latency.

    Raises:
        HTTPException 500: If the LLM call or vector search fails.
    """
    started = time.perf_counter()
    try:
        # Retrieve relevant chunks
        context_chunks = vector_store.similarity_search(
            query=request.query,
            document_ids=request.document_ids if request.document_ids else None,
            top_k=5,
        )

        # Generate answer
        answer, citations, usage, contributing_docs = rag_engine.generate_answer(
            query=request.query,
            context_chunks=context_chunks,
        )

        latency_ms = (time.perf_counter() - started) * 1000

        # Persist usage log for aggregate stats (best-effort).
        try:
            db_log = SessionLocal()
            try:
                db_log.add(
                    QueryLog(
                        query_text=request.query[:500],
                        answer_chars=len(answer),
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        total_tokens=usage.total_tokens,
                        latency_ms=latency_ms,
                    )
                )
                db_log.commit()
            finally:
                db_log.close()
        except Exception:
            logger.warning("Could not persist query usage log", exc_info=True)

        return QueryResponse(
            answer=answer,
            citations=citations,
            usage=usage,
            latency_ms=round(latency_ms, 1),
            contributing_docs=contributing_docs,
        )

    except RuntimeError as exc:
        logger.exception("RAG pipeline error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {exc}",
        ) from exc


# ── List Documents ────────────────────────────────────────────────────────────


@router.get(
    "/documents",
    response_model=List[DocumentResponse],
    summary="List all uploaded documents",
)
async def list_documents(
    db: Session = Depends(get_db),
) -> List[DocumentResponse]:
    """Return a list of every document that has been uploaded.

    Returns:
        A list of :class:`DocumentResponse` objects ordered by upload time
        (newest first).
    """
    docs = (
        db.query(Document)
        .order_by(Document.upload_time.desc())
        .all()
    )
    return [DocumentResponse.model_validate(d) for d in docs]


# ── Usage Statistics ──────────────────────────────────────────────────────────


@router.get(
    "/stats",
    response_model=UsageStats,
    summary="Aggregated usage & token statistics",
)
async def get_stats(
    db: Session = Depends(get_db),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> UsageStats:
    """Return aggregated token usage and system statistics.

    Aggregates the ``query_logs`` table (queries answered, prompt /
    completion / total tokens, mean latency) plus live counters for
    uploaded documents and vectors in the store.

    Returns:
        A :class:`UsageStats` payload for the sidebar usage panel.
    """
    row = (
        db.query(
            func.count(QueryLog.id),
            func.coalesce(func.sum(QueryLog.prompt_tokens), 0),
            func.coalesce(func.sum(QueryLog.completion_tokens), 0),
            func.coalesce(func.sum(QueryLog.total_tokens), 0),
            func.coalesce(func.avg(QueryLog.latency_ms), 0.0),
        )
        .one()
    )
    doc_count = db.query(func.count(Document.id)).scalar() or 0

    return UsageStats(
        total_queries=row[0] or 0,
        total_prompt_tokens=row[1] or 0,
        total_completion_tokens=row[2] or 0,
        total_tokens=row[3] or 0,
        avg_latency_ms=round(float(row[4] or 0.0), 1),
        documents=doc_count,
        vectors_stored=vector_store.count_vectors(),
    )


# ── Delete Document ───────────────────────────────────────────────────────────


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and its vectors",
)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> None:
    """Remove a document record from the database and purge its vectors.

    Args:
        doc_id: The UUID of the document to delete.

    Raises:
        HTTPException 404: If no document with that ID exists.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found.",
        )

    # Remove vectors from Qdrant
    try:
        vector_store.delete_document(doc_id)
    except Exception:
        logger.warning("Could not delete vectors for %s (may not exist)", doc_id)

    # Remove file from disk
    file_path = settings.UPLOAD_DIR / f"{doc_id}.pdf"
    if file_path.exists():
        file_path.unlink()

    # Remove DB record
    db.delete(doc)
    db.commit()
    logger.info("Deleted document %s", doc_id)
