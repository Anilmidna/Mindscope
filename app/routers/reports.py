import uuid
import json
import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.report import Report
from app.models.session import AssessmentSession
from app.models.user import User

router = APIRouter()


def _get_session_for_user(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> AssessmentSession:
    return db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == user_id,
    ).first()


@router.get("/{session_id}/status")
def report_status(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_for_user(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    report = db.query(Report).filter(Report.session_id == session_id).first()
    if not report:
        return {"session_id": str(session_id), "status": "queued"}

    response = {
        "session_id": str(session_id),
        "status": report.status,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "llm_model": report.llm_model,
        "prompt_template_version": report.prompt_template_version,
    }

    # Include the JSON report sections when ready (frontend can render before PDF is built)
    if report.status == "ready" and report.raw_llm_json:
        try:
            response["report"] = json.loads(report.raw_llm_json)
        except Exception:
            pass

    return response


@router.get("/{session_id}/download")
def report_download(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns pre-signed S3 URL (1 hour). PDF generation is Week 2 — returns 404 until then."""
    session = _get_session_for_user(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    report = db.query(Report).filter(Report.session_id == session_id).first()
    if not report or report.status != "ready":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not ready")

    if not report.s3_url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation is not yet available. Use /status to get the JSON report.",
        )

    # Generate pre-signed URL from S3 key
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": report.s3_url},
        ExpiresIn=3600,
    )
    return {"session_id": str(session_id), "download_url": presigned_url, "expires_in_seconds": 3600}
