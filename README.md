# ðŸ“„ DocQ&A â€” AI-Powered Document Q&A System

A full-stack Retrieval-Augmented Generation (RAG) application that lets you upload PDF documents and ask natural-language questions about them. Answers are generated with inline citations pointing back to the exact source pages.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-3.6-Flash-4285F4?logo=google&logoColor=white)

---

## ðŸ—ï¸ Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚         Frontend (Next.js)      â”‚      â”‚          Backend (FastAPI)            â”‚
â”‚                                 â”‚      â”‚                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚ HTTP â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚FileUpload â”‚  â”‚ ChatInterfaceâ”‚ â”‚â—„â”€â”€â”€â–ºâ”‚  â”‚ routes.pyâ”‚  â”‚DocumentProcessor â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚      â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚  (PyMuPDF +      â”‚  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚      â”‚       â”‚        â”‚   LangChain)     â”‚  â”‚
â”‚  â”‚DocumentListâ”‚ â”‚  API Client â”‚  â”‚      â”‚       â–¼        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚      â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚                                 â”‚      â”‚  â”‚RAGEngine â”‚  â”‚VectorStoreServiceâ”‚  â”‚
â”‚  TailwindCSS Â· TypeScript       â”‚      â”‚  â”‚(gemini-  â”‚  â”‚  (Qdrant)        â”‚  â”‚
â”‚                                 â”‚      â”‚  â”‚ 2.0-flashâ”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚
                                         â”‚  SQLite Â· Gemini Â· Qdrant (in-mem)   â”‚
                                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## ðŸ“ Project Structure

```
RAG_caddence/
â”œâ”€â”€ ai_code_generation_prompt.md    # Original specification
â”œâ”€â”€ README.md                       # â† You are here
â”‚
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ main.py                     # FastAPI app, CORS, startup hooks
â”‚   â”œâ”€â”€ config.py                   # pydantic-settings configuration
â”‚   â”œâ”€â”€ database.py                 # SQLAlchemy engine & session factory
â”‚   â”œâ”€â”€ requirements.txt            # Python dependencies
â”‚   â”œâ”€â”€ .env.example                # Environment variable template
â”‚   â”‚
â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â”œâ”€â”€ routes.py               # REST endpoints (upload, query, list, delete)
â”‚   â”‚   â””â”€â”€ dependencies.py         # FastAPI dependency injection
â”‚   â”‚
â”‚   â”œâ”€â”€ models/
â”‚   â”‚   â”œâ”€â”€ db_models.py            # SQLAlchemy ORM models
â”‚   â”‚   â””â”€â”€ schemas.py              # Pydantic request/response schemas
â”‚   â”‚
â”‚   â””â”€â”€ services/
â”‚       â”œâ”€â”€ document_processor.py   # PDF parsing & text chunking
â”‚       â”œâ”€â”€ embedding_service.py    # OpenAI embeddings wrapper
â”‚       â”œâ”€â”€ vector_store.py         # Qdrant vector database interface
â”‚       â””â”€â”€ rag_engine.py           # LLM answer generation with citations
â”‚
â””â”€â”€ frontend/
    â”œâ”€â”€ package.json
    â”œâ”€â”€ next.config.ts
    â”œâ”€â”€ tailwind.config.ts
    â”‚
    â””â”€â”€ src/
        â”œâ”€â”€ app/
        â”‚   â”œâ”€â”€ layout.tsx          # Root layout (Inter font, dark mode)
        â”‚   â”œâ”€â”€ page.tsx            # Main page (sidebar + chat)
        â”‚   â””â”€â”€ globals.css         # Dark theme & scrollbar styling
        â”‚
        â”œâ”€â”€ components/
        â”‚   â”œâ”€â”€ FileUpload.tsx      # Drag-and-drop PDF upload
        â”‚   â”œâ”€â”€ DocumentList.tsx    # Sidebar document list with selection
        â”‚   â””â”€â”€ ChatInterface.tsx   # Chat feed with citation rendering
        â”‚
        â””â”€â”€ lib/
            â””â”€â”€ api.ts              # Typed HTTP client for the backend
```

---

## ðŸš€ Getting Started

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| **Python** | 3.11+ | `python --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **Google API Key** | â€” | [Get one here](https://aistudio.google.com/apikey) |

---

### 1ï¸âƒ£ Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your environment file
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

**Edit `backend/.env`** and set your Google API key:

```env
GOOGLE_API_KEY=your-google-api-key-here
```

> **Note:** The default configuration uses **SQLite** and **Qdrant in-memory mode**, so no external database servers are needed.

#### Start the Backend Server

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**. Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

### 2ï¸âƒ£ Frontend Setup

```bash
# Navigate to the frontend directory (from project root)
cd frontend

# Install dependencies (already done during scaffold, but just in case)
npm install

# Start the development server
npm run dev
```

The frontend will be available at **http://localhost:3000**.

---

## ðŸŽ® Usage

1. **Upload a PDF** â€” Use the drag-and-drop zone in the sidebar, or click to browse.
2. **Wait for processing** â€” The status badge will change from `PROCESSING` â†’ `COMPLETED`.
3. **Select documents** â€” Click the checkbox next to documents you want to query.
4. **Ask a question** â€” Type your question in the chat input and press Enter.
5. **View cited answers** â€” The AI response includes inline citations like `[Doc: file.pdf, Page: 3]` rendered as styled badges. Click "sources" to expand the full citation details.

---

## ðŸ”Œ API Endpoints

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a PDF file (multipart form-data) |
| `POST` | `/api/query` | Ask a question (JSON: `{ query, document_ids }`) â€” returns answer, citations, token usage & latency |
| `GET` | `/api/documents` | List all uploaded documents |
| `GET` | `/api/stats` | Aggregated token usage, queries, latency, doc & vector counts |
| `DELETE` | `/api/documents/{id}` | Delete a document and its vectors |
| `GET` | `/health` | Health check |

### Example: Query via cURL

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "document_ids": ["your-document-uuid"]
  }'
```

---

## âš™ï¸ Configuration

All configuration is managed via environment variables in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | *(required)* | Your Google API key from [AI Studio](https://aistudio.google.com/apikey) |
| `DATABASE_URL` | `sqlite:///./rag_app.db` | Database connection string |
| `QDRANT_URL` | `:memory:` | Qdrant URL (`:memory:` for in-memory) |
| `EMBEDDING_MODEL` | `models/gemini-embedding-001` | Google embedding model |
| `LLM_MODEL` | `gemini-3.6-flash` | Google Gemini chat model |
| `CHUNK_SIZE` | `1000` | Text chunk size in characters |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |

### Using an External Qdrant Server

To use a persistent Qdrant instance instead of in-memory:

```bash
# Start Qdrant via Docker
docker run -p 6333:6333 qdrant/qdrant

# Update .env
QDRANT_URL=http://localhost:6333
```

### Using PostgreSQL

```env
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db
```

---

## ðŸ§© Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | FastAPI |
| **LLM** | Google Gemini `gemini-3.6-flash` (via LangChain) |
| **Embeddings** | Google `text-embedding-004` |
| **Vector Database** | Qdrant (in-memory or server) |
| **PDF Parsing** | PyMuPDF (`fitz`) |
| **Text Splitting** | LangChain `RecursiveCharacterTextSplitter` |
| **Relational DB** | SQLite (default) / PostgreSQL |
| **Frontend** | Next.js 16 (App Router) + TypeScript |
| **Styling** | TailwindCSS 4 |

---

## ðŸ› Troubleshooting

### "Only PDF files are accepted"
Make sure you're uploading a file with a `.pdf` extension.

### Document stuck on "processing"
Check the backend terminal for errors. Common causes:
- Invalid or corrupted PDF file
- `GOOGLE_API_KEY` not set or invalid
- Network connectivity issues to Google Gemini API

### "Failed to fetch documents"
Ensure the backend is running on port 8000. The frontend expects the API at `http://localhost:8000/api`. You can override this by setting `NEXT_PUBLIC_API_URL` in your frontend environment.

### CORS errors in browser
The backend is configured to allow all origins in development. If you're running on a non-standard port, check the CORS middleware in `main.py`.

### PowerShell script execution errors
If you see `running scripts is disabled on this system`:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## ðŸ“„ License

This project is for educational and demonstration purposes.
