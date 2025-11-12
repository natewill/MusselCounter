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


async def _run_inference(model_device, image_path: str, threshold: float, model_type: str):
    to_thread = getattr(asyncio, "to_thread", None)
    if to_thread:
        return await to_thread(run_inference_on_image, model_device, image_path, threshold, model_type)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_inference_on_image, model_device, image_path, threshold, model_type)


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
            result = await _run_inference(model_device, image_path, threshold, model_type)
        except Exception as exc:
            logger.error("Inference error for image %s: %s", image_id, exc, exc_info=True)
            return await _record_error(db_path, run_id, image_id, f"Inference error: {exc}")
        polygon_path = _save_polygons(image_id, result, threshold)
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
                (run_id, image_id, result["live_count"], result["dead_count"], polygon_path, now),
            )
            await db.commit()
        return (image_id, True, result["live_count"], result["dead_count"])
    except Exception as exc:
        logger.error("Error processing image %s: %s", image_id, exc, exc_info=True)
        return await _record_error(db_path, run_id, image_id, f"Processing error: {exc}")

