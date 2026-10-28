"""Response models. They also drive the interactive docs at /docs."""
from pydantic import BaseModel


class Candidate(BaseModel):
    id: int
    name: str
    experience_years: int
    availability: str  # human-readable: "Immediate", "2 weeks", "Not looking"
    open_to_work: bool
    notice_days: int
    skills: list[str]
    traits: list[str]
    quirk: str | None


class ScoreBreakdown(BaseModel):
    """Each component is 0-1; availability is the multiplier applied last."""
    skill: float
    experience: float
    culture: float
    availability: float


class MatchDetails(BaseModel):
    score: float
    breakdown: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    reason: str


class CandidateMatch(MatchDetails):
    """A candidate ranked for a job."""
    candidate_id: int
    candidate_name: str


class JobMatch(MatchDetails):
    """A job ranked for a candidate."""
    job_id: int
    job_title: str


class Job(BaseModel):
    id: int
    title: str
    min_experience_years: int
    required_skills: list[str]
    culture_keywords: list[str]
    tagline: str | None
