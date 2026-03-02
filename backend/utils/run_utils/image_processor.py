import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import aiosqlite
from utils.model_utils import run_inference_on_image


async def _record_error(db_path: str, run_id: int, image_id: int, message: str) -> tuple[int, bool, int, int]:
    try:
        async with aiosqlite.connect(db_path) as db:
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """INSERT OR REPLACE INTO image_result
                       (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at, error_msg)
                       VALUES (?, ?, 0, 0, ?, ?)""",
                (run_id, image_id, now, message),
            )
            await db.commit()
    except Exception as exc:  # pragma: no cover - log but continue returning failure tuple
        pass
    return (image_id, False, 0, 0)


async def _get_counts_from_db(db_path: str, run_id: int, image_id: int, threshold: float) -> tuple[int, int]:
    """
    Query the database to get live/dead counts for an image based on threshold.
    
    Uses the same logic as the recalculation endpoint:
    - edit_live / edit_dead always count as edited values
    - live / dead are model values and are threshold filtered
    
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
            return

        now = datetime.now(timezone.utc).isoformat()
        detection_rows = []

        for polygon in polygons:
            detection_rows.append((
                run_id,
                image_id,
                polygon["confidence"],
                polygon["class"],  # live/dead base class from model
                json.dumps(polygon.get("bbox", [])),  # bbox as JSON string [x1, y1, x2, y2]
                now,
            ))

        async with aiosqlite.connect(db_path) as db:
            await db.executemany(
                """INSERT INTO detection
                   (run_id, image_id, confidence, class, bbox, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                detection_rows,
            )
            await db.commit()
    except Exception as exc:
        pass
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
            return await _record_error(db_path, run_id, image_id, f"Inference error: {exc}")
        
        # Save ALL detections to database (threshold 0.0)
        await _save_detections_to_db(db_path, run_id, image_id, result)

        # Query database to get counts based on run's threshold
        # This uses the same logic as the recalculation endpoint
        try:
            live_count, dead_count = await _get_counts_from_db(db_path, run_id, image_id, threshold)
        except Exception as e:
            # Fallback: count all detections (shouldn't happen, but safe fallback)
            live_count = sum(1 for p in result['polygons'] if p.get('class') == 'live')
            dead_count = sum(1 for p in result['polygons'] if p.get('class') == 'dead')
        
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO image_result
                   (run_id, image_id, live_mussel_count, dead_mussel_count, processed_at, error_msg)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (run_id, image_id, live_count, dead_count, now),
            )
            await db.commit()
        return (image_id, True, live_count, dead_count)
    except Exception as exc:
        return await _record_error(db_path, run_id, image_id, f"Processing error: {exc}")
