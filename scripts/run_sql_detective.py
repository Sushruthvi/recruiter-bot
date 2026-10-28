"""Run the Part 2 answers against the dataset, in a throwaway in-memory SQLite.

Usage:  python scripts/run_sql_detective.py
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def title_of(statement: str) -> str:
    for line in statement.splitlines():
        if line.startswith("-- Q"):
            return line[3:]
    return "(query)"


def main() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "sql_detective_data.sql").read_text(encoding="utf-8"))

    # Accumulate lines until SQLite says the statement is complete; this
    # ignores semicolons inside comments, unlike a plain split on ";".
    buffer = ""
    for line in (ROOT / "sql_detective.sql").read_text(encoding="utf-8").splitlines(keepends=True):
        buffer += line
        if not sqlite3.complete_statement(buffer):
            continue
        statement, buffer = buffer, ""
        cursor = conn.execute(statement)
        print(f"\n{title_of(statement)}")
        columns = [d[0] for d in cursor.description]
        print("  " + " | ".join(columns))
        for row in cursor.fetchall():
            print("  " + " | ".join("NULL" if v is None else str(v) for v in row))


if __name__ == "__main__":
    main()
