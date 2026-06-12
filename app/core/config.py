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

    # Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-sonnet-4-5"

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
