"""Load the candidates and jobs from data/seed_data.json.

Run with:  python -m app.seed

Safe to run repeatedly: rows are upserted by name and link rows are rebuilt,
so a second run changes nothing.
"""
import json
import re
import sqlite3

from app.db import ROOT, get_connection, init_db

SEED_FILE = ROOT / "data" / "seed_data.json"

DAYS_PER_UNIT = {"day": 1, "week": 7, "month": 30}


def parse_availability(text: str) -> tuple[int, int]:
    """Turn 'Immediate', '2 weeks', '1 day', 'Not looking' into
    (open_to_work, notice_days)."""
    value = text.strip().lower()
    if value == "not looking":
        return 0, 0
    if value == "immediate":
        return 1, 0
    match = re.fullmatch(r"(\d+)\s*(day|week|month)s?", value)
    if not match:
        raise ValueError(f"Unrecognised availability: {text!r}")
    return 1, int(match.group(1)) * DAYS_PER_UNIT[match.group(2)]


def skill_id(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (name,))
    return conn.execute("SELECT id FROM skills WHERE name = ?", (name,)).fetchone()["id"]


def trait_id(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO traits (name) VALUES (?)", (name,))
    return conn.execute("SELECT id FROM traits WHERE name = ?", (name,)).fetchone()["id"]


def upsert_candidate(conn: sqlite3.Connection, c: dict) -> None:
    open_to_work, notice_days = parse_availability(c["availability"])
    conn.execute(
        """
        INSERT INTO candidates (name, experience_years, open_to_work, notice_days, quirk)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            experience_years = excluded.experience_years,
            open_to_work     = excluded.open_to_work,
            notice_days      = excluded.notice_days,
            quirk            = excluded.quirk
        """,
        (c["name"], c["experience_years"], open_to_work, notice_days, c["quirk"]),
    )
    cid = conn.execute("SELECT id FROM candidates WHERE name = ?", (c["name"],)).fetchone()["id"]

    conn.execute("DELETE FROM candidate_skills WHERE candidate_id = ?", (cid,))
    conn.executemany(
        "INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (?, ?)",
        [(cid, skill_id(conn, s)) for s in c["skills"]],
    )
    conn.execute("DELETE FROM candidate_traits WHERE candidate_id = ?", (cid,))
    conn.executemany(
        "INSERT INTO candidate_traits (candidate_id, trait_id) VALUES (?, ?)",
        [(cid, trait_id(conn, t)) for t in c["traits"]],
    )


def upsert_job(conn: sqlite3.Connection, j: dict) -> None:
    conn.execute(
        """
        INSERT INTO jobs (title, min_experience_years, tagline)
        VALUES (?, ?, ?)
        ON CONFLICT(title) DO UPDATE SET
            min_experience_years = excluded.min_experience_years,
            tagline              = excluded.tagline
        """,
        (j["title"], j["min_experience_years"], j["tagline"]),
    )
    jid = conn.execute("SELECT id FROM jobs WHERE title = ?", (j["title"],)).fetchone()["id"]

    conn.execute("DELETE FROM job_skills WHERE job_id = ?", (jid,))
    conn.executemany(
        "INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)",
        [(jid, skill_id(conn, s)) for s in j["required_skills"]],
    )
    conn.execute("DELETE FROM job_culture_keywords WHERE job_id = ?", (jid,))
    conn.executemany(
        "INSERT INTO job_culture_keywords (job_id, trait_id) VALUES (?, ?)",
        [(jid, trait_id(conn, k)) for k in j["culture_keywords"]],
    )


def seed(conn: sqlite3.Connection) -> tuple[int, int]:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    with conn:  # one transaction: all rows load, or none do
        for candidate in data["candidates"]:
            upsert_candidate(conn, candidate)
        for job in data["jobs"]:
            upsert_job(conn, job)
    return len(data["candidates"]), len(data["jobs"])


if __name__ == "__main__":
    connection = get_connection()
    init_db(connection)
    n_candidates, n_jobs = seed(connection)
    print(f"Seeded {n_candidates} candidates and {n_jobs} jobs.")
