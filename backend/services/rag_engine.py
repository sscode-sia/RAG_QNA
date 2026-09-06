"""
services/rag_engine.py — Retrieval-Augmented Generation answer pipeline.

Takes a user query plus retrieved context chunks and generates an answer
using Google's Gemini API (via LangChain).  The prompt is
carefully designed to:
    1. Only use information present in the provided context.
    2. Emit structured inline citations in the format ``[Doc: <filename>, Page: <n>]``
       so the frontend can parse and render them.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from models.schemas import Citation, TokenUsage

logger = logging.getLogger(__name__)

# ── Prompt Template ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a precise, helpful research assistant that answers questions based
ONLY on the provided document excerpts.

RULES — you MUST follow every one:
1. Use ONLY the information in the CONTEXT below.  Do NOT use prior knowledge.
2. If the context does not contain enough information to answer the question,
   say "I don't have enough information in the provided documents to answer
   this question."
3. After every statement you make that comes from the context, add an inline
   citation in EXACTLY this format:  [Doc: <filename>, Page: <page_number>]
4. The context may contain excerpts from MULTIPLE documents.  You may combine
   information across them; cite each one.
5. Be concise yet thorough.  Use bullet points where appropriate.
6. Do not repeat the excerpts back verbatim — answer in your own words.
"""

USER_PROMPT_TEMPLATE = """\
CONTEXT (document excerpts):
{context}

---

QUESTION: {query}

Provide a well-structured answer with inline citations.
"""


class RAGEngine:
    """Orchestrates the answer-generation step of the RAG pipeline.

    Usage::

        engine = RAGEngine()
        answer, citations = engine.generate_answer(
            query="What is X?",
            context_chunks=[{...}, ...],
        )
    """

    def __init__(self, model: str | None = None, temperature: float = 0.0) -> None:
        """Initialise the LLM client.

        Args:
            model:       Google Gemini chat model name (default from settings).
            temperature: Sampling temperature (0 = deterministic).
        """
        self._model_name = model or settings.LLM_MODEL
        self._llm = ChatGoogleGenerativeAI(
            model=self._model_name,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY,
        )
        logger.info(
            "RAGEngine initialised (model=%s, temperature=%s)",
            self._model_name,
            temperature,
        )

    # ── Public API ────────────────────────────────────────────────────────

    def generate_answer(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Tuple[str, List[Citation], TokenUsage, List[str]]:
        """Generate a cited answer from retrieved context.

        Args:
            query:          The user's natural-language question.
            context_chunks: A list of dicts returned by
                            :meth:`VectorStoreService.similarity_search`.
                            Each dict must have keys ``text``, ``filename``,
                            ``page_number``, and ``document_id``.

        Returns:
            A tuple of ``(answer_text, citations, usage, contributing_docs)``
            where *answer_text* is the raw LLM response string, *citations*
            is a deduplicated list of :class:`Citation` objects extracted
            from the inline tags, *usage* holds the token counts reported
            by the LLM, and *contributing_docs* lists the filenames of the
            documents that supplied context.
        """
        if not context_chunks:
            return (
                "I don't have enough information in the provided documents "
                "to answer this question.",
                [],
                TokenUsage(),
                [],
            )

        # ── Build the context block ──────────────────────────────────────
        context_parts: List[str] = []
        for i, chunk in enumerate(context_chunks, start=1):
            context_parts.append(
                f"[Excerpt {i}] (Source: {chunk['filename']}, "
                f"Page {chunk['page_number']})\n{chunk['text']}"
            )
        context_block = "\n\n".join(context_parts)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_PROMPT_TEMPLATE.format(
                    context=context_block,
                    query=query,
                )
            ),
        ]

        try:
            response = self._llm.invoke(messages)
            answer_text = self._coerce_content(response.content)

            # Extract token usage metadata (LangChain AIMessage.usage_metadata
            # or Gemini response_info).
            um = getattr(response, "usage_metadata", None) or {}
            usage = TokenUsage(
                prompt_tokens=int(um.get("input_tokens", 0) or 0),
                completion_tokens=int(um.get("output_tokens", 0) or 0),
                total_tokens=int(um.get("total_tokens", 0) or 0),
            )
        except Exception as exc:
            logger.exception("LLM invocation failed")
            raise RuntimeError(f"Failed to generate answer: {exc}") from exc

        # ── Extract citations from the answer ────────────────────────────
        citations = self._extract_citations(answer_text, context_chunks)

        # ── Which documents actually contributed context? ─────────────────
        contributing_docs = list(
            dict.fromkeys(c["filename"] for c in context_chunks)
        )

        logger.info(
            "Generated answer with %d citations, %d tokens, %d source docs "
            "for query=%r",
            len(citations),
            usage.total_tokens,
            len(contributing_docs),
            query[:60],
        )
        return answer_text, citations, usage, contributing_docs

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _coerce_content(content: Any) -> str:
        """Coerce LLM response content into a plain string.

        Gemini may return either a plain string or a list of parts, where
        each part is a dict like ``{'type': 'text', 'text': '...'}``.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            return "".join(parts)
        return str(content)

    @staticmethod
    def _extract_citations(
        answer: str,
        context_chunks: List[Dict[str, Any]],
    ) -> List[Citation]:
        """Parse ``[Doc: <filename>, Page: <n>]`` tags from the answer.

        Falls back to the context metadata when needed, ensuring we always
        return valid, deduplicated citations.
        """
        # Pattern: [Doc: some_file.pdf, Page: 3]
        pattern = r"\[Doc:\s*(.+?),\s*Page:\s*(\d+)\]"
        matches = re.findall(pattern, answer)

        def _norm(name: str) -> str:
            """Normalise a filename for tolerant matching (case/space-insensitive)."""
            return " ".join(name.lower().split())

        # Build lookups from (filename, page) and filename alone → chunk.
        chunk_lookup: Dict[Tuple[str, int], Dict[str, Any]] = {}
        by_filename: Dict[str, Dict[str, Any]] = {}
        for chunk in context_chunks:
            norm_name = _norm(chunk["filename"])
            chunk_lookup.setdefault((norm_name, chunk["page_number"]), chunk)
            by_filename.setdefault(norm_name, chunk)

        seen: set = set()
        citations: List[Citation] = []

        for filename, page_str in matches:
            page_number = int(page_str)
            norm_name = _norm(filename)
            key = (norm_name, page_number)
            if key in seen:
                continue
            seen.add(key)

            # Exact (name, page) match first; else any chunk from that file.
            chunk_data = chunk_lookup.get(key) or by_filename.get(norm_name, {})
            if chunk_data:
                # Trust the retrieved chunk's canonical metadata over the
                # LLM's transcription of the filename.
                cited_name = chunk_data["filename"]
                cited_page = chunk_data.get("page_number", page_number)
            else:
                cited_name = filename.strip()
                cited_page = page_number

            citations.append(
                Citation(
                    document_id=chunk_data.get("document_id", "unknown"),
                    filename=cited_name,
                    page_number=cited_page,
                    text_snippet=chunk_data.get("text", "")[:200],
                )
            )

        # If the LLM forgot to cite but we have context, add the top chunks.
        if not citations and context_chunks:
            for chunk in context_chunks[:3]:
                citations.append(
                    Citation(
                        document_id=chunk.get("document_id", "unknown"),
                        filename=chunk.get("filename", "unknown"),
                        page_number=chunk.get("page_number", 0),
                        text_snippet=chunk.get("text", "")[:200],
                    )
                )

        return citations
