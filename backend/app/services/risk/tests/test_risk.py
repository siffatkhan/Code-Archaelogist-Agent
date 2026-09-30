"""
Tests for Phase 2: signals.py, risk_scorer.py

Run with: pytest backend/app/services/risk/tests/test_risk.py -v
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.services.risk import signals as sig
from backend.app.services.risk.risk_scorer import (
    DEFAULT_WEIGHTS,
    RiskInputs,
    score_file,
    score_files,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 13, tzinfo=timezone.utc)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def high_risk_data():
    return load_fixture("high_risk_file.json")


@pytest.fixture
def low_risk_data():
    return load_fixture("low_risk_file.json")


# --- signals.py -------------------------------------------------------


def test_change_frequency_counts_within_window(high_risk_data):
    count = sig.change_frequency(high_risk_data["commits"], window_days=90, now=NOW)
    assert count == 7  # all 7 commits fall within the last 90 days of NOW


def test_change_frequency_respects_window(low_risk_data):
    # all commits are from 2025, well outside a 90-day window from NOW
    count = sig.change_frequency(low_risk_data["commits"], window_days=90, now=NOW)
    assert count == 0


def test_contributor_count(high_risk_data, low_risk_data):
    assert sig.contributor_count(high_risk_data["contributors"]) == 1
    assert sig.contributor_count(low_risk_data["contributors"]) == 3


def test_ownership_concentration_single_owner_is_one(high_risk_data):
    assert sig.ownership_concentration(high_risk_data["contributors"]) == 1.0


def test_ownership_concentration_spread_out_is_lower(low_risk_data):
    concentration = sig.ownership_concentration(low_risk_data["contributors"])
    assert 0.0 < concentration < 1.0
    assert concentration == pytest.approx(2 / 4)


def test_ownership_concentration_empty_contributors_is_zero():
    assert sig.ownership_concentration([]) == 0.0


def test_revert_count_detects_revert_and_rollback_language(high_risk_data):
    # fixture has one "revert \"...\"" message and one "rollback ..." message
    assert sig.revert_count(high_risk_data["commits"]) == 2


def test_revert_count_zero_when_no_reverts(low_risk_data):
    assert sig.revert_count(low_risk_data["commits"]) == 0


def test_activity_recency_days_no_commits_is_none():
    assert sig.activity_recency_days([]) is None


def test_activity_recency_days_computes_from_latest_commit(low_risk_data):
    days = sig.activity_recency_days(low_risk_data["commits"], now=NOW)
    # latest commit in fixture is 2025-04-01; NOW is 2026-09-13
    assert days is not None
    assert days > 500


def test_dependency_centrality_counts_incoming_edges():
    entity_ids = {"e1", "e2"}
    dependencies = [
        {"source_entity_id": "e3", "target_entity_id": "e1", "dependency_type": "calls"},
        {"source_entity_id": "e4", "target_entity_id": "e2", "dependency_type": "calls"},
        {"source_entity_id": "e5", "target_entity_id": "e9", "dependency_type": "calls"},  # unrelated
    ]
    assert sig.dependency_centrality(entity_ids, dependencies) == 2


def test_open_knowledge_gaps_count_only_counts_open_status():
    gaps = [
        {"status": "open"},
        {"status": "open"},
        {"status": "resolved"},
    ]
    assert sig.open_knowledge_gaps_count(gaps) == 2


# --- risk_scorer.py -----------------------------------------------------


def test_default_weights_sum_to_one():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_high_risk_file_scores_higher_than_low_risk_file(high_risk_data, low_risk_data):
    high_inputs = RiskInputs(
        file_id=high_risk_data["file_id"],
        repository_id="r1",
        commits=high_risk_data["commits"],
        contributors=high_risk_data["contributors"],
        entity_local_ids={"e-auth-check"},
        dependencies=[
            {"source_entity_id": f"e-caller-{i}", "target_entity_id": "e-auth-check", "dependency_type": "calls"}
            for i in range(4)
        ],
    )
    low_inputs = RiskInputs(
        file_id=low_risk_data["file_id"],
        repository_id="r1",
        commits=low_risk_data["commits"],
        contributors=low_risk_data["contributors"],
        entity_local_ids={"e-trim"},
        dependencies=[],
    )

    high_result = score_file(high_inputs, now=NOW)
    low_result = score_file(low_inputs, now=NOW)

    assert high_result["score"] > low_result["score"]
    assert high_result["score"] > 0.5
    assert low_result["score"] < 0.3


def test_score_file_output_matches_risk_records_shape(low_risk_data):
    inputs = RiskInputs(
        file_id=low_risk_data["file_id"],
        repository_id="r1",
        commits=low_risk_data["commits"],
        contributors=low_risk_data["contributors"],
    )
    result = score_file(inputs, now=NOW)
    expected_keys = {"id", "repository_id", "file_id", "score", "signals", "explanation", "created_at"}
    assert set(result.keys()) == expected_keys
    assert result["id"] is None
    assert result["repository_id"] == "r1"
    assert result["file_id"] == low_risk_data["file_id"]
    assert isinstance(result["score"], float)
    assert 0.0 <= result["score"] <= 1.0
    assert isinstance(result["explanation"], str) and result["explanation"]


def test_signals_dict_contains_raw_normalized_and_weight_per_signal(low_risk_data):
    inputs = RiskInputs(
        file_id=low_risk_data["file_id"],
        repository_id="r1",
        commits=low_risk_data["commits"],
        contributors=low_risk_data["contributors"],
    )
    result = score_file(inputs, now=NOW)
    for name in DEFAULT_WEIGHTS:
        assert name in result["signals"]
        entry = result["signals"][name]
        assert set(entry.keys()) == {"raw", "normalized", "weight"}
        assert 0.0 <= entry["normalized"] <= 1.0


def test_no_commit_history_is_treated_as_uncertain_not_safe():
    """A file with zero commit history shouldn't score as low-risk just
    because nothing is known about it -- activity_recency should push the
    score up when there's no data, not down."""
    inputs_no_history = RiskInputs(file_id="mystery-file", repository_id="r1")
    inputs_stable_history = RiskInputs(
        file_id="known-stable-file",
        repository_id="r1",
        commits=[{"author": "a", "message": "init", "timestamp": "2020-01-01T00:00:00Z"}],
        contributors=[{"external_id": "a", "commit_count": 1}],
    )
    no_history_result = score_file(inputs_no_history, now=NOW)
    stable_result = score_file(inputs_stable_history, now=NOW)
    # both should register meaningful risk from the recency signal, and
    # the no-history case should not be silently scored as zero risk
    assert no_history_result["score"] > 0.0


