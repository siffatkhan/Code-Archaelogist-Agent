# services/risk/ — Phase 2 (M3)

Deterministic file/module risk scoring. No LLM call anywhere in this
module, by design — the Technical Build Specification requires risk to
come from concrete signals, not a model's guess.

## Files

- `signals.py` — one function per raw signal named in the Technical
  Build Spec: `change_frequency`, `contributor_count`,
  `ownership_concentration`, `revert_count`, `activity_recency_days`,
  `dependency_centrality`, `open_knowledge_gaps_count`. Each returns a
  plain number, no normalization — kept simple and independently testable.
- `risk_scorer.py` — combines the raw signals into one 0.0-1.0 score per
  file, with `DEFAULT_WEIGHTS` documented and easy to retune, plus a
  plain-English explanation naming the top contributing factors. Output
  matches the `risk_records` table and the `GET
  /repositories/{repository_id}/risks` response shape.

## Where the input data comes from

- `commits` / `contributors` — Member 2's git history extraction
  (`services/history/`), already filtered to the file being scored. This
  phase doesn't do that filtering itself.
- `entity_local_ids` / `dependencies` — Phase 1's parsing output
  (`services/parsing/`). `dependency_centrality` currently only reflects
  same-file fan-in, since Phase 1's dependency mapping is same-file only
  for now — documented in `signals.py`, and this function needs no changes
  if cross-file mapping is added later.
- `knowledge_gaps` — Phase 5's gap detection (`services/knowledge/`), once
  that phase exists. Until then, pass an empty list; the signal degrades
  to 0 rather than erroring.

## Weights — a judgment call, not a formula

`DEFAULT_WEIGHTS` in `risk_scorer.py` weights ownership concentration and
dependency centrality highest, since "one person understands this and a
lot depends on it" is the exact problem the offboarding feature exists to
catch. There's no dataset to fit these against in a hackathon timeframe —
treat them as a documented starting point, easy to retune in one place,
not a fixed constant.

## Running the tests

```
cd <repo-root>
python3 -m pytest backend/app/services/risk/tests/test_risk.py -v
```

20 tests: each signal function in isolation, a synthetic high-risk fixture
(one contributor, frequent changes, two revert-like commits, several
dependents) scoring meaningfully higher than a synthetic low-risk fixture
(three contributors, changes over a year old, no reverts), output shape
validation against the `risk_records`/API contract, the "no commit
history is uncertainty, not safety" behavior, and a documentation-style
test asserting this module has no LLM dependency.

## Known limitations (by design)

- `dependency_centrality` is same-file only until Phase 1's dependency
  mapper gets cross-file resolution (documented there as a stretch goal).
- Associating a knowledge gap with a specific file is left to the caller
  (likely Phase 5) — this module just counts whatever open-gap list it's
  handed for that file.
- Weight values are a documented starting point for tuning against real
  repository data during integration testing, not a final answer.
