"""
Collection management API endpoints.

This router handles all collection-related operations:
- Creating new collections
- Retrieving collection information and images
- Uploading images to collections
- Removing images from collections

A collection is a collection of images that can be processed together through
inference runs. Images are deduplicated by hash, so the same image file
uploaded multiple times only stores one copy.
"""
from typing import Any, Dict, List
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from db import get_db
from utils.collection_utils import (
    create_collection,
    get_collection,
    get_all_collections,
    get_collection_images,
    get_collection_images_with_results,
    get_latest_run,
    get_all_runs,
    remove_image_from_collection,
)
from utils.image_utils import add_multiple_images_optimized
from utils.file_processing import process_single_file
from utils.validation import validate_file_size, validate_collection_size
from api.schemas import CreateCollectionRequest, CollectionListResponse, UploadResponse
from config import MAX_FILE_SIZE, MAX_COLLECTION_SIZE
from utils.logger import logger
from utils.security import validate_integer_id

# Create router with prefix - all endpoints will be under /api/collections
router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.post("", response_model=Dict[str, int])
async def create_collection_endpoint(request: CreateCollectionRequest) -> Dict[str, int]:
    """
    Create a new collection.
    
    A collection is a container for images that will be processed together.
    Returns the ID of the newly created collection.
    """
    async with get_db() as db:
        collection_id = await create_collection(db, request.name, request.description)
        return {"collection_id": collection_id}


@router.get("", response_model=List[CollectionListResponse])
async def get_all_collections_endpoint() -> List[CollectionListResponse]:
    """
    Get all collections, ordered by creation date (newest first).
    
    Returns a list of all collections in the system.
    """
    async with get_db() as db:
        # Fetch all collections from database (ordered by created_at DESC)
        collections = await get_all_collections(db)
        
        # Convert database rows to validated Pydantic response models
        return [
            CollectionListResponse.model_validate(dict[Any, Any](collection))
            for collection in collections
        ]


