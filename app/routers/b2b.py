"""B2B account provisioning endpoints.

POST /b2b/create-org       — create org with X licenses + invite code
POST /b2b/generate-invites — regenerate invite code for an org
GET  /b2b/validate-invite  — validate invite code, return org info
POST /b2b/activate-invite  — activate invite for logged-in user, tag as B2B
"""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.b2b import B2BLicense, UserLicense
from app.models.user import User
from app.schemas.session import VALID_CONTEXTS

router = APIRouter()


class CreateOrgRequest(BaseModel):
    org_name: str
    context_of_origin: str
    total_licenses: int
    created_by: Optional[str] = None
    expires_at: Optional[datetime] = None


class OrgResponse(BaseModel):
    id: str
    org_name: str
    context_of_origin: str
    total_licenses: int
    used_licenses: int
    invite_code: str
    is_active: bool
    licenses_remaining: int


def _org_response(org: B2BLicense) -> OrgResponse:
    return OrgResponse(
        id=str(org.id),
        org_name=org.org_name,
        context_of_origin=org.context_of_origin,
        total_licenses=org.total_licenses,
        used_licenses=org.used_licenses,
        invite_code=org.invite_code,
        is_active=org.is_active,
        licenses_remaining=org.total_licenses - org.used_licenses,
    )


@router.post("/create-org", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
def create_org(
    body: CreateOrgRequest,
    db: Session = Depends(get_db),
):
    if body.context_of_origin not in VALID_CONTEXTS:
        raise HTTPException(status_code=422, detail=f"context_of_origin must be one of {sorted(VALID_CONTEXTS)}")
    if body.total_licenses < 1:
        raise HTTPException(status_code=422, detail="total_licenses must be at least 1")

    invite_code = secrets.token_urlsafe(32)
    org = B2BLicense(
        org_name=body.org_name,
        context_of_origin=body.context_of_origin,
        total_licenses=body.total_licenses,
        invite_code=invite_code,
        created_by=body.created_by,
        expires_at=body.expires_at,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return _org_response(org)


@router.post("/generate-invites/{org_id}", response_model=OrgResponse)
def regenerate_invite(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    org = db.query(B2BLicense).filter(B2BLicense.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    org.invite_code = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(org)
    return _org_response(org)


@router.get("/validate-invite")
def validate_invite(
    code: str,
    db: Session = Depends(get_db),
):
    org = db.query(B2BLicense).filter(B2BLicense.invite_code == code).first()
    if not org:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if not org.is_active:
        raise HTTPException(status_code=410, detail="This invite link is no longer active")
    if org.expires_at and org.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This invite link has expired")
    if org.used_licenses >= org.total_licenses:
        raise HTTPException(status_code=409, detail="All licenses for this organisation have been used")

    return {
        "valid": True,
        "org_name": org.org_name,
        "context_of_origin": org.context_of_origin,
        "licenses_remaining": org.total_licenses - org.used_licenses,
    }


@router.post("/activate-invite")
def activate_invite(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activate an invite for the logged-in user. Tags user as B2B, decrements license count."""
    org = db.query(B2BLicense).filter(B2BLicense.invite_code == code).first()
    if not org:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if not org.is_active:
        raise HTTPException(status_code=410, detail="Invite link is no longer active")
    if org.expires_at and org.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite link has expired")
    if org.used_licenses >= org.total_licenses:
        raise HTTPException(status_code=409, detail="All licenses have been used")

    # Prevent double-activation
    already = db.query(UserLicense).filter(
        UserLicense.user_id == current_user.id,
        UserLicense.license_id == org.id,
    ).first()
    if already:
        raise HTTPException(status_code=409, detail="You have already activated this invite")

    # Tag user as B2B
    current_user.account_type = "b2b"
    current_user.context_of_origin = org.context_of_origin

    # Create license record and decrement count
    ul = UserLicense(user_id=current_user.id, license_id=org.id)
    org.used_licenses += 1
    db.add(ul)
    db.commit()

    return {
        "activated": True,
        "org_name": org.org_name,
        "context_of_origin": org.context_of_origin,
        "account_type": "b2b",
    }
