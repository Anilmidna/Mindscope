import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

logger = logging.getLogger(__name__)
from jwt.exceptions import PyJWTError
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
    blocklist_all_user_refresh_tokens,
    blocklist_refresh_token,
    exchange_google_code,
    is_jti_blocked,
    is_refresh_token_blocked,
    upsert_user,
)

_REFRESH_COOKIE = "refresh_token"
_COOKIE_PATH = "/auth/refresh"

router = APIRouter()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=_COOKIE_PATH,
    )


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    body: GoogleCallbackRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    redirect_uri = body.redirect_uri or settings.GOOGLE_REDIRECT_URI

    try:
        claims = await exchange_google_code(body.code, body.code_verifier, redirect_uri)
    except ValueError as e:
        logger.warning("Google token validation failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error("Google token exchange failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google error: {str(e)}")

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
    refresh_token_value = create_refresh_token(user_id=str(user.id))
    _set_refresh_cookie(response, refresh_token_value)

    return TokenResponse(access_token=access_token)


def _extract_refresh_token(request: Request, body_token: str | None) -> str:
    """Read refresh token from HttpOnly cookie, fall back to body for tests."""
    token = request.cookies.get(_REFRESH_COOKIE) or body_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    return token


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    token = _extract_refresh_token(request, body.refresh_token)

    # Decode first so we can extract jti for reuse detection
    try:
        payload = decode_token(token)
    except (PyJWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    # Reuse detection: if jti already blocklisted, token was stolen — nuclear option
    if jti and is_jti_blocked(db, jti):
        logger.warning("refresh_token_reuse_detected", extra={"user_id": user_id, "token_jti": jti})
        blocklist_all_user_refresh_tokens(db, user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token reuse detected")

    # Also check legacy hash-based blocklist
    if is_refresh_token_blocked(db, token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Blocklist the old token before issuing new one
    blocklist_refresh_token(db, token, jti=jti, user_id=user_id)

    new_access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        context_of_origin=user.context_of_origin,
    )
    new_refresh_token = create_refresh_token(user_id=str(user.id))
    _set_refresh_cookie(response, new_refresh_token)

    return AccessTokenResponse(access_token=new_access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest,
    db: Session = Depends(get_db),
):
    token = _extract_refresh_token(request, body.refresh_token)

    try:
        payload = decode_token(token)
    except (PyJWTError, Exception):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    jti = payload.get("jti")
    user_id = payload.get("sub")
    blocklist_refresh_token(db, token, jti=jti, user_id=user_id)
    response.delete_cookie(_REFRESH_COOKIE, path=_COOKIE_PATH)
