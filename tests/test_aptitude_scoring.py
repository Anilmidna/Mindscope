"""Unit tests for scoring/aptitude.py — Day 7 requirement."""
import pytest
from scoring.aptitude import (
    AptitudeResult,
    DomainResult,
    score,
    score_domain,
    _normal_cdf_approx,
    _percentile,
    APTITUDE_NORMS,
    DOMAINS,
)

# ---------------------------------------------------------------------------
# Answer keys extracted from item banks (correct_answer values)
# ---------------------------------------------------------------------------
LOGICAL_KEY = {
    "LG-01": 1, "LG-02": 1, "LG-03": 1, "LG-04": 2, "LG-05": 1,
    "LG-06": 0, "LG-07": 0, "LG-08": 2, "LG-09": 2, "LG-10": 0,
    "LG-11": 2, "LG-12": 2, "LG-13": 0, "LG-14": 1, "LG-15": 1,
}
NUMERICAL_KEY = {
    "NM-01": 1, "NM-02": 1, "NM-03": 2, "NM-04": 2, "NM-05": 1,
    "NM-06": 2, "NM-07": 1, "NM-08": 1, "NM-09": 1, "NM-10": 2,
    "NM-11": 2, "NM-12": 1, "NM-13": 0, "NM-14": 1, "NM-15": 0,
}
VERBAL_KEY = {
    "VB-01": 1, "VB-02": 1, "VB-03": 1, "VB-04": 2, "VB-05": 1,
    "VB-06": 1, "VB-07": 1, "VB-08": 0, "VB-09": 2, "VB-10": 1,
    "VB-11": 2, "VB-12": 1, "VB-13": 1, "VB-14": 1, "VB-15": 2,
}
SPATIAL_KEY = {
    "SP-01": 1, "SP-02": 0, "SP-03": 1, "SP-04": 0, "SP-05": 1,
    "SP-06": 0, "SP-07": 3, "SP-08": 0, "SP-09": 3, "SP-10": 1,
    "SP-11": 1, "SP-12": 1, "SP-13": 2, "SP-14": 1, "SP-15": 1,
}


def _all_correct(key: dict) -> list:
    return [{"item_id": k, "answer": v, "response_time_ms": 5000} for k, v in key.items()]


def _all_wrong(key: dict) -> list:
    return [{"item_id": k, "answer": (v + 1) % 4, "response_time_ms": 5000} for k, v in key.items()]


# ---------------------------------------------------------------------------
# Normal CDF approximation
# ---------------------------------------------------------------------------

def test_cdf_midpoint():
    assert _normal_cdf_approx(0) == pytest.approx(0.5, abs=0.01)


def test_cdf_extremes():
    assert _normal_cdf_approx(-7) == 0.0
    assert _normal_cdf_approx(7) == 1.0


def test_cdf_positive():
    # z=1.645 ≈ 95th percentile
    assert _normal_cdf_approx(1.645) == pytest.approx(0.95, abs=0.01)


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

def test_percentile_at_mean():
    for domain in DOMAINS:
        pct = _percentile(APTITUDE_NORMS[domain]["mean"], domain)
        assert 45.0 <= pct <= 55.0, f"{domain} at mean should be ~50th, got {pct}"


def test_percentile_zero_std():
    pct = _percentile(10, "Logical", {"Logical": {"mean": 10, "std_dev": 0}})
    assert pct == 50.0


# ---------------------------------------------------------------------------
# score_domain — Logical
# ---------------------------------------------------------------------------

