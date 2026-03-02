"""
Image detail API endpoints.

This router handles retrieving detailed information about individual images,
including inference results, polygon data, and metadata.
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from db import get_db
from datetime import datetime, timezone

router = APIRouter(prefix="/api/images", tags=["images"])


class ImageDetailResponse(BaseModel):
    """Detailed response for image with inference results"""
    # Image metadata
    image_id: int
    filename: str
    stored_path: str
    
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
    
    # Polygon data
    polygons: List[Dict[str, Any]]  # Full polygon data with labels and confidence
    detection_count: int  # Number of detections (may differ from counts due to filtering)
    
    # Collection context (helpful for navigation)
    collection_id: int


#When you open an image in the /results page this is called
@router.get("/{image_id}/results", response_model=ImageDetailResponse)
async def get_image_results_endpoint(image_id: int, model_id: int, collection_id: int) -> ImageDetailResponse:
    """
    Get detailed results for a specific image from a specific run.
    
    Returns comprehensive data including:
    - Image metadata (filename and stored path)
    - Mussel counts (live, dead, total, percentages)
    - Polygon data (coordinates, labels, confidence scores)
    - Model information (which model was used, threshold)
    - Collection context (for navigation back to collection/run)
    - Processing metadata (when processed)
    
    Args:
        image_id: ID of the image to get results for
        model_id: ID of the model to get results from
        
    Returns:
        ImageDetailResponse with all image details and inference results
        
    Raises:
        HTTPException 404: If image result not found
        HTTPException 400: If invalid IDs provided
    """
    async with get_db() as db:
        # Get main image and result data
        params = [image_id, model_id, collection_id]
        cursor = await db.execute("""
            SELECT 
                i.image_id,
                i.filename,
                i.stored_path,
                ir.live_mussel_count,
                ir.dead_mussel_count,
                ir.processed_at,
                r.run_id,
                r.collection_id,
                r.threshold,
                r.model_id,
                m.name as model_name,
                m.type as model_type
            FROM image i
            JOIN image_result ir ON i.image_id = ir.image_id
            JOIN run r ON ir.run_id = r.run_id
            JOIN model m ON r.model_id = m.model_id
            WHERE i.image_id = ? AND r.model_id = ?
              AND r.collection_id = ?
            ORDER BY r.run_id DESC
            LIMIT 1
        """, params)
        
        result = await cursor.fetchone()
        
        if not result:
            # No run results found for this image/model/collection.
            # Return a placeholder response with zero counts so the image page can still render.
            # Get basic image metadata scoped to the collection
            image_cursor = await db.execute("""
                SELECT i.image_id, i.filename, i.stored_path, ci.collection_id
                FROM image i
                JOIN collection_image ci ON ci.image_id = i.image_id
                WHERE i.image_id = ? AND ci.collection_id = ?
                LIMIT 1
            """, (image_id, collection_id))
            image_row = await image_cursor.fetchone()

            if not image_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No image {image_id} found in collection {collection_id}"
                )

            # Get model metadata
            model_cursor = await db.execute(
                "SELECT name, type FROM model WHERE model_id = ?",
                (model_id,)
            )
            model_row = await model_cursor.fetchone()
            if not model_row:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

            return ImageDetailResponse(
                image_id=image_row['image_id'],
                filename=image_row['filename'],
                stored_path=image_row['stored_path'],
                run_id=0,
                model_id=model_id,
                model_name=model_row['name'],
                model_type=model_row['type'],
                threshold=0.0,
                live_mussel_count=0,
                dead_mussel_count=0,
                total_mussel_count=0,
                live_percentage=None,
                dead_percentage=None,
                processed_at=datetime.now(timezone.utc).isoformat(),
                polygons=[],
                detection_count=0,
                collection_id=image_row['collection_id'],
            )
        
        # Build polygon payload from detection rows in the database.
        polygons = []
        detections_cursor = await db.execute(
            """
            SELECT detection_id, confidence, class, polygon_coords
            FROM detection
            WHERE run_id = ? AND image_id = ?
            ORDER BY detection_id ASC
            """,
            (result["run_id"], image_id),
        )
        detection_rows = await detections_cursor.fetchall()
        for row in detection_rows:
            coords = []
            if row["polygon_coords"]:
                try:
                    parsed = json.loads(row["polygon_coords"])
                    if isinstance(parsed, list):
                        coords = parsed
                except Exception:
                    coords = []

            stored_class = row["class"]
            manually_edited = stored_class.startswith("edit_")
            polygon = {
                "detection_id": row["detection_id"],
                "coords": coords,
                "class": stored_class.replace("edit_", ""),
                "confidence": row["confidence"],
                "manually_edited": manually_edited,
            }
            polygons.append(polygon)
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
        
        return ImageDetailResponse(
            # Image metadata
            image_id=result['image_id'],
            filename=result['filename'],
            stored_path=result['stored_path'],
            
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
            
            # Polygon data
            polygons=polygons,
            detection_count=detection_count,
            
            # Collection context
            collection_id=result['collection_id'],
        )


#edit endpoint
@router.patch("/{image_id}/results/{model_id}/detections/{detection_id}", response_model=Dict)
async def update_polygon_classification(
    image_id: int,
    model_id: int,
    detection_id: int,
    collection_id: int,
    new_class: str = Body(..., embed=True),
) -> Dict:
    """
    Update the classification of a specific polygon (mussel detection).

    Changes a detection from "live" to "dead" or vice versa by updating the
    detection table's class field (manual override) and recalculating counts.

    Args:
        image_id: ID of the image
        model_id: ID of the model
        detection_id: ID of the detection being edited
        new_class: New classification ("live" or "dead")
        collection_id: ID of the collection

    Returns:
        Updated image result data
    """
    if new_class not in ["live", "dead"]:
        raise HTTPException(status_code=400, detail="Classification must be 'live' or 'dead'")

    async with get_db() as db:
        # Resolve detection on the latest run for this image/model within this collection.
        params = [detection_id, image_id, model_id, collection_id]
        subquery_params = [image_id, model_id, collection_id]

        cursor = await db.execute("""
            SELECT d.detection_id, d.class, d.run_id
            FROM detection d
            JOIN run r ON d.run_id = r.run_id
            WHERE d.detection_id = ?
              AND d.image_id = ?
              AND r.model_id = ?
              AND r.collection_id = ?
              AND d.run_id = (
                  SELECT r2.run_id
                  FROM run r2
                  JOIN detection d2 ON d2.run_id = r2.run_id
                  WHERE d2.image_id = ? AND r2.model_id = ?
                    AND r2.collection_id = ?
                  ORDER BY r2.run_id DESC
                  LIMIT 1
              )
            LIMIT 1
        """, params + subquery_params)

        detection = await cursor.fetchone()
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")

        detection_id = detection['detection_id']
        run_id = detection['run_id']
        current_class = detection['class']
        old_class = current_class.replace("edit_", "")

        if old_class == new_class:
            return {"message": "Classification unchanged", "detection_id": detection_id}

        await db.execute(
            """
            UPDATE detection
            SET class = ?
            WHERE detection_id = ?
            """,
            (f"edit_{new_class}", detection_id),
        )

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
                    WHEN class = 'edit_live' THEN 1
                    WHEN class = 'live' AND confidence >= ? THEN 1
                    ELSE 0
                END) as live_count,
                SUM(CASE
                    WHEN class = 'edit_dead' THEN 1
                    WHEN class = 'dead' AND confidence >= ? THEN 1
                    ELSE 0
                END) as dead_count
            FROM detection
            WHERE image_id = ? AND run_id = ?
        """, (threshold, threshold, image_id, run_id))

        counts = await counts_cursor.fetchone()
        live_count = counts['live_count'] or 0
        dead_count = counts['dead_count'] or 0

        # Update image_result
        now = datetime.now(timezone.utc).isoformat()
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
            "detection_id": detection_id,
            "old_class": old_class,
            "new_class": new_class,
            "live_count": live_count,
            "dead_count": dead_count,
            "total_live": total_live,
            "total_dead": total_dead
        }
