"""
Model management API endpoints.

This router handles retrieving information about available ML models.
Models can be R-CNN or YOLO architectures, each with their own weights file.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from db import get_db
from utils.model_utils import get_all_models, get_model
from utils.security import validate_integer_id
from api.schemas import ModelResponse

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=List[ModelResponse])
async def get_all_models_endpoint() -> List[ModelResponse]:
    """Get all available models"""
    async with get_db() as db:
        models = await get_all_models(db)
        return [ModelResponse.model_validate(dict(model)) for model in models]


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model_endpoint(model_id: int) -> ModelResponse:
    """Get model information"""
    # Validate model_id
    model_id = validate_integer_id(model_id)

    async with get_db() as db:
        model = await get_model(db, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return ModelResponse.model_validate(dict(model))
