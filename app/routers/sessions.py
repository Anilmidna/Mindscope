import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db, SessionLocal
from app.models.payment import Payment
from app.models.report import Report
from app.models.user import User
from app.schemas.session import (
    IntakeFormRequest,
    IntakeFormResponse,
    QuestionBatchResponse,
    ResponseSubmitRequest,
    ResponseSubmitResponse,
    SectionStatusResponse,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionResponse,
    VALID_CONTEXTS,
    VALID_DOMAINS,
)
from app.services.session_service import (
    create_session,
    get_completed_domains,
    get_question_batch,
    get_section_status,
    get_session_or_404,
    save_intake,
    save_responses,
)
from app.services.report_service import run_scoring_pipeline
from app.middleware.rate_limit import limiter, get_user_id

router = APIRouter()


def _run_scoring_in_background(session_id: uuid.UUID) -> None:
    """Background task wrapper — creates its own DB session so it outlives the request."""
    from app.models.session import AssessmentSession
    db = SessionLocal()
    try:
        session = db.query(AssessmentSession).filter(AssessmentSession.id == session_id).first()
        if session:
            run_scoring_pipeline(db, session)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("", response_model=list[SessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.session import AssessmentSession as AS
    return db.query(AS).filter(AS.user_id == current_user.id).order_by(AS.started_at.desc()).all()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/day", key_func=get_user_id)
def create_assessment_session(
    request: Request,
    body: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.context_of_origin not in VALID_CONTEXTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"context_of_origin must be one of {sorted(VALID_CONTEXTS)}",
        )
    session = create_session(db, user_id=current_user.id, context_of_origin=body.context_of_origin)
    return session


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session_or_404(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    completed_domains = get_completed_domains(db, session_id)
    return SessionDetailResponse(
        id=session.id,
        user_id=session.user_id,
        context_of_origin=session.context_of_origin,
        flow_type=session.flow_type,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        completed_domains=completed_domains,
    )


@router.post("/{session_id}/intake", response_model=IntakeFormResponse)
def submit_intake(
    session_id: uuid.UUID,
    body: IntakeFormRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session_or_404(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    intake = save_intake(db, session, body)
    return intake


@router.get("/{session_id}/questions", response_model=QuestionBatchResponse)
def get_questions(
    session_id: uuid.UUID,
    domain: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if domain not in VALID_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"domain must be one of {sorted(VALID_DOMAINS)}",
        )
    session = get_session_or_404(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # B2C sessions require payment before assessment access
    if session.flow_type == "b2c":
        paid = db.query(Payment).filter(
            Payment.session_id == session_id,
            Payment.status == "paid",
        ).first()
        if not paid:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Payment required to start assessment",
            )

    items, section_started_at, time_limit, persona = get_question_batch(db, session, domain)
    return QuestionBatchResponse(
        session_id=session_id,
        domain=domain,
        persona=persona,
        section_started_at=section_started_at,
        time_limit_seconds=time_limit,
        items=items,
    )


@router.post("/{session_id}/responses", response_model=ResponseSubmitResponse)
def submit_responses(
    session_id: uuid.UUID,
    body: ResponseSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.domain not in VALID_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"domain must be one of {sorted(VALID_DOMAINS)}",
        )
    session = get_session_or_404(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    stored, timed_out = save_responses(db, session, body.domain, body.items)
    return ResponseSubmitResponse(
        session_id=session_id,
        domain=body.domain,
        items_stored=stored,
        timed_out=timed_out,
    )


@router.get("/{session_id}/section-status", response_model=SectionStatusResponse)
def section_status(
    session_id: uuid.UUID,
    domain: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if domain not in VALID_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"domain must be one of {sorted(VALID_DOMAINS)}",
        )
    session = get_session_or_404(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    time_remaining, is_complete = get_section_status(db, session, domain)
    return SectionStatusResponse(
        session_id=session_id,
        domain=domain,
        time_remaining_seconds=time_remaining,
        is_complete=is_complete,
    )


@router.post("/{session_id}/complete", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/day", key_func=get_user_id)
def complete_session(
    request: Request,
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark session complete and trigger scoring + Bedrock report generation.
    Returns immediately (202) — poll /reports/{session_id}/status for result.
    """
    session = get_session_or_404(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status == "complete":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already complete")

    # Queue pipeline in background — response returns immediately
    # Pass session_id (not the ORM object) so the task creates its own DB session
    background_tasks.add_task(_run_scoring_in_background, session.id)

    return {"session_id": str(session_id), "status": "queued", "message": "Scoring and report generation started. Poll /reports/{session_id}/status for updates."}
