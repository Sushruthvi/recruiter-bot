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


# One row per (candidate, job) pair. The LEFT JOIN onto candidate_skills is NULL
# exactly when the candidate lacks a required skill, so a single GROUP BY yields
# the counts plus the matched and missing skill names. LEFT JOINs also keep
# jobs that happen to list no required skills (required_count = 0).
SKILL_OVERLAP_SQL = """
    SELECT c.id AS candidate_id,
           j.id AS job_id,
           COUNT(js.skill_id) AS required_count,
           COUNT(cs.skill_id) AS matched_count,
           group_concat(CASE WHEN cs.skill_id IS NOT NULL THEN s.name END, ',') AS matched_skills,
           group_concat(CASE WHEN cs.skill_id IS NULL THEN s.name END, ',')     AS missing_skills
      FROM jobs j
      CROSS JOIN candidates c
      LEFT JOIN job_skills js       ON js.job_id = j.id
      LEFT JOIN skills s            ON s.id = js.skill_id
      LEFT JOIN candidate_skills cs ON cs.candidate_id = c.id AND cs.skill_id = js.skill_id
     WHERE (:job_id IS NULL OR j.id = :job_id)
       AND (:candidate_id IS NULL OR c.id = :candidate_id)
     GROUP BY c.id, j.id
"""
                       
                          
def skill_overlap(
    conn: sqlite3.Connection,
    job_id: int | None = None,
    candidate_id: int | None = None,
) -> list[dict]:
    """How many of each job's required skills each candidate has.

    Pass job_id and/or candidate_id to narrow the result; with neither, every
    candidate/job pair is returned.
    """
    rows = conn.execute(
        SKILL_OVERLAP_SQL, {"job_id": job_id, "candidate_id": candidate_id}
    ).fetchall()
    return [
        {
            "candidate_id": r["candidate_id"],
            "job_id": r["job_id"],
            "required_count": r["required_count"],
            "matched_count": r["matched_count"],
            "matched_skills": _split(r["matched_skills"]),
            "missing_skills": _split(r["missing_skills"]),
        }
        for r in rows
    ]


# Same shape as SKILL_OVERLAP_SQL, but for the job's culture keywords versus
# the candidate's traits (both live in the shared `traits` table).
CULTURE_OVERLAP_SQL = """
    SELECT c.id AS candidate_id,
           j.id AS job_id,
           COUNT(jk.trait_id) AS culture_total,
           group_concat(CASE WHEN ct.trait_id IS NOT NULL THEN t.name END, ',') AS shared_traits
      FROM jobs j
      CROSS JOIN candidates c
      LEFT JOIN job_culture_keywords jk ON jk.job_id = j.id
      LEFT JOIN traits t                ON t.id = jk.trait_id
      LEFT JOIN candidate_traits ct     ON ct.candidate_id = c.id AND ct.trait_id = jk.trait_id
     WHERE (:job_id IS NULL OR j.id = :job_id)
       AND (:candidate_id IS NULL OR c.id = :candidate_id)
     GROUP BY c.id, j.id
"""

# Everything the scorer needs for each pair, in one round trip. The two
# overlap queries are reused as CTEs so each is still written only once.
MATCH_INPUTS_SQL = f"""
    WITH skill AS ({SKILL_OVERLAP_SQL}),
         culture AS ({CULTURE_OVERLAP_SQL})
    SELECT c.id AS candidate_id, c.name AS candidate_name,
           c.experience_years, c.open_to_work, c.notice_days,
           j.id AS job_id, j.title AS job_title, j.min_experience_years,
           skill.required_count, skill.matched_count,
           skill.matched_skills, skill.missing_skills,
           culture.culture_total, culture.shared_traits
      FROM skill
      JOIN culture ON culture.candidate_id = skill.candidate_id
                  AND culture.job_id = skill.job_id
      JOIN candidates c ON c.id = skill.candidate_id
      JOIN jobs j ON j.id = skill.job_id
"""


def match_inputs(
    conn: sqlite3.Connection,
    job_id: int | None = None,
    candidate_id: int | None = None,
) -> list[dict]:
    """Per candidate/job pair: the facts the scoring functions work from."""
    rows = conn.execute(
        MATCH_INPUTS_SQL, {"job_id": job_id, "candidate_id": candidate_id}
    ).fetchall()
    return [
        {
            "candidate_id": r["candidate_id"],
            "candidate_name": r["candidate_name"],
            "experience_years": r["experience_years"],
            "open_to_work": r["open_to_work"],
            "notice_days": r["notice_days"],
            "availability": availability_label(r["open_to_work"], r["notice_days"]),
            "job_id": r["job_id"],
            "job_title": r["job_title"],
            "min_experience_years": r["min_experience_years"],
            "required_count": r["required_count"],
            "matched_count": r["matched_count"],
            "matched_skills": _split(r["matched_skills"]),
            "missing_skills": _split(r["missing_skills"]),
            "culture_total": r["culture_total"],
            "shared_traits": _split(r["shared_traits"]),
        }
        for r in rows
    ]
