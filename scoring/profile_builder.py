"""Assembles the structured profile object passed to Bedrock (Claude Sonnet).

AI receives ONLY this object — never raw item responses.
Every field maps directly to a prompt grounding anchor.
"""
from typing import Dict, Optional
from scoring.riasec import RIASECResult
from scoring.ocean import OCEANResult

SCORING_ENGINE_VERSION = "1.0"


def build_profile(
    riasec: RIASECResult,
    ocean: OCEANResult,
    aptitude: Dict,        # {"logical": 82, "numerical": 67, "verbal": 74, "spatial": 55}
    intake: Dict,          # from IntakeForm model
    norm_group: str,
) -> Dict:
    """
    Returns a structured dict ready to be serialized and injected into the Bedrock prompt.
    Shape matches TDD section 5.4 exactly.
    """
    return {
        "user": {
            "name": intake.get("name", ""),
            "life_stage": intake.get("life_stage", ""),
            "current_role": intake.get("specialization", ""),
            "domain": intake.get("domain", ""),
            "education_level": intake.get("education_level", ""),
            "preferred_work_style": intake.get("preferred_work_style", ""),
        },
        "intake": {
            "future_goals": intake.get("future_goals", ""),
            "challenges": intake.get("challenges", ""),
            "satisfaction": intake.get("satisfaction"),
        },
        "scores": {
            "riasec": {
                "R": riasec.normalized["R"],
                "I": riasec.normalized["I"],
                "A": riasec.normalized["A"],
                "S": riasec.normalized["S"],
                "E": riasec.normalized["E"],
                "C": riasec.normalized["C"],
                "top_code": riasec.ranked_code[:3],
                "full_code": riasec.ranked_code,
            },
            "ocean": {
                "O": ocean.raw_scores["O"],
                "C": ocean.raw_scores["C"],
                "E": ocean.raw_scores["E"],
                "A": ocean.raw_scores["A"],
                "N": ocean.raw_scores["N"],
                "percentiles": ocean.percentiles,
            },
            "aptitude": {
                "logical": aptitude.get("logical", 0),
                "numerical": aptitude.get("numerical", 0),
                "verbal": aptitude.get("verbal", 0),
                "spatial": aptitude.get("spatial", 0),
            },
        },
        "meta": {
            "scoring_engine_version": SCORING_ENGINE_VERSION,
            "norm_group": norm_group,
            "persona": intake.get("persona", ""),
        },
    }
