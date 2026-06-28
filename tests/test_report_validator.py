"""Tests for report output validator (Layer 3 guardrail)."""
from app.services.report_validator import validate_report, BLOCKLIST, REQUIRED_KEYS

_CLEAN_REPORT = {
    "snapshot": "You have strong investigative and artistic interests.",
    "strengths": "Your verbal aptitude is in the 84th percentile.",
    "friction_points": "Your satisfaction score of 4/10 suggests misalignment.",
    "career_directions": ["UX Research", "Data Science"],
    "next_steps": ["Take an advanced Python course", "Update your LinkedIn profile"],
}


def test_valid_report_passes():
    is_valid, violations = validate_report(_CLEAN_REPORT)
    assert is_valid
    assert violations == []


def test_missing_required_key_fails():
    bad = {k: v for k, v in _CLEAN_REPORT.items() if k != "snapshot"}
    is_valid, violations = validate_report(bad)
    assert not is_valid
    assert any("snapshot" in v for v in violations)


def test_all_required_keys_missing():
    is_valid, violations = validate_report({})
    assert not is_valid
    assert any("Missing required keys" in v for v in violations)


def test_blocklist_term_disorder_caught():
    bad = {**_CLEAN_REPORT, "snapshot": "You may have a personality disorder."}
    is_valid, violations = validate_report(bad)
    assert not is_valid
    assert any("disorder" in v for v in violations)


def test_blocklist_term_medication_caught():
    bad = {**_CLEAN_REPORT, "next_steps": ["Consider medication for your focus issues."]}
    is_valid, violations = validate_report(bad)
    assert not is_valid
    assert any("medication" in v for v in violations)


def test_blocklist_case_insensitive():
    bad = {**_CLEAN_REPORT, "strengths": "You may have ADHD traits."}
    is_valid, violations = validate_report(bad)
    assert not is_valid


def test_all_blocklist_terms_detected():
    """Each term in BLOCKLIST must be detectable."""
    for term in BLOCKLIST:
        report = {**_CLEAN_REPORT, "snapshot": f"Something about {term} here."}
        is_valid, _ = validate_report(report)
        assert not is_valid, f"Blocklist term not detected: '{term}'"


def test_snapshot_length_limit():
    bad = {**_CLEAN_REPORT, "snapshot": "x" * 2001}
    is_valid, violations = validate_report(bad)
    assert not is_valid
    assert any("Snapshot" in v for v in violations)


def test_snapshot_at_limit_passes():
    ok = {**_CLEAN_REPORT, "snapshot": "x" * 2000}
    is_valid, _ = validate_report(ok)
    assert is_valid


def test_multiple_violations_reported():
    bad = {
        "snapshot": "You have a disorder. " * 5,
        "strengths": "Take medication.",
        # missing friction_points, career_directions, next_steps
    }
    is_valid, violations = validate_report(bad)
    assert not is_valid
    assert len(violations) >= 2
