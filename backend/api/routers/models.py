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
from utils.security import validate_integer_id, sanitize_filename, validate_path_in_directory
from utils.validation import validate_file_size
from api.schemas import ModelResponse
from config import MODELS_DIR, MAX_MODEL_SIZE
from datetime import datetime, timezone

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
    # Validate model_id
    model_id = validate_integer_id(model_id)

    async with get_db() as db:
        model = await get_model(db, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return ModelResponse.model_validate(dict(model))


@router.post("", response_model=ModelResponse)
async def create_model_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    model_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
) -> ModelResponse:
    """Upload a new model file"""
    from utils.logger import logger
    
    logger.info(f"[MODEL_UPLOAD] Request received")
    logger.info(f"[MODEL_UPLOAD] File: filename={file.filename}, size={file.size}, content_type={file.content_type}")
    logger.info(f"[MODEL_UPLOAD] Form params: name={name}, model_type={model_type}, description={description}")
    
    # Validate filename
    if not file.filename:
        logger.error("[MODEL_UPLOAD] FAILED: No filename provided")
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Sanitize filename
    try:
        sanitized_filename = sanitize_filename(file.filename)
        logger.info(f"[MODEL_UPLOAD] Sanitized filename: '{file.filename}' -> '{sanitized_filename}'")
    except HTTPException as e:
        logger.error(f"[MODEL_UPLOAD] FAILED: Invalid filename '{file.filename}': {e.detail}")
        raise HTTPException(status_code=400, detail=f"Invalid filename: {e.detail}")
    
    # Validate file extension
    file_ext = Path(sanitized_filename).suffix.lower()
    logger.info(f"[MODEL_UPLOAD] File extension: '{file_ext}'")
    logger.info(f"[MODEL_UPLOAD] Allowed extensions: {MODEL_EXTENSIONS}")
    if file_ext not in MODEL_EXTENSIONS:
        logger.error(f"[MODEL_UPLOAD] FAILED: Invalid file extension '{file_ext}' for file '{sanitized_filename}'. Allowed: {MODEL_EXTENSIONS}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Supported: {', '.join(MODEL_EXTENSIONS)}"
        )
    
    # Validate file size
    logger.info(f"[MODEL_UPLOAD] Validating file size: {file.size} bytes (max: {MAX_MODEL_SIZE} bytes)")
    if file.size:
        try:
            validate_file_size(file.size, MAX_MODEL_SIZE)
            logger.info(f"[MODEL_UPLOAD] File size validation passed")
        except HTTPException as e:
            logger.error(f"[MODEL_UPLOAD] FAILED: File size validation failed: {e.detail}")
            raise
    
    # Read file content
    logger.info(f"[MODEL_UPLOAD] Reading file content...")
    content = await file.read()
    logger.info(f"[MODEL_UPLOAD] Read {len(content)} bytes from file")
    if not content:
        logger.error("[MODEL_UPLOAD] FAILED: File is empty")
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Validate content size (in case file.size wasn't available)
    logger.info(f"[MODEL_UPLOAD] Validating content size: {len(content)} bytes (max: {MAX_MODEL_SIZE} bytes)")
    try:
        validate_file_size(len(content), MAX_MODEL_SIZE)
        logger.info(f"[MODEL_UPLOAD] Content size validation passed")
    except HTTPException as e:
        logger.error(f"[MODEL_UPLOAD] FAILED: Content size validation failed: {e.detail}")
        raise
    
    # Determine model type from filename or parameter
    if not model_type:
        filename_lower = sanitized_filename.lower()
        logger.info(f"[MODEL_UPLOAD] Inferring model type from filename: '{filename_lower}'")
        if "yolo" in filename_lower:
            model_type = "YOLO"
        elif "rcnn" in filename_lower or "faster" in filename_lower:
            model_type = "Faster R-CNN"
        else:
            model_type = "YOLO"  # Default
        logger.info(f"[MODEL_UPLOAD] Inferred model type: '{model_type}'")
    else:
        logger.info(f"[MODEL_UPLOAD] Using provided model type: '{model_type}'")
    
    # Use provided name or derive from filename
    model_name = name or Path(sanitized_filename).stem
    logger.info(f"[MODEL_UPLOAD] Model name: '{model_name}'")
    
    # Prepare file path
    logger.info(f"[MODEL_UPLOAD] MODELS_DIR: {MODELS_DIR}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = MODELS_DIR / sanitized_filename
    logger.info(f"[MODEL_UPLOAD] Target file path: {file_path}")
    
    # Validate path is within MODELS_DIR (security check)
    try:
        validate_path_in_directory(file_path, MODELS_DIR)
        logger.info(f"[MODEL_UPLOAD] Path validation passed")
    except HTTPException as e:
        logger.error(f"[MODEL_UPLOAD] FAILED: Path validation failed: {e.detail}")
        raise HTTPException(status_code=403, detail="Invalid file path")
    
    # Check if file already exists
    if file_path.exists():
        logger.error(f"[MODEL_UPLOAD] FAILED: File already exists at {file_path}")
        raise HTTPException(
            status_code=400, 
            detail=f"Model file {sanitized_filename} already exists"
        )
    
    # Write uploaded file (async, race-safe)
    logger.info(f"[MODEL_UPLOAD] Writing file to disk...")
    try:
        async with aiofiles.open(file_path, "xb") as f:  # 'x' = fail if exists
            await f.write(content)
        logger.info(f"[MODEL_UPLOAD] File written successfully to {file_path}")
    except FileExistsError:
        logger.error(f"[MODEL_UPLOAD] FAILED: FileExistsError (race condition)")
        raise HTTPException(
            status_code=400, 
            detail=f"Model file {sanitized_filename} already exists"
        )
    except Exception as e:
        logger.error(f"[MODEL_UPLOAD] FAILED: Exception writing file: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save model file: {str(e)}"
        )
    
    # Add to database
    logger.info(f"[MODEL_UPLOAD] Adding model to database...")
    async with get_db() as db:
        # Check if model with same path already exists in DB
        logger.info(f"[MODEL_UPLOAD] Checking for existing model with path: {file_path}")
        cursor = await db.execute(
            "SELECT model_id, name FROM model WHERE weights_path = ?",
            (str(file_path),)
        )
        existing = await cursor.fetchone()
        
        if existing:
            logger.error(f"[MODEL_UPLOAD] FAILED: Model already exists in DB with ID: {existing[0]}, name: {existing[1]}")
            # Model already in database, return error instead of silently returning it
            raise HTTPException(
                status_code=400,
                detail=f"Model '{existing[1]}' already exists. Please upload a different model file or use a different filename."
            )
        
        # Insert new model
        now = datetime.now(timezone.utc).isoformat()
        logger.info(f"[MODEL_UPLOAD] Inserting new model: name={model_name}, type={model_type}, path={file_path}")
        cursor = await db.execute(
            """INSERT INTO model (name, type, weights_path, description, optimal_batch_size, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                model_name,
                model_type,
                str(file_path),
                description or f"Uploaded {model_type} model",
                8,  # Default batch size (will be detected on first load)
                now,
                now
            )
        )
        model_id = cursor.lastrowid
        await db.commit()
        logger.info(f"[MODEL_UPLOAD] Model inserted with ID: {model_id}")
        
        # Fetch and return the created model
        model = await get_model(db, model_id)
        logger.info(f"[MODEL_UPLOAD] SUCCESS: Model uploaded and saved. Model ID: {model_id}")
        return ModelResponse.model_validate(dict(model))
