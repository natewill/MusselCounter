import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import aiosqlite
import logging
from utils.model_utils import run_inference_on_image

logger = logging.getLogger(__name__)


async def _record_error(db_path: str, run_id: int, image_id: int, message: str) -> tuple[int, bool, int, int]:
    try:
        async with aiosqlite.connect(db_path) as db:
            now = datetime.now().isoformat()
            await db.execute(
                """INSERT OR REPLACE INTO image_result
                       (run_id, image_id, live_mussel_count, dead_mussel_count, polygon_path, processed_at, error_msg)
                       VALUES (?, ?, 0, 0, NULL, ?, ?)""",
                (run_id, image_id, now, message),
            )
            await db.commit()
    except Exception as exc:  # pragma: no cover - log but continue returning failure tuple
        logger.error("Failed to persist error for image %s: %s", image_id, exc, exc_info=True)
    return (image_id, False, 0, 0)


async def _get_counts_from_db(db_path: str, run_id: int, image_id: int, threshold: float) -> tuple[int, int]:
    """
    Query the database to get live/dead counts for an image based on threshold.
    
    Uses the same logic as the recalculation endpoint:
    - If class IS NOT NULL (manual override), always count it
    - If class IS NULL (auto mode), count if confidence >= threshold
    
    Args:
        db_path: Path to database
        run_id: Run ID
        image_id: Image ID
        threshold: Threshold to filter by
        
    Returns:
        Tuple of (live_count, dead_count)
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT
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
               WHERE run_id = ? AND image_id = ?""",
            (threshold, threshold, run_id, image_id)
        )
        row = await cursor.fetchone()
        live_count = row['live_count'] or 0
        dead_count = row['dead_count'] or 0
        return (live_count, dead_count)


async def _run_inference(model_device, image_path: str, model_type: str):
    """
    Run inference on a single image.
    
    Note: Inference always returns ALL detections (no threshold filtering).
    Counts are calculated by querying the database after detections are saved.
    """
    to_thread = getattr(asyncio, "to_thread", None)
    if to_thread:
        return await to_thread(run_inference_on_image, model_device, image_path, model_type)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_inference_on_image, model_device, image_path, model_type)


def _save_polygons(image_id: int, result: dict, threshold: float) -> Optional[str]:
    if not result.get("polygons"):
        return None
    polygon_dir = Path("data/polygons")
    polygon_dir.mkdir(parents=True, exist_ok=True)
    polygon_path = polygon_dir / f"{image_id}.json"
    with open(polygon_path, "w") as handle:
        json.dump(
            {
                "polygons": result["polygons"],
                "live_count": result["live_count"],
                "dead_count": result["dead_count"],
                "threshold": threshold,
                "image_width": result["image_width"],
                "image_height": result["image_height"],
            },
            handle,
            indent=2,
        )
    return str(polygon_path)


async def _save_detections_to_db(db_path: str, run_id: int, image_id: int, result: dict) -> None:
    """
    Save individual detections to the detection table for threshold recalculation.

    Args:
        db_path: Path to SQLite database
        run_id: ID of the current run
        image_id: ID of the image being processed
        result: Inference result dict containing polygons with confidence scores
    """
    try:
        polygons = result.get("polygons", [])
        if not polygons:
            logger.debug(f"No polygons to save for image {image_id}")
            return

        now = datetime.now().isoformat()
        detection_rows = []

        for polygon in polygons:
            bbox = polygon.get("bbox", [])
            bbox_x1 = bbox[0] if len(bbox) > 0 else None
            bbox_y1 = bbox[1] if len(bbox) > 1 else None
            bbox_x2 = bbox[2] if len(bbox) > 2 else None
            bbox_y2 = bbox[3] if len(bbox) > 3 else None

            detection_rows.append((
                run_id,
                image_id,
                polygon["confidence"],
                polygon["class"],  # original_class
                None,  # class (NULL for auto mode, can be manually overridden later)
                bbox_x1,
                bbox_y1,
                bbox_x2,
                bbox_y2,
                json.dumps(polygon.get("coords", [])),  # polygon_coords as JSON string
                now,
            ))

        async with aiosqlite.connect(db_path) as db:
            await db.executemany(
                """INSERT INTO detection
                   (run_id, image_id, confidence, original_class, class, bbox_x1, bbox_y1, bbox_x2, bbox_y2, polygon_coords, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                detection_rows,
            )
            await db.commit()
            logger.info(f"Saved {len(detection_rows)} detections for image {image_id} in run {run_id}")
    except Exception as exc:
        logger.error(f"Failed to save detections for image {image_id} in run {run_id}: {exc}", exc_info=True)
        # Don't raise - allow processing to continue even if detection saving fails


async def process_image_for_run(
    db_path: str,
    run_id: int,
    image_id: int,
    image_path: str,
    image_filename: str,
    model_device,
    threshold: float,
    model_type: str,
    idx: int,
    total: int,
) -> tuple[int, bool, int, int]:
    try:
        if not Path(image_path).exists():
            return await _record_error(db_path, run_id, image_id, f"Image file not found: {image_path}")
        try:
            result = await _run_inference(model_device, image_path, model_type)
        except Exception as exc:
            logger.error("Inference error for image %s: %s", image_id, exc, exc_info=True)
            return await _record_error(db_path, run_id, image_id, f"Inference error: {exc}")
        
        # Save ALL detections to database (threshold 0.0)
        await _save_detections_to_db(db_path, run_id, image_id, result)

        # Query database to get counts based on run's threshold
        # This uses the same logic as the recalculation endpoint
        try:
            live_count, dead_count = await _get_counts_from_db(db_path, run_id, image_id, threshold)
        except Exception as e:
            logger.error(f"Failed to get counts from DB for image {image_id}: {e}", exc_info=True)
            # Fallback: count all detections (shouldn't happen, but safe fallback)
            live_count = sum(1 for p in result['polygons'] if p.get('class') == 'live')
            dead_count = sum(1 for p in result['polygons'] if p.get('class') == 'dead')
        
        # Save polygon JSON with filtered counts
        polygon_path = _save_polygons(image_id, {**result, 'live_count': live_count, 'dead_count': dead_count}, threshold)

        now = datetime.now().isoformat()
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """UPDATE image SET width = ?, height = ?, updated_at = ? WHERE image_id = ?""",
                (result["image_width"], result["image_height"], now, image_id),
            )
            await db.execute(
                """INSERT OR REPLACE INTO image_result
                   (run_id, image_id, live_mussel_count, dead_mussel_count, polygon_path, processed_at, error_msg)
                   VALUES (?, ?, ?, ?, ?, ?, NULL)""",
                (run_id, image_id, live_count, dead_count, polygon_path, now),
            )
            await db.commit()
        return (image_id, True, live_count, dead_count)
    except Exception as exc:
        logger.error("Error processing image %s: %s", image_id, exc, exc_info=True)
        return await _record_error(db_path, run_id, image_id, f"Processing error: {exc}")

