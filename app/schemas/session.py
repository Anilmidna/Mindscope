from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


VALID_CONTEXTS = {"standalone-public", "DATE-college", "training-program"}
VALID_DOMAINS = {"RIASEC", "OCEAN", "Logical", "Numerical", "Verbal", "Spatial"}
VALID_STATUSES = {"started", "riasec_done", "bigfive_done", "aptitude_done", "complete"}


class SessionCreateRequest(BaseModel):
    context_of_origin: str = Field(..., description="standalone-public | DATE-college | training-program")

    def validate_context(self):
        if self.context_of_origin not in VALID_CONTEXTS:
            raise ValueError(f"context_of_origin must be one of {VALID_CONTEXTS}")


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    context_of_origin: str
    status: str
    started_at: datetime

    class Config:
        from_attributes = True


class IntakeFormRequest(BaseModel):
    life_stage: Optional[str] = Field(None, max_length=100)
    current_role: Optional[str] = Field(None, max_length=200)
    current_field: Optional[str] = Field(None, max_length=200)
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    goals: Optional[str] = Field(None, max_length=200)
    challenges: Optional[str] = Field(None, max_length=200)
    background_tags: Optional[str] = Field(None, max_length=500)
    years_of_experience: Optional[str] = Field(None, max_length=50)
    highest_education: Optional[str] = Field(None, max_length=100)


class IntakeFormResponse(BaseModel):
    session_id: UUID
    life_stage: Optional[str]
    current_role: Optional[str]
    current_field: Optional[str]
    satisfaction_rating: Optional[int]
    goals: Optional[str]
    challenges: Optional[str]

    class Config:
        from_attributes = True


class QuestionItem(BaseModel):
    item_id: str
    text: str
    domain: str
    options: Optional[List[str]] = None
    is_reverse_keyed: Optional[bool] = None
    time_limit_seconds: Optional[int] = None


class QuestionBatchResponse(BaseModel):
    session_id: UUID
    domain: str
    section_started_at: Optional[datetime]
    time_limit_seconds: Optional[int]
    items: List[QuestionItem]


class ResponseItem(BaseModel):
    item_id: str
    answer: int
    response_time_ms: Optional[int] = None


class ResponseSubmitRequest(BaseModel):
    domain: str
    items: List[ResponseItem]


class ResponseSubmitResponse(BaseModel):
    session_id: UUID
    domain: str
    items_stored: int
    timed_out: bool = False


class SectionStatusResponse(BaseModel):
    session_id: UUID
    domain: str
    time_remaining_seconds: Optional[int]
    is_complete: bool
