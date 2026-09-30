"""
risk_scorer.py

Combines the raw signals from signals.py into a single risk score per
file, plus the raw contributing signals and a plain-English explanation --
matching the API Contract's GET /repositories/{repository_id}/risks
response ("file/module, score, contributing signals, explanation") and
the `risk_records` table shape.

This entire module is deterministic arithmetic. No LLM call belongs here
-- the Technical Build Specification is explicit that risk must be
"deterministic signals, not an LLM guess." If a future change wants an
LLM to phrase the explanation more naturally, that's fine as a presentation
layer on top of this output, but the score itself must stay computable
from signals.py alone, reproducibly, with no model in the loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from . import signals as sig

# --- Weights -----------------------------------------------------------
#
# These are a starting point, not a scientifically derived formula --
# there's no ground truth dataset for "how risky is this file" to fit
# against in a hackathon. The weights below reflect a judgment call:
# ownership concentration and dependency centrality get the most weight
# because "one person understands this and a lot depends on it" is the
# core thing this whole feature exists to catch (per the PRD's framing
# of the offboarding problem). Reverts and change frequency matter but
# less. Knowledge gaps get the smallest weight since Phase 5 (which
# produces them) may still be sparse early in a repository's analysis.
# Change these together with risk_scorer's tests if you do -- they're
# meant to be tuned, not treated as fixed constants.

DEFAULT_WEIGHTS: dict[str, float] = {
    "ownership_concentration": 0.25,
    "dependency_centrality": 0.20,
    "change_frequency": 0.15,
    "revert_count": 0.15,
    "contributor_count": 0.15,  # inverse: fewer contributors = higher risk
    "activity_recency": 0.05,
    "knowledge_gaps": 0.05,
}

assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9, "risk weights must sum to 1.0"


# --- Normalization -------------------------------------------------------
#
# Each raw signal is squashed into 0.0-1.0 so weights can be combined
# meaningfully. The caps below (e.g. "30 commits in 90 days = max risk
# from this signal") are reasonable guesses for a typical repository, not
# universal constants -- documented here so they're easy to find and
# adjust once real repository data shows they're off.


def _normalize_change_frequency(raw: int, cap: int = 30) -> float:
    return min(raw / cap, 1.0) if cap > 0 else 0.0


def _normalize_contributor_count(raw: int, cap: int = 10) -> float:
    """Inverted: 1 contributor -> 1.0 (highest risk), `cap` or more -> 0.0."""
    if raw <= 1:
        return 1.0
    return max(1.0 - (raw - 1) / (cap - 1), 0.0) if cap > 1 else 0.0


def _normalize_revert_count(raw: int, cap: int = 5) -> float:
    return min(raw / cap, 1.0) if cap > 0 else 0.0


def _normalize_recency(days: Optional[int], cap_days: int = 365) -> float:
    """No commit history at all is treated as maximum uncertainty (1.0),
    not as "safe because nothing ever changes" -- an untouched, unexplained
    file is exactly the kind of thing this feature should flag, not ignore.
    Otherwise: older last-touch = higher risk, capped at `cap_days`."""
    if days is None:
        return 1.0
    return min(days / cap_days, 1.0) if cap_days > 0 else 0.0


def _normalize_dependency_centrality(raw: int, cap: int = 5) -> float:
    return min(raw / cap, 1.0) if cap > 0 else 0.0


def _normalize_knowledge_gaps(raw: int, cap: int = 3) -> float:
    return min(raw / cap, 1.0) if cap > 0 else 0.0


@dataclass
class RiskInputs:
    """Everything score_file() needs for one file, gathered from other
    modules. Grouping them here keeps score_file's signature manageable
    and makes it obvious what this module depends on."""

    file_id: Optional[str]
    repository_id: Optional[str]
    commits: list[dict] = field(default_factory=list)              # Member 2, filtered to this file
    contributors: list[dict] = field(default_factory=list)         # Member 2, filtered to this file
    entity_local_ids: set[str] = field(default_factory=set)        # Phase 1, this file's entities
    dependencies: list[dict] = field(default_factory=list)         # Phase 1, repo- or file-scope edges
    knowledge_gaps: list[dict] = field(default_factory=list)       # Phase 5, associated with this file


def _compute_raw_signals(inputs: RiskInputs, now: Optional[datetime] = None) -> dict[str, Any]:
    return {
        "change_frequency": sig.change_frequency(inputs.commits, now=now),
        "contributor_count": sig.contributor_count(inputs.contributors),
        "ownership_concentration": sig.ownership_concentration(inputs.contributors),
        "revert_count": sig.revert_count(inputs.commits),
        "activity_recency_days": sig.activity_recency_days(inputs.commits, now=now),
        "dependency_centrality": sig.dependency_centrality(
            inputs.entity_local_ids, inputs.dependencies
        ),
        "knowledge_gaps": sig.open_knowledge_gaps_count(inputs.knowledge_gaps),
    }


def _normalize_signals(raw: dict[str, Any]) -> dict[str, float]:
    return {
        "change_frequency": _normalize_change_frequency(raw["change_frequency"]),
        "contributor_count": _normalize_contributor_count(raw["contributor_count"]),
        "ownership_concentration": raw["ownership_concentration"],  # already 0.0-1.0
        "revert_count": _normalize_revert_count(raw["revert_count"]),
        "activity_recency": _normalize_recency(raw["activity_recency_days"]),
        "dependency_centrality": _normalize_dependency_centrality(raw["dependency_centrality"]),
        "knowledge_gaps": _normalize_knowledge_gaps(raw["knowledge_gaps"]),
    }


def _build_explanation(raw: dict[str, Any], normalized: dict[str, float], weights: dict[str, float]) -> str:
    """Plain-English explanation naming the top contributing factors, so
    the frontend (Member 5's Risk dashboard) has something to show besides
    a bare number. Picks the top 2 signals by weighted contribution."""
    contributions = sorted(
        ((name, normalized[name] * weights[name]) for name in weights),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top = [name for name, contribution in contributions[:2] if contribution > 0]

    phrases = {
        "ownership_concentration": (
            f"{raw['contributor_count']} contributor(s), "
            f"{raw['ownership_concentration']:.0%} of commits from one person"
        ),
        "dependency_centrality": f"{raw['dependency_centrality']} other entities depend on it",
        "change_frequency": f"changed {raw['change_frequency']} times in the last 90 days",
        "revert_count": f"{raw['revert_count']} revert-like commit(s)",
        "contributor_count": f"only {raw['contributor_count']} contributor(s) total",
        "activity_recency": (
            "no commit history found"
            if raw["activity_recency_days"] is None
            else f"last changed {raw['activity_recency_days']} days ago"
        ),
        "knowledge_gaps": f"{raw['knowledge_gaps']} open knowledge gap(s)",
    }

    total = sum(c for _, c in contributions)
    if total >= 0.6:
        level = "high"
    elif total >= 0.3:
        level = "moderate"
    else:
        level = "low"

    if not top:
        return f"{level} risk: no significant contributing factors detected."

    reasons = "; ".join(phrases[name] for name in top)
    return f"{level} risk: {reasons}."


def score_file(
    inputs: RiskInputs,
    weights: Optional[dict[str, float]] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Compute a deterministic risk record for one file.

    Returns a dict matching the `risk_records` table plus the structure
    the API contract's GET /repositories/{repository_id}/risks endpoint
    needs: score, contributing signals (raw + normalized + weight, so the
    frontend can show *why*, not just the number), and a plain-English
    explanation.
    """
    weights = weights or DEFAULT_WEIGHTS
    raw = _compute_raw_signals(inputs, now=now)
    normalized = _normalize_signals(raw)

    score = sum(normalized[name] * weights[name] for name in weights)
    explanation = _build_explanation(raw, normalized, weights)

    contributing_signals = {
        name: {
            "raw": raw[name if name != "activity_recency" else "activity_recency_days"],
            "normalized": round(normalized[name], 4),
            "weight": weights[name],
        }
        for name in weights
    }

    return {
        "id": None,
        "repository_id": inputs.repository_id,
        "file_id": inputs.file_id,
        "score": round(score, 4),
        "signals": contributing_signals,
        "explanation": explanation,
        "created_at": None,  # set by whoever performs the actual DB insert
    }


def score_files(
    inputs_list: list[RiskInputs],
    weights: Optional[dict[str, float]] = None,
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Convenience batch entry point, sorted highest-risk first -- this is
    the shape a risk dashboard actually wants to render."""
    scored = [score_file(inputs, weights=weights, now=now) for inputs in inputs_list]
    return sorted(scored, key=lambda r: r["score"], reverse=True)
