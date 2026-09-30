from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID, uuid4

from backend.app.services.github import fetch_commits, fetch_file
from backend.app.services.parsing.entity_extractor import CodeEntity
from backend.app.services.parsing.javascript_parser import parse_javascript_file
from backend.app.services.parsing.python_parser import parse_python_file
from backend.app.services.repository_store import RepositoryRecord
from backend.app.services.risk.risk_scorer import RiskInputs, score_files


CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".c", ".cpp", ".h", ".hpp"}
OFF_TOPIC_MARKERS = {"medicine", "medical", "weather", "recipe", "politics", "stock price"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_file(path: str, content: str, repository_id: UUID) -> list[dict[str, Any]]:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".py":
        entities, _ = parse_python_file(content, file_id=path, repository_id=str(repository_id))
    elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
        entities, _ = parse_javascript_file(content, file_id=path, repository_id=str(repository_id))
    else:
        return []
    return [
        {
            "local_id": entity.local_id,
            "entity_type": entity.entity_type,
            "name": entity.name,
            "start_line": entity.start_line,
            "end_line": entity.end_line,
            "signature": entity.signature,
        }
        for entity in entities
    ]


async def enrich_analysis(record: RepositoryRecord) -> None:
    """Fetch bounded read-only analysis inputs and compute local artifacts."""
    try:
        record.commits = await fetch_commits(record.owner, record.name, record.default_branch or "main")
    except Exception:
        record.commits = []

    for path in record.files[:150]:
        if PurePosixPath(path).suffix.lower() not in CODE_SUFFIXES:
            continue
        try:
            content, _ = await fetch_file(record.owner, record.name, record.default_branch or "main", path)
        except Exception:
            continue
        record.file_contents[path] = content
        record.entities[path] = _parse_file(path, content, record.repository_id)

    contributors: dict[str, dict[str, Any]] = {}
    for commit in record.commits:
        author = commit.get("author") or "Unknown"
        contributors.setdefault(author, {"name": author, "commit_count": 0})["commit_count"] += 1

    inputs = [
        RiskInputs(
            file_id=path,
            repository_id=str(record.repository_id),
            commits=record.commits,
            contributors=list(contributors.values()),
            entity_local_ids={entity["local_id"] for entity in record.entities.get(path, [])},
        )
        for path in record.files
    ]
    record.risks = []
    for risk in score_files(inputs):
        risk["file_path"] = risk.pop("file_id")
        record.risks.append(risk)


def answer_question(record: RepositoryRecord, question: str) -> dict[str, Any]:
    lowered = question.lower()
    if any(marker in lowered for marker in OFF_TOPIC_MARKERS):
        return {
            "answer": "This assistant only answers questions related to the analyzed repository.",
            "evidence": [],
            "confidence": "low",
            "classification": "inferred",
            "is_refusal": True,
            "gap_detected": False,
            "gap_id": None,
        }

    words = {word for word in lowered.replace("/", " ").split() if len(word) > 2}
    matches = [path for path in record.files if any(word in path.lower() for word in words)]

    evidence = [
        {
            "source_type": "file",
            "path": path,
            "excerpt": record.file_contents.get(path, "")[:240] or None,
            "reason": "Matched the question against analyzed repository files.",
        }
        for path in matches[:5]
    ]
    if not evidence:
        gap_id = uuid4()
        record.knowledge_gaps.append(
            {"gap_id": gap_id, "question": question, "context": None, "priority": "medium", "status": "open", "created_at": _now()}
        )
        return {
            "answer": "I do not have enough analyzed repository evidence to answer this confidently. The question was saved as a knowledge gap.",
            "evidence": [],
            "confidence": "low",
            "classification": "inferred",
            "is_refusal": False,
            "gap_detected": True,
            "gap_id": gap_id,
        }

    return {
        "answer": f"The analyzed repository contains {len(evidence)} relevant file(s). The strongest starting point is {evidence[0]['path']}. Review its source and commit history to verify why this code exists.",
        "evidence": evidence,
        "confidence": "medium",
        "classification": "inferred",
        "is_refusal": False,
        "gap_detected": False,
        "gap_id": None,
    }


def build_guidance(record: RepositoryRecord, task: str) -> dict[str, Any]:
    words = {word.lower() for word in task.split() if len(word) > 2}
    matches = [path for path in record.files if any(word in path.lower() for word in words)]
    matches = (matches or [path for path in record.files if PurePosixPath(path).suffix.lower() in CODE_SUFFIXES])[:8]
    steps = [
        {"order": index, "title": f"Review {path}", "files": [path], "reasoning": "This file was selected from the analyzed repository because its path matches the task context."}
        for index, path in enumerate(matches, start=1)
    ]
    return {"task": task, "steps": steps}


def create_offboarding(record: RepositoryRecord, contributor: str) -> dict[str, Any]:
    session_id = uuid4()
    contributor_commits = [commit for commit in record.commits if str(commit.get("author", "")).lower() == contributor.lower()]
    candidate_paths = [risk["file_path"] for risk in record.risks[:5]]
    if not contributor_commits:
        candidate_paths = candidate_paths[:3]
    questions = [
        {"question_id": uuid4(), "question": f"What context should a new maintainer know before changing {path}?", "priority": "high", "answer": None, "status": "pending", "file_path": path}
        for path in candidate_paths
    ]
    record.offboarding_sessions[session_id] = {
        "session_id": session_id,
        "contributor": contributor,
        "status": "created",
        "created_at": _now(),
        "completed_at": None,
        "questions": questions,
    }
    return {"session_id": session_id, "status": "created"}