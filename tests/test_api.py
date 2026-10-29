import pytest


def names(matches, key="candidate_name"):
    return [m[key] for m in matches]


class TestBrowse:
    def test_health(self, client):
        assert client.get("/health").json() == {"status": "ok"}

    def test_lists_seeded_data(self, client):
        assert len(client.get("/candidates").json()) == 15
        assert len(client.get("/jobs").json()) == 6

    def test_availability_is_rendered_in_the_briefs_wording(self, client, ids):
        by_name = {c["name"]: c for c in client.get("/candidates").json()}
        assert by_name["Sherlock H."]["availability"] == "Immediate"
        assert by_name["Hermione G."]["availability"] == "2 weeks"
        assert by_name["Tony S."]["availability"] == "Not looking"

    def test_unknown_candidate_and_job_are_404(self, client):
        assert client.get("/candidates/999").status_code == 404
        assert client.get("/jobs/999").status_code == 404


class TestJobMatches:
    def test_ranks_candidates_best_first(self, client, ids):
        job = ids["jobs"]["Rapid Prototyping Engineer"]
        matches = client.get(f"/jobs/{job}/matches").json()
        assert [(m["candidate_name"], m["score"]) for m in matches] == [
            ("Rick S.", 90.0),
            ("MacGyver", 87.9),
            ("Tony S.", 57.0),
        ]

    def test_response_has_score_breakdown_skills_and_reason(self, client, ids):
        job = ids["jobs"]["Backend Detective"]
        top = client.get(f"/jobs/{job}/matches").json()[0]
        assert top["candidate_name"] == "Sherlock H."
        assert top["score"] == 95.0
        assert top["missing_skills"] == []
        assert top["matched_skills"] == ["deduction", "forensics", "pattern-recognition"]
        assert set(top["breakdown"]) == {"skill", "experience", "culture", "availability"}
        assert "3/3 required skills" in top["reason"]

    def test_candidates_without_any_required_skill_are_excluded(self, client, ids):
        job = ids["jobs"]["Backend Detective"]
        matches = client.get(f"/jobs/{job}/matches").json()
        assert names(matches) == ["Sherlock H.", "Sheldon C."]

    def test_missing_skills_are_reported(self, client, ids):
        job = ids["jobs"]["Backend Detective"]
        sheldon = client.get(f"/jobs/{job}/matches").json()[1]
        assert sheldon["missing_skills"] == ["deduction", "forensics"]

    def test_equal_scores_are_ordered_by_closest_experience_fit(self, client, ids):
        # Leslie (6 yrs) and Ted (7 yrs) tie at 51.7 for a 5-year minimum;
        # Leslie is the closer fit.
        job = ids["jobs"]["Engineering Manager, Chaos Team"]
        matches = client.get(f"/jobs/{job}/matches").json()
        assert [m["score"] for m in matches[:2]] == [51.7, 51.7]
        assert names(matches[:2]) == ["Leslie K.", "Ted L."]

    def test_scores_are_sorted_descending_and_within_range(self, client, ids):
        for job_id in ids["jobs"].values():
            scores = [m["score"] for m in client.get(f"/jobs/{job_id}/matches").json()]
            assert scores == sorted(scores, reverse=True)
            assert all(0 < s <= 100 for s in scores)

    def test_unknown_job_is_404(self, client):
        assert client.get("/jobs/999/matches").status_code == 404

    def test_non_numeric_job_id_is_422(self, client):
        assert client.get("/jobs/abc/matches").status_code == 422


class TestCandidateMatches:
    def test_ranks_jobs_for_a_candidate(self, client, ids):
        rick = ids["candidates"]["Rick S."]
        matches = client.get(f"/candidates/{rick}/matches").json()
        assert [(m["job_title"], m["score"]) for m in matches] == [
            ("Rapid Prototyping Engineer", 90.0)
        ]

    def test_both_directions_agree_on_the_score(self, client, ids):
        for cname, cid in ids["candidates"].items():
            for m in client.get(f"/candidates/{cid}/matches").json():
                reverse = client.get(f"/jobs/{m['job_id']}/matches").json()
                same = next(r for r in reverse if r["candidate_id"] == cid)
                assert same["score"] == m["score"], cname

    def test_unknown_candidate_is_404(self, client):
        assert client.get("/candidates/999/matches").status_code == 404


class TestQueryParameters:
    def test_weights_change_the_ranking(self, client, ids):
        job = ids["jobs"]["Engineering Manager, Chaos Team"]
        default = client.get(f"/jobs/{job}/matches").json()
        skills_only = client.get(
            f"/jobs/{job}/matches?w_skill=1&w_experience=0&w_culture=0"
        ).json()
        assert default[0]["candidate_name"] != "Miranda P."
        assert skills_only[0]["candidate_name"] == "Miranda P."

    def test_only_the_weight_ratio_matters(self, client, ids):
        job = ids["jobs"]["Engineering Manager, Chaos Team"]
        default = client.get(f"/jobs/{job}/matches").json()
        scaled = client.get(
            f"/jobs/{job}/matches?w_skill=6.5&w_experience=2.5&w_culture=1"
        ).json()
        assert default == scaled

    def test_include_unavailable_false_hides_candidates_not_looking(self, client, ids):
        job = ids["jobs"]["Rapid Prototyping Engineer"]
        matches = client.get(f"/jobs/{job}/matches?include_unavailable=false").json()
        assert names(matches) == ["Rick S.", "MacGyver"]

    def test_limit_caps_the_number_of_results(self, client, ids):
        job = ids["jobs"]["Rapid Prototyping Engineer"]
        matches = client.get(f"/jobs/{job}/matches?limit=1").json()
        assert names(matches) == ["Rick S."]

    @pytest.mark.parametrize(
        "query",
        [
            "w_skill=-1",
            "w_skill=abc",
            "w_skill=inf",
            "w_skill=0&w_experience=0&w_culture=0",
            "limit=0",
            "limit=101",
        ],
    )
    def test_invalid_parameters_are_422(self, client, ids, query):
        job = ids["jobs"]["Rapid Prototyping Engineer"]
        assert client.get(f"/jobs/{job}/matches?{query}").status_code == 422

    def test_weights_also_apply_to_the_candidate_direction(self, client, ids):
        olivia = ids["candidates"]["Olivia P."]
        default = client.get(f"/candidates/{olivia}/matches").json()
        culture_only = client.get(
            f"/candidates/{olivia}/matches?w_skill=0&w_experience=0&w_culture=1"
        ).json()
        assert default[0]["score"] != culture_only[0]["score"]
