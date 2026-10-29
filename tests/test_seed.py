import pytest

from app.db import get_connection, init_db
from app.seed import parse_availability, seed


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Immediate", (1, 0)),
        ("2 weeks", (1, 14)),
        ("3 weeks", (1, 21)),
        ("1 day", (1, 1)),
        ("Not looking", (0, 0)),
        ("  immediate ", (1, 0)),
    ],
)
def test_parse_availability(text, expected):
    assert parse_availability(text) == expected


def test_parse_availability_rejects_unknown_text():
    with pytest.raises(ValueError):
        parse_availability("whenever")


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_seed_loads_all_rows(conn):
    assert count(conn, "candidates") == 15
    assert count(conn, "jobs") == 6


def test_seed_is_idempotent(conn):
    tables = ["candidates", "jobs", "skills", "traits", "candidate_skills",
              "job_skills", "candidate_traits", "job_culture_keywords"]
    before = {t: count(conn, t) for t in tables}
    seed(conn)
    assert {t: count(conn, t) for t in tables} == before


def test_seed_leaves_no_foreign_key_violations(conn):
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(Exception):
        conn.execute("INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (999, 999)")


def test_init_db_is_safe_to_repeat(tmp_path, monkeypatch):
    monkeypatch.setenv("RECRUITER_DB", str(tmp_path / "again.db"))
    connection = get_connection()
    init_db(connection)
    init_db(connection)
    connection.close()
