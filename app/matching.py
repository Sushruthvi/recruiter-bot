"""Ranked matches in both directions: scoring plus deterministic ordering."""
import sqlite3

from app import repository
from app.scoring import DEFAULT_WEIGHTS, Weights, score_match


def _experience_gap(pair: dict) -> int:
    return abs(pair["experience_years"] - pair["min_experience_years"])


def _ranked(pairs: list[dict], weights: Weights, id_key: str) -> list[tuple[dict, dict]]:
    """Score the pairs, drop non-matches, and order best first.

    Ties on the displayed score go to the smaller experience gap (the closer
    fit), then to the lower id, so the order never changes between calls.
    """
    scored = []
    for pair in pairs:
        result = score_match(pair, weights)
        if result is not None:
            scored.append((pair, result))
    scored.sort(key=lambda pr: (-pr[1]["score"], _experience_gap(pr[0]), pr[0][id_key]))
    return scored


def matches_for_job(
    conn: sqlite3.Connection, job_id: int, weights: Weights = DEFAULT_WEIGHTS
) -> list[dict]:
    """Candidates ranked for one job."""
    pairs = repository.match_inputs(conn, job_id=job_id)
    return [
        {"candidate_id": p["candidate_id"], "candidate_name": p["candidate_name"], **r}
        for p, r in _ranked(pairs, weights, "candidate_id")
    ]


def matches_for_candidate(
    conn: sqlite3.Connection, candidate_id: int, weights: Weights = DEFAULT_WEIGHTS
) -> list[dict]:
    """Jobs ranked for one candidate."""
    pairs = repository.match_inputs(conn, candidate_id=candidate_id)
    return [
        {"job_id": p["job_id"], "job_title": p["job_title"], **r}
        for p, r in _ranked(pairs, weights, "job_id")
    ]
