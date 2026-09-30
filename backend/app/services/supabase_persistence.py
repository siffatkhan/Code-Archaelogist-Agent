from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from backend.app.core.config import get_settings


class SupabasePersistence:
    """Small PostgREST adapter for the API's persistence boundary.

    It uses the server-only service-role key. The frontend publishable key
    must never be used here because this layer writes user-owned data.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{(settings.supabase_url or '').rstrip('/')}/rest/v1"
        self.key = settings.supabase_service_role_key

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.base_url != "/rest/v1")

    def _request(self, method: str, table: str, **kwargs: Any) -> list[dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError("Supabase persistence is not configured")
        headers = {
            "apikey": self.key or "",
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        headers.update(kwargs.pop("headers", {}))
        response = httpx.request(method, f"{self.base_url}/{table}", headers=headers, timeout=20, **kwargs)
        response.raise_for_status()
        if not response.content:
            return []
        return response.json()

    @staticmethod
    def _eq(column: str, value: str | UUID) -> str:
        return f"eq.{quote(str(value), safe='-_.')}"

    def create_repository(self, user_id: str, github_url: str) -> dict[str, Any]:
        rows = self._request(
            "POST",
            "repositories",
            params={"select": "*"},
            headers={"Prefer": "return=representation"},
            json={"user_id": user_id, "github_url": github_url, "status": "created"},
        )
        return rows[0]

    def list_repositories(self, user_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "repositories", params={"user_id": self._eq("user_id", user_id), "select": "*"})

    def get_repository(self, user_id: str, repository_id: UUID) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "repositories",
            params={"user_id": self._eq("user_id", user_id), "id": self._eq("id", repository_id), "select": "*"},
        )
        return rows[0] if rows else None

    def update_repository(
        self,
        repository_id: UUID,
        status: str,
        default_branch: str | None = None,
        last_analyzed_at: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"status": status}
        if default_branch is not None:
            payload["default_branch"] = default_branch
        if last_analyzed_at is not None:
            payload["last_analyzed_at"] = last_analyzed_at
        self._request("PATCH", "repositories", params={"id": self._eq("id", repository_id)}, json=payload)

    def create_job(self, repository_id: UUID) -> dict[str, Any]:
        rows = self._request(
            "POST",
            "analysis_jobs",
            params={"select": "*"},
            headers={"Prefer": "return=representation"},
            json={"repository_id": str(repository_id), "status": "queued"},
        )
        return rows[0]

    def update_job(self, job_id: UUID, status: str, error_message: str | None = None) -> None:
        self._request(
            "PATCH",
            "analysis_jobs",
            params={"id": self._eq("id", job_id)},
            json={"status": status, "error_message": error_message},
        )

    def get_job(self, job_id: UUID) -> dict[str, Any] | None:
        rows = self._request("GET", "analysis_jobs", params={"id": self._eq("id", job_id), "select": "*"})
        return rows[0] if rows else None

    def replace_files(self, repository_id: UUID, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._request("DELETE", "repository_files", params={"repository_id": self._eq("repository_id", repository_id)})
        if files:
            self._request("POST", "repository_files", json=files)
        return self.list_files(repository_id)

    def list_files(self, repository_id: UUID) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "repository_files",
            params={"repository_id": self._eq("repository_id", repository_id), "select": "*", "order": "path.asc"},
        )

    def replace_commits(self, repository_id: UUID, commits: list[dict[str, Any]]) -> None:
        self._request("DELETE", "commits", params={"repository_id": self._eq("repository_id", repository_id)})
        rows = [
            {
                "repository_id": str(repository_id),
                "commit_hash": commit.get("hash") or "unknown",
                "author": commit.get("author"),
                "message": commit.get("message"),
                "timestamp": commit.get("timestamp"),
            }
            for commit in commits
        ]
        if rows:
            self._request("POST", "commits", json=rows)

    def replace_contributors(self, repository_id: UUID, commits: list[dict[str, Any]]) -> None:
        self._request("DELETE", "contributors", params={"repository_id": self._eq("repository_id", repository_id)})
        counts: dict[str, int] = {}
        for commit in commits:
            author = commit.get("author") or "Unknown"
            counts[author] = counts.get(author, 0) + 1
        rows = [
            {"repository_id": str(repository_id), "external_id": name, "name": name, "commit_count": count}
            for name, count in counts.items()
        ]
        if rows:
            self._request("POST", "contributors", json=rows)

    def replace_entities(self, repository_id: UUID, entities_by_path: dict[str, list[dict[str, Any]]]) -> None:
        self._request("DELETE", "code_entities", params={"repository_id": self._eq("repository_id", repository_id)})
        files = {row["path"]: row["id"] for row in self.list_files(repository_id)}
        rows = []
        for path, entities in entities_by_path.items():
            file_id = files.get(path)
            if not file_id:
                continue
            rows.extend(
                {
                    "repository_id": str(repository_id),
                    "file_id": file_id,
                    "entity_type": entity["entity_type"],
                    "name": entity["name"],
                    "start_line": entity.get("start_line"),
                    "end_line": entity.get("end_line"),
                    "signature": entity.get("signature"),
                }
                for entity in entities
            )
        if rows:
            self._request("POST", "code_entities", json=rows)

    def replace_risks(self, repository_id: UUID, risks: list[dict[str, Any]]) -> None:
        self._request("DELETE", "risk_records", params={"repository_id": self._eq("repository_id", repository_id)})
        files = {row["path"]: row["id"] for row in self.list_files(repository_id)}
        rows = [
            {
                "repository_id": str(repository_id),
                "file_id": files[risk["file_path"]],
                "score": risk["score"],
                "signals": risk["signals"],
                "explanation": risk["explanation"],
            }
            for risk in risks
            if risk.get("file_path") in files
        ]
        if rows:
            self._request("POST", "risk_records", json=rows)

    def create_knowledge_gap(self, repository_id: UUID, gap: dict[str, Any]) -> None:
        self._request(
            "POST",
            "knowledge_gaps",
            json={
                "id": str(gap["gap_id"]),
                "repository_id": str(repository_id),
                "question": gap["question"],
                "context": gap.get("context"),
                "priority": gap.get("priority", "medium"),
                "status": gap.get("status", "open"),
            },
        )

    def create_knowledge_item(self, repository_id: UUID, item: dict[str, Any], user_id: str) -> None:
        self._request(
            "POST",
            "knowledge_items",
            json={
                "id": str(item["knowledge_item_id"]),
                "repository_id": str(repository_id),
                "user_id": user_id,
                "title": item["title"],
                "content": item["content"],
                "source": item["source"],
            },
        )

    def resolve_knowledge_gap(self, gap_id: UUID, item_id: UUID) -> None:
        self._request(
            "PATCH",
            "knowledge_gaps",
            params={"id": self._eq("id", gap_id)},
            json={"status": "resolved", "resolved_knowledge_item_id": str(item_id)},
        )

    def list_knowledge_gaps(self, repository_id: UUID) -> list[dict[str, Any]]:
        return self._request("GET", "knowledge_gaps", params={"repository_id": self._eq("repository_id", repository_id), "select": "*"})

    def list_knowledge_items(self, repository_id: UUID) -> list[dict[str, Any]]:
        return self._request("GET", "knowledge_items", params={"repository_id": self._eq("repository_id", repository_id), "select": "*"})

    def list_risks(self, repository_id: UUID) -> list[dict[str, Any]]:
        return self._request("GET", "risk_records", params={"repository_id": self._eq("repository_id", repository_id), "select": "*"})

    def list_commits(self, repository_id: UUID) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "commits",
            params={"repository_id": self._eq("repository_id", repository_id), "select": "*", "order": "timestamp.desc"},
        )

    def list_entities(self, repository_id: UUID) -> list[dict[str, Any]]:
        return self._request("GET", "code_entities", params={"repository_id": self._eq("repository_id", repository_id), "select": "*"})


supabase_persistence = SupabasePersistence()