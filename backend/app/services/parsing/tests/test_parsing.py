"""
Tests for Phase 1: python_parser, javascript_parser, entity_extractor,
dependency_mapper.

Run with: pytest backend/app/services/parsing/tests/test_parsing.py -v
"""

from pathlib import Path

import pytest

from backend.app.services.parsing.dependency_mapper import (
    map_dependencies,
    map_inheritance,
    map_same_file_calls,
)
from backend.app.services.parsing.entity_extractor import (
    EntityType,
    normalize_entities,
    to_db_dict,
    validate_entity,
)
from backend.app.services.parsing.javascript_parser import parse_javascript_file
from backend.app.services.parsing.python_parser import parse_python_file

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


# --- python_parser.py -----------------------------------------------------


def test_python_parser_extracts_functions_and_classes():
    source = read_fixture("sample_python_1.py")
    entities, imports = parse_python_file(source, file_id="f1", repository_id="r1")

    names = {e.name for e in entities}
    assert "add" in names
    assert "helper" in names
    assert "Animal" in names
    assert "Dog" in names
    assert "Animal.speak" in names
    assert "Dog.speak" in names
    assert "Dog.bark" in names

    types_by_name = {e.name: e.entity_type for e in entities}
    assert types_by_name["add"] == EntityType.FUNCTION
    assert types_by_name["Animal"] == EntityType.CLASS
    assert types_by_name["Animal.speak"] == EntityType.METHOD


def test_python_parser_captures_calls_for_dependency_mapping():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source)
    add_entity = next(e for e in entities if e.name == "add")
    assert "helper" in add_entity.calls

    dog_speak = next(e for e in entities if e.name == "Dog.speak")
    assert "bark" in dog_speak.calls


def test_python_parser_captures_inheritance():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source)
    dog = next(e for e in entities if e.name == "Dog")
    assert dog.bases == ["Animal"]


def test_python_parser_captures_imports():
    source = read_fixture("sample_python_1.py")
    _, imports = parse_python_file(source)
    modules = {imp.module for imp in imports}
    assert "os" in modules
    assert "typing" in modules


def test_python_parser_handles_syntax_errors_gracefully():
    source = read_fixture("sample_python_2_broken.py")
    entities, imports = parse_python_file(source, file_id="broken")
    # Must not raise. Graceful degradation = empty result, not a crash.
    assert entities == []
    assert imports == []


def test_python_parser_all_entities_pass_validation():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source, file_id="f1", repository_id="r1")
    for entity in entities:
        problems = validate_entity(entity)
        assert problems == [], f"{entity.name}: {problems}"


def test_python_entities_normalize_to_db_shape():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source, file_id="f1", repository_id="r1")
    rows = normalize_entities(entities)
    expected_keys = {
        "id",
        "repository_id",
        "file_id",
        "entity_type",
        "name",
        "start_line",
        "end_line",
        "signature",
    }
    for row in rows:
        assert set(row.keys()) == expected_keys
        assert row["repository_id"] == "r1"
        assert row["file_id"] == "f1"


# --- javascript_parser.py --------------------------------------------------


def test_javascript_parser_extracts_functions_and_classes():
    source = read_fixture("sample_javascript_1.js")
    entities, imports = parse_javascript_file(source, file_id="f2", repository_id="r1")

    names = {e.name for e in entities}
    assert "add" in names
    assert "helper" in names
    assert "multiply" in names
    assert "Animal" in names
    assert "Dog" in names

    modules = {imp.module for imp in imports}
    assert "react" in modules


def test_javascript_parser_captures_inheritance_when_babel_available():
    source = read_fixture("sample_javascript_1.js")
    entities, _ = parse_javascript_file(source)
    dog = next((e for e in entities if e.name == "Dog"), None)
    assert dog is not None
    # If the babel path ran, bases will be populated. If the environment
    # had no Node/babel and fell back to regex, bases still gets the
    # `extends X` name via the fallback's own class regex, so this should
    # hold either way.
    assert dog.bases == ["Animal"]


def test_javascript_entities_normalize_to_db_shape():
    source = read_fixture("sample_javascript_1.js")
    entities, _ = parse_javascript_file(source, file_id="f2", repository_id="r1")
    rows = normalize_entities(entities)
    for row in rows:
        assert row["repository_id"] == "r1"
        assert row["file_id"] == "f2"
        assert row["entity_type"] in EntityType.ALL


# --- dependency_mapper.py ---------------------------------------------------


def test_map_same_file_calls_python():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source, file_id="f1", repository_id="r1")
    deps = map_same_file_calls(entities, repository_id="r1")

    add_entity = next(e for e in entities if e.name == "add")
    helper_entity = next(e for e in entities if e.name == "helper")
    assert any(
        d["source_entity_id"] == add_entity.local_id
        and d["target_entity_id"] == helper_entity.local_id
        and d["dependency_type"] == "calls"
        for d in deps
    )


def test_map_same_file_calls_resolves_method_calls_via_self():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source)
    deps = map_same_file_calls(entities)

    dog_speak = next(e for e in entities if e.name == "Dog.speak")
    dog_bark = next(e for e in entities if e.name == "Dog.bark")
    assert any(
        d["source_entity_id"] == dog_speak.local_id and d["target_entity_id"] == dog_bark.local_id
        for d in deps
    )


def test_map_inheritance_python():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source)
    deps = map_inheritance(entities, repository_id="r1")

    dog = next(e for e in entities if e.name == "Dog")
    animal = next(e for e in entities if e.name == "Animal")
    assert any(
        d["source_entity_id"] == dog.local_id
        and d["target_entity_id"] == animal.local_id
        and d["dependency_type"] == "inherits"
        for d in deps
    )


def test_no_self_referential_calls_by_default():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source)
    deps = map_same_file_calls(entities)
    for d in deps:
        assert d["source_entity_id"] != d["target_entity_id"]


def test_map_dependencies_returns_all_dependency_shape_keys():
    source = read_fixture("sample_python_1.py")
    entities, _ = parse_python_file(source, repository_id="r1")
    deps = map_dependencies(entities, repository_id="r1")
    assert len(deps) > 0
    expected_keys = {"id", "repository_id", "source_entity_id", "target_entity_id", "dependency_type"}
    for d in deps:
        assert set(d.keys()) == expected_keys
        assert d["repository_id"] == "r1"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
