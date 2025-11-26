"""
Image detail API endpoints.

This router handles retrieving detailed information about individual images,
including inference results, polygon data, and metadata.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from db import get_db
from utils.security import validate_integer_id
from datetime import datetime

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


@router.patch("/{image_id}/results/{run_id}/polygons/{polygon_index}", response_model=Dict)
async def update_polygon_classification(
    image_id: int,
    run_id: int,
    polygon_index: int,
    new_class: str = Body(..., embed=True)
) -> Dict:
    """
    Update the classification of a specific polygon (mussel detection).

    Changes a detection from "live" to "dead" or vice versa by updating the
    detection table's class field (manual override). Also updates the JSON file
    for backward compatibility and recalculates counts.

    Args:
        image_id: ID of the image
        run_id: ID of the run
        polygon_index: Index of the polygon in the polygons array (0-based)
        new_class: New classification ("live" or "dead")

    Returns:
        Updated image result data
    """
    from utils.security import validate_integer_id

    image_id = validate_integer_id(image_id)
    run_id = validate_integer_id(run_id)

    if new_class not in ["live", "dead"]:
        raise HTTPException(status_code=400, detail="Classification must be 'live' or 'dead'")

    async with get_db() as db:
        # Get the detection by polygon_index (ORDER BY detection_id to match insertion order)
        cursor = await db.execute("""
            SELECT detection_id, original_class, class
            FROM detection
            WHERE image_id = ? AND run_id = ?
            ORDER BY detection_id
            LIMIT 1 OFFSET ?
        """, (image_id, run_id, polygon_index))

        detection = await cursor.fetchone()
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        detection_id = detection['detection_id']
        original_class = detection['original_class']
        current_class = detection['class']

        # Determine what the old effective class was
        old_class = current_class if current_class else original_class

        if old_class == new_class:
            return {"message": "Classification unchanged", "polygon_index": polygon_index}

        # Update detection table
        # If new_class matches original_class, set class=NULL (revert to auto mode)
        # Otherwise, set class=new_class (manual override)
        if new_class == original_class:
            await db.execute("""
                UPDATE detection
                SET class = NULL
                WHERE detection_id = ?
            """, (detection_id,))
        else:
            await db.execute("""
                UPDATE detection
                SET class = ?
                WHERE detection_id = ?
            """, (new_class, detection_id))

        # Also update the JSON file for backward compatibility
        result_cursor = await db.execute("""
            SELECT polygon_path
            FROM image_result
            WHERE image_id = ? AND run_id = ?
        """, (image_id, run_id))

        result = await result_cursor.fetchone()
        if result and result['polygon_path']:
            polygon_path = result['polygon_path']
            polygon_file = Path(polygon_path)
            if polygon_file.exists():
                with open(polygon_path, 'r') as f:
                    polygon_data = json.load(f)

                polygons = polygon_data.get('polygons', [])
                if polygon_index < len(polygons):
                    polygons[polygon_index]['class'] = new_class

                    # Mark as manually edited
                    if 'original_class' not in polygons[polygon_index]:
                        polygons[polygon_index]['original_class'] = old_class
                        polygons[polygon_index]['manually_edited'] = True
                    elif new_class == polygons[polygon_index].get('original_class'):
                        # Reverted to original - remove manual edit markers
                        if 'manually_edited' in polygons[polygon_index]:
                            del polygons[polygon_index]['manually_edited']
                        if 'original_class' in polygons[polygon_index]:
                            del polygons[polygon_index]['original_class']

                    # Recalculate counts for JSON
                    live_count = sum(1 for p in polygons if p['class'] == 'live')
                    dead_count = sum(1 for p in polygons if p['class'] == 'dead')

                    polygon_data['polygons'] = polygons
                    polygon_data['live_count'] = live_count
                    polygon_data['dead_count'] = dead_count

                    with open(polygon_path, 'w') as f:
                        json.dump(polygon_data, f, indent=2)

        # Recalculate counts from detection table
        # This uses the same logic as the recalculation endpoint
        run_cursor = await db.execute("""
            SELECT run_id, threshold FROM run WHERE run_id = ?
        """, (run_id,))
        run_info = await run_cursor.fetchone()
        threshold = run_info['threshold'] if run_info else 0.5

        counts_cursor = await db.execute("""
            SELECT
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
            WHERE image_id = ? AND run_id = ?
        """, (threshold, threshold, image_id, run_id))

        counts = await counts_cursor.fetchone()
        live_count = counts['live_count'] or 0
        dead_count = counts['dead_count'] or 0

        # Update image_result
        now = datetime.now().isoformat()
        await db.execute("""
            UPDATE image_result
            SET live_mussel_count = ?,
                dead_mussel_count = ?,
                processed_at = ?
            WHERE image_id = ? AND run_id = ?
        """, (live_count, dead_count, now, image_id, run_id))

        # Update run totals (recalculate from all image results in this run)
        run_cursor = await db.execute("""
            SELECT SUM(live_mussel_count) as total_live,
                   SUM(dead_mussel_count) as total_dead
            FROM image_result
            WHERE run_id = ?
        """, (run_id,))

        totals = await run_cursor.fetchone()
        total_live = totals['total_live'] or 0
        total_dead = totals['total_dead'] or 0

        await db.execute("""
            UPDATE run
            SET live_mussel_count = ?
            WHERE run_id = ?
        """, (total_live, run_id))

        await db.commit()

        return {
            "message": "Classification updated successfully",
            "polygon_index": polygon_index,
            "detection_id": detection_id,
            "old_class": old_class,
            "new_class": new_class,
            "live_count": live_count,
            "dead_count": dead_count,
            "total_live": total_live,
            "total_dead": total_dead
        }

