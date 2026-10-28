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
    conn: sqlite3.Connection,
    job_id: int,
    weights: Weights = DEFAULT_WEIGHTS,
    include_unavailable: bool = True,
    limit: int | None = None,
) -> list[dict]:
    """Candidates ranked for one job.

    include_unavailable=False drops candidates who are not looking, instead of
    just ranking them lower.
    """
    pairs = repository.match_inputs(conn, job_id=job_id)
    if not include_unavailable:
        pairs = [p for p in pairs if p["open_to_work"]]
    ranked = _ranked(pairs, weights, "candidate_id")[:limit]
    return [
        {"candidate_id": p["candidate_id"], "candidate_name": p["candidate_name"], **r}
        for p, r in ranked
    ]


def matches_for_candidate(
    conn: sqlite3.Connection,
    candidate_id: int,
    weights: Weights = DEFAULT_WEIGHTS,
    limit: int | None = None,
) -> list[dict]:
    """Jobs ranked for one candidate."""
    pairs = repository.match_inputs(conn, candidate_id=candidate_id)
    ranked = _ranked(pairs, weights, "job_id")[:limit]
    return [
        {"job_id": p["job_id"], "job_title": p["job_title"], **r}
        for p, r in ranked
    ]
