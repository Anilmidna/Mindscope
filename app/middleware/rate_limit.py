"""
Rate limiting middleware (TDD §8.5 Layer 4).

Limits:
  - 60 requests/minute per IP (all endpoints)
  - 3 report generations per user per day
  - 10 session starts per user per day
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_token


def get_user_id(request: Request) -> str:
    """Extract user_id from Bearer JWT for per-user rate limiting.
    Falls back to IP if token is absent or invalid."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = decode_token(auth[7:])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return get_remote_address(request)


# Keyed by IP for global limit; override key_func per-route for user-scoped limits
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
