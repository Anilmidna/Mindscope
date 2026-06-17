import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.intake import IntakeForm
from app.models.response import Response
from app.models.section_timer import SectionTimer
from app.models.session import AssessmentSession
from app.schemas.session import (
    IntakeFormRequest,
    QuestionItem,
    ResponseItem,
    LIFE_STAGE_TO_PERSONA,
)

# Server-side time limits per aptitude domain (seconds)
APTITUDE_TIME_LIMITS = {
    "Logical": 900,
    "Numerical": 900,
    "Verbal": 900,
    "Spatial": 900,
}

TIMED_DOMAINS = set(APTITUDE_TIME_LIMITS.keys())

ITEM_BANK_PATHS = {
    "RIASEC_student":     Path("scoring/item_banks/riasec_student.json"),
    "RIASEC_professional": Path("scoring/item_banks/riasec_professional.json"),
    "OCEAN":              Path("scoring/item_banks/ocean.json"),
    "Logical":            Path("scoring/item_banks/aptitude_logical.json"),
    "Numerical":          Path("scoring/item_banks/aptitude_numerical.json"),
    "Verbal":             Path("scoring/item_banks/aptitude_verbal.json"),
    "Spatial":            Path("scoring/item_banks/aptitude_spatial.json"),
}

_item_banks: dict = {}


def _load_bank(key: str) -> dict:
    if key not in _item_banks:
        path = ITEM_BANK_PATHS.get(key)
        if path and path.exists():
            with open(path) as f:
                _item_banks[key] = json.load(f)
        else:
            _item_banks[key] = {"items": [], "attention_checks": []}
    return _item_banks[key]


def _get_persona_for_session(db: Session, session: AssessmentSession) -> str:
    intake = db.query(IntakeForm).filter(IntakeForm.session_id == session.id).first()
    if intake:
        return intake.persona
    return "student"  # safe default


def _inject_attention_checks(items: List[dict], checks: List[dict], rng: random.Random) -> List[dict]:
    """Insert attention check items at the positions hinted in the bank."""
    result = list(items)
    for check in checks:
        hint = check.get("position_hint", "")
        try:
            # parse "insert around item 15-20" → pick midpoint
            parts = hint.replace("insert around item ", "").split("-")
            lo, hi = int(parts[0]), int(parts[1])
            pos = rng.randint(lo - 1, min(hi - 1, len(result)))
        except Exception:
            pos = rng.randint(0, len(result))
        result.insert(pos, {**check, "is_attention_check": True})
    return result


def create_session(db: Session, user_id: uuid.UUID, context_of_origin: str) -> AssessmentSession:
    session = AssessmentSession(
        user_id=user_id,
        context_of_origin=context_of_origin,
        status="started",
        scoring_engine_version="1.0",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def save_intake(db: Session, session: AssessmentSession, data: IntakeFormRequest) -> IntakeForm:
    existing = db.query(IntakeForm).filter(IntakeForm.session_id == session.id).first()
    if existing:
        for field in ("life_stage", "persona", "domain", "specialization", "future_goals",
                      "satisfaction", "challenges", "education_level", "preferred_work_style"):
            val = getattr(data, field, None)
            if field == "persona":
                val = data.persona
            if val is not None:
                setattr(existing, field, val)
        db.commit()
        db.refresh(existing)
        return existing

    intake = IntakeForm(
        session_id=session.id,
        life_stage=data.life_stage,
        persona=data.persona,
        domain=data.domain,
        specialization=data.specialization,
        future_goals=data.future_goals,
        satisfaction=data.satisfaction,
        challenges=data.challenges,
        education_level=data.education_level,
        preferred_work_style=data.preferred_work_style,
    )
    db.add(intake)
    db.commit()
    db.refresh(intake)
    return intake


def get_question_batch(
    db: Session,
    session: AssessmentSession,
    domain: str,
) -> tuple[List[QuestionItem], Optional[datetime], Optional[int], Optional[str]]:
    """Returns (items, section_started_at, time_limit_seconds, persona)."""

    persona = None
    if domain == "RIASEC":
        persona = _get_persona_for_session(db, session)
        bank = _load_bank(f"RIASEC_{persona}")
    else:
        bank = _load_bank(domain)

    raw_items = bank.get("items", [])
    attention_checks = bank.get("attention_checks", [])

    # Reproducible shuffle per session+domain
    rng = random.Random(str(session.id) + domain)
    shuffled = list(raw_items)
    rng.shuffle(shuffled)

    # Inject attention checks at hinted positions
    if attention_checks:
        shuffled = _inject_attention_checks(shuffled, attention_checks, rng)

    # Start server-side timer on first fetch for timed domains
    timer = None
    time_limit = None
    if domain in TIMED_DOMAINS:
        timer = db.query(SectionTimer).filter(
            SectionTimer.session_id == session.id,
            SectionTimer.domain == domain,
        ).first()
        if not timer:
            time_limit = APTITUDE_TIME_LIMITS[domain]
            timer = SectionTimer(
                session_id=session.id,
                domain=domain,
                time_limit_seconds=time_limit,
            )
            db.add(timer)
            db.commit()
            db.refresh(timer)
        time_limit = timer.time_limit_seconds

    questions = [
        QuestionItem(
            item_id=item["item_id"],
            text=item["text"],
            domain=domain,
            subscale=item.get("subscale"),
            options=item.get("options"),
            is_reverse_keyed=item.get("reverse_keyed", False),
            time_limit_seconds=APTITUDE_TIME_LIMITS.get(domain),
        )
        for item in shuffled
    ]

    section_started_at = timer.started_at if timer else None
    return questions, section_started_at, time_limit, persona


def save_responses(
    db: Session,
    session: AssessmentSession,
    domain: str,
    items: List[ResponseItem],
) -> tuple[int, bool]:
    timed_out = False

    if domain in TIMED_DOMAINS:
        timer = db.query(SectionTimer).filter(
            SectionTimer.session_id == session.id,
            SectionTimer.domain == domain,
        ).first()
        if timer:
            elapsed = (datetime.now(timezone.utc) - timer.started_at.replace(tzinfo=timezone.utc)).total_seconds()
            if elapsed > timer.time_limit_seconds:
                timed_out = True

    stored = 0
    for item in items:
        exists = db.query(Response).filter(
            Response.session_id == session.id,
            Response.item_id == item.item_id,
        ).first()
        if exists:
            continue
        resp = Response(
            session_id=session.id,
            item_id=item.item_id,
            answer=item.answer,
            response_time_ms=item.response_time_ms,
            domain=domain,
        )
        db.add(resp)
        stored += 1

    db.commit()
    return stored, timed_out


def get_section_status(
    db: Session,
    session: AssessmentSession,
    domain: str,
) -> tuple[Optional[int], bool]:
    if domain not in TIMED_DOMAINS:
        return None, False

    timer = db.query(SectionTimer).filter(
        SectionTimer.session_id == session.id,
        SectionTimer.domain == domain,
    ).first()
    if not timer:
        return None, False

    elapsed = (datetime.now(timezone.utc) - timer.started_at.replace(tzinfo=timezone.utc)).total_seconds()
    remaining = max(0, timer.time_limit_seconds - int(elapsed))
    return remaining, remaining == 0


def get_session_or_404(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> Optional[AssessmentSession]:
    return db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == user_id,
    ).first()
