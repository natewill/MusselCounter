"""
Collection-run orchestration for model inference.

This module coordinates the full lifecycle of a run:
1) Validate run/model metadata and load model weights.
2) Determine which images still need processing for this run.
3) Process remaining images sequentially and persist per-image progress.
4) Aggregate final totals and mark run status.

Important behavior:
- Runs are resumable/reusable: if a run already has image_result rows,
  only missing images are processed.
- Image processing is intentionally sequential to reduce CPU spikes and
  simplify runtime behavior.
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from config import DB_PATH
from utils.collection_utils import get_collection_images
from utils.model_utils.db import get_model
from utils.model_utils.loader import load_model
from .db import get_run, update_run_status
from .image_processor import process_image_for_run


async def _fail(db: aiosqlite.Connection, run_id: int, message: str, status: str = 'failed') -> None:
    """
    Best-effort run failure/update helper.

    We never want error-reporting itself to crash the task, so this function
    intentionally suppresses secondary exceptions from status updates.
    """
    try:
        await update_run_status(db, run_id, status, message)
    except Exception:
        pass


async def _setup_run_and_load_model(db: aiosqlite.Connection, run_id: int):
    """
    Prepare run metadata and load the configured model.

    Steps:
    - Fetch run row and mark status as running.
    - Resolve model metadata (weights path + model type).
    - Validate weights file exists.
    - Load model in a worker thread so the event loop stays responsive.

    Returns:
        (model_device, collection_id, threshold, model_type) on success.
        None when setup fails (and run is marked failed).
    """
    run = await get_run(db, run_id)
    if not run:
        await _fail(db, run_id, "Run not found in database")
        return None
    
    collection_id = run['collection_id']
    model_id = run['model_id']
    threshold = run['threshold']
    await update_run_status(db, run_id, 'running')
    
    model_row = await get_model(db, model_id)
    if not model_row:
        await _fail(db, run_id, f"Model {model_id} not found in database")
        return None
    
    weights_path = model_row['weights_path']
    model_type = model_row['type']
    
    if not Path(weights_path).exists():
        await _fail(db, run_id, f"Model weights file not found: {weights_path}")
        return None
    
    # PyTorch model loading is blocking/CPU-heavy; push it off the event loop.
    try:
        model_device = await asyncio.to_thread(load_model, weights_path, model_type)
    except Exception as e:
        await _fail(db, run_id, f"Failed to load model: {e}")
        return None
    
    return (model_device, collection_id, threshold, model_type)


async def _prepare_images(db: aiosqlite.Connection, collection_id: int, run_id: int):
    """
    Build the image worklist for a run.

    Returns:
        (images_to_process, total_images, images_already_done)
        or None when the collection has no images.

    Notes:
    - We check image_result for this run_id to support run reuse.
    - Only images without a result row are sent through inference again.
    """
    # Get all images in the collection
    all_images = await get_collection_images(db, collection_id)
    
    if not all_images:
        return None
    
    total_images = len(all_images)
    
    # Get images that haven't been processed in this run yet
    cursor = await db.execute(
        """SELECT image_id FROM image_result WHERE run_id = ?""",
        (run_id,)
    )
    already_processed = {row[0] for row in await cursor.fetchall()}
    images_already_done = len(already_processed)
    
    # Only process images without results in this run
    images_to_process = [
        img for img in all_images 
        if img['image_id'] not in already_processed
    ]
    
    return (images_to_process, total_images, images_already_done)


async def _handle_all_images_processed(db: aiosqlite.Connection, run_id: int, total_images: int):
    """
    Finalize a run when there is nothing left to process.

    This path is hit when every image in the collection already has an
    image_result row for this run_id.
    """
    cursor = await db.execute(
        """SELECT SUM(live_mussel_count) FROM image_result WHERE run_id = ?""",
        (run_id,)
    )
    row = await cursor.fetchone()
    total_live_count = row[0] or 0

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE run
           SET status = ?,
               finished_at = ?,
               total_images = ?,
               processed_count = ?,
               live_mussel_count = ?
           WHERE run_id = ?""",
        ('completed', now, total_images, total_images, total_live_count, run_id)
    )
    await db.commit()


