from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from backend.app.services.github import parse_github_url
from backend.app.services.supabase_persistence import supabase_persistence


@dataclass
class RepositoryRecord:
    repository_id: UUID
    user_id: str
    github_url: str
    owner: str
    name: str
    status: str = "created"
    default_branch: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_analyzed_at: datetime | None = None
    files: list[str] = field(default_factory=list)
    file_contents: dict[str, str] = field(default_factory=dict)
    entities: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    commits: list[dict[str, Any]] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)
    knowledge_gaps: list[dict[str, Any]] = field(default_factory=list)
    knowledge_items: list[dict[str, Any]] = field(default_factory=list)
    offboarding_sessions: dict[UUID, dict[str, Any]] = field(default_factory=dict)
    jobs: dict[UUID, dict[str, str | None]] = field(default_factory=dict)


class RepositoryStore:
    def __init__(self) -> None:
        self._repositories: dict[UUID, RepositoryRecord] = {}

    def create(self, user_id: str, github_url: str, owner: str, name: str) -> RepositoryRecord:
        if supabase_persistence.enabled:
            row = supabase_persistence.create_repository(user_id, github_url)
            repository_id = UUID(row["id"])
            created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            record = RepositoryRecord(repository_id, user_id, github_url, owner, name, row.get("status", "created"), created_at=created_at)
        else:
            record = RepositoryRecord(uuid4(), user_id, github_url, owner, name)
        self._repositories[record.repository_id] = record
        return record

    def list_for_user(self, user_id: str) -> list[RepositoryRecord]:
        if supabase_persistence.enabled:
            records = [self._from_row(row) for row in supabase_persistence.list_repositories(user_id)]
            for record in records:
                self._hydrate_files(record)
                self._repositories[record.repository_id] = record
            return records
        return [record for record in self._repositories.values() if record.user_id == user_id]

    def get_for_user(self, user_id: str, repository_id: UUID) -> RepositoryRecord | None:
        if supabase_persistence.enabled:
            row = supabase_persistence.get_repository(user_id, repository_id)
            if not row:
                return None
            record = self._from_row(row)
            self._hydrate_files(record)
            self._repositories[record.repository_id] = record
            return record
        record = self._repositories.get(repository_id)
        return record if record and record.user_id == user_id else None

    def create_job(self, record: RepositoryRecord) -> UUID:
        if supabase_persistence.enabled:
            job_id = UUID(supabase_persistence.create_job(record.repository_id)["id"])
        else:
            job_id = uuid4()
        record.jobs[job_id] = {"status": "queued", "error_message": None}
        record.status = "queued"
        if supabase_persistence.enabled:
            supabase_persistence.update_repository(record.repository_id, "queued")
        return job_id

    def get_job(self, user_id: str, job_id: UUID) -> tuple[RepositoryRecord, dict[str, str | None]] | None:
        if supabase_persistence.enabled:
            job = supabase_persistence.get_job(job_id)
            if not job:
                return None
            record = self.get_for_user(user_id, UUID(job["repository_id"]))
            if not record:
                return None
            return record, {"status": job["status"], "error_message": job.get("error_message")}
        for record in self._repositories.values():
            if record.user_id == user_id and job_id in record.jobs:
                return record, record.jobs[job_id]
        return None

    @staticmethod
    def _from_row(row: dict[str, Any]) -> RepositoryRecord:
        github_url = row["github_url"]
        owner, name = parse_github_url(github_url)
        created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        last_analyzed_at = row.get("last_analyzed_at")
        return RepositoryRecord(
            UUID(row["id"]),
            str(row["user_id"]),
            github_url,
            owner,
            name,
            row.get("status", "created"),
            default_branch=row.get("default_branch"),
            created_at=created_at,
            last_analyzed_at=datetime.fromisoformat(last_analyzed_at.replace("Z", "+00:00")) if last_analyzed_at else None,
        )

    @staticmethod
    def _hydrate_files(record: RepositoryRecord) -> None:
        if not supabase_persistence.enabled:
            return
        rows = supabase_persistence.list_files(record.repository_id)
        record.files = [row["path"] for row in rows]
        record.file_contents = {row["path"]: row.get("content") or "" for row in rows}
        record.knowledge_gaps = [
            {
                "gap_id": UUID(row["id"]),
                "question": row["question"],
                "context": row.get("context"),
                "priority": row.get("priority", "medium"),
                "status": row.get("status", "open"),
                "created_at": row["created_at"],
            }
            for row in supabase_persistence.list_knowledge_gaps(record.repository_id)
        ]
        record.knowledge_items = [
            {
                "knowledge_item_id": UUID(row["id"]),
                "title": row["title"],
                "content": row["content"],
                "source": row["source"],
                "created_at": row["created_at"],
            }
            for row in supabase_persistence.list_knowledge_items(record.repository_id)
        ]
        file_paths = {row["id"]: row["path"] for row in rows}
        record.risks = [
            {
                "file_path": file_paths.get(row["file_id"], str(row["file_id"])),
                "score": row["score"],
                "signals": row["signals"],
                "explanation": row["explanation"],
            }
            for row in supabase_persistence.list_risks(record.repository_id)
        ]
        record.commits = [
            {
                "hash": row["commit_hash"],
                "author": row.get("author") or "Unknown",
                "message": row.get("message") or "",
                "timestamp": row.get("timestamp"),
            }
            for row in supabase_persistence.list_commits(record.repository_id)
        ]
        entities_by_file_id = {}
        for row in supabase_persistence.list_entities(record.repository_id):
            entities_by_file_id.setdefault(row["file_id"], []).append(
                {
                    "local_id": str(row["id"]),
                    "entity_type": row["entity_type"],
                    "name": row["name"],
                    "start_line": row.get("start_line"),
                    "end_line": row.get("end_line"),
                    "signature": row.get("signature") or row["name"],
                }
            )
        record.entities = {file_paths[file_id]: entities for file_id, entities in entities_by_file_id.items() if file_id in file_paths}


repository_store = RepositoryStore()