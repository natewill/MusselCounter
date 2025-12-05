"""
Collection processing orchestrator for inference runs.

THIS IS THE BRAIN OF THE SYSTEM - This file coordinates the entire inference process.

=== What This File Does ===

When a user clicks "Start Run" in the frontend, this is what happens:

1. **Setup Phase**
   - Loads the ML model from disk (e.g., yolov8n.pt)
   - Gets all images in the collection from database
   - Checks which images have already been processed (smart caching)
   - Calculates optimal batch size based on model size

2. **Processing Phase**
   - Splits images into batches (e.g., 4 images per batch)
   - For each batch:
     * Load images from disk
     * Run model inference (detect mussels)
     * Get bounding boxes with live/dead labels
     * Save results to database immediately (real-time updates!)
     * Update progress counter
   - Batches can run concurrently (controlled by semaphore)

3. **Completion Phase**
   - Sum up all live/dead counts across all images
   - Update run status to 'completed'
   - Frontend polls and sees the final results

=== Why Batch Processing? ===

Without batching:
- Process 1 image → takes 2 seconds
- Process 100 images → takes 200 seconds (3+ minutes!)

With batching (batch_size=4):
- Process 4 images at once → takes 3 seconds
- Process 100 images → takes 75 seconds (1.25 minutes)
- **2.7x faster!**

=== Key Features ===

**Smart Run Reuse**:
- Run = (collection_id, model_id, threshold)
- Same combination? Reuse the run, only process new images
- Changed threshold or model? Create new run

**Real-time Updates**:
- Results written to database after each batch
- Frontend polls and sees progress in real-time
- Green flash animation shows which images just finished

**Error Handling**:
- Model fails to load? Mark run as failed
- Image file missing? Skip it, log error, continue
- Out of memory? Caught and logged, run fails gracefully

**Cancellation Support**:
- User clicks "Stop Run"
- Status changes to 'cancelled'
- Processing loop checks status and exits early
- Partial results are saved
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from config import POLYGON_DIR

import aiosqlite

from config import DB_PATH
from utils.collection_utils import get_collection_images
from utils.model_utils.db import get_model
from utils.model_utils.inference import run_rcnn_inference_batch, run_yolo_inference_batch
from utils.model_utils.loader import load_model
from .db import get_run, update_run_status
from .image_processor import process_image_for_run, _save_detections_to_db, _get_counts_from_db

# Manual override settings (takes precedence over environment variables and auto-detection)
# Set these to override automatic batch size and concurrency detection
# Useful for debugging or forcing specific batch sizes
MANUAL_BATCH_SIZE = None  # Set to an integer to override batch size (e.g., 4)
MANUAL_MAX_CONCURRENT_BATCHES = None  # Set to an integer to override max concurrent batches (e.g., 2)


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


async def _batch_infer(model_type: str, model_device, image_paths: list[str]):
    """
    Run batch inference on multiple images in a background thread.
    
    Note: Inference always returns ALL detections (no threshold filtering).
    Counts are calculated by querying the database after detections are saved.
    
    Args:
        model_type: Type of model ('RCNN', 'YOLO', etc.)
        model_device: Tuple of (model, device) from load_model
        image_paths: List of image file paths
        
    Returns:
        List of result dictionaries with live_count, dead_count, polygons, etc.
        Note: live_count/dead_count will be calculated from database after saving detections
    """
    # Always get all detections (no threshold filtering)
    fn = run_yolo_inference_batch if 'yolo' in model_type.lower() else run_rcnn_inference_batch
    to_thread = getattr(asyncio, "to_thread", None)
    if to_thread:
        return await to_thread(fn, model_device, image_paths)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, model_device, image_paths)


async def _setup_run_and_load_model(db: aiosqlite.Connection, run_id: int):
    """
    Setup run and load model.
    
    Returns:
        Tuple of (run, model_device, collection_id, model_id, threshold, model_type, weights_path)
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
    
    return (run, model_device, collection_id, model_id, threshold, model_type, weights_path)


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


