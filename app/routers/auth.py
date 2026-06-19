import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    GoogleCallbackRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.auth_service import (
    blocklist_refresh_token,
    exchange_google_code,
    is_refresh_token_blocked,
    upsert_user,
)

router = APIRouter()


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(body: GoogleCallbackRequest, db: Session = Depends(get_db)):
    redirect_uri = body.redirect_uri or settings.GOOGLE_REDIRECT_URI

    try:
        claims = await exchange_google_code(body.code, body.code_verifier, redirect_uri)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to contact Google")

    google_sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name")

    if not google_sub or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incomplete Google profile")

    user = upsert_user(db, google_sub=google_sub, email=email, name=name)

    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        context_of_origin=user.context_of_origin,
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    if is_refresh_token_blocked(db, body.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        context_of_origin=user.context_of_origin,
    )
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    blocklist_refresh_token(db, body.refresh_token)
