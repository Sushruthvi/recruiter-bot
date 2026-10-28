"""Recruiter Bot API.  Run with:  uvicorn app.main:app --reload"""
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from app import repository
from app.db import get_connection, init_db
from app.schemas import Candidate, Job


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


@app.get("/jobs", response_model=list[Job])
def list_jobs(conn: sqlite3.Connection = Depends(db_connection)):
    return repository.list_jobs(conn)


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: int, conn: sqlite3.Connection = Depends(db_connection)):
    job = repository.get_job(conn, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
