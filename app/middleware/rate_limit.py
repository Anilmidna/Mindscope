"""
Rate limiting middleware (TDD §8.5 Layer 4).

Limits:
  - 60 requests/minute per IP (all endpoints)
  - 3 report generations per user per day
  - 10 session starts per user per day
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by IP for global limit; override key_func per-route for user-scoped limits
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
