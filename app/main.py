from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, sessions, reports, admin, b2b

app = FastAPI(
    title="MindScope API",
    version="0.1.0",
    description="AI Psychometric Assessment Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(b2b.router, prefix="/b2b", tags=["b2b"])


@app.get("/ping")
def ping():
    return {"status": "ok"}
