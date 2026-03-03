"""
Model management API endpoints.

This router handles retrieving information about available ML models.
Models can be R-CNN or YOLO architectures, each with their own weights file.
"""

from typing import List, Optional
from pathlib import Path
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from utils.model_utils import get_all_models, get_model
from utils.security import sanitize_filename
from api.schemas import ModelResponse
from config import MODELS_DIR

router = APIRouter(prefix="/api/models", tags=["models"])

# Model file extensions
MODEL_EXTENSIONS = ['.pt', '.pth', '.ckpt']


@router.get("", response_model=List[ModelResponse])
async def get_all_models_endpoint() -> List[ModelResponse]:
    """Get all available models"""
    models = await get_all_models()
    return [ModelResponse.model_validate(model) for model in models]


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model_endpoint(model_id: int) -> ModelResponse:
    """Get model information"""
    model = await get_model(model_id=model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.post("", response_model=ModelResponse)
async def create_model_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    model_type: str = Form(...)
) -> ModelResponse:
    """Upload a new model file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        sanitized_filename = sanitize_filename(file.filename)
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=f"Invalid filename: {e.detail}")

    file_ext = Path(sanitized_filename).suffix.lower()
    if file_ext not in MODEL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported: {', '.join(MODEL_EXTENSIONS)}"
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    if model_type not in {"YOLO", "FASTRCNN"}:
        raise HTTPException(status_code=400, detail="model_type must be YOLO or FASTRCNN")

    model_name = name or Path(sanitized_filename).stem
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = MODELS_DIR / sanitized_filename

    try:
        async with aiofiles.open(file_path, "xb") as f:
            await f.write(content)
    except FileExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"Model file {sanitized_filename} already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save model file: {str(e)}"
        )

    # Model metadata is file-derived; return the discovered row.
    discovered = await get_all_models()
    model = next((m for m in discovered if m["weights_path"] == str(file_path)), None)
    if not model:
        raise HTTPException(status_code=500, detail="Model file saved but could not be discovered")

    # Respect optional model name override by persisting via filename-less alias in response only.
    # Current simplified model registry derives name from file stem.
    if name and name.strip():
        model = {**model, "name": model_name}

    return ModelResponse.model_validate(model)
