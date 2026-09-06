## Project Overview
You are tasked with building a full-stack Retrieval-Augmented Generation (RAG) application that allows users to upload PDF documents and ask questions about them in natural language.

## Tech Stack
*   **Backend:** Python 3.11+, FastAPI
*   **AI/RAG Orchestration:** LangChain
*   **PDF Processing:** PyMuPDF (`fitz`) or `pdfplumber`
*   **Embeddings & LLM:** OpenAI API (`text-embedding-3-small`, `gpt-4o-mini`)
*   **Vector Database:** Qdrant (using local/memory instance for simplicity, or Pinecone if configured)
*   **Database:** SQLite (for local development/metadata) or PostgreSQL
*   **Frontend:** React (Next.js), TailwindCSS
*   **Task Queue (Optional but recommended):** Celery + Redis (for handling large PDF uploads asynchronously)

---

## Part 1: Backend Implementation (FastAPI)

Please generate the complete Python FastAPI backend. The structure should be highly modular.

### 1.1 Directory Structure
Create the following directory structure:
```text
backend/
├── main.py
├── config.py
├── requirements.txt
├── api/
│   ├── routes.py
│   └── dependencies.py
├── services/
│   ├── document_processor.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   └── rag_engine.py
├── models/
│   ├── schemas.py
│   └── db_models.py
└── database.py
```

### 1.2 Core Modules to Implement

**1. `requirements.txt`**
Include: `fastapi`, `uvicorn`, `langchain`, `langchain-openai`, `qdrant-client`, `pymupdf`, `python-multipart`, `sqlalchemy`, `pydantic`, `python-dotenv`.

**2. `config.py`**
Use `pydantic-settings` to manage environment variables: `OPENAI_API_KEY`, `DATABASE_URL`, `QDRANT_URL`.

**3. `models/schemas.py` (Pydantic Models)**
*   `DocumentResponse`: id, filename, status
*   `QueryRequest`: query (str), document_ids (List[str])
*   `QueryResponse`: answer (str), citations (List[dict])

**4. `services/document_processor.py`**
*   Implement a class to handle PDF parsing.
*   Extract text and metadata (page numbers).
*   Use `RecursiveCharacterTextSplitter` from LangChain to chunk the text (chunk_size=1000, overlap=200).

**5. `services/vector_store.py`**
*   Initialize Qdrant client.
*   Implement methods to `upsert_documents` (convert chunks to vectors and store with metadata).
*   Implement `similarity_search` (filter by document IDs).

**6. `services/rag_engine.py`**
*   Create a method `generate_answer(query, context)`.
*   Define a strict prompt template instructing the LLM to use ONLY provided context and cite page numbers.
*   Use `ChatOpenAI` (gpt-4o-mini) with `temperature=0`.

**7. `api/routes.py`**
Implement the endpoints:
*   `POST /upload`: Accept `UploadFile`, save to disk/storage, call `document_processor`, store in `vector_store`, return doc ID. (Bonus: make this asynchronous/background task).
*   `POST /query`: Accept `QueryRequest`, retrieve context from `vector_store`, call `rag_engine`, return `QueryResponse`.

**8. `main.py`**
Initialize FastAPI app, include routers, set up CORS middleware.

---

## Part 2: Frontend Implementation (React/Next.js)

Please generate a simple, clean React frontend to interact with the API.

### 2.1 Core Components
1.  **FileUpload Component:**
    *   A drag-and-drop zone or file input for PDFs.
    *   Show upload progress and success/failure status.
    *   Maintain a list of uploaded `document_ids` in state.

2.  **Chat Interface Component:**
    *   A scrolling window showing conversation history (User messages and AI responses).
    *   An input field for the natural language query.
    *   When the user submits a query, send the query AND the list of active `document_ids` to the backend `/query` endpoint.
    *   Render the AI's response, properly formatting the citations (e.g., displaying `[Doc: X, Page: Y]` as small clickable tags or bold text).

### 2.2 Styling
Use TailwindCSS for styling. The UI should look like a clean chat application (similar to ChatGPT but with a sidebar for document management).

---

## Constraints & Best Practices for Code Generation
1.  **Error Handling:** Implement try/except blocks in the backend to handle invalid PDFs, API limits, or empty search results. Return proper HTTP status codes.
2.  **Type Hinting:** Use strict Python type hinting for all function arguments and return types.
3.  **Comments:** Add docstrings to all major classes and functions explaining their purpose and inputs/outputs.
4.  **Citations:** The RAG prompt MUST explicitly force the LLM to output citations in a parsable format so the frontend can display them correctly.
