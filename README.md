# Recruiter Bot

A small backend service that ingests candidate profiles and job openings, then
ranks the best matches in both directions: candidates for a job, and jobs for a
candidate. Every match comes with a score, a per-component breakdown, the
skills matched and missing, and a short human-readable reason.

**Stack:** Python 3.10+, FastAPI, SQLite. All SQL is hand-written and
parameterised: no ORM, no query builder.

## Run it locally

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed                # creates recruiter.db and loads 15 candidates + 6 jobs
uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

Interactive API docs: <http://127.0.0.1:8000/docs>. The seed script is safe to
run repeatedly. Set `RECRUITER_DB` to use a different database file.

## API

| Endpoint | Description |
|---|---|
| `GET /jobs/{id}/matches` | Candidates ranked for a job |
| `GET /candidates/{id}/matches` | Jobs ranked for a candidate |
| `GET /jobs`, `GET /jobs/{id}` | Browse jobs |
| `GET /candidates`, `GET /candidates/{id}` | Browse candidates |
| `GET /health` | Liveness check |

Both match endpoints accept optional query parameters:

| Parameter | Meaning |
|---|---|
| `w_skill`, `w_experience`, `w_culture` | Relative weights (default 0.65 / 0.25 / 0.10). Omitted ones keep their default; all three are rescaled to sum to 1, so only the ratio matters. |
| `limit` | Return at most this many matches (1-100). |
| `include_unavailable=false` | Jobs endpoint only: hide candidates who are not looking. |

Unknown ids return `404`; invalid parameters (negative or all-zero weights,
`limit` out of range, non-numeric ids) return `422`. On Windows PowerShell use
`curl.exe`, since plain `curl` is an alias for something else.

```bash
curl "http://127.0.0.1:8000/jobs/1/matches"
curl "http://127.0.0.1:8000/candidates/6/matches"
curl "http://127.0.0.1:8000/jobs/2/matches?include_unavailable=false&limit=2"
curl "http://127.0.0.1:8000/jobs/4/matches?w_skill=1&w_experience=0&w_culture=0"
```

Example: the top match for job 1, *Backend Detective*:

```json
{
  "score": 95.0,
  "breakdown": { "skill": 1.0, "experience": 1.0, "culture": 0.5, "availability": 1.0 },
  "matched_skills": ["deduction", "forensics", "pattern-recognition"],
  "missing_skills": [],
  "reason": "3/3 required skills (deduction, forensics, pattern-recognition); 8 yrs vs 3 yrs minimum (well above); available immediately; shares culture keywords: analytical",
  "candidate_id": 1,
  "candidate_name": "Sherlock H."
}
```

## Design decisions and trade-offs

### Schema

Skills and traits are multi-valued, so they sit in lookup tables joined through
link tables (no comma-separated strings), which lets the matching be plain
`JOIN` + `GROUP BY`. Candidate traits and job culture keywords share one
`traits` table, so "analytical" on a candidate and on a job is the same row.
Availability is stored as two facts, `open_to_work` and `notice_days`, instead
of a fixed list of labels, so a value like "3 weeks" or "1 day" needs no schema
change; the API renders it back as "Immediate", "2 weeks" or "Not looking".

**Matches are computed on request, not stored.** Scores can never go stale and
the weights can be tuned per call. The cost is recomputation on every request,
which is trivial at this size.

### Scoring

```
score = 100 x (0.65 x skill + 0.25 x experience + 0.10 x culture) x availability
```

- **Skill** is *coverage*: matched required skills / required skills. Extra
  skills never hurt a candidate (Ron's woodworking doesn't count against him).
  A candidate with **no** matching skill is not returned at all, so culture or
  experience alone can never create a match.
- **Experience** is `years / minimum` when below the minimum, else 1.0. I chose
  **not** to penalise over-qualification: "more experience is worse" is hard to
  defend, so the reason string just notes "well above" instead.
- **Culture** is shared traits / the job's keywords. It is deliberately a small
  bonus: trait and keyword vocabularies barely overlap in the seed data (only 7
  of the 12 job keywords appear on any candidate), so a large weight would add
  noise.
- **Availability** is a *multiplier*, not an addition, so a perfect candidate
  who can't start can't outrank a good one who can. Notice period discounts
  smoothly (up to 15% at 90+ days); "not looking" gets x0.6. They are ranked
  lower rather than hidden, and `include_unavailable=false` hides them.
- **Ties** go to the smaller gap between experience and the minimum (the closer
  fit), then to the lower id, so ordering is deterministic.

A consequence worth knowing: on *Engineering Manager, Chaos Team*, Miranda has
the best skill coverage (2/3) but is not looking, so she ranks 4th. Setting
`w_skill=1&w_experience=0&w_culture=0` moves her to 1st, which is what the
tunable weights are for.

### Known limits, and what I'd do at scale

- Skills match by exact name. Real data would need synonyms and proficiency
  levels (a `skill_aliases` table and a level column on the link tables).
- `limit` is applied after ranking in Python. For a large candidate pool I would
  pre-filter with the reverse skill indexes (candidates sharing at least one
  required skill), rank and paginate in SQL, and cache results.
- SQLite is the right size for this prototype; production would use Postgres.
- No authentication, and no automated tests yet.

## Part 2: SQL Detective

- [`sql_detective.sql`](sql_detective.sql): the five answers, one query per
  question, each preceded by a comment with the question number and reasoning.
- [`sql_detective_data.sql`](sql_detective_data.sql): the dataset exactly as
  given.
- `python scripts/run_sql_detective.py` loads the data into an in-memory SQLite
  database and prints every result.

Notable points: Q3 treats applicants 1 and 2 as the same person (same email in
different letter case); Q2 keeps postings with zero finalists; Q4 uses decimal
division; Q5 uses `RANK() OVER (PARTITION BY department ...)`.

## Use of AI tools

I built this with Claude Code (an AI coding assistant), working one small commit
at a time. I used it to scaffold the code and the SQL, and to talk through the
design. The design decisions, including the schema and the scoring formula and
its weights, were reviewed and approved by me before they were committed. I
cross-checked the seed data and the SQL Detective answers against the brief.

## Project layout

```
app/
  main.py         FastAPI routes
  matching.py     ranking and tie-breaking, both directions
  scoring.py      pure scoring functions and the reason string
  repository.py   all hand-written SQL
  db.py           connection + schema setup
  seed.py         idempotent loader for data/seed_data.json
  schemas.py      response models
schema.sql        hand-written DDL
data/             seed data
scripts/          Part 2 runner
```
