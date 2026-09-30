from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from backend.app.core.security import get_current_user
from backend.app.schemas.repositories import CreateRepositoryRequest, RepositoryResponse
from backend.app.services.github import parse_github_url
from backend.app.services.repository_store import RepositoryRecord, repository_store
from backend.app.services.supabase_persistence import supabase_persistence

router = APIRouter(prefix="/repositories", tags=["repositories"])


def user_id(user: dict[str, object] = Depends(get_current_user)) -> str:
    subject = user.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Authenticated user has no subject.")
    try:
        UUID(subject)
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Authenticated user ID is invalid.") from error
    return subject


def to_response(record: RepositoryRecord) -> RepositoryResponse:
    return RepositoryResponse(
        repository_id=record.repository_id,
        github_url=record.github_url,
        status=record.status,
        owner=record.owner,
        name=record.name,
        default_branch=record.default_branch,
        last_analyzed_at=record.last_analyzed_at,
        created_at=record.created_at,
    )


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(payload: CreateRepositoryRequest, current_user: str = Depends(user_id)) -> RepositoryResponse:
    try:
        owner, name = parse_github_url(str(payload.github_url))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return to_response(repository_store.create(current_user, str(payload.github_url), owner, name))


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(current_user: str = Depends(user_id)) -> list[RepositoryResponse]:
    return [to_response(record) for record in repository_store.list_for_user(current_user)]


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: UUID, current_user: str = Depends(user_id)) -> RepositoryResponse:
    record = repository_store.get_for_user(current_user, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return to_response(record)


async def run_analysis(repository_id: UUID, job_id: UUID) -> None:
    record = repository_store._repositories.get(repository_id)
    if not record:
        return
    job = record.jobs[job_id]
    try:
        from backend.app.services.github import fetch_file_paths, fetch_repository_metadata
        from backend.app.services.local_intelligence import enrich_analysis

        job["status"] = "running"
        if supabase_persistence.enabled:
            supabase_persistence.update_job(job_id, "running")
            supabase_persistence.update_repository(record.repository_id, "running")
        metadata = await fetch_repository_metadata(record.owner, record.name)
        record.default_branch = metadata["default_branch"]
        record.files = await fetch_file_paths(record.owner, record.name, record.default_branch)
        await enrich_analysis(record)
        if supabase_persistence.enabled:
            supabase_persistence.replace_files(
                record.repository_id,
                [
                    {
                        "repository_id": str(record.repository_id),
                        "path": path,
                        "content": record.file_contents.get(path),
                        "size": len(record.file_contents.get(path, "").encode()),
                        "language": None,
                    }
                    for path in record.files
                ],
            )
            supabase_persistence.replace_commits(record.repository_id, record.commits)
            supabase_persistence.replace_contributors(record.repository_id, record.commits)
            supabase_persistence.replace_entities(record.repository_id, record.entities)
            supabase_persistence.replace_risks(record.repository_id, record.risks)
        record.status = "completed"
        from datetime import datetime, timezone

        record.last_analyzed_at = datetime.now(timezone.utc)
        job["status"] = "completed"
        if supabase_persistence.enabled:
            supabase_persistence.update_job(job_id, "completed")
            supabase_persistence.update_repository(
                record.repository_id,
                "completed",
                default_branch=record.default_branch,
                last_analyzed_at=record.last_analyzed_at.isoformat(),
            )
    except Exception as error:
        record.status = "failed"
        job["status"] = "failed"
        job["error_message"] = str(error)
        if supabase_persistence.enabled:
            supabase_persistence.update_job(job_id, "failed", str(error))
            supabase_persistence.update_repository(record.repository_id, "failed")


@router.post("/{repository_id}/analyze", response_model=dict[str, object], status_code=status.HTTP_202_ACCEPTED)
async def analyze_repository(
    repository_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(user_id),
) -> dict[str, object]:
    record = repository_store.get_for_user(current_user, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository was not found.")
    job_id = repository_store.create_job(record)
    background_tasks.add_task(run_analysis, repository_id, job_id)
    return {"analysis_job_id": job_id, "status": "queued"}