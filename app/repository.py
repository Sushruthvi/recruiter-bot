"""Read queries for candidates and jobs. All SQL is hand-written."""
import sqlite3

# Skills and traits are collected with correlated subqueries so each entity
# comes back as one row. None of the names contain a comma.
CANDIDATE_SELECT = """
    SELECT c.id, c.name, c.experience_years, c.open_to_work, c.notice_days, c.quirk,
           (SELECT group_concat(s.name, ',')
              FROM candidate_skills cs JOIN skills s ON s.id = cs.skill_id
             WHERE cs.candidate_id = c.id) AS skills,
           (SELECT group_concat(t.name, ',')
              FROM candidate_traits ct JOIN traits t ON t.id = ct.trait_id
             WHERE ct.candidate_id = c.id) AS traits
      FROM candidates c
"""

JOB_SELECT = """
    SELECT j.id, j.title, j.min_experience_years, j.tagline,
           (SELECT group_concat(s.name, ',')
              FROM job_skills js JOIN skills s ON s.id = js.skill_id
             WHERE js.job_id = j.id) AS required_skills,
           (SELECT group_concat(t.name, ',')
              FROM job_culture_keywords jk JOIN traits t ON t.id = jk.trait_id
             WHERE jk.job_id = j.id) AS culture_keywords
      FROM jobs j
"""


def availability_label(open_to_work: int, notice_days: int) -> str:
    """Render the stored availability the way the brief words it."""
    if not open_to_work:
        return "Not looking"
    if notice_days == 0:
        return "Immediate"
    if notice_days % 7 == 0:
        weeks = notice_days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''}"
    return f"{notice_days} day{'s' if notice_days != 1 else ''}"


def _split(value: str | None) -> list[str]:
    return sorted(value.split(",")) if value else []


def _candidate(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "experience_years": row["experience_years"],
        "availability": availability_label(row["open_to_work"], row["notice_days"]),
        "open_to_work": bool(row["open_to_work"]),
        "notice_days": row["notice_days"],
        "skills": _split(row["skills"]),
        "traits": _split(row["traits"]),
        "quirk": row["quirk"],
    }


def _job(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "min_experience_years": row["min_experience_years"],
        "required_skills": _split(row["required_skills"]),
        "culture_keywords": _split(row["culture_keywords"]),
        "tagline": row["tagline"],
    }


def list_candidates(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(CANDIDATE_SELECT + " ORDER BY c.id").fetchall()
    return [_candidate(r) for r in rows]


def get_candidate(conn: sqlite3.Connection, candidate_id: int) -> dict | None:
    row = conn.execute(CANDIDATE_SELECT + " WHERE c.id = ?", (candidate_id,)).fetchone()
    return _candidate(row) if row else None


def list_jobs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(JOB_SELECT + " ORDER BY j.id").fetchall()
    return [_job(r) for r in rows]


def get_job(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute(JOB_SELECT + " WHERE j.id = ?", (job_id,)).fetchone()
    return _job(row) if row else None
