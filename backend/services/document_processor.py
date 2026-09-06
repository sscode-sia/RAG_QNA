"""
services/document_processor.py — PDF parsing and text chunking.

Responsibilities:
    1. Extract raw text + page-level metadata from uploaded PDFs using PyMuPDF.
    2. Split extracted text into overlapping chunks suitable for embedding,
       using LangChain's ``RecursiveCharacterTextSplitter``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument

from config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles the full pipeline from raw PDF file to embeddable text chunks.

    Usage::

        processor = DocumentProcessor()
        pages = processor.extract_text("uploads/paper.pdf")
        chunks = processor.chunk_documents(pages, doc_id="abc-123", filename="paper.pdf")
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        """Initialise the processor with configurable chunk parameters.

        Args:
            chunk_size:    Maximum characters per chunk (default from settings).
            chunk_overlap: Overlapping characters between consecutive chunks.
        """
        self._chunk_size = chunk_size or settings.CHUNK_SIZE
        self._chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    # ── Public API ────────────────────────────────────────────────────────

    def extract_text(self, file_path: str | Path) -> List[Dict[str, Any]]:
        """Extract text from every page of a PDF file.

        Args:
            file_path: Absolute or relative path to the PDF on disk.

        Returns:
            A list of dicts, each with keys ``page_number`` (1-based) and
            ``text`` (the raw extracted text for that page).

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            ValueError:        If the file cannot be opened as a PDF.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        pages: List[Dict[str, Any]] = []

        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            raise ValueError(f"Cannot open file as PDF: {exc}") from exc

        try:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text.strip():
                    pages.append({"page_number": page_num, "text": text})
            logger.info("Extracted %d non-empty pages from %s", len(pages), path.name)
        finally:
            doc.close()

        return pages

    def chunk_documents(
        self,
        pages: List[Dict[str, Any]],
        doc_id: str,
        filename: str,
    ) -> List[LCDocument]:
        """Split page-level text into smaller, overlapping chunks.

        Each resulting :class:`~langchain_core.documents.Document` carries
        metadata including the source ``document_id``, ``filename``, and
        ``page_number`` so that citations can be reconstructed later.

        Args:
            pages:    Output of :meth:`extract_text`.
            doc_id:   UUID of the parent document (for citation linking).
            filename: Original PDF filename (for human-readable citations).

        Returns:
            A flat list of LangChain ``Document`` objects ready for embedding.
        """
        all_chunks: List[LCDocument] = []

        for page in pages:
            page_docs = self._splitter.create_documents(
                texts=[page["text"]],
                metadatas=[
                    {
                        "document_id": doc_id,
                        "filename": filename,
                        "page_number": page["page_number"],
                    }
                ],
            )
            all_chunks.extend(page_docs)

        logger.info(
            "Created %d chunks from %d pages (doc_id=%s)",
            len(all_chunks),
            len(pages),
            doc_id,
        )
        return all_chunks
