"""
Collection processing orchestrator for inference runs.

This module orchestrates the complete inference run process:
1. Loads the ML model (R-CNN or YOLO)
2. Retrieves images from the collection
3. Implements smart caching (reuses results from previous runs with same model/threshold)
4. Processes images in batches for efficiency (R-CNN/YOLO) or individually (other models)
5. Writes results incrementally to database for real-time updates
6. Aggregates final counts and updates run status

Key features:
- Real-time updates: Results are written to database as each batch completes
- Smart caching: Reuses results from previous runs when model/threshold match
- Batch processing: Processes multiple images at once for R-CNN/YOLO (much faster)
- Parallel execution: Multiple batches can run concurrently (with concurrency limits)
- Progress tracking: Updates processed_count as images complete
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import aiosqlite
import torch

from config import DB_PATH
from utils.collection_utils import get_collection_images
from utils.model_utils.db import get_model
from utils.model_utils.inference import run_rcnn_inference_batch, run_yolo_inference_batch
from utils.model_utils.loader import load_model
from utils.resource_detector import auto_bs
from .db import get_run, update_run_status
from .image_processor import process_image_for_run

logger = logging.getLogger(__name__)

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
    logger.error(f"[RUN {run_id}] {message}")
    try:
        await update_run_status(db, run_id, status, message)
    except Exception:
        logger.exception(f"[RUN {run_id}] Failed to update status [{status}]")


async def _batch_infer(model_type: str, model_device, image_paths: list[str], threshold: float):
    """
    Run batch inference on multiple images in a background thread.
    
    Args:
        model_type: Type of model ('RCNN', 'YOLO', etc.)
        model_device: Tuple of (model, device) from load_model
        image_paths: List of image file paths
        threshold: Threshold score for classification
        
    Returns:
        List of result dictionaries with live_count, dead_count, polygons, etc.
    """
    fn = run_yolo_inference_batch if 'yolo' in model_type.lower() else run_rcnn_inference_batch
    to_thread = getattr(asyncio, "to_thread", None)
    if to_thread:
        return await to_thread(fn, model_device, image_paths, threshold)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, model_device, image_paths, threshold)


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
        run = await get_run(db, run_id)
        if not run:
            await _fail(db, run_id, "Run not found in database")
            return
        
        collection_id = run['collection_id']
        model_id = run['model_id']
        threshold = run['threshold']
        await update_run_status(db, run_id, 'running')
        
        model_row = await get_model(db, model_id)
        if not model_row:
            await _fail(db, run_id, f"Model {model_id} not found in database")
            return
        
        weights_path = model_row['weights_path']
        model_type = model_row['type']
        
        if not Path(weights_path).exists():
            await _fail(db, run_id, f"Model weights file not found: {weights_path}")
            return
        
        # Get optimal batch size from database (default to 8 if not found)
        try:
            optimal_batch_size = model_row['optimal_batch_size']
        except (KeyError, TypeError):
            optimal_batch_size = 8
        
        try:
            model_device = load_model(weights_path, model_type, optimal_batch_size=optimal_batch_size)
        except Exception as e:
            await _fail(db, run_id, f"Failed to load model: {e}")
            return
        
        # Get all images in the collection
        all_images = await get_collection_images(db, collection_id)
        
        if not all_images:
            await _fail(db, run_id, "No images found in collection")
            return
        
        # Filter out duplicate images (marked with is_duplicate = 1)
        # Duplicates are images that were already in the collection when uploaded
        duplicate_image_ids = set()
        try:
            cursor = await db.execute(
                """SELECT image_id FROM collection_image 
                   WHERE collection_id = ? AND is_duplicate = 1""",
                (collection_id,)
            )
            duplicate_image_ids = {row[0] for row in await cursor.fetchall()}
        except Exception:
            pass
        
        if duplicate_image_ids:
            all_images = [img for img in all_images if img['image_id'] not in duplicate_image_ids]
        
        if not all_images:
            await _fail(db, run_id, "No images to process (all were duplicates)", status='completed')
            return
        
        # Get images that haven't been processed in this run yet
        # Since we now reuse runs, we only process images without results
        cursor = await db.execute(
            """SELECT image_id FROM image_result WHERE run_id = ?""",
            (run_id,)
        )
        already_processed = {row[0] for row in await cursor.fetchall()}
        
        # Only process images without results in this run
        images_to_process = [
            img for img in all_images 
            if img['image_id'] not in already_processed
        ]
        
        if not images_to_process:
            # All images already processed - recalculate totals and mark completed
            cursor = await db.execute(
                """SELECT SUM(live_mussel_count) FROM image_result WHERE run_id = ?""",
                (run_id,)
            )
            row = await cursor.fetchone()
            total_live_count = row[0] or 0
            
            now = datetime.now().isoformat()
            await db.execute(
                """UPDATE run 
                   SET status = 'completed', 
                       finished_at = ?, 
                       total_images = ?,
                       processed_count = ?,
                       live_mussel_count = ?
                   WHERE run_id = ?""",
                (now, len(all_images), len(all_images), total_live_count, run_id)
            )
            # Update collection-level count as well
            await db.execute(
                "UPDATE collection SET live_mussel_count = ?, updated_at = ? WHERE collection_id = ?",
                (total_live_count, now, collection_id)
            )
            await db.commit()
            logger.info(f"[RUN {run_id}] All images already processed")
            return
        
        # Set up for processing
        images = images_to_process
        total_images = len(all_images)  # Total includes both already processed and new
        images_already_done = len(already_processed)
        
        # Initialize run with total count and already-processed count
        await db.execute(
            "UPDATE run SET total_images = ?, processed_count = ? WHERE run_id = ?",
            (total_images, images_already_done, run_id)
        )
        await db.commit()
        
        # Get database path for creating separate connections in parallel processing
        # (needed for thread safety when writing results concurrently)
        db_path = DB_PATH
        
        # Use batch inference for R-CNN and YOLO models (much faster than processing one-by-one)
        # For other model types, fall back to parallel single-image processing
        use_batch_inference = ('rcnn' in model_type.lower() or 'faster' in model_type.lower() or 
                              'yolo' in model_type.lower())
        
        if use_batch_inference:
            # Use cached optimal batch size from model loading
            # Priority: manual override > environment variable > cached auto-detection
            auto_batch_size = model_device[2] if len(model_device) > 2 else 8  # Get cached batch size or fallback
            auto_max_concurrent = 1  # Simple: one batch at a time
            batch_size = MANUAL_BATCH_SIZE or int(os.getenv("INFERENCE_BATCH_SIZE", auto_batch_size))
            max_concurrent_batches = MANUAL_MAX_CONCURRENT_BATCHES or int(os.getenv("MAX_CONCURRENT_BATCHES", auto_max_concurrent))
            logger.info(f"[RUN {run_id}] Using batch_size={batch_size}, max_concurrent={max_concurrent_batches}")
            # Semaphore limits how many batches can run concurrently (prevents memory exhaustion)
            semaphore = asyncio.Semaphore(max_concurrent_batches)
            
            async def process_batch_of_images(batch_images, batch_idx):
                """
                Process a single batch of images: run inference, save polygons, prepare database updates.
                
                Args:
                    batch_images: List of image dictionaries
                    batch_idx: Batch index (for logging)
                    
                Returns:
                    Tuple of (batch_results, updates)
                    - batch_results: List of (image_id, success, live_count, dead_count) tuples
                    - updates: List of tuples for database updates
                """
                async with semaphore:
                    image_data = [
                        (img['image_id'], img.get('filename', 'unknown'), img.get('stored_path'))
                        for img in batch_images
                        if img.get('stored_path') and Path(img['stored_path']).exists()
                    ]
                    if not image_data:
                        return [], []
                    image_paths = [path for _, _, path in image_data]
                    results = await _batch_infer(model_type, model_device, image_paths, threshold)
                    polygon_dir = Path("data/polygons")
                    polygon_dir.mkdir(parents=True, exist_ok=True)
                    now = datetime.now().isoformat()
                    batch_results = []
                    updates = []
                    for (image_id, _, _), result in zip(image_data, results):
                        polygon_path = None
                        if result['polygons']:
                            polygon_path = polygon_dir / f"{image_id}.json"
                            with open(polygon_path, 'w') as f:
                                json.dump({
                                    'polygons': result['polygons'],
                                    'live_count': result['live_count'],
                                    'dead_count': result['dead_count'],
                                    'threshold': threshold,
                                    'image_width': result['image_width'],
                                    'image_height': result['image_height']
                                }, f, indent=2)
                            polygon_path = str(polygon_path)
                        updates.append((
                            result['live_count'],
                            result['dead_count'],
                            polygon_path,
                            now,
                            result['image_width'],
                            result['image_height'],
                            image_id
                        ))
                        batch_results.append((image_id, True, result['live_count'], result['dead_count']))
                    return batch_results, updates
            
            # Split images into batches of the calculated batch_size
            # e.g., if batch_size=4 and we have 10 images: [0:4], [4:8], [8:10]
            image_batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]
            # Create tasks for all batches (they'll run concurrently up to max_concurrent_batches limit)
            # The semaphore inside process_batch_of_images will limit actual concurrency
            tasks = [process_batch_of_images(batch, idx) for idx, batch in enumerate(image_batches)]
            batch_results = []
            all_updates = []
            processed_count = 0
            
            # Process batches as they complete (allows incremental progress updates)
            # as_completed() yields coroutines as they finish, not in order
            # This means we can write results to DB as soon as each batch completes
            for coro in asyncio.as_completed(tasks):
                try:
                    batch_result, updates = await coro
                    batch_results.append(batch_result)
                    all_updates.extend(updates)
                    
                    # Write results to database immediately as each batch completes (for real-time updates)
                    # Combine batch writes and progress update into single connection for efficiency
                    processed_count += len(batch_result)
                    if updates:
                        async with aiosqlite.connect(db_path) as db_batch:
                            dimension_updates = [(width, height, datetime.now().isoformat(), image_id) 
                                                for _, _, _, _, width, height, image_id in updates]
                            await db_batch.executemany(
                                """UPDATE image 
                                   SET width = ?, height = ?, updated_at = ?
                                   WHERE image_id = ?""",
                                dimension_updates
                            )
                            
                            # Insert results into image_result table immediately
                            result_inserts = [(run_id, image_id, live_count, dead_count, polygon_path, processed_at, None)
                                             for live_count, dead_count, polygon_path, processed_at, _, _, image_id in updates]
                            await db_batch.executemany(
                                """INSERT INTO image_result 
                                   (run_id, image_id, live_mussel_count, dead_mussel_count, polygon_path, processed_at, error_msg)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                result_inserts
                            )
                            
                            # Update progress counter in same transaction
                            await db_batch.execute(
                                "UPDATE run SET processed_count = ? WHERE run_id = ?",
                                (processed_count + images_already_done, run_id)
                            )
                            await db_batch.commit()
                    else:
                        # Still update progress even if no results (for error cases)
                        async with aiosqlite.connect(db_path) as db_progress:
                            await db_progress.execute(
                                "UPDATE run SET processed_count = ? WHERE run_id = ?",
                                (processed_count + images_already_done, run_id)
                            )
                            await db_progress.commit()
                except Exception as batch_error:
                    raise  # Re-raise to trigger outer exception handler
            
            # Flatten results from all batches
            results = [result for batch_result in batch_results for result in batch_result]
            
        else:
            # Fallback to parallel single-image processing for non-R-CNN/YOLO models
            max_concurrent = int(os.getenv("MAX_CONCURRENT_IMAGES", "4"))
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(idx, image):
                async with semaphore:
                    image_id = image['image_id']
                    image_filename = image['filename'] if 'filename' in image.keys() else 'unknown'
                    image_path = image['stored_path'] if 'stored_path' in image.keys() else 'unknown'
                    
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
                except Exception as image_error:
                    raise  # Re-raise to trigger outer exception handler
        
        # Aggregate results from newly processed images
        successes = [result for result in results if result[1]]  # Filter successful results
        successful_images = len(successes)
        
        # Get total counts from ALL results in this run (old + new)
        cursor = await db.execute(
            """SELECT SUM(live_mussel_count) FROM image_result WHERE run_id = ?""",
            (run_id,)
        )
        row = await cursor.fetchone()
        total_live_count = row[0] or 0
        
        # Update run with final results
        now = datetime.now().isoformat()
        final_status = 'completed' if successful_images == total_images else 'completed_with_errors'
        
        await db.execute(
            """UPDATE run 
               SET total_images = ?,
                   live_mussel_count = ?,
                   status = ?,
                   finished_at = ?
               WHERE run_id = ?""",
            (total_images, total_live_count, final_status, now, run_id)
        )
        
        # Update collection live_mussel_count from run's count
        await db.execute(
            "UPDATE collection SET live_mussel_count = ?, updated_at = ? WHERE collection_id = ?",
            (total_live_count, datetime.now().isoformat(), collection_id)
        )
        
        await db.commit()
        logger.info(f"[RUN {run_id}] Completed with {total_live_count} live detections")
        
    except Exception as e:
        await _fail(db, run_id, f"Run processing error: {e}")

