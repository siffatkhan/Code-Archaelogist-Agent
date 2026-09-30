from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.routes_repositories import user_id
from backend.app.schemas.repositories import AnalysisJobResponse
from backend.app.services.repository_store import repository_store

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{analysis_job_id}", response_model=AnalysisJobResponse)
async def get_analysis(analysis_job_id: UUID, current_user: str = Depends(user_id)) -> AnalysisJobResponse:
    result = repository_store.get_job(current_user, analysis_job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis job was not found.")
    _, job = result
    return AnalysisJobResponse(
        analysis_job_id=analysis_job_id,
        status=job["status"],
        error_message=job["error_message"],
    )