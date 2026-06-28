"""
Report output validator — Layer 3 guardrail (TDD §8.5).

Scans LLM JSON output for clinical/diagnostic language before storage.
"""
import json

BLOCKLIST = [
    "diagnosed with", "you may have", "you likely have",
    "disorder", "syndrome", "condition", "pathology",
    "medication", "prescription", "antidepressant",
    "seek therapy", "see a therapist", "psychiatrist",
    "mental illness", "clinical depression", "anxiety disorder",
    "ADHD", "autism", "bipolar", "schizophreni",
    "suicid", "self-harm", "self harm",
]

REQUIRED_KEYS = {"snapshot", "strengths", "friction_points", "career_directions", "next_steps"}


def validate_report(report_json: dict) -> tuple[bool, list[str]]:
    """
    Returns (is_valid, list_of_violations).
    Checks: clinical keyword blocklist, required JSON keys, snapshot length.
    """
    violations = []
    text = json.dumps(report_json).lower()

    for term in BLOCKLIST:
        if term.lower() in text:
            violations.append(f"Blocklisted term: '{term}'")

    missing = REQUIRED_KEYS - report_json.keys()
    if missing:
        violations.append(f"Missing required keys: {missing}")

    if len(report_json.get("snapshot", "")) > 2000:
        violations.append("Snapshot exceeds 2000 chars")

    return (len(violations) == 0, violations)
