"""
entity_extractor.py

The single normalization point for code entities, regardless of which
language parser produced them. python_parser.py and javascript_parser.py
both build CodeEntity objects through this module, so anything downstream
(risk scoring, dependency mapping, agents) can treat every entity the same
way no matter what language it came from.

This module never reads files or executes anything -- it only defines the
shared shape and helpers for converting that shape to/from plain dicts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


class EntityType:
    """Allowed values for CodeEntity.entity_type. Keep this closed set --
    downstream code (risk scoring, the API layer) matches against these
    exact strings."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"

    ALL = (FUNCTION, CLASS, METHOD)


@dataclass
class CodeEntity:
    """
    In-memory representation of one parsed code entity (a function, class,
    or method). Field names mirror the `code_entities` database table:

        code_entities: id, repository_id, file_id, entity_type, name,
                        start_line, end_line, signature

    `local_id` is NOT a database column. It's a stable identifier assigned
    at parse time so dependency_mapper.py can wire up source/target edges
    between entities before any of them has a real database id. When a
    file's entities are actually inserted into the database, the caller
    (Member 1's integration layer) is expected to replace local_id with the
    real row id and update any dependency edges that reference it -- a 1:1
    swap, not a re-derivation.

    `calls` and `bases` are extraction metadata used only by
    dependency_mapper.py. They are deliberately dropped by `to_db_dict()`
    because they aren't columns on `code_entities`.
    """

    local_id: str
    entity_type: str
    name: str
    start_line: Optional[int]
    end_line: Optional[int]
    signature: str
    repository_id: Optional[str] = None
    file_id: Optional[str] = None
    calls: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    id: Optional[str] = None  # populated later, once a real DB row exists


def make_entity(
    entity_type: str,
    name: str,
    start_line: Optional[int],
    end_line: Optional[int],
    signature: str,
    repository_id: Optional[str] = None,
    file_id: Optional[str] = None,
    calls: Optional[list[str]] = None,
    bases: Optional[list[str]] = None,
) -> CodeEntity:
    """Convenience constructor used by both language parsers so entity
    creation stays consistent in one place."""
    if entity_type not in EntityType.ALL:
        raise ValueError(
            f"Unknown entity_type {entity_type!r}; must be one of {EntityType.ALL}"
        )
    return CodeEntity(
        local_id=str(uuid.uuid4()),
        entity_type=entity_type,
        name=name,
        start_line=start_line,
        end_line=end_line,
        signature=signature,
        repository_id=repository_id,
        file_id=file_id,
        calls=list(calls or []),
        bases=list(bases or []),
    )


def to_db_dict(entity: CodeEntity) -> dict[str, Any]:
    """Return only the fields that exist on the `code_entities` table.
    This is what should actually be written to the database -- internal
    fields like `local_id`, `calls`, and `bases` are stripped."""
    return {
        "id": entity.id,
        "repository_id": entity.repository_id,
        "file_id": entity.file_id,
        "entity_type": entity.entity_type,
        "name": entity.name,
        "start_line": entity.start_line,
        "end_line": entity.end_line,
        "signature": entity.signature,
    }


def normalize_entities(entities: list[CodeEntity]) -> list[dict[str, Any]]:
    """Convert a list of CodeEntity objects to a list of plain dicts
    matching the `code_entities` table shape, in order."""
    return [to_db_dict(e) for e in entities]


def validate_entity(entity: CodeEntity) -> list[str]:
    """Return a list of human-readable problems with an entity, empty if
    it's valid. Doesn't raise -- callers decide whether a problem is fatal.
    Useful in tests and as a sanity check before writing to the database."""
    problems = []
    if entity.entity_type not in EntityType.ALL:
        problems.append(f"invalid entity_type: {entity.entity_type!r}")
    if not entity.name:
        problems.append("entity has no name")
    if entity.start_line is not None and entity.end_line is not None:
        if entity.end_line < entity.start_line:
            problems.append(
                f"end_line ({entity.end_line}) is before start_line ({entity.start_line})"
            )
    if not entity.signature:
        problems.append("entity has no signature")
    return problems
