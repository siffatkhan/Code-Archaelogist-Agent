"""
javascript_parser.py

Extracts code entities (functions, classes, methods) and import
statements from JavaScript/TypeScript/JSX/TSX source.

Python has no built-in parser for this language family, so this module
uses a two-tier strategy:

1. Preferred: shell out to a small Node.js helper script
   (js_ast_helper/parse_js.js) that parses the source with @babel/parser
   and walks it with @babel/traverse. This gives real AST-based
   extraction, on par with python_parser.py's accuracy.
2. Fallback: if Node.js or the babel packages aren't available in the
   deployment environment, fall back to a regex/heuristic extractor.
   This is intentionally shallower -- it won't catch every pattern (e.g.
   multi-line function signatures, unusual formatting) -- and that's
   accepted per the PRD's "graceful degradation" allowance for
   less-fully-supported languages. It is documented here, not hidden.

Neither path executes the source being analyzed. The Node helper only
parses to an AST; it never calls `eval`, `require`s the target file, or
runs the code in any way.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .entity_extractor import CodeEntity, EntityType, make_entity
from .python_parser import ImportInfo

logger = logging.getLogger(__name__)

_HELPER_SCRIPT = Path(__file__).parent / "js_ast_helper" / "parse_js.js"
_SUBPROCESS_TIMEOUT_SECONDS = 10


def _try_babel_parse(source: str) -> Optional[dict]:
    """Attempt AST-based parsing via the Node/babel helper. Returns the
    parsed JSON dict on success, or None if the helper isn't usable for
    any reason (node missing, script missing, non-zero exit, timeout,
    bad JSON). Every failure path is a controlled fallback, not a crash."""
    if shutil.which("node") is None:
        logger.info("javascript_parser: node not found on PATH, using regex fallback")
        return None
    if not _HELPER_SCRIPT.exists():
        logger.info("javascript_parser: helper script missing, using regex fallback")
        return None

    try:
        result = subprocess.run(
            ["node", str(_HELPER_SCRIPT)],
            input=source,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("javascript_parser: babel helper failed to run: %s", exc)
        return None

    if result.returncode != 0:
        logger.warning(
            "javascript_parser: babel helper exited %s: %s", result.returncode, result.stderr
        )
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.warning("javascript_parser: could not parse helper output: %s", exc)
        return None

    if data.get("error"):
        logger.info("javascript_parser: babel could not parse source: %s", data["error"])
        return None

    return data


def _entities_from_babel_json(
    data: dict, repository_id: Optional[str], file_id: Optional[str]
) -> list[CodeEntity]:
    entities = []
    for raw in data.get("entities", []):
        entities.append(
            make_entity(
                entity_type=raw["entity_type"],
                name=raw["name"],
                start_line=raw.get("start_line"),
                end_line=raw.get("end_line"),
                signature=raw.get("signature", raw["name"]),
                repository_id=repository_id,
                file_id=file_id,
                calls=raw.get("calls", []),
                bases=raw.get("bases", []),
            )
        )
    return entities


def _imports_from_babel_json(data: dict) -> list[ImportInfo]:
    imports = []
    for raw in data.get("imports", []):
        for name in raw.get("names", []) or ["*"]:
            imports.append(
                ImportInfo(module=raw["source"], name=name, alias=None, lineno=0)
            )
    return imports


# --- Regex fallback -----------------------------------------------------
#
# Deliberately simple, line-oriented patterns. Known limitations (documented
# rather than silently accepted): multi-line function signatures aren't
# matched, methods inside classes aren't extracted (class body detection via
# regex is unreliable), and `calls` are not collected at all in this path --
# dependency_mapper.py will simply have nothing to map for a file that fell
# back to regex. This is the accepted "graceful degradation" floor, not the
# target quality bar -- the babel path above is what should run whenever
# Node is available.

_RE_FUNCTION_DECL = re.compile(r"^\s*(?:export\s+)?function\s+(\w+)\s*\(([^)]*)\)")
_RE_ARROW_CONST = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>"
)
_RE_CLASS_DECL = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?")
_RE_IMPORT = re.compile(r"^\s*import\s+.*?from\s+['\"]([^'\"]+)['\"]")
_RE_REQUIRE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")


def _regex_parse(source: str) -> tuple[list[CodeEntity], list[ImportInfo]]:
    entities: list[CodeEntity] = []
    imports: list[ImportInfo] = []
    lines = source.splitlines()

    for lineno, line in enumerate(lines, start=1):
        m = _RE_FUNCTION_DECL.match(line)
        if m:
            name, params = m.group(1), m.group(2)
            entities.append(
                make_entity(
                    entity_type=EntityType.FUNCTION,
                    name=name,
                    start_line=lineno,
                    end_line=lineno,  # regex path can't reliably find the end
                    signature=f"{name}({params.strip()})",
                )
            )
            continue

        m = _RE_ARROW_CONST.match(line)
        if m:
            name, params = m.group(1), m.group(2)
            entities.append(
                make_entity(
                    entity_type=EntityType.FUNCTION,
                    name=name,
                    start_line=lineno,
                    end_line=lineno,
                    signature=f"{name}({params.strip()})",
                )
            )
            continue

        m = _RE_CLASS_DECL.match(line)
        if m:
            name, base = m.group(1), m.group(2)
            entities.append(
                make_entity(
                    entity_type=EntityType.CLASS,
                    name=name,
                    start_line=lineno,
                    end_line=lineno,
                    signature=f"class {name}" + (f" extends {base}" if base else ""),
                    bases=[base] if base else [],
                )
            )
            continue

        m = _RE_IMPORT.match(line)
        if m:
            imports.append(ImportInfo(module=m.group(1), name="*", alias=None, lineno=lineno))

        for req_match in _RE_REQUIRE.finditer(line):
            imports.append(
                ImportInfo(module=req_match.group(1), name="*", alias=None, lineno=lineno)
            )

    return entities, imports


def parse_javascript_file(
    source: str,
    file_id: Optional[str] = None,
    repository_id: Optional[str] = None,
) -> tuple[list[CodeEntity], list[ImportInfo]]:
    """
    Parse JavaScript/TypeScript source into (entities, imports).

    Tries the babel-based helper first for real AST accuracy (functions,
    classes, and class methods, with call sites collected for dependency
    mapping). Falls back to a shallower regex extractor -- functions,
    arrow-function consts, and top-level classes only, no methods, no
    call collection -- if Node/babel aren't available. Never raises on
    malformed input; returns whatever it could extract.
    """
    babel_result = _try_babel_parse(source)
    if babel_result is not None:
        entities = _entities_from_babel_json(babel_result, repository_id, file_id)
        imports = _imports_from_babel_json(babel_result)
        return entities, imports

    entities, imports = _regex_parse(source)
    for e in entities:
        e.repository_id = repository_id
        e.file_id = file_id
    return entities, imports
