"""
models/schemas.py — Pydantic v2 request / response schemas.

These schemas define the public API contract and are used by FastAPI for
automatic validation, serialisation, and OpenAPI doc generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Document Schemas ──────────────────────────────────────────────────────────


class DocumentResponse(BaseModel):
    """Returned after a successful document upload or when listing documents.

    Attributes:
        id:          Unique document identifier (UUID4).
        filename:    Original file name of the uploaded PDF.
        status:      Current processing status (``processing`` | ``completed`` | ``failed``).
        upload_time: UTC timestamp of when the upload was received.
        page_count:  Number of pages in the PDF (0 while still processing).
    """

    id: str
    filename: str
    status: str
    upload_time: Optional[datetime] = None
    page_count: int = 0
    chunk_count: int = 0

    model_config = {"from_attributes": True}


# ── Query Schemas ─────────────────────────────────────────────────────────────


class TokenUsage(BaseModel):
    """Token consumption reported by the LLM for a single call.

    Attributes:
        prompt_tokens:     Tokens consumed by the prompt (system + context + question).
        completion_tokens: Tokens consumed by the generated answer.
        total_tokens:      Sum of prompt + completion tokens.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class QueryRequest(BaseModel):
    """Payload sent by the frontend when the user asks a question.

    Attributes:
        query:        The natural-language question.
        document_ids: List of document UUIDs to search within.  If empty, all
                      documents are searched.
    """

    query: str = Field(..., min_length=1, max_length=2000)
    document_ids: List[str] = Field(default_factory=list)


class Citation(BaseModel):
    """A single source citation attached to an answer.

    Attributes:
        document_id:  UUID of the source document.
        filename:     Human-readable file name.
        page_number:  1-based page number where the evidence was found.
        text_snippet: Short excerpt of the relevant passage.
    """

    document_id: str
    filename: str
    page_number: int
    text_snippet: str


class QueryResponse(BaseModel):
    """Returned to the frontend after the RAG pipeline finishes.

    Attributes:
        answer:     The LLM-generated answer (may contain inline citation tags).
        citations:  Structured list of source citations.
        usage:      Token usage for this query (input/output/total tokens).
        latency_ms: Milliseconds spent on retrieval + generation.
        contributing_docs: Filenames of documents that supplied context.
    """

    answer: str
    citations: List[Citation] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    contributing_docs: List[str] = Field(default_factory=list)


class UsageStats(BaseModel):
    """Aggregated usage statistics across all answered queries.

    Attributes:
        total_queries:            Number of queries answered.
        total_prompt_tokens:      Sum of input tokens across all queries.
        total_completion_tokens:  Sum of output tokens across all queries.
        total_tokens:             Grand total of tokens consumed.
        avg_latency_ms:           Mean latency in milliseconds.
        documents:                Number of uploaded documents.
        vectors_stored:           Number of chunks currently in the vector store.
    """

    total_queries: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    documents: int = 0
    vectors_stored: int = 0
