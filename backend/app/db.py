"""Read-only access to the SQLite serving database built by `python -m src.export_db`."""
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from urllib.request import pathname2url

from fastapi import Depends, Request

EXPECTED_SCHEMA_VERSION = 3


class DatabaseError(RuntimeError):
    """The serving database is missing or was built with an incompatible schema."""


def connect(db_path: Path) -> sqlite3.Connection:
    # mode=ro: never write; immutable=1: the file never changes while open, so SQLite skips locking.
    uri = f"file:{pathname2url(str(db_path.resolve()))}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def check_database(db_path: Path) -> dict[str, str]:
    """Fail fast at startup if the database is unusable. Returns the `meta` table."""
    if not db_path.exists():
        raise DatabaseError(f"Database not found at {db_path}. Build it with: python -m src.export_db")
    conn = connect(db_path)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version != EXPECTED_SCHEMA_VERSION:
            raise DatabaseError(f"Database schema version {version}, expected {EXPECTED_SCHEMA_VERSION}. Rebuild it.")
        return {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
    finally:
        conn.close()


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one short-lived read-only connection per request."""
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


DbConn = Annotated[sqlite3.Connection, Depends(get_db)]
