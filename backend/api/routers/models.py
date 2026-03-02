"""
Model management API endpoints.

This router handles retrieving information about available ML models.
Models can be R-CNN or YOLO architectures, each with their own weights file.
"""

from typing import List, Optional
from pathlib import Path
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from db import get_db
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
    async with get_db() as db:
        models = await get_all_models(db)
        return [ModelResponse.model_validate(dict(model)) for model in models]


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model_endpoint(model_id: int) -> ModelResponse:
    """Get model information"""
    async with get_db() as db:
        model = await get_model(db, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return ModelResponse.model_validate(dict(model))


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

    if file_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Model file {sanitized_filename} already exists"
        )

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

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT model_id, name FROM model WHERE weights_path = ?",
            (str(file_path),)
        )
        existing = await cursor.fetchone()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{existing[1]}' already exists. Please upload a different model file or use a different filename."
            )

        cursor = await db.execute(
            """INSERT INTO model (name, type, weights_path)
               VALUES (?, ?, ?)""",
            (
                model_name,
                model_type,
                str(file_path)
            )
        )
        model_id = cursor.lastrowid
        await db.commit()

        model = await get_model(db, model_id)
        return ModelResponse.model_validate(dict(model))
