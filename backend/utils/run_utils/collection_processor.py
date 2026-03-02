"""
Collection processing orchestrator for inference runs.
"""
import asyncio
import os
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
    Helper function to log errors and update run status to failed.
    
    Args:
        db: Database connection
        run_id: Run ID
        message: Error message
        status: Status to set (default: 'failed')
    """
    try:
        await update_run_status(db, run_id, status, message)
    except Exception:
        pass


async def _setup_run_and_load_model(db: aiosqlite.Connection, run_id: int):
    """
    Setup run and load model.
    
    Returns:
        Tuple of (model_device, collection_id, threshold, model_type)
        or None if setup fails
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
    
    # Load model in background thread to avoid blocking the event loop
    try:
        to_thread = getattr(asyncio, "to_thread", None)
        if to_thread:
            model_device = await to_thread(load_model, weights_path, model_type)
        else:
            loop = asyncio.get_event_loop()
            model_device = await loop.run_in_executor(None, load_model, weights_path, model_type)
    except Exception as e:
        await _fail(db, run_id, f"Failed to load model: {e}")
        return None
    
    return (model_device, collection_id, threshold, model_type)


async def _prepare_images(db: aiosqlite.Connection, collection_id: int, run_id: int):
    """
    Get images from collection and check which are already processed.
    
    Returns:
        Tuple of (images_to_process, total_images, images_already_done)
        or None if no images found
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
    Handle case where all images are already processed - recalculate totals and mark completed.
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
           SET status = 'completed', 
               finished_at = ?, 
               total_images = ?,
               processed_count = ?,
               live_mussel_count = ?
           WHERE run_id = ?""",
        (now, total_images, total_images, total_live_count, run_id)
    )
    await db.commit()


async def _process_single_images(
    db_path: str,
    run_id: int,
    images: list,
    model_device,
    threshold: float,
    model_type: str,
    images_already_done: int = 0,
):
    """
    Process images one at a time.

    Returns:
        List of (image_id, success, live_count, dead_count) tuples
    """
    max_concurrent = int(os.getenv("MAX_CONCURRENT_IMAGES", "4"))
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(idx, image):
        async with semaphore:
            image_id = image['image_id']
            image_filename = image.get('filename', 'unknown')
            image_path = image.get('stored_path', 'unknown')
            
            return await process_image_for_run(
                db_path, run_id, image_id, image_path, image_filename,
                model_device, threshold, model_type, idx, len(images)
            )
    
    tasks = [
        process_with_semaphore(idx + 1, image)
        for idx, image in enumerate(images)
    ]
    
    results = []
    processed_count = 0
    
    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            results.append(result)
            
            processed_count += 1
            async with aiosqlite.connect(db_path) as db_progress:
                await db_progress.execute(
                    "UPDATE run SET processed_count = ? WHERE run_id = ?",
                    (processed_count + images_already_done, run_id)
                )
                await db_progress.commit()
        except Exception:
            raise
    
    return results


async def _finalize_run(
    db: aiosqlite.Connection,
    run_id: int,
    results: list,
    images_processed_in_this_run: int,
    images_already_done: int = 0
):
    """
    Aggregate results and update run status to completed.
    
    Args:
        db: Database connection
        run_id: Run ID
        results: List of (image_id, success, live_count, dead_count) tuples from this run
        images_processed_in_this_run: Number of images that were processed in this run
        images_already_done: Number of images that were already processed before this run
    """
    successes = [result for result in results if result[1]]
    successful_images = len(successes)
    
    # Get total counts from ALL results in this run
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
           SET total_images = ?,
               live_mussel_count = ?,
               status = ?,
               finished_at = ?
           WHERE run_id = ?""",
        (total_expected, total_live_count, final_status, now, run_id)
    )

    await db.commit()


async def process_collection_run(db: aiosqlite.Connection, run_id: int):
    """
    Process a collection run: load model, get images, run inference, and save results.
    
    This is the main function that orchestrates a complete inference run:
    1. Loads the model and validates it exists
    2. Gets all images in the collection (excluding duplicates)
    3. Checks for cached results from previous runs with same model+threshold
    4. Processes images one at a time
    5. Writes results incrementally to the database for real-time updates
    6. Aggregates final counts and updates run status
    
    Args:
        db: Database connection
        run_id: Run ID to process
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
        
        db_path = DB_PATH
        results = await _process_single_images(
            db_path,
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
        
        # Get collection_id from run (in case exception happened before setup)
        run = await get_run(db, run_id)
        if not run:
            return
        collection_id = run['collection_id']
        
        # Check if all images are already processed (using same logic as main path)
        image_prep = await _prepare_images(db, collection_id, run_id)
        if image_prep:
            images_to_process, total_images, _ = image_prep
            if not images_to_process:
                # All images already processed - mark as completed despite error
                await _handle_all_images_processed(db, run_id, total_images)
                return