async def _process_single_images(
    run_id: int,
    images: list,
    model_device,
    threshold: float,
    model_type: str,
    images_already_done: int = 0,
):
    """
    Process (run inference on) images sequentially (one image at a time).

    Returns:
        List of (image_id, success, live_count, dead_count) tuples
    """
    results = []
    processed_count = 0

    for image in images:
        # Pull safe defaults so per-image failures are captured cleanly.
        image_id = image['image_id']
        image_path = image.get('stored_path', 'unknown')

        # process_image_for_run handles:
        # - file existence checks
        # - model inference
        # - detection writes
        # - thresholded counts
        # - image_result writes
        result = await process_image_for_run(
            run_id,
            image_id,
            image_path,
            model_device,
            threshold,
            model_type,
        )
        results.append(result)

        processed_count += 1
        # Persist incremental progress after each image so polling clients
        # get accurate progress updates during long runs.
        async with aiosqlite.connect(DB_PATH) as db_progress:
            await db_progress.execute(
                "UPDATE run SET processed_count = ? WHERE run_id = ?",
                (processed_count + images_already_done, run_id)
            )
            await db_progress.commit()
    
    return results


async def _finalize_run(
    db: aiosqlite.Connection,
    run_id: int,
    results: list,
    images_processed_in_this_run: int,
    images_already_done: int = 0
):
    """
    Aggregate final run totals and set terminal status.

    Status rules:
    - completed: every image processed in this invocation succeeded.
    - completed_with_errors: at least one image failed in this invocation.

    total_images is stored as:
        images_already_done + images_processed_in_this_run
    so resumed runs still report full collection progress.
    """
    successes = [result for result in results if result[1]]
    successful_images = len(successes)
    
    cursor = await db.execute(
        """SELECT SUM(live_mussel_count) FROM image_result WHERE run_id = ?""",
        (run_id,)
    )
    row = await cursor.fetchone()
    total_live_count = row[0] or 0
    
    # Update run with final results
    now = datetime.now(timezone.utc).isoformat()
    # Compare successful images to images processed in THIS run, not total collection
    # This fixes the issue where deleting and re-uploading images causes false "completed_with_errors"
    total_expected = images_processed_in_this_run + images_already_done
    final_status = 'completed' if successful_images == images_processed_in_this_run else 'completed_with_errors'
    
    await db.execute(
        """UPDATE run
           SET status = ?,
               finished_at = ?,
               total_images = ?,
               processed_count = ?,
               live_mussel_count = ?
           WHERE run_id = ?""",
        (final_status, now, total_expected, total_expected, total_live_count, run_id)
    )
    await db.commit()


async def process_collection_run(db: aiosqlite.Connection, run_id: int):
    """
    Main run entrypoint used by the background task.

    High-level flow:
    1) Setup run + load model.
    2) Build image worklist (skip already-processed images for this run).
    3) Initialize run counters.
    4) Process remaining images sequentially.
    5) Finalize totals/status.

    Error behavior:
    - Any unhandled exception marks the run failed.
    - If failure occurs but all images are already processed, we recover the
      run into completed to avoid false failures on resumed/cached runs.
    """
    try:
        # Setup: Load run and model
        setup_result = await _setup_run_and_load_model(db, run_id)
        if not setup_result:
            return
        
        model_device, collection_id, threshold, model_type = setup_result
        
        # Prepare images: Get images, filter duplicates, check already processed
        image_prep = await _prepare_images(db, collection_id, run_id)
        if not image_prep:
            await _fail(db, run_id, "No images found in collection")
            return
        
        images_to_process, total_images, images_already_done = image_prep
        
        if not images_to_process:
            # All images already processed
            await _handle_all_images_processed(db, run_id, total_images)
            return
        
        # Initialize run with total count and already-processed count
        await db.execute(
            "UPDATE run SET total_images = ?, processed_count = ? WHERE run_id = ?",
            (total_images, images_already_done, run_id)
        )
        await db.commit()
        
        results = await _process_single_images(
            run_id,
            images_to_process,
            model_device,
            threshold,
            model_type,
            images_already_done,
        )
        
        # Finalize: Aggregate results and update status
        await _finalize_run(db, run_id, results, len(images_to_process), images_already_done)
        
    except Exception as e:
        await _fail(db, run_id, f"Run processing error: {e}")
        run = await get_run(db, run_id)
        if not run:
            return

        collection_id = run['collection_id']
        image_prep = await _prepare_images(db, collection_id, run_id)
        if not image_prep:
            return

        images_to_process, total_images, _ = image_prep
        if images_to_process:
            return

        await _handle_all_images_processed(db, run_id, total_images)
