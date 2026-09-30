"""
signals.py

One function per raw risk signal, named per the Technical Build
Specification: change frequency, contributor count, ownership
concentration, reverts, activity recency, dependency centrality, and open
knowledge gaps.

Every function here is a plain, deterministic calculation over data
already produced by other modules (Member 2's commit/contributor history,
Phase 1's entities/dependencies, Phase 5's knowledge gaps). Nothing in
this file calls an LLM, and nothing should ever be added here that does --
that's the whole point of this module existing separately from the
agents in agents/. If a "signal" needs judgment instead of arithmetic, it
belongs in an agent, not here.

Each function returns a plain number (int or float) -- no normalization,
no weighting. risk_scorer.py is where raw signal values get combined into
one score. Keeping normalization out of this file means each signal stays
independently testable and its raw value stays available for the
"contributing signals" the API contract asks for.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# Commit messages that look like an automated or manual revert. Deliberately
# conservative (few false positives) rather than exhaustive.
_REVERT_MARKERS = ("revert", "rollback", "undo")


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Best-effort parse of a commit/contributor timestamp. Repository
    history data can come from different sources with slightly different
    string formats (Member 2's git history extraction, a fixture, a test),
    so this is deliberately tolerant. Returns None if it can't be parsed --
    callers treat that as "no usable timestamp" rather than raising, since
    one malformed timestamp in a large commit history shouldn't blow up an
    entire risk calculation."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def change_frequency(
    commits: list[dict], window_days: int = 90, now: Optional[datetime] = None
) -> int:
    """Number of commits touching this file within the last `window_days`
    days. `commits` is expected to already be filtered to the file in
    question (Member 2's history data is per-file or per-commit-with-diff;
    filtering which commits touched which file is the caller's job, not
    this function's)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    count = 0
    for commit in commits:
        ts = _parse_timestamp(commit.get("timestamp"))
        if ts is not None and ts >= cutoff:
            count += 1
    return count


def contributor_count(contributors: list[dict]) -> int:
    """Distinct contributors who have touched this file, per Member 2's
    contributor records already scoped to the file."""
    return len(contributors)


def ownership_concentration(contributors: list[dict]) -> float:
    """0.0-1.0: what fraction of commits to this file belong to its single
    most active contributor. 1.0 means one person wrote all of it (highest
    risk if they leave); a low value means work is spread out. Returns 0.0
    if there's no commit data to compute a ratio from."""
    if not contributors:
        return 0.0
    total = sum(c.get("commit_count", 0) for c in contributors)
    if total <= 0:
        return 0.0
    busiest = max(c.get("commit_count", 0) for c in contributors)
    return busiest / total


def revert_count(commits: list[dict]) -> int:
    """Number of commits whose message looks like a revert/rollback --
    a signal that this area has been unstable or a fix didn't stick the
    first time."""
    count = 0
    for commit in commits:
        message = (commit.get("message") or "").lower()
        if any(marker in message for marker in _REVERT_MARKERS):
            count += 1
    return count


def activity_recency_days(commits: list[dict], now: Optional[datetime] = None) -> Optional[int]:
    """Days since the most recent commit to this file. Returns None if
    there are no commits at all (caller decides how to treat "no data" --
    risk_scorer.py treats it as maximum uncertainty, not zero risk)."""
    now = now or datetime.now(timezone.utc)
    timestamps = [
        ts for ts in (_parse_timestamp(c.get("timestamp")) for c in commits) if ts is not None
    ]
    if not timestamps:
        return None
    most_recent = max(timestamps)
    return max((now - most_recent).days, 0)


def dependency_centrality(entity_local_ids: set[str], dependencies: list[dict]) -> int:
    """How many dependency edges point *at* any entity in this file --
    i.e. how many other things would potentially break if this file's
    entities changed incorrectly. `entity_local_ids` is the set of
    CodeEntity.local_id values belonging to this file (see Phase 1's
    entity_extractor.py).

    Caveat, documented rather than hidden: as of Phase 1, dependency_mapper
    only produces same-file edges (cross-file import resolution is a
    stretch goal there). This means dependency_centrality currently only
    reflects in-file fan-in. If/when cross-file mapping is added later,
    this function needs no changes -- it will automatically pick up the
    wider edge set, since it just counts whatever `dependencies` contains.
    """
    return sum(1 for dep in dependencies if dep.get("target_entity_id") in entity_local_ids)


def open_knowledge_gaps_count(knowledge_gaps_for_file: list[dict]) -> int:
    """Count of currently-open knowledge gaps associated with this file.
    Associating a gap (which is stored as a question + free-text context,
    per the knowledge_gaps schema) with a specific file is a matching
    problem for the caller to solve -- likely Phase 5's gap_detector.py,
    or a simple keyword/file-path match for the hackathon build. This
    function just counts whatever list it's handed."""
    return sum(1 for gap in knowledge_gaps_for_file if gap.get("status") == "open")
