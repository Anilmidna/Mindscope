from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.rate_limit import limiter
from app.routers import auth, sessions, reports, admin, b2b, payments

setup_logging()

app = FastAPI(
    title="MindScope API",
    version="0.1.0",
    description="AI Psychometric Assessment Platform",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(b2b.router, prefix="/b2b", tags=["b2b"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])


@app.get("/ping")
def ping():
    return {"status": "ok"}
