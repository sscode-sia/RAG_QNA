"""
main.py — FastAPI application entry-point.

Starts the app, configures CORS, includes the API router, and initialises
the database on startup.

Run locally with::

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from api.routes import router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-Powered Document Q&A API",
    description=(
        "Upload PDF documents and ask natural-language questions. "
        "Answers are generated via Retrieval-Augmented Generation (RAG) "
        "with inline citations."
    ),
    version="1.0.0",
)

# ── CORS (allow everything in development) ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include API routes ────────────────────────────────────────────────────────
app.include_router(router, prefix="/api", tags=["Documents & Q&A"])


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup() -> None:
    """Run once when the server starts."""
    # Ensure upload directory exists
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory: %s", settings.UPLOAD_DIR.resolve())

    # Create DB tables
    init_db()
    logger.info("Database initialised")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check() -> dict:
    """Simple health-check endpoint for monitoring."""
    return {"status": "ok"}
