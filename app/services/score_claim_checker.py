"""
Score-claim cross-checker — Layer 3 post-LLM validation (TDD §8.5).

Detects when the LLM cites a trait value that doesn't match the actual score.
This is a deterministic check — no Bedrock call required.
"""
import json
import re
from typing import Any

TRAIT_PATTERNS: dict[str, list[str]] = {
    "openness":          ["ocean_O", "ocean_O_pct"],
    "conscientiousness": ["ocean_C", "ocean_C_pct"],
    "extraversion":      ["ocean_E", "ocean_E_pct"],
    "agreeableness":     ["ocean_A", "ocean_A_pct"],
    "neuroticism":       ["ocean_N", "ocean_N_pct"],
    "logical":           ["apt_logical"],
    "numerical":         ["apt_numerical"],
    "verbal":            ["apt_verbal"],
    "spatial":           ["apt_spatial"],
    "realistic":         ["riasec_R"],
    "investigative":     ["riasec_I"],
    "artistic":          ["riasec_A"],
    "social":            ["riasec_S"],
    "enterprising":      ["riasec_E"],
    "conventional":      ["riasec_C"],
}

_TOLERANCE = 3


def _build_known_values(profile: dict) -> dict[str, float]:
    known: dict[str, float] = {}
    scores = profile.get("scores", {})

    riasec = scores.get("riasec", {})
    for code in ["R", "I", "A", "S", "E", "C"]:
        if code in riasec:
            known[f"riasec_{code}"] = float(riasec[code])

    ocean = scores.get("ocean", {})
    for trait in ["O", "C", "E", "A", "N"]:
        if trait in ocean:
            known[f"ocean_{trait}"] = float(ocean[trait])
    ocean_pct = ocean.get("percentiles", {})
    for trait, pct in ocean_pct.items():
        known[f"ocean_{trait}_pct"] = float(pct)

    aptitude = scores.get("aptitude", {})
    for domain in ["logical", "numerical", "verbal", "spatial"]:
        if domain in aptitude:
            known[f"apt_{domain}"] = float(aptitude[domain])
    apt_pct = aptitude.get("percentiles", {})
    for domain, pct in apt_pct.items():
        known[f"apt_{domain}_pct"] = float(pct)

    return known


def _flatten_report(report_json: dict) -> dict[str, str]:
    """Return a dict of section_name → section_text for per-section attribution."""
    sections: dict[str, str] = {}
    for key, value in report_json.items():
        if isinstance(value, str):
            sections[key] = value
        elif isinstance(value, (list, dict)):
            sections[key] = json.dumps(value)
    return sections


def check_score_claims(
    report_json: dict, profile: dict
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Scan report_json for numeric claims about trait scores and verify against profile.

    Returns (is_valid, mismatches) where each mismatch has:
        {trait, claimed_value, actual_value, section}
    """
    known_values = _build_known_values(profile)
    sections = _flatten_report(report_json)
    mismatches: list[dict] = []

    for section_name, section_text in sections.items():
        text_lower = section_text.lower()
        for trait_name, value_keys in TRAIT_PATTERNS.items():
            # Find each occurrence of the trait name in the text
            for match in re.finditer(re.escape(trait_name), text_lower):
                start = match.start()
                # Look for a number within 30 chars before or after the trait name
                window = section_text[max(0, start - 30): start + len(trait_name) + 30]
                numbers = re.findall(r"\b(\d+(?:\.\d+)?)(?:st|nd|rd|th)?\b", window)
                for num_str in numbers:
                    claimed = float(num_str)
                    # Check if claimed value matches any known value for this trait
                    matching_keys = [k for k in value_keys if k in known_values]
                    if not matching_keys:
                        continue
                    # It's a mismatch only if the number is close to what a score value
                    # would be (between 0–100) AND doesn't match any known value
                    if not (0 <= claimed <= 100):
                        continue
                    any_match = any(
                        abs(claimed - known_values[k]) <= _TOLERANCE
                        for k in matching_keys
                    )
                    if not any_match:
                        actual = known_values[matching_keys[0]]
                        mismatches.append({
                            "trait": trait_name,
                            "claimed_value": claimed,
                            "actual_value": actual,
                            "section": section_name,
                        })
                        # Only report one mismatch per trait per section occurrence
                        break

    is_valid = len(mismatches) == 0
    return is_valid, mismatches