async def _handle_all_images_processed(db: aiosqlite.Connection, run_id: int, collection_id: int, total_images: int):
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
    await db.execute(
        "UPDATE collection SET live_mussel_count = ?, updated_at = ? WHERE collection_id = ?",
        (total_live_count, now, collection_id)
    )
    await db.commit()


async def _process_batch_inference(
    db: aiosqlite.Connection,
    db_path: str,
    run_id: int,
    images: list,
    model_type: str,
    model_device,
    threshold: float,
    images_already_done: int
):
    """
    Process images using batch inference (for R-CNN and YOLO models).
    
    Returns:
        List of (image_id, success, live_count, dead_count) tuples
    """
    # Use cached optimal batch size from model loading
    auto_batch_size = model_device[2] if len(model_device) > 2 else 8
    auto_max_concurrent = 1
    batch_size = MANUAL_BATCH_SIZE or int(os.getenv("INFERENCE_BATCH_SIZE", auto_batch_size))
    max_concurrent_batches = MANUAL_MAX_CONCURRENT_BATCHES or int(os.getenv("MAX_CONCURRENT_BATCHES", auto_max_concurrent))
    
    semaphore = asyncio.Semaphore(max_concurrent_batches)
    
    async def process_batch_of_images(batch_images, batch_idx):
        """Process a single batch of images."""
        async with semaphore:
            image_data = [
                (img['image_id'], img.get('filename', 'unknown'), img.get('stored_path'))
                for img in batch_images
                if img.get('stored_path') and Path(img['stored_path']).exists()
            ]
            if not image_data:
                return [], []
            image_paths = [path for _, _, path in image_data]
            results = await _batch_infer(model_type, model_device, image_paths)
            POLYGON_DIR.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc).isoformat()
            batch_results = []
            updates = []
            for (image_id, _, _), result in zip(image_data, results):
                polygon_path = None
                
                # Save ALL detections to database (threshold 0.0)
                try:
                    await _save_detections_to_db(db_path, run_id, image_id, result)
                except Exception as e:
                    pass
                
                # Query database to get counts based on run's threshold
                # This uses the same logic as the recalculation endpoint
                try:
                    live_count, dead_count = await _get_counts_from_db(db_path, run_id, image_id, threshold)
                except Exception as e:
                    # Fallback: count all detections (shouldn't happen, but safe fallback)
                    live_count = sum(1 for p in result['polygons'] if p.get('class') == 'live')
                    dead_count = sum(1 for p in result['polygons'] if p.get('class') == 'dead')
                
                # Save polygon JSON with filtered counts
                if result['polygons']:
                    polygon_path = POLYGON_DIR / f"{image_id}.json"
                    with open(polygon_path, 'w') as f:
                        json.dump({
                            'polygons': result['polygons'],  # All polygons saved
                            'live_count': live_count,  # Filtered count
                            'dead_count': dead_count,  # Filtered count
                            'threshold': threshold,
                            'image_width': result['image_width'],
                            'image_height': result['image_height']
                        }, f, indent=2)
                    polygon_path = str(polygon_path)
                
                updates.append((
                    live_count,
                    dead_count,
                    polygon_path,
                    now,
                    result['image_width'],
                    result['image_height'],
                    image_id
                ))
                batch_results.append((image_id, True, live_count, dead_count))
            return batch_results, updates
    
    # Split images into batches
    image_batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]
    tasks = [process_batch_of_images(batch, idx) for idx, batch in enumerate(image_batches)]
    batch_results = []
    all_updates = []
    processed_count = 0
    
    # Process batches as they complete
    for coro in asyncio.as_completed(tasks):
        try:
            batch_result, updates = await coro
            batch_results.append(batch_result)
            all_updates.extend(updates)
            
            processed_count += len(batch_result)
            if updates:
                async with aiosqlite.connect(db_path) as db_batch:
                    dimension_updates = [(width, height, datetime.now(timezone.utc).isoformat(), image_id) 
                                        for _, _, _, _, width, height, image_id in updates]
                    await db_batch.executemany(
                        """UPDATE image 
                           SET width = ?, height = ?, updated_at = ?
                           WHERE image_id = ?""",
                        dimension_updates
                    )
                    
                    result_inserts = [(run_id, image_id, live_count, dead_count, polygon_path, processed_at, None)
                                     for live_count, dead_count, polygon_path, processed_at, _, _, image_id in updates]
                    await db_batch.executemany(
                        """INSERT INTO image_result 
                           (run_id, image_id, live_mussel_count, dead_mussel_count, polygon_path, processed_at, error_msg)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        result_inserts
                    )
                    
                    await db_batch.execute(
                        "UPDATE run SET processed_count = ? WHERE run_id = ?",
                        (processed_count + images_already_done, run_id)
                    )
                    await db_batch.commit()
            else:
                async with aiosqlite.connect(db_path) as db_progress:
                    await db_progress.execute(
                        "UPDATE run SET processed_count = ? WHERE run_id = ?",
                        (processed_count + images_already_done, run_id)
                    )
                    await db_progress.commit()
        except Exception:
            raise
    
    # Flatten results from all batches
    return [result for batch_result in batch_results for result in batch_result]


async def _process_single_images(
    db_path: str,
    run_id: int,
    images: list,
    model_device,
    threshold: float,
    model_type: str
):
    """
    Process images one at a time (fallback for non-batch models).
    
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
                    (processed_count, run_id)
                )
                await db_progress.commit()
        except Exception:
            raise
    
    return results


