"""
database.py — SQLAlchemy engine, session factory, and declarative base.

Provides:
    * ``engine``        – the SQLAlchemy engine bound to ``DATABASE_URL``.
    * ``SessionLocal``  – a scoped session factory.
    * ``Base``          – the declarative base for ORM models.
    * ``init_db()``     – creates all tables (idempotent) + migrates missing
                           columns on existing tables.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

logger = logging.getLogger(__name__)

# SQLite requires `check_same_thread=False` when used with FastAPI's
# async event loop.  PostgreSQL (or other dialects) ignore this kwarg.
_connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables defined by ORM models (safe to call repeatedly).

    Also performs lightweight schema migration: any column defined on the
    ORM model but missing from an existing table (e.g. after a model
    change on a database created by an older version) is added via
    ``ALTER TABLE`` with the model's default value.
    """
    # Import models so they register with ``Base.metadata``.
    import models.db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Add columns that exist on the models but not in the database yet.
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, table_obj in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table_obj.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(engine.dialect)
                default = "NULL" if column.default is None else str(
                    column.default.arg
                    if hasattr(column.default, "arg")
                    else column.default
                )
                conn.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
                    f" DEFAULT {default}"
                )
                logger.warning(
                    "Schema migration: added column %s.%s",
                    table_name,
                    column.name,
                )
