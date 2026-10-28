"""Match scoring: pure functions, no database access.

score = 100 * (w_skill*skill + w_experience*experience + w_culture*culture) * availability

  skill         matched required skills / required skills (coverage, so extra
                skills never hurt a candidate)
  experience    years / minimum when below the minimum, else 1.0 (no penalty
                for being over-qualified; the reason string just says so)
  culture       shared traits / the job's culture keywords (a small bonus, since
                traits and keywords overlap only sparsely)
  availability  a multiplier: ~1.0 when they can start soon, lower for long
                notice, and a heavy discount for candidates not looking

A candidate with no matching skill at all is not a match (score_match -> None).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Weights:
    skill: float = 0.65
    experience: float = 0.25
    culture: float = 0.10


DEFAULT_WEIGHTS = Weights()

NOT_LOOKING_FACTOR = 0.6   # multiplier for candidates who are not open to work
MAX_NOTICE_PENALTY = 0.15  # largest discount for a long notice period
NOTICE_CAP_DAYS = 90       # notice beyond this earns no further discount


def skill_fit(matched: int, required: int) -> float:
    return matched / required if required else 0.0


def experience_fit(years: int, min_years: int) -> float:
    if min_years <= 0 or years >= min_years:
        return 1.0
    return years / min_years


def culture_fit(shared: int, keywords: int) -> float:
    return shared / keywords if keywords else 0.0


def availability_factor(open_to_work: bool, notice_days: int) -> float:
    if not open_to_work:
        return NOT_LOOKING_FACTOR
    return 1.0 - MAX_NOTICE_PENALTY * min(notice_days / NOTICE_CAP_DAYS, 1.0)


def _yrs(n: int) -> str:
    return f"{n} yr" if n == 1 else f"{n} yrs"


def build_reason(pair: dict) -> str:
    """A short sentence explaining the score, built from the same inputs."""
    skills = f"{pair['matched_count']}/{pair['required_count']} required skills"
    if pair["matched_skills"]:
        skills += f" ({', '.join(pair['matched_skills'])})"
    if pair["missing_skills"]:
        skills += f", missing {', '.join(pair['missing_skills'])}"
    parts = [skills]

    years, minimum = pair["experience_years"], pair["min_experience_years"]
    if years < minimum:
        parts.append(f"{_yrs(years)}, below the {_yrs(minimum)} minimum")
    elif minimum > 0 and years >= 2 * minimum:
        parts.append(f"{_yrs(years)} vs {_yrs(minimum)} minimum (well above)")
    else:
        parts.append(f"{_yrs(years)} vs {_yrs(minimum)} minimum")

    if not pair["open_to_work"]:
        parts.append("not currently looking (ranked lower)")
    elif pair["notice_days"] == 0:
        parts.append("available immediately")
    else:
        parts.append(f"available in {pair['availability']}")

    if pair["shared_traits"]:
        parts.append(f"shares culture keywords: {', '.join(pair['shared_traits'])}")
    return "; ".join(parts)


def score_match(pair: dict, weights: Weights = DEFAULT_WEIGHTS) -> dict | None:
    """Score one candidate/job pair, or None when no required skill matches."""
    if pair["matched_count"] == 0:
        return None

    skill = skill_fit(pair["matched_count"], pair["required_count"])
    experience = experience_fit(pair["experience_years"], pair["min_experience_years"])
    culture = culture_fit(len(pair["shared_traits"]), pair["culture_total"])
    availability = availability_factor(bool(pair["open_to_work"]), pair["notice_days"])

    weighted = (
        weights.skill * skill
        + weights.experience * experience
        + weights.culture * culture
    )
    return {
        "score": round(100 * weighted * availability, 1),
        "breakdown": {
            "skill": round(skill, 3),
            "experience": round(experience, 3),
            "culture": round(culture, 3),
            "availability": round(availability, 3),
        },
        "matched_skills": pair["matched_skills"],
        "missing_skills": pair["missing_skills"],
        "reason": build_reason(pair),
    }
