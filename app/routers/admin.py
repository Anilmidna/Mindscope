"""
Admin endpoints for runtime model management.
Protected — only accessible with admin credentials.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.deps import require_admin
from app.core.llm import llm_service, BEDROCK_MODELS

router = APIRouter()


class ModelUpdateRequest(BaseModel):
    """Request to change the default model for a pipeline stage."""
    stage: str
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@router.get("/models")
def get_current_models(_: None = Depends(require_admin)):
    """
    Show current model assignments for all pipeline stages.
    Use this to see what's running before making changes.
    """
    return {
        "current_defaults": llm_service.get_defaults(),
        "available_models": {
            name: model_id for name, model_id in BEDROCK_MODELS.items()
        },
        "available_stages": list(llm_service.get_defaults().keys()),
    }


@router.put("/models")
def update_model(req: ModelUpdateRequest, _: None = Depends(require_admin)):
    """
    Change the default model for a pipeline stage at runtime.
    Takes effect immediately — no restart needed.

    Example body:
        {"stage": "report_generation", "model": "sonnet"}
        {"stage": "report_generation", "model": "haiku", "temperature": 0.2}
        {"stage": "question_generation", "model": "opus"}
    """
    try:
        llm_service.set_default(
            stage=req.stage,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "updated",
        "stage": req.stage,
        "new_config": llm_service.get_defaults()[req.stage],
    }


@router.post("/models/test")
def test_model(model: str = "sonnet", _: None = Depends(require_admin)):
    """
    Quick test call to verify a model works on Bedrock.
    Sends a trivial prompt and returns the response.
    """
    if model not in BEDROCK_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Available: {list(BEDROCK_MODELS.keys())}",
        )

    try:
        chat = llm_service.get_chat_model(model, temperature=0.1, max_tokens=100)
        from langchain_core.messages import HumanMessage
        response = chat.invoke([HumanMessage(content="Reply with: MindScope model test OK")])
        return {
            "model": model,
            "model_id": BEDROCK_MODELS[model],
            "status": "ok",
            "response": response.content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model test failed: {str(e)}")
