"""
dependency_mapper.py

Takes the entities produced by python_parser.py / javascript_parser.py
(for a single file) and maps dependency edges between them, matching the
`dependencies` database table shape:

    dependencies: id, repository_id, source_entity_id, target_entity_id,
                  dependency_type

Scope for this phase (per the Phase 1 spec): same-file call detection and
same-file class inheritance. Cross-file import resolution -- e.g. matching
an `import` statement to an entity that lives in a *different* file -- is
explicitly a stretch goal here, not required for done, since it needs the
whole-repository file set rather than one file's entities.

`source_entity_id` / `target_entity_id` are populated with each entity's
`local_id` (see entity_extractor.py), not a real database id -- entities
don't have one yet at parse time. Whoever performs the actual database
insert (Member 1's integration layer) is expected to swap local_id values
for real row ids consistently across both `code_entities` and
`dependencies` when writing them.
"""

from __future__ import annotations

from typing import Any, Optional

from .entity_extractor import CodeEntity, EntityType


def _build_name_index(entities: list[CodeEntity]) -> dict[str, list[CodeEntity]]:
    """Map a callable short name to the entities it could refer to.
    Methods are indexed both under their full "Class.method" name and
    their bare "method" name, since a call site like `self.method()` only
    gives us the bare name."""
    index: dict[str, list[CodeEntity]] = {}
    for entity in entities:
        index.setdefault(entity.name, []).append(entity)
        if entity.entity_type == EntityType.METHOD and "." in entity.name:
            bare_name = entity.name.split(".")[-1]
            index.setdefault(bare_name, []).append(entity)
    return index


def _make_dependency(
    source: CodeEntity, target: CodeEntity, dependency_type: str, repository_id: Optional[str]
) -> dict[str, Any]:
    return {
        "id": None,
        "repository_id": repository_id or source.repository_id or target.repository_id,
        "source_entity_id": source.local_id,
        "target_entity_id": target.local_id,
        "dependency_type": dependency_type,
    }


def map_same_file_calls(
    entities: list[CodeEntity],
    repository_id: Optional[str] = None,
    include_self_calls: bool = False,
) -> list[dict[str, Any]]:
    """
    For each entity's recorded `calls` (raw called names collected by the
    parser), find other entities in the same file whose name matches, and
    emit a `calls` dependency edge from the caller to the callee.

    Ambiguous matches (a name that matches more than one entity, e.g. two
    same-named methods on different classes) produce an edge to every
    match -- better to over-report a possible edge than silently drop it.
    """
    name_index = _build_name_index(entities)
    dependencies: list[dict[str, Any]] = []

    for source in entities:
        for called_name in source.calls:
            for target in name_index.get(called_name, []):
                if target is source and not include_self_calls:
                    continue
                dependencies.append(_make_dependency(source, target, "calls", repository_id))

    return dependencies


def map_inheritance(
    entities: list[CodeEntity], repository_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """For each class entity's recorded `bases`, find other class entities
    in the same file with a matching name and emit an `inherits` edge."""
    class_by_name = {e.name: e for e in entities if e.entity_type == EntityType.CLASS}
    dependencies: list[dict[str, Any]] = []

    for entity in entities:
        if entity.entity_type != EntityType.CLASS:
            continue
        for base_name in entity.bases:
            base_entity = class_by_name.get(base_name)
            if base_entity is not None and base_entity is not entity:
                dependencies.append(
                    _make_dependency(entity, base_entity, "inherits", repository_id)
                )

    return dependencies


def map_dependencies(
    entities: list[CodeEntity], repository_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Convenience entry point: run every same-file mapping this module
    supports and return the combined list of dependency dicts."""
    return map_same_file_calls(entities, repository_id) + map_inheritance(entities, repository_id)
