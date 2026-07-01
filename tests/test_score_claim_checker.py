"""Tests for score-claim cross-checker (Task 5)."""
import pytest

from app.services.score_claim_checker import check_score_claims


def _make_profile(**overrides) -> dict:
    base = {
        "scores": {
            "riasec": {"R": 55, "I": 70, "A": 40, "S": 60, "E": 50, "C": 45},
            "ocean": {
                "O": 78, "C": 65, "E": 55, "A": 72, "N": 30,
                "percentiles": {"O": 78, "C": 65, "E": 55, "A": 72, "N": 30},
            },
            "aptitude": {
                "logical": 82, "numerical": 74, "verbal": 68, "spatial": 60,
            },
        }
    }
    base["scores"].update(overrides)
    return base


class TestScoreClaimChecker:
    def test_correct_openness_percentile_passes(self):
        profile = _make_profile()
        report = {
            "snapshot": "You scored Openness at 78th percentile, showing high curiosity.",
            "strengths": "Strong investigative drive.",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is True
        assert mismatches == []

    def test_wrong_openness_percentile_detected(self):
        profile = _make_profile()
        report = {
            "snapshot": "You scored Openness at 85th percentile.",
            "strengths": "",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is False
        assert any(m["trait"] == "openness" and m["claimed_value"] == 85.0 for m in mismatches)

    def test_correct_logical_score_passes(self):
        profile = _make_profile()
        report = {
            "snapshot": "Your logical reasoning score of 82 places you above average.",
            "strengths": "",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is True
        assert mismatches == []

    def test_no_numbers_in_report_passes(self):
        profile = _make_profile()
        report = {
            "snapshot": "You show strong openness and extraversion traits.",
            "strengths": "Good logical and verbal reasoning.",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is True
        assert mismatches == []

    def test_number_near_unrelated_word_no_false_positive(self):
        profile = _make_profile()
        report = {
            "snapshot": "With 5 years of experience, you demonstrate strong skills.",
            "strengths": "Top 10 in class performance.",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is True
        assert mismatches == []

    def test_mismatch_includes_section_name(self):
        profile = _make_profile()
        report = {
            "snapshot": "",
            "strengths": "Your conscientiousness score is 99.",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is False
        assert mismatches[0]["section"] == "strengths"

    def test_value_within_tolerance_passes(self):
        profile = _make_profile()
        # actual O=78, claimed 80 (within ±3)
        report = {
            "snapshot": "Your openness score is approximately 80.",
            "strengths": "",
            "friction_points": "",
            "career_directions": "",
            "next_steps": "",
        }
        is_valid, mismatches = check_score_claims(report, profile)
        assert is_valid is True

    def test_empty_report_passes(self):
        profile = _make_profile()
        is_valid, mismatches = check_score_claims({}, profile)
        assert is_valid is True
        assert mismatches == []
