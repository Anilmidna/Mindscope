from pydantic import BaseModel
from typing import Optional


class GoogleCallbackRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Kept for backwards-compatibility in tests; production uses HttpOnly cookie
    refresh_token: Optional[str] = None


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    # Kept for backwards-compatibility in tests; production uses HttpOnly cookie
    refresh_token: Optional[str] = None
