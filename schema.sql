-- Recruiter Bot schema (SQLite, hand-written DDL).
--
-- Design notes:
--   * Skills and traits/culture keywords are multi-valued, so they live in
--     lookup tables joined through link tables (no comma-separated strings).
--     This lets the matching logic count overlaps with plain JOIN + GROUP BY.
--   * Candidate traits and job culture keywords share ONE vocabulary
--     (the `traits` table), so "analytical" on a candidate and "analytical" on
--     a job are the same row and can be matched with a simple join.
--   * Matches are NOT stored. They are computed on demand from current data,
--     so scores can never go stale and the weights can be tuned per request.
--   * Foreign keys are off by default in SQLite; every connection must run
--     `PRAGMA foreign_keys = ON` (the db layer does this).

CREATE TABLE IF NOT EXISTS candidates (
    id                INTEGER PRIMARY KEY,
    name              TEXT    NOT NULL UNIQUE,
    experience_years  INTEGER NOT NULL CHECK (experience_years >= 0),
    -- Availability is modelled as two facts instead of a fixed list of labels,
    -- so values like "1 day" or "3 weeks" need no schema change:
    --   open_to_work : 0 = not looking, 1 = looking
    --   notice_days  : days until they can start (Immediate = 0, 2 weeks = 14)
    open_to_work      INTEGER NOT NULL DEFAULT 1 CHECK (open_to_work IN (0, 1)),
    notice_days       INTEGER NOT NULL DEFAULT 0 CHECK (notice_days >= 0),
    quirk             TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id                    INTEGER PRIMARY KEY,
    title                 TEXT    NOT NULL UNIQUE,
    min_experience_years  INTEGER NOT NULL CHECK (min_experience_years >= 0),
    tagline               TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS traits (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS candidate_skills (
    candidate_id  INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id      INTEGER NOT NULL REFERENCES skills(id)     ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id    INTEGER NOT NULL REFERENCES jobs(id)   ON DELETE CASCADE,
    skill_id  INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS candidate_traits (
    candidate_id  INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    trait_id      INTEGER NOT NULL REFERENCES traits(id)     ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, trait_id)
);

CREATE TABLE IF NOT EXISTS job_culture_keywords (
    job_id    INTEGER NOT NULL REFERENCES jobs(id)   ON DELETE CASCADE,
    trait_id  INTEGER NOT NULL REFERENCES traits(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, trait_id)
);

-- The composite primary keys already serve lookups by candidate_id / job_id.
-- These reverse indexes serve lookups by skill or trait (e.g. "which
-- candidates have skill X?"), which the job -> candidates match relies on.
CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill ON candidate_skills (skill_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill       ON job_skills (skill_id, job_id);
CREATE INDEX IF NOT EXISTS idx_candidate_traits_trait ON candidate_traits (trait_id, candidate_id);
CREATE INDEX IF NOT EXISTS idx_job_culture_trait      ON job_culture_keywords (trait_id, job_id);
