"""Tests for norm group seeder and DB-driven scoring."""
import pytest
from unittest.mock import MagicMock, patch
from scripts.seed_norms import seed, NORM_ROWS
from scoring.riasec import score as riasec_score, _FALLBACK_NORMS
from scoring.ocean import score as ocean_score
from scoring.aptitude import score as aptitude_score, APTITUDE_NORMS


# ── Seeder tests ──────────────────────────────────────────────────────────────

def _make_mock_db(existing_contexts=None):
    """Return a mock DB session that simulates existing norm rows.

    seed() iterates NORM_ROWS in order and calls .filter().first() once per row.
    We return a non-None value for each context in existing_contexts.
    """
    existing_contexts = existing_contexts or set()
    # Build a first() return sequence matching NORM_ROWS order
    first_returns = [
        MagicMock() if row["context"] in existing_contexts else None
        for row in NORM_ROWS
    ]
    call_index = {"i": 0}

    def query_side_effect(model):
        mock_query = MagicMock()

        def filter_side_effect(*args, **kwargs):
            mock_filter = MagicMock()
            idx = call_index["i"]
            call_index["i"] += 1
            mock_filter.first.return_value = first_returns[idx] if idx < len(first_returns) else None
            return mock_filter

        mock_query.filter.side_effect = filter_side_effect
        return mock_query

    db = MagicMock()
    db.query.side_effect = query_side_effect
    return db


def test_seed_inserts_all_rows_when_empty():
    db = _make_mock_db(existing_contexts=set())
    inserted, skipped = seed(db)
    assert inserted == len(NORM_ROWS)
    assert skipped == 0
    assert db.add.call_count == len(NORM_ROWS)
    db.commit.assert_called_once()


def test_seed_skips_existing_rows():
    all_contexts = {r["context"] for r in NORM_ROWS}
    db = _make_mock_db(existing_contexts=all_contexts)
    inserted, skipped = seed(db)
    assert inserted == 0
    assert skipped == len(NORM_ROWS)
    db.add.assert_not_called()


def test_seed_is_idempotent_partial():
    # One already exists
    db = _make_mock_db(existing_contexts={"riasec-general"})
    inserted, skipped = seed(db)
    assert inserted + skipped == len(NORM_ROWS)


# ── RIASEC percentile tests ───────────────────────────────────────────────────

def _riasec_responses(scores_per_subscale: dict) -> list:
    """Build fake responses for given raw scores per subscale."""
    responses = []
    for subscale, total in scores_per_subscale.items():
        items_per = 8
        per_item = total // items_per
        remainder = total % items_per
        for i in range(items_per):
            answer = per_item + (1 if i < remainder else 0)
            answer = max(1, min(5, answer))
            responses.append({"item_id": f"S-{subscale}0{i+1}", "answer": answer})
    return responses


def test_riasec_score_returns_percentiles():
    responses = _riasec_responses({"R": 24, "I": 32, "A": 20, "S": 28, "E": 24, "C": 26})
    result = riasec_score(responses)
    assert hasattr(result, "percentiles")
    assert set(result.percentiles.keys()) == {"R", "I", "A", "S", "E", "C"}
    for v in result.percentiles.values():
        assert 0.0 <= v <= 100.0


def test_riasec_percentile_above_mean_exceeds_50():
    # I score above mean (24.5) → percentile > 50
    responses = _riasec_responses({"R": 23, "I": 30, "A": 22, "S": 26, "E": 24, "C": 25})
    result = riasec_score(responses)
    assert result.percentiles["I"] > 50.0


def test_riasec_uses_custom_norms():
    custom_norms = {s: {"mean": 20.0, "std_dev": 5.0} for s in ["R", "I", "A", "S", "E", "C"]}
    responses = _riasec_responses({"R": 30, "I": 30, "A": 30, "S": 30, "E": 30, "C": 30})
    result = riasec_score(responses, norms=custom_norms)
    # raw=30, mean=20, std=5 → z=2 → ~97.7th percentile
    for v in result.percentiles.values():
        assert v > 90.0


def test_riasec_fallback_norms_used_when_none():
    responses = _riasec_responses({"R": 23, "I": 25, "A": 23, "S": 26, "E": 25, "C": 26})
    result_none = riasec_score(responses, norms=None)
    result_explicit = riasec_score(responses, norms=_FALLBACK_NORMS)
    assert result_none.percentiles == result_explicit.percentiles


# ── OCEAN DB norms passthrough ────────────────────────────────────────────────

def test_ocean_accepts_db_norms():
    db_norms = {
        "O": {"mean": 30.0, "std_dev": 5.0},
        "C": {"mean": 30.0, "std_dev": 5.0},
        "E": {"mean": 30.0, "std_dev": 5.0},
        "A": {"mean": 30.0, "std_dev": 5.0},
        "N": {"mean": 30.0, "std_dev": 5.0},
    }
    responses = [{"item_id": f"O-{i:02d}", "answer": 4} for i in range(1, 11)]
    result = ocean_score(responses, norms=db_norms)
    assert result.percentiles["O"] > 50.0  # raw=40 > mean=30


# ── Aptitude DB norms passthrough ─────────────────────────────────────────────

def test_aptitude_accepts_db_norms():
    db_norms = {
        "Logical":   {"mean": 5.0, "std_dev": 2.0},
        "Numerical": {"mean": 5.0, "std_dev": 2.0},
        "Verbal":    {"mean": 5.0, "std_dev": 2.0},
        "Spatial":   {"mean": 5.0, "std_dev": 2.0},
    }
    # No real answers needed — just check norms are forwarded
    result = aptitude_score({}, norms=db_norms)
    # All domains get 0 correct → below mean of 5 → percentile < 50
    for domain_result in result.domains.values():
        assert domain_result.percentile < 50.0