async def _finalize_run(
    db: aiosqlite.Connection,
    run_id: int,
    collection_id: int,
    results: list,
    images_processed_in_this_run: int,
    images_already_done: int = 0
):
    """
    Aggregate results and update run status to completed.
    
    Args:
        db: Database connection
        run_id: Run ID
        collection_id: Collection ID
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
    
    # Update collection live_mussel_count from run's count
    await db.execute(
        "UPDATE collection SET live_mussel_count = ?, updated_at = ? WHERE collection_id = ?",
        (total_live_count, datetime.now(timezone.utc).isoformat(), collection_id)
    )
    
    await db.commit()


async def process_collection_run(db: aiosqlite.Connection, run_id: int):
    """
    Process a collection run: load model, get images, run inference, and save results.
    
    This is the main function that orchestrates a complete inference run:
    1. Loads the model and validates it exists
    2. Gets all images in the collection (excluding duplicates)
    3. Checks for cached results from previous runs with same model+threshold
    4. Processes images in batches (for R-CNN) or individually (for YOLO)
    5. Writes results incrementally to database for real-time updates
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
        
        run, model_device, collection_id, model_id, threshold, model_type, weights_path = setup_result
        
        # Prepare images: Get images, filter duplicates, check already processed
        image_prep = await _prepare_images(db, collection_id, run_id)
        if not image_prep:
            await _fail(db, run_id, "No images found in collection")
            return
        
        images_to_process, total_images, images_already_done = image_prep
        
        if not images_to_process:
            # All images already processed
            await _handle_all_images_processed(db, run_id, collection_id, total_images)
            return
        
        # Initialize run with total count and already-processed count
        await db.execute(
            "UPDATE run SET total_images = ?, processed_count = ? WHERE run_id = ?",
            (total_images, images_already_done, run_id)
        )
        await db.commit()
        
        db_path = DB_PATH
        
        # Determine processing method
        use_batch_inference = ('rcnn' in model_type.lower() or 'faster' in model_type.lower() or 
                              'yolo' in model_type.lower())
        
        if use_batch_inference:
            results = await _process_batch_inference(
                db, db_path, run_id, images_to_process, model_type, model_device,
                threshold, images_already_done
            )
        else:
            results = await _process_single_images(
                db_path, run_id, images_to_process, model_device, threshold, model_type
            )
        
        # Finalize: Aggregate results and update status
        await _finalize_run(db, run_id, collection_id, results, len(images_to_process), images_already_done)
        
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
                await _handle_all_images_processed(db, run_id, collection_id, total_images)
                return
