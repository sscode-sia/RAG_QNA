"""
config.py — Centralised application settings.

Uses ``pydantic-settings`` to read values from a ``.env`` file (or real
environment variables).  Every service imports the singleton ``settings``
instance exported at the bottom of this module.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration backed by environment variables."""

    # ── Google Gemini ─────────────────────────────────────────────────────
    GOOGLE_API_KEY: str

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./rag_app.db"

    # ── Qdrant ────────────────────────────────────────────────────────────
    QDRANT_URL: str = ":memory:"
    QDRANT_COLLECTION_NAME: str = "documents"

    # ── Model names ───────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    LLM_MODEL: str = "gemini-3.6-flash"

    # ── Chunking ──────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # ── File storage ──────────────────────────────────────────────────────
    UPLOAD_DIR: Path = Path("uploads")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton instance — import this everywhere.
settings = Settings()  # type: ignore[call-arg]
