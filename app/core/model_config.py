# DEPRECATED — replaced by app.core.llm
# This file kept only to avoid import errors during migration.
# All model configuration now lives in app/core/llm.py
# Use: from app.core.llm import llm_service

from app.core.llm import llm_service, BEDROCK_MODELS  # noqa: F401
