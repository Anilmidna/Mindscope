"""RIASEC scoring engine — deterministic, versioned.

Input:  list of {item_id, answer (1-5)} from the responses table
Output: RIASECResult with raw scores, normalized scores, ranked six-code profile,
        and Cronbach's alpha per subscale.
"""
from dataclasses import dataclass, field
from typing import List, Dict

VERSION = "1.0"

SUBSCALES = ["R", "I", "A", "S", "E", "C"]
ITEMS_PER_SUBSCALE = 8
LIKERT_MAX = 5
LIKERT_MIN = 1


@dataclass
class RIASECResult:
    raw_scores: Dict[str, float]          # sum of Likert responses per subscale
    normalized: Dict[str, float]          # 0-100 scale
    ranked_code: str                       # e.g. "IRS"
    cronbach_alpha: Dict[str, float]
    scoring_engine_version: str = VERSION


def _extract_subscale(item_id: str) -> str:
    """Extract subscale letter from item_id like 'S-R01' or 'P-I04'."""
    parts = item_id.split("-")
    if len(parts) >= 2:
        return parts[1][0].upper()
    return ""


def _cronbach_alpha(responses: List[int]) -> float:
    """Compute Cronbach's alpha for a list of item scores."""
    n = len(responses)
    if n < 2:
        return 0.0
    total = sum(responses)
    item_variances = []
    for i in range(n):
        vals = [responses[i]]
        mean = sum(vals) / len(vals)
        item_variances.append(sum((v - mean) ** 2 for v in vals))
    total_variance = sum(
        (responses[i] - (total / n)) ** 2 for i in range(n)
    ) / n
    if total_variance == 0:
        return 0.0
    alpha = (n / (n - 1)) * (1 - sum(item_variances) / (n * total_variance))
    return round(max(0.0, min(1.0, alpha)), 3)


def score(responses: List[Dict]) -> RIASECResult:
    """
    responses: [{"item_id": "S-R01", "answer": 4}, ...]
    Attention check items (S-ATT*, P-ATT*) are silently excluded from scoring.
    """
    buckets: Dict[str, List[int]] = {s: [] for s in SUBSCALES}

    for r in responses:
        item_id = r["item_id"]
        answer = int(r["answer"])
        # Skip attention checks
        if "ATT" in item_id.upper():
            continue
        subscale = _extract_subscale(item_id)
        if subscale in buckets:
            buckets[subscale].append(answer)

    raw_scores: Dict[str, float] = {}
    normalized: Dict[str, float] = {}
    alphas: Dict[str, float] = {}

    max_possible = ITEMS_PER_SUBSCALE * LIKERT_MAX
    min_possible = ITEMS_PER_SUBSCALE * LIKERT_MIN

    for s in SUBSCALES:
        items = buckets[s]
        raw = sum(items) if items else 0
        raw_scores[s] = raw
        # Normalize to 0-100
        if max_possible > min_possible:
            normalized[s] = round((raw - min_possible) / (max_possible - min_possible) * 100, 1)
        else:
            normalized[s] = 0.0
        alphas[s] = _cronbach_alpha(items) if len(items) >= 2 else 0.0

    # Rank subscales by normalized score descending
    ranked = sorted(SUBSCALES, key=lambda s: normalized[s], reverse=True)
    ranked_code = "".join(ranked)

    return RIASECResult(
        raw_scores=raw_scores,
        normalized=normalized,
        ranked_code=ranked_code,
        cronbach_alpha=alphas,
    )
