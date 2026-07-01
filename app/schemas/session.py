from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

VALID_CONTEXTS = {"standalone-public", "DATE-college", "training-program", "b2b-partner"}

# B2B contexts skip payment gate
B2B_CONTEXTS = {"DATE-college", "training-program", "b2b-partner"}
VALID_DOMAINS = {"RIASEC", "OCEAN", "Logical", "Numerical", "Verbal", "Spatial"}

# From persona_intake.json maps_to_persona
LIFE_STAGE_TO_PERSONA = {
    "School Student (Class 9-12)": "student",
    "Undergraduate Student": "student",
    "Final-Year / Graduate Student": "student",
    "Working Professional (0-3 years)": "professional",
    "Working Professional (3-10 years)": "professional",
    "Working Professional (10+ years)": "professional",
    "Career Switcher": "professional",
    "Currently Not Working": "professional",
}


class SessionCreateRequest(BaseModel):
    context_of_origin: str = Field(..., description="standalone-public | DATE-college | training-program")


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    context_of_origin: str
    status: str
    started_at: datetime

    class Config:
        from_attributes = True


class IntakeFormRequest(BaseModel):
    life_stage: str = Field(..., description="Determines RIASEC persona (student/professional)")
    domain: Optional[str] = Field(None, max_length=200)
    specialization: Optional[str] = Field(None, max_length=100)
    future_goals: str = Field(..., max_length=200)
    satisfaction: int = Field(..., ge=1, le=10)
    challenges: Optional[str] = Field(None, max_length=200)
    education_level: Optional[str] = Field(None, max_length=100)
    preferred_work_style: Optional[str] = Field(None, max_length=100)
    consent_given_at: datetime = Field(..., description="DPDP: timestamp when user accepted data processing consent")
    date_of_birth: Optional[date] = Field(None, description="DPDP §9: required for age-based consent checks")
    parent_email: Optional[str] = Field(None, max_length=254, description="Required if age 16-17")

    @model_validator(mode="after")
    def validate_life_stage(self):
        if self.life_stage not in LIFE_STAGE_TO_PERSONA:
            raise ValueError(f"life_stage must be one of: {list(LIFE_STAGE_TO_PERSONA.keys())}")
        return self

    @property
    def persona(self) -> str:
        return LIFE_STAGE_TO_PERSONA[self.life_stage]


class IntakeFormResponse(BaseModel):
    session_id: UUID
    life_stage: str
    persona: str
    domain: Optional[str]
    specialization: Optional[str]
    future_goals: Optional[str]
    satisfaction: Optional[int]
    challenges: Optional[str]
    consent_given_at: datetime
    date_of_birth: Optional[date] = None
    parent_email: Optional[str] = None
    minor_consent_pending: Optional[bool] = None

    class Config:
        from_attributes = True


class QuestionItem(BaseModel):
    item_id: str
    text: str
    domain: str
    subscale: Optional[str] = None
    options: Optional[List[str]] = None
    is_reverse_keyed: Optional[bool] = None
    time_limit_seconds: Optional[int] = None


class QuestionBatchResponse(BaseModel):
    session_id: UUID
    domain: str
    persona: Optional[str] = None
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


class SessionDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    context_of_origin: str
    flow_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    completed_domains: List[str]

    class Config:
        from_attributes = True