class TestScoreDomainLogical:
    def test_perfect_score(self):
        res = score_domain(_all_correct(LOGICAL_KEY), "Logical")
        assert res.correct == 15
        assert res.total == 15
        assert res.score_pct == 100.0
        assert res.percentile > 90

    def test_zero_score(self):
        res = score_domain(_all_wrong(LOGICAL_KEY), "Logical")
        assert res.correct == 0
        assert res.score_pct == 0.0
        assert res.percentile < 10

    def test_partial_score(self):
        responses = _all_correct(LOGICAL_KEY)[:8] + _all_wrong(LOGICAL_KEY)[8:]
        res = score_domain(responses, "Logical")
        assert res.correct == 8
        assert res.score_pct == pytest.approx(8 / 15 * 100, abs=0.2)

    def test_empty_responses(self):
        res = score_domain([], "Logical")
        assert res.correct == 0
        assert res.total == 0
        assert res.score_pct == 0.0

    def test_fast_response_flagging(self):
        responses = [{"item_id": k, "answer": v, "response_time_ms": 500}
                     for k, v in LOGICAL_KEY.items()]
        res = score_domain(responses, "Logical")
        assert res.fast_response_flags == 15

    def test_no_fast_flags_above_threshold(self):
        responses = [{"item_id": k, "answer": v, "response_time_ms": 3000}
                     for k, v in LOGICAL_KEY.items()]
        res = score_domain(responses, "Logical")
        assert res.fast_response_flags == 0

    def test_unknown_item_id_ignored(self):
        responses = [{"item_id": "FAKE-99", "answer": 1, "response_time_ms": 5000}]
        res = score_domain(responses, "Logical")
        assert res.correct == 0
        assert res.total == 0

    def test_missing_response_time_ok(self):
        responses = [{"item_id": k, "answer": v} for k, v in LOGICAL_KEY.items()]
        res = score_domain(responses, "Logical")
        assert res.correct == 15
        assert res.fast_response_flags == 0


# ---------------------------------------------------------------------------
# score_domain — other domains
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("domain,key", [
    ("Numerical", NUMERICAL_KEY),
    ("Verbal",    VERBAL_KEY),
    ("Spatial",   SPATIAL_KEY),
])
def test_perfect_score_all_domains(domain, key):
    res = score_domain(_all_correct(key), domain)
    assert res.correct == 15
    assert res.score_pct == 100.0


@pytest.mark.parametrize("domain,key", [
    ("Numerical", NUMERICAL_KEY),
    ("Verbal",    VERBAL_KEY),
    ("Spatial",   SPATIAL_KEY),
])
def test_zero_score_all_domains(domain, key):
    res = score_domain(_all_wrong(key), domain)
    assert res.correct == 0


# ---------------------------------------------------------------------------
# Full score() function
# ---------------------------------------------------------------------------

class TestFullScore:
    def test_all_domains_present(self):
        inp = {
            "Logical":   _all_correct(LOGICAL_KEY),
            "Numerical": _all_correct(NUMERICAL_KEY),
            "Verbal":    _all_correct(VERBAL_KEY),
            "Spatial":   _all_correct(SPATIAL_KEY),
        }
        result = score(inp)
        assert set(result.domains.keys()) == set(DOMAINS)

    def test_missing_domain_gets_zero(self):
        result = score({})
        for d in DOMAINS:
            assert result.domains[d].correct == 0
            assert result.domains[d].score_pct == 0.0

    def test_as_scores_dict_keys(self):
        result = score({d: _all_correct(k) for d, k in [
            ("Logical", LOGICAL_KEY), ("Numerical", NUMERICAL_KEY),
            ("Verbal", VERBAL_KEY), ("Spatial", SPATIAL_KEY),
        ]})
        scores = result.as_scores_dict()
        assert set(scores.keys()) == {"logical", "numerical", "verbal", "spatial"}

    def test_as_scores_dict_values_perfect(self):
        result = score({
            "Logical":   _all_correct(LOGICAL_KEY),
            "Numerical": _all_correct(NUMERICAL_KEY),
            "Verbal":    _all_correct(VERBAL_KEY),
            "Spatial":   _all_correct(SPATIAL_KEY),
        })
        for v in result.as_scores_dict().values():
            assert v == 100.0

    def test_as_percentiles_dict_keys(self):
        result = score({d: [] for d in DOMAINS})
        pcts = result.as_percentiles_dict()
        assert set(pcts.keys()) == {"logical", "numerical", "verbal", "spatial"}

    def test_percentiles_range(self):
        result = score({
            "Logical":   _all_correct(LOGICAL_KEY),
            "Numerical": _all_correct(NUMERICAL_KEY),
            "Verbal":    _all_correct(VERBAL_KEY),
            "Spatial":   _all_correct(SPATIAL_KEY),
        })
        for v in result.as_percentiles_dict().values():
            assert 0 <= v <= 100

    def test_custom_norms(self):
        custom = {d: {"mean": 15.0, "std_dev": 1.0} for d in DOMAINS}
        result = score(
            {"Logical": _all_correct(LOGICAL_KEY)},
            norms=custom,
        )
        # Perfect score of 15 at mean=15 → ~50th percentile
        assert 45 <= result.domains["Logical"].percentile <= 55

    def test_scoring_engine_version(self):
        result = score({})
        assert result.scoring_engine_version == "1.0"
