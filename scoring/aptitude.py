"""Aptitude scoring engine — deterministic, versioned.

Input:  list of {item_id, answer (0-indexed option selected)} per domain
Output: AptitudeResult with correct count, percentage, percentile per domain.

Correct answers are loaded from the item bank JSONs.
Score = number of correct answers per domain.
Timed section enforcement is handled at the API layer — this module scores only.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

VERSION = "1.0"

DOMAINS = ["Logical", "Numerical", "Verbal", "Spatial"]

BANK_PATHS = {
    "Logical":   Path("scoring/item_banks/aptitude_logical.json"),
    "Numerical": Path("scoring/item_banks/aptitude_numerical.json"),
    "Verbal":    Path("scoring/item_banks/aptitude_verbal.json"),
    "Spatial":   Path("scoring/item_banks/aptitude_spatial.json"),
}

# Published/estimated norms for percentile calculation (15 items per domain)
# Based on typical graduate population performance estimates
APTITUDE_NORMS = {
    "Logical":   {"mean": 8.5,  "std_dev": 2.8},
    "Numerical": {"mean": 8.0,  "std_dev": 2.9},
    "Verbal":    {"mean": 9.0,  "std_dev": 2.7},
    "Spatial":   {"mean": 7.5,  "std_dev": 3.0},
}

_answer_keys: Dict[str, Dict[str, int]] = {}


def _load_answer_key(domain: str) -> Dict[str, int]:
    if domain not in _answer_keys:
        path = BANK_PATHS.get(domain)
        if path and path.exists():
            with open(path, encoding='utf-8') as f:
                bank = json.load(f)
            _answer_keys[domain] = {
                item["item_id"]: item["correct_answer"]
                for item in bank.get("items", [])
            }
        else:
            _answer_keys[domain] = {}
    return _answer_keys[domain]


def _normal_cdf_approx(z: float) -> float:
    import math
    if z < -6:
        return 0.0
    if z > 6:
        return 1.0
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return p if z >= 0 else 1 - p


def _percentile(raw: float, domain: str, norms: Optional[Dict] = None) -> float:
    if norms is None:
        norms = APTITUDE_NORMS
    norm = norms.get(domain, {"mean": raw, "std_dev": 1})
    mean, std = norm["mean"], norm["std_dev"]
    if std == 0:
        return 50.0
    z = (raw - mean) / std
    return round(_normal_cdf_approx(z) * 100, 1)


@dataclass
class DomainResult:
    domain: str
    correct: int
    total: int
    score_pct: float          # correct / total * 100
    percentile: float
    fast_response_flags: int  # items answered in < 2s


@dataclass
class AptitudeResult:
    domains: Dict[str, DomainResult] = field(default_factory=dict)
    scoring_engine_version: str = VERSION

    def as_scores_dict(self) -> Dict[str, float]:
        """Returns format expected by profile_builder: {logical, numerical, verbal, spatial}."""
        return {d.lower(): self.domains[d].score_pct for d in DOMAINS if d in self.domains}

    def as_percentiles_dict(self) -> Dict[str, float]:
        return {d.lower(): self.domains[d].percentile for d in DOMAINS if d in self.domains}


def score_domain(responses: List[Dict], domain: str, norms: Optional[Dict] = None) -> DomainResult:
    """
    Score a single aptitude domain.
    responses: [{"item_id": "LG-01", "answer": 1, "response_time_ms": 4200}, ...]
    answer is 0-indexed option index matching correct_answer in the bank.
    """
    answer_key = _load_answer_key(domain)
    correct = 0
    total = len([r for r in responses if r["item_id"] in answer_key])
    fast_flags = 0

    for r in responses:
        item_id = r["item_id"]
        if item_id not in answer_key:
            continue
        if int(r["answer"]) == answer_key[item_id]:
            correct += 1
        rt = r.get("response_time_ms")
        if rt is not None and rt < 2000:
            fast_flags += 1

    score_pct = round(correct / total * 100, 1) if total > 0 else 0.0
    pct = _percentile(correct, domain, norms)

    return DomainResult(
        domain=domain,
        correct=correct,
        total=total,
        score_pct=score_pct,
        percentile=pct,
        fast_response_flags=fast_flags,
    )


def score(responses_by_domain: Dict[str, List[Dict]], norms: Optional[Dict] = None) -> AptitudeResult:
    """
    Score all aptitude domains.
    responses_by_domain: {"Logical": [...], "Numerical": [...], ...}
    """
    result = AptitudeResult()
    for domain in DOMAINS:
        responses = responses_by_domain.get(domain, [])
        result.domains[domain] = score_domain(responses, domain, norms)
    return result
