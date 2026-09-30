from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, HttpUrl


AnalysisStatus = Literal["queued", "running", "completed", "failed"]


class CreateRepositoryRequest(BaseModel):
    github_url: HttpUrl


class RepositoryResponse(BaseModel):
    repository_id: UUID
    github_url: str
    status: str
    owner: str
    name: str
    default_branch: str | None = None
    last_analyzed_at: datetime | None = None
    created_at: datetime


class AnalysisJobResponse(BaseModel):
    analysis_job_id: UUID
    status: AnalysisStatus
    error_message: str | None = None


class FileNode(BaseModel):
    path: str
    name: str
    type: Literal["file", "directory"]
    children: list["FileNode"] | None = None


class FileContentResponse(BaseModel):
    path: str
    content: str
    language: str | None = None
    size_bytes: int
    truncated: bool = False