"""test_rag_engine.py — Unit tests for RAGEngine prompt orchestration and citation parsing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from models.schemas import TokenUsage
from services.rag_engine import RAGEngine


class TestRAGEngine:
    """Test suite for RAGEngine logic and helper methods."""

    def test_empty_context_handling(self) -> None:
        """Verify fallback response when no context chunks are provided."""
        with patch("services.rag_engine.ChatGoogleGenerativeAI"):
            engine = RAGEngine()
            answer, citations, usage, contributing_docs = engine.generate_answer(
                query="What is the meaning of life?",
                context_chunks=[],
            )
            assert "don't have enough information" in answer
            assert citations == []
            assert usage.total_tokens == 0
            assert contributing_docs == []

    def test_coerce_content(self) -> None:
        """Verify _coerce_content handles various Gemini output structures."""
        # Plain string
        assert RAGEngine._coerce_content("Simple string") == "Simple string"

        # List of string parts
        assert RAGEngine._coerce_content(["Part 1 ", "Part 2"]) == "Part 1 Part 2"

        # List of dict parts
        dict_parts = [{"type": "text", "text": "Hello "}, {"type": "text", "text": "World"}]
        assert RAGEngine._coerce_content(dict_parts) == "Hello World"

        # Fallback to str conversion
        assert RAGEngine._coerce_content(12345) == "12345"

    def test_extract_citations_exact_match(self) -> None:
        """Verify citation parsing and metadata attachment from context chunks."""
        context_chunks = [
            {
                "document_id": "doc-1",
                "filename": "annual_report.pdf",
                "page_number": 3,
                "text": "Revenue increased by 15% in Q4.",
            }
        ]
        answer = "The company saw revenue growth [Doc: annual_report.pdf, Page: 3]."

        citations = RAGEngine._extract_citations(answer, context_chunks)
        assert len(citations) == 1
        assert citations[0].filename == "annual_report.pdf"
        assert citations[0].page_number == 3
        assert citations[0].document_id == "doc-1"
        assert "Revenue increased" in citations[0].text_snippet

    def test_extract_citations_deduplication(self) -> None:
        """Verify repeated citation tags in the answer are deduplicated."""
        context_chunks = [
            {
                "document_id": "doc-1",
                "filename": "paper.pdf",
                "page_number": 2,
                "text": "Key finding text.",
            }
        ]
        answer = (
            "Statement one [Doc: paper.pdf, Page: 2]. "
            "Statement two [Doc: paper.pdf, Page: 2]."
        )

        citations = RAGEngine._extract_citations(answer, context_chunks)
        assert len(citations) == 1
        assert citations[0].page_number == 2

    def test_extract_citations_fallback_when_llm_omits(self) -> None:
        """Verify fallback to top context chunks when LLM forgets to format tags."""
        context_chunks = [
            {
                "document_id": "doc-a",
                "filename": "doc_a.pdf",
                "page_number": 1,
                "text": "Snippet A",
            },
            {
                "document_id": "doc-b",
                "filename": "doc_b.pdf",
                "page_number": 2,
                "text": "Snippet B",
            },
        ]
        answer = "This answer contains no explicit citation tags."

        citations = RAGEngine._extract_citations(answer, context_chunks)
        assert len(citations) == 2
        assert citations[0].filename == "doc_a.pdf"
        assert citations[1].filename == "doc_b.pdf"

    def test_generate_answer_success(self) -> None:
        """Verify end-to-end generate_answer with mocked ChatGoogleGenerativeAI."""
        with patch("services.rag_engine.ChatGoogleGenerativeAI") as mock_chat_cls:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Vector databases are fast [Doc: db.pdf, Page: 5]."
            mock_response.usage_metadata = {
                "input_tokens": 120,
                "output_tokens": 30,
                "total_tokens": 150,
            }
            mock_llm.invoke.return_value = mock_response
            mock_chat_cls.return_value = mock_llm

            engine = RAGEngine()
            context_chunks = [
                {
                    "document_id": "uuid-db",
                    "filename": "db.pdf",
                    "page_number": 5,
                    "text": "Vector databases enable sub-second indexing.",
                }
            ]

            answer, citations, usage, contributing_docs = engine.generate_answer(
                query="Are vector databases fast?",
                context_chunks=context_chunks,
            )

            assert "Vector databases are fast" in answer
            assert len(citations) == 1
            assert citations[0].filename == "db.pdf"
            assert citations[0].page_number == 5
            assert usage.prompt_tokens == 120
            assert usage.completion_tokens == 30
            assert usage.total_tokens == 150
            assert contributing_docs == ["db.pdf"]

    def test_generate_answer_llm_exception_raises_runtime_error(self) -> None:
        """Verify LLM errors are caught and re-raised as RuntimeError."""
        with patch("services.rag_engine.ChatGoogleGenerativeAI") as mock_chat_cls:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("API quota exceeded")
            mock_chat_cls.return_value = mock_llm

            engine = RAGEngine()
            context_chunks = [
                {
                    "document_id": "doc-1",
                    "filename": "f.pdf",
                    "page_number": 1,
                    "text": "sample",
                }
            ]

            with pytest.raises(RuntimeError, match="Failed to generate answer"):
                engine.generate_answer(
                    query="Test query",
                    context_chunks=context_chunks,
                )
