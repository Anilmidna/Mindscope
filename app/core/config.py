from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS
    AWS_REGION: str = "us-east-1"

    # S3
    S3_BUCKET_NAME: str = "mindscope-reports"

    # SES
    SES_FROM_EMAIL: str = "reports@mindscope.ai"

    # Bedrock — must use cross-region inference profile, not direct model ID
    BEDROCK_MODEL_ID: str = "us.anthropic.claude-sonnet-4-6"
    BEDROCK_OPUS_MODEL_ID: str = "us.anthropic.claude-opus-4-7"

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # Bedrock Guardrails (Layer 1 — set after running scripts/create_bedrock_guardrail.py)
    BEDROCK_GUARDRAIL_ID: str = ""
    BEDROCK_GUARDRAIL_VERSION: str = "DRAFT"

    # PDF Lambda (B5 — empty means use WeasyPrint fallback)
    PDF_LAMBDA_FUNCTION_NAME: str = ""

    # App
    APP_ENV: str = "development"
    # Comma-separated list: "https://app.vercel.app,http://localhost:5173"
    # Stored as str so pydantic-settings doesn't try to JSON-decode it.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
