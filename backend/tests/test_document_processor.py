"""test_document_processor.py — Unit tests for PDF parsing and text chunking."""

from __future__ import annotations

from pathlib import Path
import fitz
import pytest

from services.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test suite for DocumentProcessor service."""

    def test_extract_text_from_valid_pdf(self, synthetic_pdf: Path) -> None:
        """Verify successful extraction of text from a multi-page PDF."""
        processor = DocumentProcessor()
        pages = processor.extract_text(synthetic_pdf)

        assert len(pages) == 2
        assert pages[0]["page_number"] == 1
        assert "Retrieval-Augmented Generation" in pages[0]["text"]
        assert pages[1]["page_number"] == 2
        assert "Vector databases such as Qdrant" in pages[1]["text"]

    def test_extract_text_file_not_found(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError is raised when file does not exist."""
        processor = DocumentProcessor()
        missing_file = tmp_path / "does_not_exist.pdf"
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            processor.extract_text(missing_file)

    def test_extract_text_corrupted_file(self, tmp_path: Path) -> None:
        """Verify ValueError is raised when file is not a valid PDF."""
        corrupt_file = tmp_path / "corrupt.pdf"
        corrupt_file.write_text("Not a real PDF file header.")
        processor = DocumentProcessor()
        with pytest.raises(ValueError, match="Cannot open file as PDF"):
            processor.extract_text(corrupt_file)

    def test_extract_text_skips_empty_pages(self, tmp_path: Path) -> None:
        """Verify empty pages containing only whitespace are skipped."""
        pdf_path = tmp_path / "has_empty_page.pdf"
        doc = fitz.open()

        # Page 1: Has text
        p1 = doc.new_page()
        p1.insert_text((50, 72), "Non-empty page content.")

        # Page 2: Completely empty
        doc.new_page()

        doc.save(str(pdf_path))
        doc.close()

        processor = DocumentProcessor()
        pages = processor.extract_text(pdf_path)
        assert len(pages) == 1
        assert pages[0]["page_number"] == 1
        assert "Non-empty page content" in pages[0]["text"]

    def test_chunk_documents_metadata_and_attributes(self, synthetic_pdf: Path) -> None:
        """Verify chunks retain document_id, filename, and page_number metadata."""
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=20)
        pages = processor.extract_text(synthetic_pdf)

        chunks = processor.chunk_documents(
            pages=pages,
            doc_id="test-doc-id-123",
            filename="sample_test_doc.pdf",
        )

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["document_id"] == "test-doc-id-123"
            assert chunk.metadata["filename"] == "sample_test_doc.pdf"
            assert chunk.metadata["page_number"] in [1, 2]
            assert len(chunk.page_content.strip()) > 0

    def test_chunking_size_granularity(self) -> None:
        """Verify smaller chunk_size creates more chunks."""
        processor_large = DocumentProcessor(chunk_size=1000, chunk_overlap=100)
        processor_small = DocumentProcessor(chunk_size=100, chunk_overlap=20)

        sample_pages = [
            {
                "page_number": 1,
                "text": "Sentence number one. " * 30,  # ~630 characters
            }
        ]

        large_chunks = processor_large.chunk_documents(sample_pages, "id", "doc.pdf")
        small_chunks = processor_small.chunk_documents(sample_pages, "id", "doc.pdf")

        assert len(small_chunks) > len(large_chunks)
