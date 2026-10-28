"""Recruiter Bot API.  Run with:  uvicorn app.main:app --reload"""
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query

from app import matching, repository
from app.db import get_connection, init_db
from app.schemas import Candidate, CandidateMatch, Job, JobMatch
from app.scoring import DEFAULT_WEIGHTS, Weights


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_db(conn)
    conn.close()
    yield


app = FastAPI(
    title="Recruiter Bot",
    description="Ingests candidates and jobs, then ranks the best matches.",
    lifespan=lifespan,
)


def db_connection():
    """One short-lived connection per request (SQLite connections are not
    shared across threads)."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/candidates", response_model=list[Candidate])
def list_candidates(conn: sqlite3.Connection = Depends(db_connection)):
    return repository.list_candidates(conn)


@app.get("/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: int, conn: sqlite3.Connection = Depends(db_connection)):
    candidate = repository.get_candidate(conn, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    return candidate


def scoring_weights(
    w_skill: float | None = Query(None, ge=0, allow_inf_nan=False,
                                  description="Relative weight of skill coverage (default 0.65)"),
    w_experience: float | None = Query(None, ge=0, allow_inf_nan=False,
                                       description="Relative weight of experience fit (default 0.25)"),
    w_culture: float | None = Query(None, ge=0, allow_inf_nan=False,
                                    description="Relative weight of culture fit (default 0.10)"),
) -> Weights:
    """Optional per-request weights. Omitted ones keep their default, then all
    three are rescaled to sum to 1, so only their ratio matters."""
    weights = Weights(
        skill=DEFAULT_WEIGHTS.skill if w_skill is None else w_skill,
        experience=DEFAULT_WEIGHTS.experience if w_experience is None else w_experience,
        culture=DEFAULT_WEIGHTS.culture if w_culture is None else w_culture,
    )
    try:
        return weights.normalized()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/candidates/{candidate_id}/matches", response_model=list[JobMatch])
def candidate_matches(
    candidate_id: int,
    weights: Weights = Depends(scoring_weights),
    limit: int | None = Query(None, ge=1, le=100, description="Return at most this many matches"),
    conn: sqlite3.Connection = Depends(db_connection),
):
    """Jobs ranked best-first for one candidate."""
    if repository.get_candidate(conn, candidate_id) is None:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    return matching.matches_for_candidate(conn, candidate_id, weights, limit)


@app.get("/jobs/{job_id}/matches", response_model=list[CandidateMatch])
def job_matches(
    job_id: int,
    weights: Weights = Depends(scoring_weights),
    include_unavailable: bool = Query(
        True, description="Set false to hide candidates who are not looking"
    ),
    limit: int | None = Query(None, ge=1, le=100, description="Return at most this many matches"),
    conn: sqlite3.Connection = Depends(db_connection),
):
    """Candidates ranked best-first for one job."""
    if repository.get_job(conn, job_id) is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return matching.matches_for_job(conn, job_id, weights, include_unavailable, limit)


@app.get("/jobs", response_model=list[Job])
def list_jobs(conn: sqlite3.Connection = Depends(db_connection)):
    return repository.list_jobs(conn)


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: int, conn: sqlite3.Connection = Depends(db_connection)):
    job = repository.get_job(conn, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