@router.get("/{collection_id}", response_model=Dict)
async def get_collection_endpoint(collection_id: int) -> Dict:
    """
    Get detailed information about a specific collection.
    
    Returns:
    - Collection metadata (name, description, etc.)
    - All images in the collection (with latest results if available)
    - Latest run information (if any runs exist)
    - All runs for this collection
    
    If a latest run exists, images include their inference results from that run.
    Otherwise, images are returned without results.
    """
    collection_id = validate_integer_id(collection_id)
    async with get_db() as db:
        collection = await get_collection(db, collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Get latest run to show results from most recent inference
        latest_run = await get_latest_run(db, collection_id)
        if latest_run:
            # If there's a latest run, get images with their results from that run
            latest_run_dict = dict[Any, Any](latest_run)
            images = await get_collection_images_with_results(
                db,
                collection_id,
                latest_run_dict['run_id'],
                latest_run_dict.get('threshold'),  # Filter results by threshold
            )
        else:
            # No runs yet, just get images without results
            images = await get_collection_images(db, collection_id)
        
        # Get all runs for this collection (for showing run history)
        all_runs = await get_all_runs(db, collection_id)
        
        return {
            "collection": dict(collection),
            "images": [dict(img) for img in images],
            "latest_run": dict(latest_run) if latest_run else None,
            "all_runs": [dict(run) for run in all_runs],
        }


@router.get("/{collection_id}/recalculate", response_model=Dict)
async def recalculate_threshold_endpoint(
    collection_id: int,
    threshold: float,
    model_id: int
) -> Dict:
    """
    Recalculate mussel counts for a new threshold without re-running the model.
    
    Updates the run threshold and all image_result counts based on the new threshold value.
    This permanently changes the threshold for the run.

    Args:
        collection_id: ID of the collection
        threshold: New confidence threshold (0.0 - 1.0)
        model_id: Model ID to use for recalculation

    Returns:
        {
            "images": {
                image_id: {"live_count": int, "dead_count": int},
                ...
            },
            "totals": {"live_total": int, "dead_total": int},
            "run_id": int or None
        }
    """
    collection_id = validate_integer_id(collection_id)
    model_id = validate_integer_id(model_id)

    if threshold < 0 or threshold > 1:
        raise HTTPException(status_code=400, detail="Threshold must be between 0 and 1")

    async with get_db() as db:
        # Verify collection exists
        collection = await get_collection(db, collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Find the latest run for this collection with the specified model
        cursor = await db.execute(
            """SELECT run_id FROM run
               WHERE collection_id = ? AND model_id = ?
               ORDER BY run_id DESC LIMIT 1""",
            (collection_id, model_id)
        )
        run_row = await cursor.fetchone()

        if not run_row:
            # No run exists for this model yet
            return {
                "images": {},
                "totals": {"live_total": 0, "dead_total": 0},
                "run_id": None
            }

        run_id = run_row[0]

        # Debug: Check how many detections exist for this run
        debug_cursor = await db.execute(
            "SELECT COUNT(*) FROM detection WHERE run_id = ?",
            (run_id,)
        )
        detection_count = (await debug_cursor.fetchone())[0]
        logger.info(f"[RECALCULATE] Found {detection_count} detections for run {run_id}, updating threshold to {threshold}")

        # Query detections and recalculate counts with new threshold
        # Count logic:
        # - If class IS NOT NULL (manual override), always count it
        # - If class IS NULL (auto mode), count if confidence >= threshold
        cursor = await db.execute(
            """SELECT
                   image_id,
                   SUM(CASE
                       WHEN class = 'live' THEN 1
                       WHEN class IS NULL AND confidence >= ? AND original_class = 'live' THEN 1
                       ELSE 0
                   END) as live_count,
                   SUM(CASE
                       WHEN class = 'dead' THEN 1
                       WHEN class IS NULL AND confidence >= ? AND original_class = 'dead' THEN 1
                       ELSE 0
                   END) as dead_count
               FROM detection
               WHERE run_id = ?
               GROUP BY image_id""",
            (threshold, threshold, run_id)
        )

        rows = await cursor.fetchall()
        logger.info(f"[RECALCULATE] Recalculated counts for {len(rows)} images")

        # Build response and update database
        images_dict = {}
        live_total = 0
        dead_total = 0
        now = datetime.now().isoformat()

        # Update each image_result with new counts
        for row in rows:
            image_id = row[0]
            live_count = row[1] or 0
            dead_count = row[2] or 0

            images_dict[image_id] = {
                "live_count": live_count,
                "dead_count": dead_count
            }

            live_total += live_count
            dead_total += dead_count

            # Update image_result table with new counts
            await db.execute(
                """UPDATE image_result
                   SET live_mussel_count = ?,
                       dead_mussel_count = ?,
                       processed_at = ?
                   WHERE image_id = ? AND run_id = ?""",
                (live_count, dead_count, now, image_id, run_id)
            )

        # Update run threshold and totals
        await db.execute(
            """UPDATE run
               SET threshold = ?,
                   live_mussel_count = ?
               WHERE run_id = ?""",
            (threshold, live_total, run_id)
        )

        await db.commit()
        logger.info(f"[RECALCULATE] Updated run {run_id} threshold to {threshold}, total live: {live_total}, total dead: {dead_total}")

        return {
            "images": images_dict,
            "totals": {
                "live_total": live_total,
                "dead_total": dead_total
            },
            "run_id": run_id
        }


@router.post("/{collection_id}/upload-images", response_model=UploadResponse)
async def upload_images_endpoint(
    collection_id: int,
    files: List[UploadFile] = File(...)
) -> UploadResponse:
    """
    Upload multiple images to a collection.
    
    Process:
    1. Validates collection exists
    2. Validates file count and sizes
    3. Processes each file in parallel (validates, hashes, saves to disk)
    4. Adds images to collection using optimized bulk insert
    5. Handles duplicates (same image already in collection)
    
    Returns:
    - image_ids: All image IDs (including duplicates)
    - added_count: Number of new images actually added
    - duplicate_count: Number of images already in collection
    - duplicate_image_ids: List of duplicate image IDs
    
    Images are deduplicated by MD5 hash, so uploading the same file twice
    only stores one copy but links it to the collection.
    """
    collection_id = validate_integer_id(collection_id)
    try:
        async with get_db() as db:
            # Verify collection exists
            if not await get_collection(db, collection_id):
                raise HTTPException(status_code=404, detail="Collection not found")
            
            # Validate collection size (total number of files)
            validate_collection_size(len(files), MAX_COLLECTION_SIZE)
            
            # Validate each file size
            for file in files:
                if file.size:
                    validate_file_size(file.size, MAX_FILE_SIZE)
            
            # Process all files in parallel for better performance
            # return_exceptions=True allows us to handle individual file errors gracefully
            results = await asyncio.gather(
                *(process_single_file(file, db) for file in files),
                return_exceptions=True,
            )
            
            # Collect successfully processed files
            # Each result is (file_path, filename, file_hash) or None/Exception if invalid
            image_data = []
            for file, result in zip(files, results):
                if isinstance(result, Exception):
                    # Skip files that failed validation
                    continue
                if result:
                    image_data.append(result)
            
            if not image_data:
                raise HTTPException(status_code=400, detail="No valid image files uploaded")
            
            # Bulk add images to collection (handles deduplication and linking)
            # This is optimized to minimize database queries
            image_ids, added_count, duplicate_count, duplicate_image_ids = await add_multiple_images_optimized(
                db, collection_id, image_data
            )
            
            return UploadResponse(
                collection_id=collection_id,
                image_ids=image_ids,
                count=len(image_ids),
                added_count=added_count,
                duplicate_count=duplicate_count,
                duplicate_image_ids=duplicate_image_ids,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload failure for collection %s: %s", collection_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during upload: {exc}")


@router.delete("/{collection_id}/images/{image_id}", response_model=Dict)
async def delete_image_from_collection_endpoint(
    collection_id: int,
    image_id: int
) -> Dict:
    """
    Remove an image from a collection.
    
    Note: This only removes the link between image and collection.
    The image file and its data remain in the database (in case it's used in other collections).
    
    After removal, recalculates mussel counts for all runs that processed this image
    and updates the collection's total count.
    """
    collection_id = validate_integer_id(collection_id)
    image_id = validate_integer_id(image_id)
    async with get_db() as db:
        if not await get_collection(db, collection_id):
            raise HTTPException(status_code=404, detail="Collection not found")
        if not await remove_image_from_collection(db, collection_id, image_id):
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Find all runs that processed this image
        runs_cursor = await db.execute(
            """SELECT DISTINCT run_id FROM image_result WHERE image_id = ?""",
            (image_id,)
        )
        affected_runs = await runs_cursor.fetchall()
        
        # Recalculate counts for each affected run
        for run_row in affected_runs:
            run_id = run_row[0]
            
            # Recalculate totals from remaining image results in this run
            totals_cursor = await db.execute(
                """SELECT 
                       SUM(live_mussel_count) as total_live,
                       SUM(dead_mussel_count) as total_dead
                   FROM image_result
                   WHERE run_id = ?""",
                (run_id,)
            )
            totals = await totals_cursor.fetchone()
            total_live = totals['total_live'] or 0
            
            # Update run totals
            await db.execute(
                """UPDATE run
                   SET live_mussel_count = ?
                   WHERE run_id = ?""",
                (total_live, run_id)
            )
        
        # Update collection's live_mussel_count from latest run (if exists)
        latest_run = await get_latest_run(db, collection_id)
        if latest_run:
            collection_live_count = latest_run['live_mussel_count'] or 0
            await db.execute(
                """UPDATE collection 
                   SET live_mussel_count = ?, updated_at = ?
                   WHERE collection_id = ?""",
                (collection_live_count, datetime.now().isoformat(), collection_id)
            )
        
        await db.commit()
        logger.info(f"Removed image {image_id} from collection {collection_id} and updated counts for {len(affected_runs)} runs")
        
        return {"collection_id": collection_id, "image_id": image_id, "status": "removed"}

