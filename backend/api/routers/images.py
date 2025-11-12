"""
Image detail API endpoints.

This router handles retrieving detailed information about individual images,
including inference results, polygon data, and metadata.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import get_db
from utils.security import validate_integer_id

router = APIRouter(prefix="/api/images", tags=["images"])


class ImageDetailResponse(BaseModel):
    """Detailed response for image with inference results"""
    # Image metadata
    image_id: int
    filename: str
    stored_path: str
    width: Optional[int]
    height: Optional[int]
    file_hash: str
    created_at: str
    
    # Run/Model info
    run_id: int
    model_id: int
    model_name: str
    model_type: str
    threshold: float
    
    # Results
    live_mussel_count: int
    dead_mussel_count: int
    total_mussel_count: int  # Computed: live + dead
    live_percentage: Optional[float]  # Computed: (live / total) * 100
    dead_percentage: Optional[float]  # Computed: (dead / total) * 100
    processed_at: str
    error_msg: Optional[str]
    
    # Polygon data
    polygons: List[Dict[str, Any]]  # Full polygon data with labels and confidence
    detection_count: int  # Number of detections (may differ from counts due to filtering)
    
    # Collection context (helpful for navigation)
    collection_id: int
    collection_name: Optional[str]
    
    # Other runs on this image (for comparison)
    other_runs: List[Dict[str, Any]]  # Other runs that processed this image


@router.get("/{image_id}/results/{run_id}", response_model=ImageDetailResponse)
async def get_image_results_endpoint(image_id: int, run_id: int) -> ImageDetailResponse:
    """
    Get detailed results for a specific image from a specific run.
    
    Returns comprehensive data including:
    - Image metadata (filename, dimensions, hash, etc.)
    - Mussel counts (live, dead, total, percentages)
    - Polygon data (bounding boxes with coordinates, labels, confidence scores)
    - Model information (which model was used, threshold)
    - Collection context (for navigation back to collection/run)
    - Other runs that processed this image (for comparison)
    - Processing metadata (when processed, errors if any)
    
    Args:
        image_id: ID of the image to get results for
        run_id: ID of the run to get results from
        
    Returns:
        ImageDetailResponse with all image details and inference results
        
    Raises:
        HTTPException 404: If image result not found
        HTTPException 400: If invalid IDs provided
    """
    image_id = validate_integer_id(image_id)
    run_id = validate_integer_id(run_id)
    
    async with get_db() as db:
        # Get main image and result data
        cursor = await db.execute("""
            SELECT 
                i.image_id,
                i.filename,
                i.stored_path,
                i.file_hash,
                i.width,
                i.height,
                i.created_at,
                ir.live_mussel_count,
                ir.dead_mussel_count,
                ir.polygon_path,
                ir.processed_at,
                ir.error_msg,
                r.run_id,
                r.collection_id,
                r.threshold,
                r.model_id,
                m.name as model_name,
                m.type as model_type,
                c.name as collection_name
            FROM image i
            JOIN image_result ir ON i.image_id = ir.image_id
            JOIN run r ON ir.run_id = r.run_id
            JOIN model m ON r.model_id = m.model_id
            LEFT JOIN collection c ON r.collection_id = c.collection_id
            WHERE i.image_id = ? AND ir.run_id = ?
        """, (image_id, run_id))
        
        result = await cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"No results found for image {image_id} in run {run_id}"
            )
        
        # Load polygon data from JSON file
        polygons = []
        detection_count = 0
        if result['polygon_path']:
            polygon_file = Path(result['polygon_path'])
            if polygon_file.exists():
                with open(polygon_file, 'r') as f:
                    polygon_data = json.load(f)
                    polygons = polygon_data.get('polygons', [])
                    detection_count = len(polygons)
        
        # Calculate percentages
        live_count = result['live_mussel_count'] or 0
        dead_count = result['dead_mussel_count'] or 0
        total_count = live_count + dead_count
        
        live_percentage = None
        dead_percentage = None
        if total_count > 0:
            live_percentage = round((live_count / total_count) * 100, 1)
            dead_percentage = round((dead_count / total_count) * 100, 1)
        
        # Get other runs that processed this image (for comparison)
        other_runs_cursor = await db.execute("""
            SELECT 
                r.run_id,
                r.threshold,
                r.status,
                r.started_at,
                m.name as model_name,
                m.type as model_type,
                ir.live_mussel_count,
                ir.dead_mussel_count
            FROM image_result ir
            JOIN run r ON ir.run_id = r.run_id
            JOIN model m ON r.model_id = m.model_id
            WHERE ir.image_id = ? AND r.run_id != ?
            ORDER BY r.started_at DESC
            LIMIT 10
        """, (image_id, run_id))
        
        other_runs = [dict(row) for row in await other_runs_cursor.fetchall()]
        
        return ImageDetailResponse(
            # Image metadata
            image_id=result['image_id'],
            filename=result['filename'],
            stored_path=result['stored_path'],
            file_hash=result['file_hash'],
            width=result['width'],
            height=result['height'],
            created_at=result['created_at'],
            
            # Run/Model info
            run_id=result['run_id'],
            model_id=result['model_id'],
            model_name=result['model_name'],
            model_type=result['model_type'],
            threshold=result['threshold'],
            
            # Results
            live_mussel_count=live_count,
            dead_mussel_count=dead_count,
            total_mussel_count=total_count,
            live_percentage=live_percentage,
            dead_percentage=dead_percentage,
            processed_at=result['processed_at'],
            error_msg=result['error_msg'],
            
            # Polygon data
            polygons=polygons,
            detection_count=detection_count,
            
            # Collection context
            collection_id=result['collection_id'],
            collection_name=result['collection_name'],
            
            # Comparison data
            other_runs=other_runs
        )

