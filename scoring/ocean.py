"""Big Five / OCEAN scoring engine — deterministic, versioned.

Input:  list of {item_id, answer (1-5)} — reverse-keyed items handled internally
Output: OCEANResult with raw trait scores, percentiles, social-desirability score.

Reverse-key formula: score = (LIKERT_MAX + 1) - raw_response
Social desirability items have item_ids containing 'SD' — scored separately.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional

VERSION = "1.0"

TRAITS = ["O", "C", "E", "A", "N"]
ITEMS_PER_TRAIT = 10
LIKERT_MAX = 5
SD_ITEMS_COUNT = 6

# Published BFI-2-S norms (standalone-public cohort, approximate)
# mean and std_dev per trait for percentile calculation
BFI_NORMS = {
    "O": {"mean": 35.2, "std_dev": 6.1},
    "C": {"mean": 33.8, "std_dev": 6.4},
    "E": {"mean": 30.5, "std_dev": 7.2},
    "A": {"mean": 36.1, "std_dev": 5.8},
    "N": {"mean": 25.4, "std_dev": 7.6},
}


@dataclass
class OCEANResult:
    raw_scores: Dict[str, float]
    percentiles: Dict[str, float]
    social_desirability_score: Optional[float]
    scoring_engine_version: str = VERSION


def _extract_trait(item_id: str) -> str:
    """Extract trait letter from item_id like 'BF-O01' or 'O-C04'."""
    parts = item_id.split("-")
    if len(parts) >= 2:
        return parts[1][0].upper()
    return ""


def _is_reverse_keyed(item_id: str, reverse_key_ids: set) -> bool:
    return item_id in reverse_key_ids


def _normal_cdf_approx(z: float) -> float:
    """Rational approximation of the normal CDF — good to ~0.001."""
    import math
    if z < -6:
        return 0.0
    if z > 6:
        return 1.0
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return p if z >= 0 else 1 - p


def _percentile_from_norm(raw: float, trait: str, norms: Dict) -> float:
    norm = norms.get(trait, {"mean": raw, "std_dev": 1})
    mean, std = norm["mean"], norm["std_dev"]
    if std == 0:
        return 50.0
    z = (raw - mean) / std
    return round(_normal_cdf_approx(z) * 100, 1)


def score(responses: List[Dict], reverse_key_ids: Optional[set] = None, norms: Optional[Dict] = None) -> OCEANResult:
    """
    responses: [{"item_id": "BF-O01", "answer": 3, "reverse_keyed": False}, ...]
    reverse_key_ids: set of item_ids that are reverse-keyed (can also read from response dict)
    norms: override default BFI norms (for different norm groups)
    """
    if reverse_key_ids is None:
        reverse_key_ids = set()
    if norms is None:
        norms = BFI_NORMS

    trait_scores: Dict[str, List[int]] = {t: [] for t in TRAITS}
    sd_scores: List[int] = []

    for r in responses:
        item_id = r["item_id"]
        answer = int(r["answer"])

        # Social desirability items
        if "SD" in item_id.upper() or "ATT" in item_id.upper():
            if "SD" in item_id.upper():
                sd_scores.append(answer)
            continue

        # Apply reverse-keying — check both the set and per-item flag
        is_rev = item_id in reverse_key_ids or r.get("reverse_keyed", False)
        scored = (LIKERT_MAX + 1 - answer) if is_rev else answer

        trait = _extract_trait(item_id)
        if trait in trait_scores:
            trait_scores[trait].append(scored)

    raw_scores: Dict[str, float] = {}
    percentiles: Dict[str, float] = {}

    for t in TRAITS:
        items = trait_scores[t]
        raw = sum(items) if items else 0
        raw_scores[t] = float(raw)
        percentiles[t] = _percentile_from_norm(raw, t, norms)

    sd_score = round(sum(sd_scores) / len(sd_scores), 2) if sd_scores else None

    return OCEANResult(
        raw_scores=raw_scores,
        percentiles=percentiles,
        social_desirability_score=sd_score,
    )
