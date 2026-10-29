import pytest

from app.scoring import (
    Weights,
    availability_factor,
    build_reason,
    culture_fit,
    experience_fit,
    score_match,
    skill_fit,
)


def make_pair(**overrides):
    """A candidate/job pair with a perfect skill match, immediately available."""
    pair = {
        "experience_years": 5,
        "min_experience_years": 3,
        "open_to_work": 1,
        "notice_days": 0,
        "availability": "Immediate",
        "required_count": 2,
        "matched_count": 2,
        "matched_skills": ["a", "b"],
        "missing_skills": [],
        "culture_total": 2,
        "shared_traits": [],
    }
    pair.update(overrides)
    return pair


class TestComponents:
    def test_skill_fit_is_coverage_of_required_skills(self):
        assert skill_fit(2, 4) == 0.5
        assert skill_fit(3, 3) == 1.0

    def test_skill_fit_with_no_required_skills_is_zero(self):
        assert skill_fit(0, 0) == 0.0

    def test_experience_at_or_above_minimum_is_not_penalised(self):
        assert experience_fit(3, 3) == 1.0
        assert experience_fit(20, 2) == 1.0

    def test_experience_below_minimum_scales_proportionally(self):
        assert experience_fit(2, 4) == 0.5

    def test_zero_minimum_experience_always_fits(self):
        assert experience_fit(0, 0) == 1.0

    def test_culture_fit_is_share_of_job_keywords(self):
        assert culture_fit(1, 2) == 0.5
        assert culture_fit(0, 0) == 0.0


class TestAvailability:
    def test_immediate_has_no_discount(self):
        assert availability_factor(True, 0) == 1.0

    def test_notice_period_discounts_smoothly(self):
        assert availability_factor(True, 14) == pytest.approx(1 - 0.15 * 14 / 90)

    def test_discount_is_capped_for_long_notice(self):
        assert availability_factor(True, 90) == pytest.approx(0.85)
        assert availability_factor(True, 365) == pytest.approx(0.85)

    def test_not_looking_gets_heavy_discount(self):
        assert availability_factor(False, 0) == 0.6


class TestWeights:
    def test_normalized_weights_sum_to_one(self):
        w = Weights(6.5, 2.5, 1.0).normalized()
        assert w.skill + w.experience + w.culture == pytest.approx(1.0)

    def test_only_the_ratio_matters(self):
        w = Weights(6.5, 2.5, 1.0).normalized()
        assert w.skill == pytest.approx(0.65)
        assert w.experience == pytest.approx(0.25)
        assert w.culture == pytest.approx(0.10)

    def test_all_zero_weights_are_rejected(self):
        with pytest.raises(ValueError):
            Weights(0, 0, 0).normalized()


class TestScoreMatch:
    def test_no_matching_skill_is_not_a_match(self):
        pair = make_pair(matched_count=0, matched_skills=[], missing_skills=["a", "b"])
        assert score_match(pair) is None

    def test_perfect_skills_and_experience_without_culture_scores_90(self):
        assert score_match(make_pair())["score"] == 90.0

    def test_shared_culture_adds_a_small_bonus(self):
        pair = make_pair(shared_traits=["x", "y"])
        assert score_match(pair)["score"] == 100.0

    def test_not_looking_multiplies_the_score(self):
        pair = make_pair(open_to_work=0)
        assert score_match(pair)["score"] == pytest.approx(90.0 * 0.6)

    def test_partial_skills_lower_the_score(self):
        pair = make_pair(matched_count=1, matched_skills=["a"], missing_skills=["b"])
        # 0.65 * 0.5 + 0.25 * 1.0 = 0.575
        assert score_match(pair)["score"] == 57.5

    def test_below_minimum_experience_lowers_the_score(self):
        pair = make_pair(experience_years=1, min_experience_years=4)
        # 0.65 + 0.25 * 0.25 = 0.7125 -> 71.2 (rounded to one decimal)
        assert score_match(pair)["score"] == pytest.approx(71.2, abs=0.1)

    def test_result_includes_breakdown_and_reason(self):
        result = score_match(make_pair())
        assert set(result["breakdown"]) == {"skill", "experience", "culture", "availability"}
        assert isinstance(result["reason"], str) and result["reason"]

    def test_custom_weights_change_the_score(self):
        pair = make_pair(matched_count=1, matched_skills=["a"], missing_skills=["b"])
        skills_only = Weights(1, 0, 0)
        assert score_match(pair, skills_only)["score"] == 50.0


class TestReason:
    def test_reason_names_missing_skills(self):
        pair = make_pair(matched_count=1, matched_skills=["a"], missing_skills=["b"])
        assert "missing b" in build_reason(pair)

    def test_reason_flags_unavailable_candidates(self):
        assert "not currently looking" in build_reason(make_pair(open_to_work=0))

    def test_reason_flags_experience_below_minimum(self):
        pair = make_pair(experience_years=1, min_experience_years=4)
        assert "below the 4 yrs minimum" in build_reason(pair)

    def test_reason_flags_experience_well_above_minimum(self):
        pair = make_pair(experience_years=20, min_experience_years=2)
        assert "well above" in build_reason(pair)

    def test_reason_mentions_notice_period(self):
        pair = make_pair(notice_days=14, availability="2 weeks")
        assert "available in 2 weeks" in build_reason(pair)
