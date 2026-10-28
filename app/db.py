"""SQLite connection helpers. All SQL in this project is hand-written."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "schema.sql"


def default_db_path() -> Path:
    """Database location; override with the RECRUITER_DB environment variable."""
    return Path(os.environ.get("RECRUITER_DB", ROOT / "recruiter.db"))


def get_connection(db_path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or default_db_path())
    conn.row_factory = sqlite3.Row
    # SQLite ignores foreign keys unless this is set on every connection.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the tables if they do not exist yet (safe to call repeatedly)."""
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
