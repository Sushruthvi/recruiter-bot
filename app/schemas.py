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


class Job(BaseModel):
    id: int
    title: str
    min_experience_years: int
    required_skills: list[str]
    culture_keywords: list[str]
    tagline: str | None
