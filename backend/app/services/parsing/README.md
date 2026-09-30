# services/parsing/ — Phase 1 (M3)

Static code entity extraction and same-file dependency mapping. No code
from an analyzed repository is ever executed by this module — everything
here is text/AST parsing only.

## Files

- `entity_extractor.py` — shared `CodeEntity` dataclass and normalization
  helpers. Both parsers below funnel through this so entity shape is
  identical regardless of source language.
- `python_parser.py` — AST-based extraction for Python (`ast` module,
  standard library, no dependency).
- `javascript_parser.py` — extraction for JS/TS/JSX/TSX. Uses a Node.js +
  Babel helper (`js_ast_helper/`) when available for full AST accuracy
  (functions, classes, methods, call sites). Falls back automatically to a
  regex-based extractor (functions, arrow-consts, top-level classes; no
  methods, no call collection) if Node/Babel aren't present. This is
  intentional graceful degradation, not a bug — see the fallback's
  docstring for exactly what it can and can't catch.
- `dependency_mapper.py` — builds `calls` and `inherits` dependency edges
  between entities that live in the same file. Cross-file import
  resolution is explicitly out of scope for this phase (needs the whole
  repository's file set, not one file).
- `js_ast_helper/parse_js.js` — the Node/Babel helper script. Requires
  `@babel/parser` and `@babel/traverse`; run `npm install` in this folder
  before deploying if `node_modules/` wasn't carried over (not shipped in
  this handoff to keep it small). If Node.js isn't installed on the
  deployment target at all, nothing breaks — `javascript_parser.py`
  detects that and uses the regex fallback automatically.

## Output shapes

Entities normalize to the `code_entities` table shape:
`id, repository_id, file_id, entity_type, name, start_line, end_line, signature`
(via `entity_extractor.to_db_dict()` / `normalize_entities()`).

Dependencies match the `dependencies` table shape:
`id, repository_id, source_entity_id, target_entity_id, dependency_type`.

`id` is always `None` at this stage — nothing here writes to a database.
`source_entity_id` / `target_entity_id` are each entity's `local_id`
(a uuid4 assigned at parse time), not a real row id. Whoever performs the
actual database insert should swap `local_id` values for real ids
consistently across both tables when writing them — a 1:1 swap.

## Running the tests

```
cd <repo-root>
pip install pytest --break-system-packages   # if not already installed
python3 -m pytest backend/app/services/parsing/tests/test_parsing.py -v
```

15 tests, covering: entity extraction (Python + JS), call collection,
inheritance detection, import extraction, graceful handling of a
syntax-broken file, DB-shape normalization, and dependency mapping
(calls + inheritance, including method calls via `self.`/`this.`).

## Known limitations (by design, not oversights)

- Nested function definitions (a `def` inside another `def`) are not
  recursed into, to avoid double-counting calls under both the outer and
  inner entity. Out of scope for this phase.
- JS/TS regex fallback only fires when Node/Babel are unavailable, and is
  deliberately shallower (no methods, no call collection, single-line
  signatures only).
- Java/C++/Go are not parsed in this phase — the PRD allows graceful
  degradation for less-supported languages; language detection for these
  is Member 2's `language_detector.py`, and adding real parsers for them
  can be a fast-follow if time allows, not a Phase 1 requirement.
- Cross-file dependency resolution (e.g. resolving an `import` to the
  entity it actually points at in another file) is a stretch goal, not
  required for this phase's definition of done.