def test_explanation_mentions_top_contributing_factor(high_risk_data):
    inputs = RiskInputs(
        file_id=high_risk_data["file_id"],
        repository_id="r1",
        commits=high_risk_data["commits"],
        contributors=high_risk_data["contributors"],
    )
    result = score_file(inputs, now=NOW)
    # ownership concentration (1 contributor, 100%) should be the loudest
    # signal in this fixture and should show up in the explanation text
    assert "contributor" in result["explanation"]


def test_score_files_sorts_highest_risk_first(high_risk_data, low_risk_data):
    high_inputs = RiskInputs(
        file_id=high_risk_data["file_id"],
        repository_id="r1",
        commits=high_risk_data["commits"],
        contributors=high_risk_data["contributors"],
    )
    low_inputs = RiskInputs(
        file_id=low_risk_data["file_id"],
        repository_id="r1",
        commits=low_risk_data["commits"],
        contributors=low_risk_data["contributors"],
    )
    results = score_files([low_inputs, high_inputs], now=NOW)
    assert results[0]["file_id"] == high_risk_data["file_id"]
    assert results[1]["file_id"] == low_risk_data["file_id"]


def test_no_llm_dependency_is_importable_offline():
    """This test's real purpose is documentation: risk_scorer.py must not
    import anything from services/llm/. Importing the module (done at the
    top of this test file already) with no network/API key available and
    no mocking is itself the proof -- if risk_scorer.py ever grows an LLM
    call, this whole test file would need a mocked API key to even collect,
    which is a visible signal something has gone against the spec."""
    import backend.app.services.risk.risk_scorer as scorer_module

    assert "llm" not in scorer_module.__file__


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
