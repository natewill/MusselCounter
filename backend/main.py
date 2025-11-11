from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
import os
from pathlib import Path
from db import init_db, get_db
from utils.batch_utils import create_batch, get_batch, get_all_batches, get_batch_images, get_latest_run, get_all_runs
from utils.image_utils import add_multiple_images
from utils.model_utils import get_all_models, get_model
from utils.run_utils import create_run, process_batch_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: (nothing needed for now)


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Backend running!"}


# Request/Response Models
class CreateBatchRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class StartRunRequest(BaseModel):
    model_id: int
    threshold: Optional[float] = 0.5  # Default threshold, can be adjusted after seeing results


# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Batch Endpoints
@app.post("/api/batches")
async def create_batch_endpoint(request: CreateBatchRequest):
    """Create a new batch"""
    async with get_db() as db:
        batch_id = await create_batch(
            db,
            name=request.name,
            description=request.description
        )
        return {"batch_id": batch_id}


@app.get("/api/batches")
async def get_all_batches_endpoint():
    """Get all batches"""
    async with get_db() as db:
        batches = await get_all_batches(db)
        return [dict(batch) for batch in batches]


@app.get("/api/batches/{batch_id}")
async def get_batch_endpoint(batch_id: int):
    """Get batch details"""
    async with get_db() as db:
        batch = await get_batch(db, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Get images in this batch
        images = await get_batch_images(db, batch_id)
        
        # Get latest run (automatically the newest one)
        latest_run = await get_latest_run(db, batch_id)
        
        return {
            "batch": dict(batch),
            "images": [dict(img) for img in images],
            "latest_run": dict(latest_run) if latest_run else None
        }


@app.post("/api/batches/{batch_id}/upload-images")
async def upload_images_endpoint(batch_id: int, files: List[UploadFile] = File(...)):
    """Upload images to a batch"""
    async with get_db() as db:
        # Verify batch exists
        batch = await get_batch(db, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Save uploaded files and collect paths
        saved_paths = []
        for file in files:
            # Validate file type (basic check - you might want to add more validation)
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                continue
            
            # Save file to upload directory
            file_path = UPLOAD_DIR / file.filename
            # Handle duplicate filenames
            counter = 1
            while file_path.exists():
                stem = Path(file.filename).stem
                suffix = Path(file.filename).suffix
                file_path = UPLOAD_DIR / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Write file
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            saved_paths.append(str(file_path))
        
        if not saved_paths:
            raise HTTPException(status_code=400, detail="No valid image files uploaded")
        
        # Add images to batch using existing utility
        image_ids = await add_multiple_images(db, batch_id, saved_paths)
        
        return {
            "batch_id": batch_id,
            "image_ids": image_ids,
            "count": len(image_ids)
        }


# Model Endpoints
@app.get("/api/models")
async def get_all_models_endpoint():
    """Get all available models"""
    async with get_db() as db:
        models = await get_all_models(db)
        return [dict(model) for model in models]


@app.get("/api/models/{model_id}")
async def get_model_endpoint(model_id: int):
    """Get model information"""
    async with get_db() as db:
        model = await get_model(db, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return dict(model)


# Run Endpoints
@app.post("/api/batches/{batch_id}/run")
async def start_run_endpoint(
    batch_id: int, 
    request: StartRunRequest,
    background_tasks: BackgroundTasks
):
    """Start an inference run on a batch"""
    async with get_db() as db:
        # Verify batch exists
        batch = await get_batch(db, batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Verify model exists
        model = await get_model(db, request.model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Use default threshold of 0.5 if not provided
        threshold = request.threshold if request.threshold is not None else 0.5
        
        # Create run record
        run_id = await create_run(db, batch_id, request.model_id, threshold)
        
        # Start background task to process the run
        # Note: BackgroundTasks will handle the async function
        async def run_inference_task():
            async with get_db() as db_task:
                await process_batch_run(db_task, run_id)
        
        background_tasks.add_task(run_inference_task)
        
        return {
            "run_id": run_id,
            "batch_id": batch_id,
            "model_id": request.model_id,
            "threshold": threshold,
            "status": "pending"
        }