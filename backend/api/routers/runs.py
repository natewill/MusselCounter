"""
Run-related API endpoints.

This router handles inference run management:
- Creating new runs (inference jobs)
- Retrieving run status and results
- Starting background processing of collections through ML models

A run processes all images in a collection through a selected model with a given
threshold, producing mussel counts and polygon annotations for each image.
Runs execute asynchronously in the background so the API can return immediately.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from db import get_db
from utils.collection_utils import get_collection
from utils.model_utils import get_model
from utils.run_utils import get_or_create_run, process_collection_run, get_run, update_run_status
from utils.validation import validate_threshold
from api.schemas import StartRunRequest, RunResponse
from utils.security import validate_integer_id

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run_endpoint(run_id: int) -> RunResponse:
    """
    Get run information including status, progress, and results.

    Returns run metadata such as:
    - Status (pending, running, completed, failed)
    - Progress (processed_count, total_images)
    - Results (live_mussel_count, dead_mussel_count)
    - Timestamps (started_at, finished_at)
    """
    run_id = validate_integer_id(run_id)

    async with get_db() as db:
        run = await get_run(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunResponse.model_validate(dict(run))


@router.post("/collections/{collection_id}/run", response_model=RunResponse)
async def start_run_endpoint(
    collection_id: int, run_request: StartRunRequest, background_tasks: BackgroundTasks
) -> RunResponse:
    """
    Start an inference run on a collection.

    This endpoint:
    1. Validates collection and model exist
    2. Validates threshold value
    3. Creates a run record in the database
    4. Starts background processing (returns immediately, doesn't wait for completion)

    The actual inference processing happens asynchronously in the background.
    The frontend can poll the run status to see progress and results as they come in.

    Returns the run ID and initial status ("pending") immediately.
    """
    # Validate IDs to prevent injection attacks
    collection_id = validate_integer_id(collection_id)
    run_request.model_id = validate_integer_id(run_request.model_id)

    async with get_db() as db:
        # Verify collection exists
        collection = await get_collection(db, collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Verify model exists
        model = await get_model(db, run_request.model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # Validate threshold (must be between 0.0 and 1.0)
        threshold = validate_threshold(run_request.threshold)

        # Get or create run record in database (reuses run if same collection+model+threshold)
        run_id, _ = await get_or_create_run(db, collection_id, run_request.model_id, threshold)

        # Fetch the run record to get all fields for the response
        run_record = await get_run(db, run_id)
        if not run_record:
            raise HTTPException(status_code=500, detail="Failed to create run")

        # Start background task to process the run
        # This runs asynchronously so the API can return immediately
        # The task will load the model, process all images, and update results incrementally
        async def run_inference_task():
            # Create new database connection for background task
            # (each async task needs its own connection)
            async with get_db() as db_task:
                await process_collection_run(db_task, run_id)

        # Add task to FastAPI's background task queue
        # FastAPI will execute this after sending the response
        background_tasks.add_task(run_inference_task)

        # Return the run response with all fields from database
        return RunResponse.model_validate(dict(run_record))


@router.post("/runs/{run_id}/stop", response_model=RunResponse)
async def stop_run_endpoint(run_id: int) -> RunResponse:
    """
    Stop/cancel a running inference run.
    
    This endpoint marks a run as 'cancelled'. The actual processing may continue
    for a short time until it checks the status, but no further results will be saved.
    
    Only runs with status 'pending' or 'running' can be stopped.
    Completed or failed runs cannot be stopped.
    
    Returns the updated run information with status 'cancelled'.
    """
    run_id = validate_integer_id(run_id)
    
    async with get_db() as db:
        # Get the run to check its current status
        run = await get_run(db, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Check if the run can be stopped
        if run['status'] not in ('pending', 'running'):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot stop run with status '{run['status']}'. Only pending or running runs can be stopped."
            )
        
        # Update the run status to 'cancelled'
        await update_run_status(db, run_id, 'cancelled', 'Run cancelled by user')
        
        # Fetch updated run record
        updated_run = await get_run(db, run_id)
        if not updated_run:
            raise HTTPException(status_code=500, detail="Failed to update run")
        
        return RunResponse.model_validate(dict(updated_run))
