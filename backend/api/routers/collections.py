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
        print("hello!!!!")
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
    """
    collection_id = validate_integer_id(collection_id)
    image_id = validate_integer_id(image_id)
    async with get_db() as db:
        if not await get_collection(db, collection_id):
            raise HTTPException(status_code=404, detail="Collection not found")
        if not await remove_image_from_collection(db, collection_id, image_id):
            raise HTTPException(status_code=404, detail="Image not found")
        return {"collection_id": collection_id, "image_id": image_id, "status": "removed"}

