import hashlib
import logging

import httpx

logger = logging.getLogger(__name__)
from jose import jwt as jose_jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.token_blocklist import RefreshTokenBlocklist

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUER = "https://accounts.google.com"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def exchange_google_code(code: str, code_verifier: str, redirect_uri: str) -> dict:
    """Exchange authorization code for Google tokens and return the verified ID token claims."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        if not response.is_success:
            raise ValueError(f"Google token endpoint returned {response.status_code}: {response.text}")
        token_data = response.json()

    id_token = token_data.get("id_token")
    if not id_token:
        raise ValueError(f"No id_token in Google response. Got keys: {list(token_data.keys())}. Error: {token_data.get('error')}, {token_data.get('error_description')}")

    access_token = token_data.get("access_token")
    claims = await _verify_google_id_token(id_token, access_token)
    return claims


async def _verify_google_id_token(id_token: str, access_token: str | None = None) -> dict:
    """Verify Google ID token signature, iss, aud, and exp."""
    async with httpx.AsyncClient() as client:
        certs_response = await client.get(GOOGLE_CERTS_URL)
        certs_response.raise_for_status()
        jwks = certs_response.json()

    try:
        claims = jose_jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            issuer=GOOGLE_ISSUER,
            # at_hash requires the access_token to verify; pass it when present
            access_token=access_token,
        )
    except JWTError as e:
        raise ValueError(f"Invalid Google ID token: {e}")

    return claims


def upsert_user(db: Session, google_sub: str, email: str, name: str | None) -> User:
    """Insert or update user record by google_sub."""
    user = db.query(User).filter(User.google_sub == google_sub).first()
    is_new = user is None
    if user is None:
        user = User(google_sub=google_sub, email=email, name=name)
        db.add(user)
    else:
        user.email = email
        if name:
            user.name = name
    db.commit()
    db.refresh(user)
    logger.info("User login", extra={"user_id": str(user.id), "is_new_user": is_new})
    return user


def blocklist_refresh_token(db: Session, token: str) -> None:
    h = _token_hash(token)
    already_blocked = (
        db.query(RefreshTokenBlocklist)
        .filter(RefreshTokenBlocklist.token_hash == h)
        .first()
    )
    if already_blocked:
        return
    db.add(RefreshTokenBlocklist(token_hash=h))
    db.commit()


def is_refresh_token_blocked(db: Session, token: str) -> bool:
    return (
        db.query(RefreshTokenBlocklist)
        .filter(RefreshTokenBlocklist.token_hash == _token_hash(token))
        .first()
        is not None
    )
