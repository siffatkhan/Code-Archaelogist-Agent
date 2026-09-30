from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.routes_repositories import user_id
from backend.app.schemas.intelligence import (
    GuidanceRequest,
    GuidanceResponse,
    KnowledgeAnswerRequest,
    KnowledgeGapResponse,
    KnowledgeItemResponse,
    OffboardingRequest,
    OffboardingResponse,
    QuestionRequest,
    QuestionResponse,
    RiskResponse,
)
from backend.app.services.local_intelligence import answer_question, build_guidance, create_offboarding
from backend.app.services.repository_store import RepositoryRecord, repository_store
from backend.app.services.supabase_persistence import supabase_persistence

router = APIRouter(prefix="/repositories/{repository_id}", tags=["intelligence"])


def repository_for_user(repository_id: UUID, current_user: str) -> RepositoryRecord:
    record = repository_store.get_for_user(current_user, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return record


@router.post("/questions", response_model=QuestionResponse)
async def ask_question(repository_id: UUID, payload: QuestionRequest, current_user: str = Depends(user_id)) -> QuestionResponse:
    record = repository_for_user(repository_id, current_user)
    result = answer_question(record, payload.question)
    if result["gap_detected"] and result["gap_id"] and supabase_persistence.enabled:
        gap = next(item for item in record.knowledge_gaps if item["gap_id"] == result["gap_id"])
        supabase_persistence.create_knowledge_gap(repository_id, gap)
    return QuestionResponse(**result)


@router.post("/guidance", response_model=GuidanceResponse)
async def get_guidance(repository_id: UUID, payload: GuidanceRequest, current_user: str = Depends(user_id)) -> GuidanceResponse:
    record = repository_for_user(repository_id, current_user)
    return GuidanceResponse(**build_guidance(record, payload.task))


@router.get("/risks", response_model=list[RiskResponse])
async def get_risks(repository_id: UUID, current_user: str = Depends(user_id)) -> list[RiskResponse]:
    record = repository_for_user(repository_id, current_user)
    return [RiskResponse(**risk) for risk in record.risks]


@router.get("/knowledge-gaps", response_model=list[KnowledgeGapResponse])
async def get_knowledge_gaps(repository_id: UUID, current_user: str = Depends(user_id)) -> list[KnowledgeGapResponse]:
    record = repository_for_user(repository_id, current_user)
    return [KnowledgeGapResponse(**gap) for gap in record.knowledge_gaps]


@router.post("/knowledge-gaps/{gap_id}/answer", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def answer_knowledge_gap(
    repository_id: UUID,
    gap_id: UUID,
    payload: KnowledgeAnswerRequest,
    current_user: str = Depends(user_id),
) -> KnowledgeItemResponse:
    record = repository_for_user(repository_id, current_user)
    gap = next((item for item in record.knowledge_gaps if item["gap_id"] == gap_id), None)
    if not gap:
        raise HTTPException(status_code=404, detail="Knowledge gap was not found.")
    gap["status"] = "resolved"
    item = {
        "knowledge_item_id": UUID(int=gap_id.int),
        "title": gap["question"][:120],
        "content": payload.answer,
        "source": "human_knowledge",
        "created_at": gap["created_at"],
    }
    record.knowledge_items.append(item)
    if supabase_persistence.enabled:
        supabase_persistence.create_knowledge_item(repository_id, item, current_user)
        supabase_persistence.resolve_knowledge_gap(gap_id, item["knowledge_item_id"])
    return KnowledgeItemResponse(**item)


@router.get("/knowledge", response_model=list[KnowledgeItemResponse])
async def get_knowledge(repository_id: UUID, current_user: str = Depends(user_id)) -> list[KnowledgeItemResponse]:
    record = repository_for_user(repository_id, current_user)
    return [KnowledgeItemResponse(**item) for item in record.knowledge_items]


@router.post("/offboarding", response_model=OffboardingResponse, status_code=status.HTTP_201_CREATED)
async def start_offboarding(
    repository_id: UUID,
    payload: OffboardingRequest,
    current_user: str = Depends(user_id),
) -> OffboardingResponse:
    record = repository_for_user(repository_id, current_user)
    return OffboardingResponse(**create_offboarding(record, payload.contributor))


@router.get("/offboarding/{session_id}")
async def get_offboarding(repository_id: UUID, session_id: UUID, current_user: str = Depends(user_id)) -> dict:
    record = repository_for_user(repository_id, current_user)
    report = record.offboarding_sessions.get(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Offboarding session was not found.")
    return report


@router.post("/offboarding/{session_id}/questions/{question_id}/answer")
async def answer_offboarding_question(
    repository_id: UUID,
    session_id: UUID,
    question_id: UUID,
    payload: KnowledgeAnswerRequest,
    current_user: str = Depends(user_id),
) -> dict:
    record = repository_for_user(repository_id, current_user)
    report = record.offboarding_sessions.get(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Offboarding session was not found.")
    question = next((item for item in report["questions"] if item["question_id"] == question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Offboarding question was not found.")
    question["answer"] = payload.answer
    question["status"] = "answered"
    if all(item["status"] == "answered" for item in report["questions"]):
        report["status"] = "completed"
    return question