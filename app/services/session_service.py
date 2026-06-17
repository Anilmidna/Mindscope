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
)

# Server-side time limits per aptitude domain (seconds)
APTITUDE_TIME_LIMITS = {
    "Logical": 900,
    "Numerical": 900,
    "Verbal": 900,
    "Spatial": 900,
}

TIMED_DOMAINS = set(APTITUDE_TIME_LIMITS.keys())

# Item bank files — loaded once at startup
_item_banks: dict = {}

ITEM_BANK_PATHS = {
    "RIASEC": Path("scoring/item_banks/riasec.json"),
    "OCEAN": Path("scoring/item_banks/ocean.json"),
    "Logical": Path("scoring/item_banks/aptitude_logical.json"),
    "Numerical": Path("scoring/item_banks/aptitude_numerical.json"),
    "Verbal": Path("scoring/item_banks/aptitude_verbal.json"),
    "Spatial": Path("scoring/item_banks/aptitude_spatial.json"),
}


def _load_item_bank(domain: str) -> List[dict]:
    if domain not in _item_banks:
        path = ITEM_BANK_PATHS.get(domain)
        if path and path.exists():
            with open(path) as f:
                _item_banks[domain] = json.load(f)
        else:
            _item_banks[domain] = []
    return _item_banks[domain]


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
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    intake = IntakeForm(session_id=session.id, **data.model_dump(exclude_none=True))
    db.add(intake)
    db.commit()
    db.refresh(intake)
    return intake


def get_question_batch(
    db: Session,
    session: AssessmentSession,
    domain: str,
) -> tuple[List[QuestionItem], Optional[datetime], Optional[int]]:
    items_raw = _load_item_bank(domain)

    # Randomise order — use session id as seed for reproducibility per attempt
    rng = random.Random(str(session.id) + domain)
    shuffled = list(items_raw)
    rng.shuffle(shuffled)

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
            options=item.get("options"),
            is_reverse_keyed=item.get("reverse_keyed"),
            time_limit_seconds=APTITUDE_TIME_LIMITS.get(domain),
        )
        for item in shuffled
    ]

    section_started_at = timer.started_at if timer else None
    return questions, section_started_at, time_limit


def save_responses(
    db: Session,
    session: AssessmentSession,
    domain: str,
    items: List[ResponseItem],
) -> tuple[int, bool]:
    """Store responses. Returns (count_stored, timed_out).
    For timed domains, items submitted after the deadline are still stored but timed_out=True is flagged.
    """
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
        existing = db.query(Response).filter(
            Response.session_id == session.id,
            Response.item_id == item.item_id,
        ).first()
        if existing:
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
    """Returns (time_remaining_seconds, is_complete). time_remaining_seconds is None for untimed domains."""
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


def get_session_or_404(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> AssessmentSession:
    session = db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == user_id,
    ).first()
    return session
