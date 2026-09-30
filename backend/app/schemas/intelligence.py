from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class EvidenceItem(BaseModel):
    source_type: str
    path: str | None = None
    excerpt: str | None = None
    reason: str


class QuestionResponse(BaseModel):
    answer: str
    evidence: list[EvidenceItem]
    confidence: Literal["high", "medium", "low"]
    classification: Literal["verified", "inferred", "human_knowledge"]
    is_refusal: bool = False
    gap_detected: bool = False
    gap_id: UUID | None = None


class GuidanceRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)


class GuidanceStep(BaseModel):
    order: int
    title: str
    files: list[str]
    reasoning: str


class GuidanceResponse(BaseModel):
    task: str
    steps: list[GuidanceStep]


class RiskResponse(BaseModel):
    file_path: str
    score: float
    signals: dict[str, Any]
    explanation: str


class KnowledgeGapResponse(BaseModel):
    gap_id: UUID
    question: str
    context: str | None = None
    priority: str
    status: Literal["open", "resolved"]
    created_at: str


class KnowledgeAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)


class KnowledgeItemResponse(BaseModel):
    knowledge_item_id: UUID
    title: str
    content: str
    source: str
    created_at: str


class OffboardingRequest(BaseModel):
    contributor: str = Field(min_length=1, max_length=200)


class OffboardingResponse(BaseModel):
    session_id: UUID
    status: str
