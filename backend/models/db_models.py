"""
models/db_models.py — SQLAlchemy ORM models.

Defines the persistent representation of documents stored in the relational
database (SQLite / PostgreSQL).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String
from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """Represents an uploaded PDF document and its processing status.

    Attributes:
        id:          Unique identifier (UUID4 string).
        filename:    Original name of the uploaded file.
        status:      Processing pipeline status — one of
                     ``processing``, ``completed``, or ``failed``.
        upload_time: UTC timestamp of when the file was received.
        page_count:  Total number of pages extracted from the PDF.
    """

    __tablename__ = "documents"

    id: str = Column(
        String,
        primary_key=True,
        default=_uuid,
    )
    filename: str = Column(String, nullable=False)
    status: str = Column(
        Enum("processing", "completed", "failed", name="document_status"),
        default="processing",
        nullable=False,
    )
    upload_time: datetime = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    page_count: int = Column(Integer, default=0)
    chunk_count: int = Column(Integer, default=0)

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id!r}, filename={self.filename!r}, "
            f"status={self.status!r})>"
        )


class QueryLog(Base):
    """One row per answered question, for usage/token statistics.

    Attributes:
        id:            Unique row ID.
        query_text:    The question the user asked.
        answer_chars:  Length of the generated answer.
        prompt_tokens:     Token count billed for input (context + question).
        completion_tokens: Token count billed for output (the answer).
        total_tokens:  prompt + completion tokens.
        latency_ms:    Wall-clock time for retrieval + generation.
        created_at:    UTC timestamp of the query.
    """

    __tablename__ = "query_logs"

    id: str = Column(String, primary_key=True, default=_uuid)
    query_text: str = Column(String, nullable=False)
    answer_chars: int = Column(Integer, default=0, nullable=False)
    prompt_tokens: int = Column(Integer, default=0, nullable=False)
    completion_tokens: int = Column(Integer, default=0, nullable=False)
    total_tokens: int = Column(Integer, default=0, nullable=False)
    latency_ms: float = Column(Float, default=0.0, nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<QueryLog(id={self.id!r}, total_tokens={self.total_tokens!r})>"
        )
